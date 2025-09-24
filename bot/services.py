"""Layanan Telethon untuk wizard bot."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SendCodeUnavailableError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from common.crypto import EncryptionError, build_cipher, encrypt_text
from common.masking import mask_phone
from common.storage import SessionRecord, SessionRepository, hash_phone_for_storage, now_utc

logger = logging.getLogger("bot")


@dataclass(slots=True)
class LoginContext:
    phone: str
    api_id: int
    api_hash: str
    owner_id: int
    cipher_secret: Optional[str]
    account_id: Optional[int] = None


class SessionFlow:
    """Kelola lifecycle login Telethon untuk menghasilkan session string."""

    def __init__(self, ctx: LoginContext) -> None:
        self.ctx = ctx
        self.client = TelegramClient(StringSession(), ctx.api_id, ctx.api_hash)
        self._sent_code = None
        self._session_string: Optional[str] = None

    async def send_code(self) -> None:
        await self.client.connect()
        try:
            self._sent_code = await self._request_code()
            logger.info("Kirim OTP ke %s", mask_phone(self.ctx.phone))
            logger.info(
                "SentCode type=%s hash=%s",
                type(self._sent_code).__name__,
                getattr(self._sent_code, "phone_code_hash", None),
            )
        except FloodWaitError as exc:
            wait_seconds = int(exc.seconds) if hasattr(exc, "seconds") else 60
            logger.warning("Flood wait saat kirim OTP, tidur %s detik", wait_seconds)
            await asyncio.sleep(wait_seconds)
            raise
        except SendCodeUnavailableError as exc:
            logger.warning("OTP tidak tersedia sementara: %s", exc)
            raise
        except Exception:
            logger.exception("Gagal mengirim OTP")
            raise

    async def resend_code(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()
        try:
            self._sent_code = await self._request_code(force_sms=True)
            logger.info("Kirim ulang OTP ke %s", mask_phone(self.ctx.phone))
            logger.info(
                "SentCode (resend) type=%s hash=%s",
                type(self._sent_code).__name__,
                getattr(self._sent_code, "phone_code_hash", None),
            )
        except FloodWaitError as exc:
            wait_seconds = int(exc.seconds) if hasattr(exc, "seconds") else 60
            logger.warning("Flood wait saat kirim ulang OTP, tidur %s detik", wait_seconds)
            await asyncio.sleep(wait_seconds)
            raise
        except SendCodeUnavailableError as exc:
            logger.warning("OTP tidak bisa dikirim ulang saat ini: %s", exc)
            raise
        except Exception:
            logger.exception("Gagal mengirim ulang OTP")
            raise

    async def _request_code(self, *, force_sms: bool = False):
        kwargs: dict = {}
        if force_sms:
            kwargs["force_sms"] = True
        try:
            return await self.client.send_code_request(self.ctx.phone, **kwargs)
        except TypeError:
            if kwargs:
                logger.debug("send_code_request tidak mendukung force_sms, fallback tanpa argumen")
                return await self.client.send_code_request(self.ctx.phone)
            raise

    async def verify_code(self, code: str, password: Optional[str] = None) -> str:
        try:
            if not self.client.is_connected():
                await self.client.connect()
            if not self._sent_code or not getattr(self._sent_code, "phone_code_hash", None):
                logger.warning("phone_code_hash hilang sebelum verifikasi OTP")
            logger.info(
                "Verifikasi OTP panjang=%s hash=%s",
                len(code),
                getattr(self._sent_code, "phone_code_hash", None),
            )
            await self.client.sign_in(
                phone=self.ctx.phone,
                code=code,
                phone_code_hash=getattr(self._sent_code, "phone_code_hash", None),
            )
        except SessionPasswordNeededError:
            if password is None:
                raise
            await self._sign_in_with_password(password)
        except PhoneCodeInvalidError:
            logger.warning("OTP tidak valid untuk %s", mask_phone(self.ctx.phone))
            raise
        except PhoneCodeExpiredError:
            logger.warning("OTP kedaluwarsa untuk %s", mask_phone(self.ctx.phone))
            raise
        except FloodWaitError as exc:
            wait_seconds = int(exc.seconds) if hasattr(exc, "seconds") else 60
            logger.warning("Flood wait saat verifikasi OTP, tidur %s detik", wait_seconds)
            await asyncio.sleep(wait_seconds)
            raise
        except Exception:
            logger.exception("Gagal verifikasi OTP")
            raise
        else:
            await self._finalize_session()
        return self._session_string or ""

    async def _sign_in_with_password(self, password: str) -> None:
        try:
            await self.client.sign_in(password=password)
        except PasswordHashInvalidError:
            logger.warning("Password 2FA salah untuk %s", mask_phone(self.ctx.phone))
            raise
        except Exception:
            logger.exception("Gagal login dengan password 2FA")
            raise
        await self._finalize_session()

    async def verify_password(self, password: str) -> str:
        await self._sign_in_with_password(password)
        return self._session_string or ""

    async def _finalize_session(self) -> None:
        me = await self.client.get_me()
        self.ctx.account_id = getattr(me, "id", None)
        self._session_string = self.client.session.save()
        await self.client.disconnect()
        logger.info("Session Telethon selesai dibuat untuk %s", mask_phone(self.ctx.phone))

    @property
    def session_string(self) -> str:
        if not self._session_string:
            raise RuntimeError("Session belum tersedia.")
        return self._session_string


class QRSessionFlow:
    """Kelola login via QR code Telethon."""

    def __init__(self, ctx: LoginContext) -> None:
        self.ctx = ctx
        self.client = TelegramClient(StringSession(), ctx.api_id, ctx.api_hash)
        self._qr_login = None
        self._session_string: Optional[str] = None

    async def start(self):
        await self.client.connect()
        self._qr_login = await self.client.qr_login()
        logger.info("QR login dimulai (valid hingga %s)", getattr(self._qr_login, "valid_until", "?"))
        return self._qr_login

    async def wait_authorization(self, timeout: int = 180) -> str:
        if not self._qr_login:
            raise RuntimeError("QR login belum dimulai")
        try:
            await self._qr_login.wait(timeout=timeout)
        except SessionPasswordNeededError:
            raise
        except TimeoutError as exc:
            logger.warning("QR login timeout menunggu otorisasi")
            raise exc
        except Exception:
            logger.exception("Gagal menunggu hasil QR login")
            raise
        else:
            await self._finalize_session()
        return self._session_string or ""

    async def recreate(self):
        if not self._qr_login:
            raise RuntimeError("QR login belum dimulai")
        await self._qr_login.recreate()
        logger.info("QR login token diperbarui (valid hingga %s)", getattr(self._qr_login, "valid_until", "?"))
        return self._qr_login

    async def verify_password(self, password: str) -> str:
        try:
            await self.client.sign_in(password=password)
        except PasswordHashInvalidError:
            logger.warning("Password 2FA salah saat QR login")
            raise
        except Exception:
            logger.exception("Gagal login QR dengan password 2FA")
            raise
        await self._finalize_session()
        return self._session_string or ""

    async def _finalize_session(self) -> None:
        me = await self.client.get_me()
        self.ctx.account_id = getattr(me, "id", None)
        self._session_string = self.client.session.save()
        await self.client.disconnect()
        logger.info("Session Telethon via QR selesai dibuat")

    @property
    def session_string(self) -> str:
        if not self._session_string:
            raise RuntimeError("Session belum tersedia.")
        return self._session_string


class SessionPersister:
    """Wrapper penyimpanan terenkripsi opsional."""

    def __init__(self, repo: SessionRepository, secret_key: Optional[str]) -> None:
        self.repo = repo
        self.secret_key = secret_key
        self.cipher = build_cipher(secret_key)

    def store(self, ctx: LoginContext, session_string: str, metadata: Optional[dict] = None) -> str:
        if not self.cipher:
            raise EncryptionError("SECRET_KEY belum diset, tidak bisa menyimpan.")
        encrypted = encrypt_text(self.cipher, session_string)
        metadata = metadata or {}
        if ctx.account_id is not None:
            metadata.setdefault("account_id", ctx.account_id)
        record = SessionRecord(
            phone_hash=hash_phone_for_storage(ctx.phone),
            session=encrypted,
            created_at=now_utc(),
            encrypted=True,
            owner_id=ctx.owner_id,
            account_id=ctx.account_id,
            metadata=metadata,
        )
        self.repo.save(record)
        logger.info("Menyimpan session terenkripsi untuk %s", mask_phone(ctx.phone))
        return encrypted

    def delete_owner(self, owner_id: int) -> int:
        removed = self.repo.delete_by_owner(owner_id)
        logger.info("Menghapus %s session milik user %s", removed, owner_id)
        return removed
