import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from license_gen import generate_license
from keep_alive import keep_alive

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

DEVICE, DAYS = range(2)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "🚫 *Access Denied*\n\nYeh bot sirf authorized admins ke liye hai.\n"
            f"Tumhara ID: `{user.id}`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "╔══════════════════════════════════╗\n"
        "║   🔑 AeroCore License Bot        ║\n"
        "╚══════════════════════════════════╝\n\n"
        "Commands:\n"
        "• /gen — Generate new license\n"
        "• /help — Show help\n"
        "• /status — Bot status\n"
        "• /id — Show your Telegram ID\n"
    )


async def gen_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Access denied.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📱 *Step 1/2:* Enter the *Device ID*\n\n"
        "(Example: `TEST_DEVICE`)\n\nType /cancel to abort.",
        parse_mode="Markdown"
    )
    return DEVICE


async def gen_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    if not device_id:
        await update.message.reply_text("❌ Device ID cannot be empty. Try again:")
        return DEVICE

    context.user_data["device_id"] = device_id
    await update.message.reply_text(
        f"✅ Device: `{device_id}`\n\n"
        "⏱ *Step 2/2:* Enter number of *days* (e.g. `60`, `365`)\n\n"
        "Type /cancel to abort.",
        parse_mode="Markdown"
    )
    return DAYS


async def gen_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
        if days <= 0 or days > 3650:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Invalid. Enter a number between 1 and 3650:")
        return DAYS

    device_id = context.user_data["device_id"]

    try:
        result = generate_license(device_id, days)
    except Exception as e:
        logger.exception("License generation failed")
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode="Markdown")
        return ConversationHandler.END

    msg = (
        "╔══════════════════════════════════╗\n"
        "║   ✅ License Generated           ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"📱 *Device:* `{result['device']}`\n"
        f"⏱ *Days:* `{result['days']}`\n"
        f"🆔 *License ID:* `{result['license_id']}`\n\n"
        "🔑 *License Key:*\n"
        f"`{result['license']}`\n\n"
        "Paste into `AeroConfig.Builder().licenseKey(...)`."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help*\n\n"
        "/gen — Generate a new license\n"
        "/status — Check bot status\n"
        "/id — Get your Telegram ID\n"
        "/cancel — Cancel current operation",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ *Bot Status*\n\n"
        "🟢 Online\n"
        "🔐 Private key loaded: " + ("Yes" if os.environ.get("AEROCORE_PRIVATE_KEY") else "No") + "\n"
        "👤 Admins: " + str(len(ADMIN_IDS))
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Your Telegram ID: `{update.effective_user.id}`",
        parse_mode="Markdown"
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN not set")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("gen", gen_start)],
        states={
            DEVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, gen_device)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, gen_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(conv)

    logger.info("🤖 Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    keep_alive()
    main()
