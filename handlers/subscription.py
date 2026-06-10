from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_plans, get_payment_methods, get_active_subscription, add_payment_request
import logging

logger = logging.getLogger(__name__)

async def subscription_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    sub = get_active_subscription(user.id)

    if sub:
        end_date = sub["end_date"][:10]
        text = (
            f"✅ *You have an active subscription!*\n\n"
            f"📦 Plan: *{sub['plan']}*\n"
            f"📅 Expires: *{end_date}*"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Renew", callback_data="select_plan")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
    else:
        text = "💳 *Buy Subscription*\n\nChoose a plan:"
        keyboard = await build_plans_keyboard()

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def build_plans_keyboard():
    plans = get_plans()
    buttons = []
    for plan in plans:
        buttons.append([
            InlineKeyboardButton(
                f"📦 {plan['name']} — ${plan['price']:.2f}",
                callback_data=f"plan_{plan['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

async def show_plan_detail(query, plan_id):
    from database import get_plans
    plans = get_plans()
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await query.edit_message_text("Plan not found.")
        return

    methods = get_payment_methods()
    if not methods:
        await query.edit_message_text(
            "⚠️ No payment methods available.\nContact support.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="buy_sub")]])
        )
        return

    text = (
        f"📦 *{plan['name']}*\n"
        f"💵 Price: *${plan['price']:.2f}*\n"
        f"📅 Duration: *{plan['months']} month(s)*\n\n"
        f"Choose payment method:"
    )
    buttons = []
    for m in methods:
        buttons.append([
            InlineKeyboardButton(f"💳 {m['name']}", callback_data=f"paymethod_{plan['id']}_{m['id']}")
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="buy_sub")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_payment_details(query, context, plan_id, method_id):
    from database import get_plans, get_payment_methods
    plans = get_plans()
    plan = next((p for p in plans if p["id"] == plan_id), None)

    conn_methods = get_payment_methods()
    method = next((m for m in conn_methods if m["id"] == method_id), None)

    if not plan or not method:
        await query.edit_message_text("Error loading payment details.")
        return

    text = (
        f"💳 *Payment Details*\n\n"
        f"📦 Plan: *{plan['name']}* — ${plan['price']:.2f}\n"
        f"💳 Method: *{method['name']}*\n\n"
        f"📋 *Send payment to:*\n"
        f"`{method['details']}`\n\n"
        f"✅ After payment, send the *Transaction ID* below.\n"
        f"Admin will verify and activate your subscription."
    )

    context.user_data["pending_payment"] = {
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "plan_months": plan["months"],
        "amount": plan["price"],
        "method": method["name"]
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit Transaction ID", callback_data="submit_trx")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"plan_{plan_id}")]
    ])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
