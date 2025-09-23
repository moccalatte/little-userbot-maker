"""State machine percakapan untuk wizard bot."""
from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from pathlib import Path
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

import qrcode

from common.config import BotSettings
from common.logging_config import forward_to_telegram, setup_logging
from common.masking import mask_phone, mask_session
from common.storage import SessionRepository
from common.validators import (validate_api_hash, validate_api_id,
                               validate_phone)

from .services import LoginContext, QRSessionFlow, SessionFlow, SessionPersister

logger = logging.getLogger("bot")

CHOOSE_METHOD, ASK_PHONE, ASK_API_ID, ASK_API_HASH, WAITING_OTP, WAITING_PASSWORD, ASK_STORE, WAITING_QR = range(8)


class WizardBot:
    def __init__(self, settings: BotSettings) -> None:
        self.settings = settings
        self.logger = setup_logging("bot", settings.log_level, settings.log_dir)
        repo_path = settings.data_dir / "sessions.json"
        self.repo = SessionRepository(repo_path)
        self.persister = SessionPersister(self.repo, settings.secret_key)
        self.application: Optional[Application] = None
        self.session_output_file = settings.session_output_file
        self.qr_timeout = settings.qr_timeout

    def build_application(self) -> Application:
        if not self.settings.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi.")
        app = ApplicationBuilder().token(self.settings.bot_token).build()
        forward_to_telegram(self.logger, self._build_log_forwarder(app))
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHOOSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_method_choice)],
                ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone)],
                ASK_API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_api_id)],
                ASK_API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_api_hash)],
                WAITING_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_otp)],
                WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_password)],
                ASK_STORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_store_decision)],
                WAITING_QR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_qr_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CommandHandler("delete", self.delete_my_sessions)],
        )
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("delete", self.delete_my_sessions))
        app.add_handler(CommandHandler("help", self.help_command))
        self.application = app
        return app

    async def start(self, update: Update, context: CallbackContext) -> int:
        await update.message.reply_text(
            "Hai! Aku UserbotMaker. Kita akan membuat Telethon session. Kirim /cancel kapan saja untuk berhenti.\n"
            "Pilih metode login: ketik 'otp' untuk kode verifikasi atau 'qr' untuk scan QR."
        )
        context.user_data.clear()
        return CHOOSE_METHOD

    async def handle_method_choice(self, update: Update, context: CallbackContext) -> int:
        choice = (update.message.text or "").strip().lower()
        if choice not in {"otp", "qr"}:
            await update.message.reply_text("Pilihan tidak dikenal. Ketik 'otp' atau 'qr'.")
            return CHOOSE_METHOD
        context.user_data["method"] = choice
        if choice == "otp":
            await update.message.reply_text("Kirim nomor teleponmu dalam format E.164 (contoh +6281234567890).")
            return ASK_PHONE
        await update.message.reply_text("Baik, kita gunakan QR login. Sekarang kirim API ID (angka).")
        return ASK_API_ID

    async def handle_phone(self, update: Update, context: CallbackContext) -> int:
        if context.user_data.get("method") != "otp":
            await update.message.reply_text("Metode ini tidak membutuhkan nomor telepon. Ketik 'otp' saat memilih metode jika ingin memakai kode SMS.")
            return CHOOSE_METHOD
        try:
            phone = validate_phone(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_PHONE
        context.user_data["phone"] = phone
        await update.message.reply_text("Sip. Sekarang kirim API ID (angka).")
        return ASK_API_ID

    async def handle_api_id(self, update: Update, context: CallbackContext) -> int:
        try:
            api_id = validate_api_id(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_API_ID
        context.user_data["api_id"] = api_id
        await update.message.reply_text("Terima kasih. Terakhir, kirim API hash (32 karakter hex).")
        return ASK_API_HASH

    async def handle_api_hash(self, update: Update, context: CallbackContext) -> int:
        try:
            api_hash = validate_api_hash(update.message.text)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return ASK_API_HASH
        context.user_data["api_hash"] = api_hash
        method = context.user_data.get("method", "otp")
        if method == "qr":
            return await self._initiate_qr_flow(update, context)
        await update.message.reply_text("Kirim OTP yang kamu terima dari Telegram. Jika butuh 2FA, akan kuminta nanti.")
        await self._initiate_flow(update, context)
        return WAITING_OTP

    async def _initiate_flow(self, update: Update, context: CallbackContext) -> None:
        phone = context.user_data["phone"]
        api_id = context.user_data["api_id"]
        api_hash = context.user_data["api_hash"]
        owner_id = update.effective_user.id
        ctx = LoginContext(
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            owner_id=owner_id,
            cipher_secret=self.settings.secret_key,
        )
        flow = SessionFlow(ctx)
        context.user_data["flow"] = flow
        try:
            await flow.send_code()
        except FloodWaitError:
            await update.message.reply_text("Telegram meminta kita menunggu. Coba lagi dalam beberapa menit.")
            await asyncio.sleep(self.settings.rate_limit_interval)
        except SendCodeUnavailableError:
            await update.message.reply_text(
                "Telegram belum mengirim kode. Tunggu 1-2 menit, lalu balas dengan kode saat sudah masuk."
            )
        except Exception:
            await update.message.reply_text("Gagal mengirim OTP. Coba lagi nanti.")
            await asyncio.sleep(self.settings.rate_limit_interval)
        else:
            self.logger.info("Mulai verifikasi OTP untuk %s", mask_phone(phone))

    async def _initiate_qr_flow(self, update: Update, context: CallbackContext) -> int:
        api_id = context.user_data["api_id"]
        api_hash = context.user_data["api_hash"]
        owner_id = update.effective_user.id
        ctx = LoginContext(
            phone=context.user_data.get("phone", ""),
            api_id=api_id,
            api_hash=api_hash,
            owner_id=owner_id,
            cipher_secret=self.settings.secret_key,
        )
        flow = QRSessionFlow(ctx)
        context.user_data["flow"] = flow
        try:
            qr_login = await flow.start()
        except FloodWaitError:
            await update.message.reply_text("Telegram sedang sibuk. Coba lagi beberapa menit lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
            return ConversationHandler.END
        except Exception:
            await update.message.reply_text("Gagal memulai QR login. /start untuk mencoba lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
            return ConversationHandler.END
        self._start_qr_wait(context, flow)
        await self._send_qr(update, qr_login)
        return WAITING_QR

    async def handle_otp(self, update: Update, context: CallbackContext) -> int:
        raw_code = update.message.text.strip()
        code = "".join(ch for ch in raw_code if ch.isalnum())
        self.logger.info("OTP diterima panjang=%s (raw=%s)", len(code), len(raw_code))
        flow: SessionFlow = context.user_data.get("flow")
        if not flow:
            await update.message.reply_text("Flow belum siap. Mulai lagi dengan /start.")
            return ConversationHandler.END
        try:
            session_string = await flow.verify_code(code)
        except SessionPasswordNeededError:
            context.user_data["pending_code"] = code
            await update.message.reply_text("Akun ini memakai password 2FA. Kirim password 2FA sekarang.")
            return WAITING_PASSWORD
        except FloodWaitError:
            await update.message.reply_text("Telegram membatasi percobaan. Tunggu sejenak sebelum mencoba lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
            return WAITING_OTP
        except PhoneCodeExpiredError as exc:
            self.logger.debug("OTP expired: %s", exc)
            await update.message.reply_text("Kode OTP kedaluwarsa. Kode baru sedang diminta, gunakan yang terbaru.")
            await self._resend_code(update, context)
            return WAITING_OTP
        except PhoneCodeInvalidError as exc:
            self.logger.debug("OTP invalid: %s", exc)
            await update.message.reply_text("Kode OTP salah. Pastikan mengetik 5 digit terbaru tanpa spasi.")
            await self._resend_code(update, context)
            return WAITING_OTP
        except Exception:
            await update.message.reply_text("Kode OTP salah atau tidak valid. Coba lagi.")
            attempts = context.user_data.get("otp_attempts", 0) + 1
            context.user_data["otp_attempts"] = attempts
            await self._resend_code(update, context)
            if attempts >= 3:
                await update.message.reply_text("Percobaan terlalu banyak. Ketik /start untuk mengulang dari awal.")
                await self._cleanup_flow(context)
                return ConversationHandler.END
            return WAITING_OTP
        else:
            context.user_data["session_string"] = session_string
            return await self._after_session(update, context)

    async def handle_qr_confirmation(self, update: Update, context: CallbackContext) -> int:
        text = (update.message.text or "").strip().lower()
        self.logger.info("QR confirmation input=%s", text)
        if text in {"retry", "ulang", "qr"}:
            await update.message.reply_text("Menghasilkan QR baru...")
            flow = context.user_data.get("flow")
            if not isinstance(flow, QRSessionFlow):
                await update.message.reply_text("QR login belum aktif. /start untuk memulai lagi.")
                return ConversationHandler.END
            try:
                qr_login = await flow.recreate()
            except Exception:
                await update.message.reply_text("Gagal membuat QR baru. /start untuk mengulang.")
                await self._cleanup_flow(context)
                return ConversationHandler.END
            self._start_qr_wait(context, flow)
            await self._send_qr(update, qr_login)
            return WAITING_QR
        flow = context.user_data.get("flow")
        if not isinstance(flow, QRSessionFlow):
            await update.message.reply_text("QR login belum aktif. Gunakan /start untuk memulai lagi.")
            return ConversationHandler.END
        wait_task = context.user_data.get("qr_task")
        if not wait_task:
            wait_task = self._start_qr_wait(context, flow)
        if not wait_task.done():
            await update.message.reply_text("Menunggu konfirmasi dari Telegram...")
            self.logger.info("Menunggu konfirmasi QR dari Telegram")
        try:
            session_string = await wait_task
        except asyncio.CancelledError:
            await update.message.reply_text("QR login dibatalkan. Balas 'retry' untuk kode baru.")
            return WAITING_QR
        except SessionPasswordNeededError:
            await update.message.reply_text("Akun membutuhkan password 2FA. Kirim password sekarang.")
            context.user_data["qr_task"] = None
            return WAITING_PASSWORD
        except TimeoutError:
            await update.message.reply_text(
                "QR login kedaluwarsa sebelum dipindai. Balas 'retry' untuk QR baru atau /start untuk ulang."
            )
            context.user_data["qr_task"] = None
            return WAITING_QR
        except Exception:
            await update.message.reply_text("QR login gagal. /start untuk mengulang.")
            await self._cleanup_flow(context)
            return ConversationHandler.END
        context.user_data["qr_task"] = None
        context.user_data["session_string"] = session_string
        context.user_data.setdefault("phone", "")
        return await self._after_session(update, context)

    async def handle_password(self, update: Update, context: CallbackContext) -> int:
        password = update.message.text
        flow = context.user_data.get("flow")
        if not flow:
            await update.message.reply_text("Sesi tidak ditemukan. Mulai ulang dengan /start.")
            return ConversationHandler.END
        try:
            session_string = await flow.verify_password(password)
        except PasswordHashInvalidError:
            attempts = context.user_data.get("password_attempts", 0) + 1
            context.user_data["password_attempts"] = attempts
            await update.message.reply_text("Password 2FA salah. Coba lagi.")
            if attempts >= 3:
                await update.message.reply_text("Percobaan terlalu banyak. Mulai ulang dengan /start.")
                return ConversationHandler.END
            await asyncio.sleep(self.settings.rate_limit_interval)
            return WAITING_PASSWORD
        except Exception:
            await update.message.reply_text("Gagal memverifikasi password. Mulai ulang dengan /start.")
            await self._cleanup_flow(context)
            return ConversationHandler.END
        else:
            context.user_data["session_string"] = session_string
            return await self._after_session(update, context)

    async def _after_session(self, update: Update, context: CallbackContext) -> int:
        session_string = context.user_data["session_string"]
        masked_phone = mask_phone(context.user_data.get("phone", ""))
        saved_path = self._write_session_file(session_string)
        await update.message.reply_text(
            "Berhasil! Berikut session string-mu (salin & simpan aman):\n" + session_string
        )
        if saved_path:
            await update.message.reply_text(
                f"Session juga disalin otomatis ke file: {saved_path}"
            )
        await update.message.reply_text(
            "Ingin kusimpan session terenkripsi di sini supaya bisa diambil lagi? (ya/tidak)"
        )
        self.logger.info("Session terkirim ke user %s", masked_phone)
        return ASK_STORE

    async def handle_store_decision(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text.strip().lower()
        if text not in {"ya", "tidak", "no", "yes"}:
            await update.message.reply_text("Jawab dengan ya atau tidak.")
            return ASK_STORE

        if text in {"ya", "yes"}:
            try:
                await self._store_session(update, context)
            except Exception as exc:  # log detail tanpa bocor
                self.logger.exception("Gagal menyimpan session: %s", exc)
                await update.message.reply_text("Gagal menyimpan session. Pastikan SECRET_KEY terpasang.")
        else:
            await update.message.reply_text("Baik, session hanya dikirim di chat ini.")

        await update.message.reply_text(
            "Kapan saja kamu bisa hapus data tersimpan dengan /delete. Terima kasih!", reply_markup=ReplyKeyboardRemove()
        )
        await self._cleanup_flow(context)
        return ConversationHandler.END

    async def _store_session(self, update: Update, context: CallbackContext) -> None:
        flow = context.user_data.get("flow")
        if not flow:
            raise RuntimeError("Flow tidak ditemukan.")
        session_string = context.user_data["session_string"]
        login_ctx = flow.ctx
        metadata = {"telegram_user": update.effective_user.id}
        encrypted = self.persister.store(login_ctx, session_string, metadata)
        masked = mask_session(encrypted)
        self.logger.info("Session terenkripsi disimpan: %s", masked)
        await update.message.reply_text("Session terenkripsi disimpan. Gunakan /delete untuk menghapus kapan saja.")

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text(
            "Gunakan /start untuk memulai wizard. /delete akan menghapus session terenkripsi yang kusimpan."
        )

    async def delete_my_sessions(self, update: Update, context: CallbackContext) -> int:
        removed = self.persister.delete_owner(update.effective_user.id)
        if removed:
            await update.message.reply_text("Data terenkripsi dihapus.")
        else:
            await update.message.reply_text("Tidak ada data yang kusimpan untukmu.")
        return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext) -> int:
        await update.message.reply_text("Wizard dibatalkan. Sampai jumpa!", reply_markup=ReplyKeyboardRemove())
        await self._cleanup_flow(context)
        return ConversationHandler.END

    def _build_log_forwarder(self, app: Application) -> Optional[callable]:
        chat_id = self.settings.telegram_log_chat_id
        if not chat_id:
            return None

        async def _sender(message: str) -> None:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                self.logger.debug("Gagal kirim log ke Telegram", exc_info=True)

        # Bungkus agar cocok dengan handler sinkron
        def send_sync(message: str) -> None:
            asyncio.create_task(_sender(message))

        return send_sync

    async def _cleanup_flow(self, context: CallbackContext) -> None:
        flow = context.user_data.get("flow")
        if flow:
            try:
                await flow.client.disconnect()
            except Exception:
                self.logger.debug("Gagal disconnect client saat cleanup", exc_info=True)
        qr_task = context.user_data.get("qr_task")
        if qr_task:
            qr_task.cancel()
        context.user_data.clear()

    async def _resend_code(self, update: Update, context: CallbackContext) -> None:
        flow = context.user_data.get("flow")
        if not isinstance(flow, SessionFlow):
            return
        try:
            await flow.resend_code()
            await update.message.reply_text("Kirim ulang OTP telah diminta. Gunakan kode terbaru dari Telegram.")
        except FloodWaitError:
            await update.message.reply_text("Telegram membatasi pengiriman ulang. Tunggu sejenak sebelum mencoba lagi.")
            await asyncio.sleep(self.settings.rate_limit_interval)
        except SendCodeUnavailableError:
            await update.message.reply_text(
                "Telegram belum bisa mengirim kode baru. Tunggu 1-2 menit lalu coba lagi."
            )
        except Exception:
            await update.message.reply_text("Gagal meminta ulang OTP. Coba lagi nanti atau mulai ulang dengan /start.")

    def _start_qr_wait(self, context: CallbackContext, flow: QRSessionFlow):
        existing_task = context.user_data.get("qr_task")
        if existing_task:
            existing_task.cancel()
        self.logger.info("Menunggu otorisasi QR dengan timeout %s detik", self.qr_timeout)
        wait_task = asyncio.create_task(self._wait_for_qr(flow))
        context.user_data["qr_task"] = wait_task
        return wait_task

    async def _wait_for_qr(self, flow: QRSessionFlow):
        try:
            return await flow.wait_authorization(timeout=self.qr_timeout)
        except asyncio.CancelledError:
            raise

    def _write_session_file(self, session_string: str) -> Optional[Path]:
        if not self.session_output_file:
            return None
        path = Path(self.session_output_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(session_string, encoding="utf-8")
        except Exception:
            self.logger.exception("Gagal menulis session ke file %s", path)
            return None
        self.logger.info("Session disalin ke file %s", path)
        return path

    async def _send_qr(self, update: Update, qr_login) -> None:
        qr_bytes = self._build_qr_image(qr_login.url)
        await update.message.reply_photo(
            photo=qr_bytes,
            caption=(
                "Scan QR ini lewat aplikasi Telegram: buka Menu → Perangkat → Pindai kode."
                " Setelah Telegram menampilkan tombol 'Masuk', tekan tombol tersebut lalu balas 'done'."
            ),
        )
        await update.message.reply_text(
            "Jika kode habis sebelum discan, balas 'retry' untuk mendapatkan QR baru."
            " Jika kamu tidak melihat tombol 'Masuk', pastikan memakai pemindai bawaan Telegram, bukan kamera biasa."
        )

    def _build_qr_image(self, url: str) -> BytesIO:
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1c274c", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer


def run_bot(settings: BotSettings) -> None:
    bot = WizardBot(settings)
    app = bot.build_application()
    app.run_polling()
