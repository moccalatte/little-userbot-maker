"""Base class for the Telegram bot wizard."""
from __future__ import annotations

import asyncio
from typing import Optional, Callable

from telegram import ReplyKeyboardRemove
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..config import BotSettings, forward_to_telegram, setup_logging
from ..services import SessionFlow, SessionPersister
from ..storage import SessionRepository
from .logging_utils import RealTimeLogger, UserActivityLogger
from .states import (
    ASK_PHONE,
    BROADCAST_CONFIG,
    CHOOSE_METHOD,
    COMMAND_CONFIG,
    COMMAND_LIST,
    COMMAND_SETTINGS,
    GOOGLE_CONFIG,
    MAIN_MENU,
    REPLY_GUARD_CONFIG,
    TOKEN_LOGIN,
    USERBOT_MENU,
    WAITING_OTP,
    WAITING_PASSWORD,
    WAITING_QR,
    WAITING_USER_ID,
    ADMIN_MENU,
)


class WizardBase:
    """Shared bot wiring and helpers."""

    def __init__(self, settings: BotSettings) -> None:
        self.settings = settings
        self.logger = setup_logging("bot", settings.log_level, settings.log_dir)
        self.repo = SessionRepository(settings.database_url)
        self.persister = SessionPersister(self.repo, settings.secret_key)
        self.application: Optional[Application] = None
        self.session_output_file = settings.session_output_file
        self.qr_timeout = settings.qr_timeout

        self.realtime_logger = RealTimeLogger()
        self.activity_logger = UserActivityLogger(settings.log_dir)

        self.realtime_logger.info("🤖 Bot Wizard initialized with real-time logging")

    def build_application(self) -> Application:
        if not self.settings.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi.")

        app = ApplicationBuilder().token(self.settings.bot_token).build()
        forward_to_telegram(self.logger, self._build_log_forwarder(app))

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_main_menu)],
                CHOOSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_method_choice)],
                ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone)],
                WAITING_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_otp)],
                WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_password)],
                WAITING_QR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_qr_confirmation)],
                TOKEN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_token_login)],
                ADMIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_admin_menu)],
                WAITING_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_id_input)],
                USERBOT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_userbot_menu)],
                COMMAND_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_command_list)],
                COMMAND_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_command_settings)],
                COMMAND_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_command_config)],
                GOOGLE_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_google_config)],
                REPLY_GUARD_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reply_guard_config)],
                BROADCAST_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast_config)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("delete", self.delete_my_sessions),
            ],
        )

        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("delete", self.delete_my_sessions))
        app.add_handler(CommandHandler("help", self.help_command))

        self.application = app
        return app

    async def help_command(self, update, context) -> None:  # type: ignore[override]
        await update.message.reply_text(
            "🆘 <b>Bantuan UserbotMaker</b>\n\n"
            "🎯 <b>Cara Penggunaan:</b>\n"
            "• Gunakan tombol keyboard untuk navigasi\n"
            "• Semua fungsi tersedia melalui menu interaktif\n"
            "• Tidak perlu mengetik command manual\n\n"
            "🔄 <b>Restart:</b> Gunakan tombol keyboard untuk kembali ke menu utama\n"
            "🗑️ <b>Hapus Data:</b> Gunakan menu admin atau ketik /delete",
            parse_mode="HTML",
        )

    async def delete_my_sessions(self, update, context) -> int:  # type: ignore[override]
        removed = self.persister.delete_owner(update.effective_user.id)
        if removed:
            await update.message.reply_text("Data terenkripsi dihapus.")
        else:
            await update.message.reply_text("Tidak ada data yang kusimpan untukmu.")
        return ConversationHandler.END

    async def cancel(self, update, context) -> int:  # type: ignore[override]
        await update.message.reply_text(
            "Wizard dibatalkan. Sampai jumpa!",
            reply_markup=ReplyKeyboardRemove(),
        )
        await self._cleanup_flow(context)
        return ConversationHandler.END

    def _build_log_forwarder(self, app: Application) -> Optional[Callable[[str], None]]:
        chat_id = self.settings.telegram_log_chat_id
        if not chat_id:
            return None

        async def _sender(message: str) -> None:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                self.logger.debug("Gagal kirim log ke Telegram", exc_info=True)

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

    async def _resend_code(self, update, context) -> None:  # type: ignore[override]
        flow = context.user_data.get("flow")
        if not isinstance(flow, SessionFlow):
            return

        try:
            await flow.resend_code()
            await update.message.reply_text(
                "Kirim ulang OTP telah diminta. Gunakan kode terbaru dari Telegram.\n"
                "⚠️ INGAT: Gunakan SPASI antar digit. Contoh: '6 5 4 3 2'",
            )
        except Exception as exc:
            await self._handle_resend_error(update, exc)

    async def _handle_resend_error(self, update, exc: Exception) -> None:
        from telethon.errors import FloodWaitError, SendCodeUnavailableError

        if isinstance(exc, FloodWaitError):
            await update.message.reply_text(
                "Telegram membatasi pengiriman ulang. Tunggu sejenak sebelum mencoba lagi.",
            )
            await asyncio.sleep(self.settings.rate_limit_interval)
        elif isinstance(exc, SendCodeUnavailableError):
            await update.message.reply_text(
                "Telegram belum bisa mengirim kode baru. Tunggu 1-2 menit lalu coba lagi.",
            )
        else:
            await update.message.reply_text(
                "Gagal meminta ulang OTP. Coba lagi nanti atau gunakan tombol keyboard untuk kembali ke menu utama.",
            )

