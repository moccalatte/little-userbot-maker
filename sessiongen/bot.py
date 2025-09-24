"""Session generator bot minimal."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (Application, ApplicationBuilder, CallbackContext,
                          CommandHandler, ConversationHandler, MessageHandler,
                          filters)
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SendCodeUnavailableError,
    SessionPasswordNeededError,
)

from common.config import SessionGenSettings
from common.logging_config import forward_to_telegram, setup_logging
from common.masking import mask_phone
from common.storage import SessionRepository
from common.validators import (validate_api_hash, validate_api_id,
                               validate_phone)

from bot.services import LoginContext, SessionFlow, SessionPersister

logger = logging.getLogger("sessiongen")

ASK_PHONE, ASK_API_ID, ASK_API_HASH, WAITING_OTP, WAITING_PASSWORD, ASK_STORE = range(6)


class SessionGeneratorBot:
    def __init__(self, settings: SessionGenSettings) -> None:
        self.settings = settings
        self.logger = setup_logging("sessiongen", settings.log_level, settings.log_dir)
        repo_path = settings.data_dir / "sessions.json"
        self.repo = SessionRepository(repo_path, settings.database_path)
        self.persister = SessionPersister(self.repo, settings.secret_key)

    def build_application(self) -> Application:
        if not self.settings.bot_token:
            raise RuntimeError("SESSIONGEN_BOT_TOKEN belum diisi.")
        app = ApplicationBuilder().token(self.settings.bot_token).build()
        forward_to_telegram(self.logger, self._build_forwarder(app))
        conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone)],
                ASK_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_api_id)],
                ASK_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_api_hash)],
                WAITING_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_otp)],
                WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_password)],
                ASK_STORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_store)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CommandHandler("delete", self.delete_my_sessions)],
        )
        app.add_handler(conv)
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("delete", self.delete_my_sessions))
        return app

    async def start(self, update: Update, context: CallbackContext) -> int:
        await update.message.reply_text(
            "Halo! Kirim nomor teleponmu (format +62...). /cancel untuk batal."
        )
        context.user_data.clear()
        return ASK_PHONE

    async def handle_phone(self, update: Update, context: CallbackContext) -> int:
        try:
            phone = validate_phone(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_PHONE
        context.user_data["phone"] = phone
        await update.message.reply_text("Masukkan API ID.")
        return ASK_API_ID

    async def handle_api_id(self, update: Update, context: CallbackContext) -> int:
        try:
            api_id = validate_api_id(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_API_ID
        context.user_data["api_id"] = api_id
        await update.message.reply_text("Masukkan API hash.")
        return ASK_API_HASH

    async def handle_api_hash(self, update: Update, context: CallbackContext) -> int:
        try:
            api_hash = validate_api_hash(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_API_HASH
        context.user_data["api_hash"] = api_hash
        await self._send_code(update, context)
        await update.message.reply_text("Tulis OTP dari Telegram.")
        return WAITING_OTP

    async def _send_code(self, update: Update, context: CallbackContext) -> None:
        owner_id = update.effective_user.id
        ctx = LoginContext(
            phone=context.user_data["phone"],
            api_id=context.user_data["api_id"],
            api_hash=context.user_data["api_hash"],
            owner_id=owner_id,
            cipher_secret=self.settings.secret_key,
        )
        flow = SessionFlow(ctx)
        context.user_data["flow"] = flow
        try:
            await flow.send_code()
        except FloodWaitError:
            await update.message.reply_text("Flood wait dari Telegram. Coba lagi beberapa menit lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
        except SendCodeUnavailableError:
            await update.message.reply_text(
                "Telegram belum mengirim kode. Tunggu sebentar hingga kode baru muncul."
            )
        except Exception:
            await update.message.reply_text("Gagal mengirim OTP. /start untuk mengulang.")

    async def _resend_code(self, update: Update, context: CallbackContext) -> None:
        flow: SessionFlow = context.user_data.get("flow")
        if not flow:
            return
        try:
            await flow.resend_code()
            await update.message.reply_text("OTP baru diminta. Gunakan kode terbaru yang masuk di Telegram.")
        except FloodWaitError:
            await update.message.reply_text("Telegram meminta kita menunggu sebelum mengirim ulang OTP.")
            await asyncio.sleep(self.settings.rate_limit_interval)
        except SendCodeUnavailableError:
            await update.message.reply_text(
                "Telegram belum bisa mengirim kode baru. Tunggu 1-2 menit sebelum mencoba lagi."
            )
        except Exception:
            await update.message.reply_text("Gagal meminta ulang OTP. /start untuk mencoba lagi nanti.")

    async def handle_otp(self, update: Update, context: CallbackContext) -> int:
        flow: SessionFlow = context.user_data.get("flow")
        if not flow:
            await update.message.reply_text("Sesi belum siap. /start untuk mengulang.")
            return ConversationHandler.END
        raw_code = update.message.text.strip()
        code = "".join(ch for ch in raw_code if ch.isalnum())
        self.logger.info("OTP diterima panjang=%s (raw=%s)", len(code), len(raw_code))
        try:
            session_string = await flow.verify_code(code)
        except SessionPasswordNeededError:
            await update.message.reply_text("Akun ini pakai password 2FA. Kirim passwordnya sekarang.")
            return WAITING_PASSWORD
        except FloodWaitError:
            await update.message.reply_text("Telegram meminta kita menunggu sebelum mencoba lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
            return WAITING_OTP
        except PhoneCodeExpiredError as exc:
            self.logger.debug("OTP expired: %s", exc)
            await update.message.reply_text("Kode OTP kedaluwarsa. Kode baru diminta, gunakan yang terbaru.")
            await self._resend_code(update, context)
            return WAITING_OTP
        except PhoneCodeInvalidError as exc:
            self.logger.debug("OTP invalid: %s", exc)
            await update.message.reply_text("Kode OTP tidak cocok. Pastikan menyalin 5 digit terbaru tanpa spasi.")
            await self._resend_code(update, context)
            return WAITING_OTP
        except Exception:
            await update.message.reply_text("OTP salah. Kirim ulang atau /start untuk ulang.")
            await self._resend_code(update, context)
            return WAITING_OTP
        context.user_data["session_string"] = session_string
        return await self._finalize(update, context)

    async def handle_password(self, update: Update, context: CallbackContext) -> int:
        flow: SessionFlow = context.user_data.get("flow")
        if not flow:
            await update.message.reply_text("Sesi hilang. /start untuk mengulang.")
            return ConversationHandler.END
        password = update.message.text
        try:
            session_string = await flow.verify_password(password)
        except PasswordHashInvalidError:
            await update.message.reply_text("Password 2FA salah. Coba lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
            return WAITING_PASSWORD
        except Exception:
            await update.message.reply_text("Gagal memverifikasi password. /start untuk ulang.")
            return ConversationHandler.END
        context.user_data["session_string"] = session_string
        return await self._finalize(update, context)

    async def _finalize(self, update: Update, context: CallbackContext) -> int:
        session_string = context.user_data["session_string"]
        await update.message.reply_text("Berikut session string-mu:\n" + session_string)
        if self.settings.secret_key:
            await update.message.reply_text("Ingin kusimpan terenkripsi untukmu? (ya/tidak)")
            return ASK_STORE
        await update.message.reply_text("Selesai! Simpan session ini di tempat aman.")
        await self._cleanup(context)
        return ConversationHandler.END

    async def handle_store(self, update: Update, context: CallbackContext) -> int:
        answer = update.message.text.strip().lower()
        if answer not in {"ya", "tidak", "yes", "no"}:
            await update.message.reply_text("Jawab dengan ya atau tidak.")
            return ASK_STORE
        if answer in {"ya", "yes"}:
            try:
                await self._store_session(update, context)
            except Exception as exc:
                self.logger.exception("Gagal simpan session: %s", exc)
                await update.message.reply_text("Tidak bisa menyimpan session. Pastikan SECRET_KEY benar.")
        else:
            await update.message.reply_text("Baik, session tidak disimpan di server.")
        await update.message.reply_text("Selesai! Gunakan /delete jika ingin menghapus data tersimpan.", reply_markup=ReplyKeyboardRemove())
        await self._cleanup(context)
        return ConversationHandler.END

    async def _store_session(self, update: Update, context: CallbackContext) -> None:
        flow: SessionFlow = context.user_data.get("flow")
        if not flow:
            raise RuntimeError("Flow tidak ditemukan.")
        session_string = context.user_data["session_string"]
        metadata = {"telegram_user": update.effective_user.id, "source": "sessiongen"}
        self.persister.store(flow.ctx, session_string, metadata)
        await update.message.reply_text("Session terenkripsi tersimpan.")

    async def delete_my_sessions(self, update: Update, context: CallbackContext) -> int:
        removed = self.persister.delete_owner(update.effective_user.id)
        if removed:
            await update.message.reply_text("Data terenkripsi dihapus.")
        else:
            await update.message.reply_text("Tidak ada data tersimpan.")
        await self._cleanup(context)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext) -> int:
        await update.message.reply_text("Dibatalkan.", reply_markup=ReplyKeyboardRemove())
        await self._cleanup(context)
        return ConversationHandler.END

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text("/start untuk membuat session baru. /delete untuk hapus data.")

    async def _cleanup(self, context: CallbackContext) -> None:
        flow: SessionFlow = context.user_data.get("flow")
        if flow:
            try:
                await flow.client.disconnect()
            except Exception:
                self.logger.debug("Gagal disconnect flow", exc_info=True)
        context.user_data.clear()

    def _build_forwarder(self, app: Application) -> Optional[callable]:
        chat_id = self.settings.telegram_log_chat_id
        if not chat_id:
            return None

        async def _async_send(message: str) -> None:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                self.logger.debug("Gagal forward log", exc_info=True)

        def wrapper(message: str) -> None:
            asyncio.create_task(_async_send(message))

        return wrapper


def run_session_generator(settings: SessionGenSettings) -> None:
    bot = SessionGeneratorBot(settings)
    app = bot.build_application()
    app.run_polling()
