"""Implementasi !help."""
from __future__ import annotations

import logging

try:
    from .base import CommandContext, CommandSpec
    from .registry import get_commands, register
except ImportError:
    from commands.base import CommandContext, CommandSpec
    from commands.registry import get_commands, register

logger = logging.getLogger("userbot.commands.help")


async def handle_help(ctx: CommandContext, args: list[str]) -> None:
    logger.info("Help command executed by user %s with args: %s", ctx.me_id, args)
    
    commands = get_commands()
    
    if args:
        target = args[0].lower()
        spec = commands.get(target)
        
        if not spec:
            logger.warning("User %s requested help for unknown command: %s", ctx.me_id, target)
            await ctx.reply(
                f"❌ <b>Command '{target}' tidak ditemukan!</b>\n\n"
                "📋 <b>Command yang tersedia:</b>\n" +
                "\n".join([f"• !{name}" for name in sorted(commands.keys())]) +
                "\n\n💡 Gunakan !help <command> untuk detail lengkap"
            )
            return
            
        logger.info("User %s requested help for command: %s", ctx.me_id, target)
        
        # Build detailed help for specific command
        usage_part = f" {spec.usage}" if spec.usage else ""
        lines = [
            f"📖 <b>Help: !{spec.name}</b>\n",
            f"📋 <b>Usage:</b> !{spec.name}{usage_part}",
            f"📝 <b>Description:</b> {spec.description}\n",
            "───────────────────────────"
        ]
        
        help_text = (spec.help_text or "Panduan detail belum tersedia untuk perintah ini.").strip()
        if help_text:
            lines.extend(["", help_text])
        
        # Add quick links to related commands
        lines.extend([
            "\n───────────────────────────",
            "🔗 <b>Related Commands:</b>"
        ])
        
        if target in ["sg", "rg"]:
            lines.extend([
                "• !gg — untuk melihat daftar grup dan ID-nya",
                "• !info — untuk melihat status sistem"
            ])
        elif target == "gg":
            lines.extend([
                "• !sg — untuk broadcast ke grup",
                "• !rg — untuk auto reply di grup"
            ])
        elif target == "info":
            lines.extend([
                "• !rg status — detail reply guard",
                "• !sg status — detail broadcast",
                "• !gg — detail grup membership"
            ])
        else:
            lines.append("• !info — untuk melihat status semua command")
            
        lines.extend([
            "\n💡 <b>Need More Help?</b>",
            "• !help — daftar semua command",
            "• !info — status sistem lengkap"
        ])
        
        await ctx.reply("\n".join(lines))
        return

    logger.info("User %s requested general help", ctx.me_id)
    
    # Build comprehensive help overview
    lines = [
        "📖 <b>UserbotMaker - Command Help</b>\n",
        "🤖 Userbot otomatis untuk manajemen grup Telegram\n",
        "───────────────────────────",
        "\n📋 <b>Available Commands:</b>"
    ]
    
    # Group commands by category
    core_commands = ["help", "info"]
    management_commands = ["gg"]
    automation_commands = ["sg", "rg"]
    
    # Core Commands
    lines.append("\n🔧 <b>Core Commands:</b>")
    for cmd_name in core_commands:
        if cmd_name in commands:
            spec = commands[cmd_name]
            lines.append(f"• !{cmd_name} — {spec.description}")
    
    # Management Commands
    lines.append("\n📊 <b>Management:</b>")
    for cmd_name in management_commands:
        if cmd_name in commands:
            spec = commands[cmd_name]
            lines.append(f"• !{cmd_name} — {spec.description}")
    
    # Automation Commands
    lines.append("\n🤖 <b>Automation:</b>")
    for cmd_name in automation_commands:
        if cmd_name in commands:
            spec = commands[cmd_name]
            lines.append(f"• !{cmd_name} — {spec.description}")
    
    # Quick Start Guide
    lines.extend([
        "\n───────────────────────────",
        "\n🚀 <b>Cara Penggunaan Utama:</b>",
        "\n👉 <b>Untuk User:</b> Gunakan Bot Wizard (interface keyboard)",
        "   • Buka bot wizard Telegram",
        "   • Pilih 'Kelola Userbot' dari keyboard menu",
        "   • Setup semua fitur melalui wizard yang mudah",
        "\n👨‍💻 <b>Untuk Developer/Admin:</b> Manual commands tersedia",
        "   • !info → lihat status semua fitur yang berjalan",
        "   • !gg → melihat semua grup yang diikuti userbot",
        "   • Commands lain untuk debugging dan monitoring",
        "\n💡 <b>Rekomendasi:</b> Gunakan Bot Wizard untuk kemudahan!"
    ])
    
    # Tips and Notes
    lines.extend([
        "\n───────────────────────────",
        "\n💡 <b>Pro Tips:</b>",
        "• 🎆 <b>Cara termudah:</b> Gunakan Bot Wizard dengan interface keyboard!",
        "• Manual commands tersedia untuk advanced users",
        "• Gunakan !help <command> untuk panduan detail command tertentu",
        "• !info untuk melihat status lengkap sistem",
        "\n⚠️ <b>Important Notes:</b>",
        "• Userbot harus menjadi member grup untuk bisa beroperasi",
        "• Beberapa fitur membutuhkan userbot sebagai admin grup",
        "• Rate limit mencegah spam - tunggu beberapa detik antar command",
        "• Backup konfigurasi secara berkala",
        "\n🚀 <b>Quick Start:</b> Buka Bot Wizard → 'Kelola Userbot' → Pilih fitur yang diinginkan!"
    ])
    
    logger.info("General help displayed to user %s (%s commands available)", ctx.me_id, len(commands))
    await ctx.reply("\n".join(lines))


register(
    CommandSpec(
        name="help",
        description="Panduan lengkap dan contoh penggunaan semua command userbot.",
        usage="[command_name]",
        handler=handle_help,
        help_text=(
            "Sistem bantuan komprehensif untuk semua fitur userbot.\n\n"
            "🎯 Cara penggunaan:\n"
            "- !help → tampilkan overview semua command + quick start guide\n"
            "- !help <command> → panduan detail untuk command tertentu\n\n"
            "📋 Yang tersedia di help system:\n"
            "- Daftar semua command dengan deskripsi\n"
            "- Quick start guide untuk pemula\n"
            "- Usage examples dan tips untuk setiap command\n"
            "- Command relationships dan workflow yang disarankan\n"
            "- Best practices dan troubleshooting tips\n\n"
            "📝 Contoh penggunaan:\n"
            "!help → panduan umum + quick start\n"
            "!help sg → detail lengkap broadcast scheduler\n"
            "!help rg → detail lengkap reply guard\n"
            "!help gg → detail lengkap group management\n\n"
            "💡 Tips:\n"
            "- Mulai dengan !help untuk overview sistem\n"
            "- Gunakan !info untuk melihat status aktual sistem\n"
            "- Baca help text sebelum mencoba fitur baru\n"
            "- Help system ini selalu up-to-date dengan fitur terbaru"
        ),
    )
)
