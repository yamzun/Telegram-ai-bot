import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
from openai import OpenAI

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TON_WALLET = os.getenv("PROJECT_TON_WALLET", "UQAAAAAAAAAAAAAAAAAAAA")

client = OpenAI(api_key=OPENAI_API_KEY)

# Payment / Ads gating
UNLOCKED_USERS = set()

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💎 Unlock with TON", callback_data="pay_ton")],
        [InlineKeyboardButton("📺 Watch Ad to Unlock", callback_data="watch_ad")],
        [InlineKeyboardButton("⭐ Unlock with Stars", callback_data="pay_stars")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the AI Bot! 🚀\n\n"
        "Unlock access to chat with the AI:\n\n"
        "💎 **Pay with TON** — Fast, cheap, decentralized\n"
        "📺 **Watch an Ad** — Free, just a few seconds\n"
        "⭐ **Unlock with Stars** — Telegram Stars\n\n"
        "Choose below:",
        reply_markup=reply_markup,
    )

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "pay_ton":
        await query.edit_message_text(
            f"💎 **TON Payment**\n\n"
            f"Send **0.5 TON** to:\n`{TON_WALLET}`\n\n"
            f"After sending, type /unlock with your transaction hash.\n\n"
            f"*This is a demo — replace with real payment verification in production.*"
        )
    elif query.data == "watch_ad":
        UNLOCKED_USERS.add(user_id)
        await query.edit_message_text(
            "📺 **Ad Watched!** ✅\n\n"
            "You now have **30 minutes** of free access.\n"
            "Go ahead and send me a message!"
        )
    elif query.data == "pay_stars":
        await query.edit_message_text(
            "⭐ **Telegram Stars**\n\n"
            "Stars are convenient but take a cut.\n"
            "For better rates, use **TON** instead!\n\n"
            "*Coming soon...*"
        )

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in UNLOCKED_USERS:
        await update.message.reply_text(
            "🔒 Please unlock first using /start"
        )
        return

    user_text = update.message.text
    await update.message.chat.send_action(action="typing")

    try:
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
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again.")

async def unlock(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    UNLOCKED_USERS.add(user_id)
    await update.message.reply_text("✅ **Unlocked!** You now have full access. Send me a message!")

async def start_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started. Polling...")
    await app.run_polling()
