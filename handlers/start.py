from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_user, get_active_subscription, get_user, get_setting
from config import ADMIN_IDS

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)

    is_admin = user.id in ADMIN_IDS
    has_sub = get_active_subscription(user.id)

    sub_status = "✅ Active" if has_sub else "❌ No Subscription"

    text = (
        f"👋 Welcome, *{user.full_name}*!\n\n"
        f"📡 *Orange Carrier Active Range Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Subscription: {sub_status}\n\n"
        f"Use the buttons below to get started."
    )

    keyboard = build_main_keyboard(is_admin, has_sub)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

def build_main_keyboard(is_admin=False, has_sub=None):
    buttons = [
        [InlineKeyboardButton("📡 View Active Ranges", callback_data="view_ranges")],
        [InlineKeyboardButton("💳 Buy Subscription", callback_data="buy_sub")],
        [InlineKeyboardButton("🌐 Our Service", callback_data="our_service"),
         InlineKeyboardButton("🛠 Support", callback_data="support")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
