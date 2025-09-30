from __future__ import annotations

"""Shared mixin extracted from the original conversation wizard."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from .states import ADMIN_MENU, ASK_PHONE, CHOOSE_METHOD, MAIN_MENU, TOKEN_LOGIN, USERBOT_MENU


class EntryMixin:
    """Provides conversation handlers from the legacy monolithic module."""

    async def start(self, update: Update, context: CallbackContext) -> int:
        context.user_data.clear()

        # Check if user is admin and has userbot session
        user_id = update.effective_user.id
        is_admin = user_id in self.settings.admin_ids or user_id in self.settings.owner_ids
        has_userbot = self.repo._database.has_active_userbot_session(user_id)

        # Log user activity dengan real-time display
        self.realtime_logger.info(
            "👤 User %s (@%s) started bot - Admin: %s, Has Userbot: %s", 
            user_id, update.effective_user.username or "N/A", is_admin, has_userbot
        )

        self.activity_logger.log_user_activity(
            user_id, 
            "start_command", 
            {
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "is_admin": is_admin,
                "has_userbot": has_userbot
            }
        )

        # Build main menu keyboard with ReplyKeyboardMarkup
        keyboard = [
            [KeyboardButton("🤖 Buat Userbot"), KeyboardButton("🔑 Token Login")]
        ]

        # Add userbot management for existing userbot owners
        if has_userbot:
            keyboard.append([KeyboardButton("⚙️ Kelola Userbot")])

        # Add admin row if user is admin
        if is_admin:
            keyboard.append([KeyboardButton("🔧 Admin Settings")])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "👋 Hai! Selamat datang di UserbotMaker.\n\n"
            "🔰 Aku dapat membantu kamu membuat dan mengelola userbot Telegram.\n"
            "👇 Pilih opsi di keyboard bawah:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        return MAIN_MENU

    async def handle_main_menu(self, update: Update, context: CallbackContext) -> int:
        """Handle main menu button presses."""
        text = update.message.text.strip()
        user_id = update.effective_user.id

        # Log menu navigation
        self.activity_logger.log_menu_navigation(
            user_id, "main_menu", text, "button_press"
        )

        if text == "🤖 Buat Userbot":
            # Build method choice keyboard
            method_keyboard = [
                [KeyboardButton("📱 OTP"), KeyboardButton("📷 QR")],
                [KeyboardButton("🔙 Back to Main")]
            ]
            reply_markup = ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "🤖 Mari kita buat userbot Telegram!\n\n"
                "Pilih metode login:\n"
                "• <b>📱 OTP</b>: Login dengan nomor HP + kode SMS\n"
                "• <b>📷 QR</b>: Login dengan scan QR code (seperti WhatsApp Web)\n\n"
                "👇 Pilih dari keyboard di bawah:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return CHOOSE_METHOD

        elif text == "🔑 Token Login":
            await update.message.reply_text(
                "🔑 <b>Token Login</b>\n\n"
                "Jika kamu sudah punya session string Telegram, kirim session string tersebut sekarang.\n\n"
                "⚠️ <b>PENTING</b>: Session string adalah data sensitif. Pastikan kamu percaya dengan bot ini.\n\n"
                "Session string biasanya dimulai dengan '1ApWap' atau similar.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )
            return TOKEN_LOGIN

        elif text == "⚙️ Kelola Userbot":
            user_id = update.effective_user.id

            # Verify user has userbot session
            if not self.repo._database.has_active_userbot_session(user_id):
                await update.message.reply_text(
                    "❌ Kamu belum memiliki userbot aktif.\n\n"
                    "Silahkan buat userbot terlebih dahulu melalui menu '🤖 Buat Userbot'."
                )
                return MAIN_MENU

            # Get user session info for display
            session_info = self.repo._database.get_user_session_info(user_id)
            userbot_name = session_info.get('first_name', 'Unknown') if session_info else 'Unknown'
            username = session_info.get('username', 'N/A') if session_info else 'N/A'

            # Build userbot management keyboard
            userbot_keyboard = [
                [KeyboardButton("📋 Lihat Commands"), KeyboardButton("⚡ Kelola Commands")],
                [KeyboardButton("📊 Status Userbot"), KeyboardButton("🔄 Restart Userbot")],
                [KeyboardButton("🔙 Back to Main"), KeyboardButton("🏠 Back to Main Menu")]
            ]
            reply_markup = ReplyKeyboardMarkup(userbot_keyboard, resize_keyboard=True)

            await update.message.reply_text(
                f"⚙️ <b>Kelola Userbot</b>\n\n"
                f"👤 <b>Userbot</b>: {userbot_name} (@{username})\n"
                f"🆔 <b>User ID</b>: {user_id}\n\n"
                "🎮 <b>Menu Kelola Userbot:</b>\n"
                "• 📋 <b>Lihat Commands</b> - Daftar semua command tersedia\n"
                "• ⚡ <b>Kelola Commands</b> - Enable/disable commands\n"
                "• 📊 <b>Status Userbot</b> - Info status userbot\n"
                "• 🔄 <b>Restart Userbot</b> - Restart userbot session\n\n"
                "👇 Pilih opsi di keyboard bawah:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return USERBOT_MENU

        elif text == "🔧 Admin Settings":
            user_id = update.effective_user.id
            if user_id not in self.settings.owner_ids and user_id not in self.settings.admin_ids:
                await update.message.reply_text("❌ Akses ditolak. Kamu bukan admin.")
                return ConversationHandler.END

            # Build admin keyboard
            admin_keyboard = [
                [KeyboardButton("🗑️ Clean Database"), KeyboardButton("📊 Database Stats")],
                [KeyboardButton("👥 List Sessions"), KeyboardButton("🔍 Debug Report")],
                [KeyboardButton("🚑 Health Check"), KeyboardButton("📈 Performance Logs")],
                [KeyboardButton("🧪 Automated Testing")],
                [KeyboardButton("🔙 Back to Main")]
            ]
            reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "🔧 <b>Admin Settings</b>\n\n"
                "Pilih opsi admin di bawah:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return ADMIN_MENU

        # Unknown command
        await update.message.reply_text(
            "❌ Perintah tidak dikenali. Pilih salah satu opsi dari keyboard di bawah."
        )
        return MAIN_MENU

    async def handle_method_choice(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text.strip()
        user_id = update.effective_user.id

        # Log user activity
        self.activity_logger.log_user_activity(
            user_id, "method_choice", {"choice": text}
        )

        # Handle back to main
        if text == "🔙 Back to Main":
            return await self.start(update, context)

        # Handle method choices
        if text == "📱 OTP":
            context.user_data["method"] = "otp"
            await update.message.reply_text(
                "📱 <b>OTP Login</b>\n\n"
                "Kirim nomor teleponmu dalam format E.164\n"
                "Contoh: +6281234567890",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )
            return ASK_PHONE

        elif text == "📷 QR":
            context.user_data["method"] = "qr"
            await update.message.reply_text(
                "📷 <b>QR Login</b>\n\n"
                "Baik, kita gunakan QR login. Sedang menyiapkan QR...",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )
            return await self._initiate_qr_flow(update, context)

        # Handle legacy text input (otp/qr) for backward compatibility
        choice = text.lower()
        if choice in {"otp", "qr"}:
            context.user_data["method"] = choice
            if choice == "otp":
                await update.message.reply_text(
                    "Kirim nomor telefonmu dalam format E.164 (contoh +6281234567890).",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ASK_PHONE
            await update.message.reply_text(
                "Baik, kita gunakan QR login. Sedang menyiapkan QR...",
                reply_markup=ReplyKeyboardRemove()
            )
            return await self._initiate_qr_flow(update, context)

        # Unknown choice
        await update.message.reply_text(
            "❌ Pilihan tidak dikenal. Pilih salah satu dari keyboard di bawah."
        )
        return CHOOSE_METHOD
