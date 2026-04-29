import os
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ── Validate env vars on startup ──────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TON_WALLET = os.getenv("PROJECT_TON_WALLET", "UQB-Yx35w5jOtcJ26z3aGY-NxCASWHr3m15Q8IpMyrCcWkm8")

missing = []
if not TELEGRAM_TOKEN:
    missing.append("TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    missing.append("OPENAI_API_KEY")

if missing:
    logger.error(f"FATAL: Missing env vars: {', '.join(missing)}")
    logger.error("Set them in Render Dashboard -> Environment -> Add Variable")
    sys.exit(1)

logger.info(f"TELEGRAM_BOT_TOKEN: set ({TELEGRAM_TOKEN[:8]}...)")
logger.info(f"OPENAI_API_KEY: set ({OPENAI_API_KEY[:8]}...)")
logger.info(f"PROJECT_TON_WALLET: {TON_WALLET[:12]}...")

# ── Lazy init (won't crash if import-time issues) ────────────────────────
_client = None
def get_openai_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

# Payment / Ads gating
UNLOCKED_USERS = set()

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("\U0001f4a9 Unlock with TON", callback_data="pay_ton")],
        [InlineKeyboardButton("\U0001f4fa Watch Ad to Unlock", callback_data="watch_ad")],
        [InlineKeyboardButton("\u2b50 Unlock with Stars", callback_data="pay_stars")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the AI Bot! \U0001f680\n\n"
        "Unlock access to chat with the AI:\n\n"
        "\U0001f4a9 **Pay with TON** \u2014 Fast, cheap, decentralized\n"
        "\U0001f4fa **Watch an Ad** \u2014 Free, just a few seconds\n"
        "\u2b50 **Unlock with Stars** \u2014 Telegram Stars\n\n"
        "Choose below:",
        reply_markup=reply_markup,
    )

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "pay_ton":
        await query.edit_message_text(
            f"\U0001f4a9 **TON Payment**\n\n"
            f"Send **0.5 TON** to:\n`{TON_WALLET}`\n\n"
            f"After sending, type /unlock with your transaction hash.\n\n"
            f"*In production this verifies via TON API.*"
        )
    elif query.data == "watch_ad":
        UNLOCKED_USERS.add(user_id)
        await query.edit_message_text(
            "\U0001f4fa **Ad Watched!** \u2705\n\n"
            "You now have **30 minutes** of free access.\n"
            "Go ahead and send me a message!"
        )
    elif query.data == "pay_stars":
        await query.edit_message_text(
            "\u2b50 **Telegram Stars**\n\n"
            "Stars are convenient but take a cut.\n"
            "For better rates, use **TON** instead!\n\n"
            "*Coming soon...*"
        )

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in UNLOCKED_USERS:
        await update.message.reply_text(
            "\U0001f512 Please unlock first using /start"
        )
        return

    user_text = update.message.text
    await update.message.chat.send_action(action="typing")

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": user_text},
            ],
            max_tokens=500,
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("\u274c Sorry, something went wrong. Please try again.")

async def unlock(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    UNLOCKED_USERS.add(user_id)
    await update.message.reply_text("\u2705 **Unlocked!** You now have full access. Send me a message!")

async def start_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started. Polling...")
    await app.run_polling()
