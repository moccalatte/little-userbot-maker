from __future__ import annotations

"""Shared mixin extracted from the original conversation wizard."""

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from ..utils import mask_phone, mask_session


class SessionMixin:
    """Provides conversation handlers from the legacy monolithic module."""

    async def _after_session(self, update: Update, context: CallbackContext) -> int:
        session_string = context.user_data["session_string"]
        masked_phone = mask_phone(context.user_data.get("phone", ""))
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        await update.message.reply_text(
            "✅ <b>Session berhasil dibuat!</b>\n\n"
            f"📱 Session string:\n<code>{session_string}</code>\n\n"
            "⚠️ <b>PENTING</b>: Simpan session string ini di tempat yang aman!",
            parse_mode='HTML'
        )

        self.logger.info("Session berhasil dibuat untuk user %s", masked_phone or f"ID:{user_id}")

        # Log successful session creation with method details
        method = context.user_data.get("method", "unknown")
        self.activity_logger.log_session_creation(
            user_id, method, True,
            {
                "username": update.effective_user.username,
                "first_name": user_name,
                "phone": masked_phone,
                "session_method": method
            }
        )

        if self.settings.secret_key:
            try:
                await self._store_session(update, context)
                self.logger.info("Session tersimpan terenkripsi untuk user %s", user_id)
            except Exception as exc:  # log detail tanpa bocor
                self.logger.exception("Gagal menyimpan session untuk user %s: %s", user_id, exc)
        else:
            self.logger.warning("SECRET_KEY kosong; session tidak disimpan terenkripsi untuk user %s", user_id)

        # Send welcome message for new userbot owner
        welcome_message = (
            f"🎉 <b>Selamat {user_name}! Kamu sekarang sudah menjadi Userbot Owner!</b>\n\n"
            "🚀 <b>Userbot kamu sudah aktif dan siap digunakan!</b>\n\n"
            "📋 <b>Langkah selanjutnya:</b>\n"
            "1️⃣ Test dan kelola userbot:\n"
            "   • Userbot akan bekerja otomatis di chat\n"
            "   • Gunakan menu 'Kelola Userbot' untuk setup\n\n"
            "2️⃣ Kelola Command & Settings:\n"
            "   • Gunakan menu <b>'⚙️ Kelola Userbot'</b> di bot ini\n"
            "   • Lihat semua command yang tersedia\n"
            "   • Monitor status userbot\n\n"
            "💡 <b>Tips:</b>\n"
            "• Userbot bekerja otomatis tanpa input manual\n"
            "• Bot wizard ini untuk manajemen, userbot untuk automation\n"
            "• Session disimpan terenkripsi dan aman\n\n"
            "🔄 <b>Untuk kembali ke menu utama, gunakan tombol keyboard yang tersedia</b>\n\n"
            "✨ <b>Selamat menggunakan UserbotMaker!</b> ✨"
        )

        await update.message.reply_text(welcome_message, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        await self._cleanup_flow(context)
        return ConversationHandler.END

    async def _store_session(self, update: Update, context: CallbackContext) -> None:
        flow = context.user_data.get("flow")
        if not flow:
            raise RuntimeError("Flow tidak ditemukan.")

        user_id = update.effective_user.id
        method = context.user_data.get("method", "unknown")

        # Check if user has existing sessions and remove them first
        existing_sessions = self.persister.repo.list_by_owner(user_id)
        if existing_sessions:
            deleted_count = self.persister.repo.delete_by_owner(user_id)
            self.logger.info(
                "Session creation: Replaced %d existing sessions for user %s", 
                deleted_count, user_id
            )
            self.activity_logger.log_user_activity(
                user_id, "session_replacement", 
                {"deleted_sessions": deleted_count, "method": method}
            )

        session_string = context.user_data["session_string"]
        login_ctx = flow.ctx
        metadata = {
            "telegram_user": user_id,
            "username": update.effective_user.username,
            "method": method,
            "replaced_existing": len(existing_sessions) > 0
        }
        encrypted = self.persister.store(login_ctx, session_string, metadata)
        masked = mask_session(encrypted);
        self.logger.info("Session terenkripsi disimpan: %s", masked)
