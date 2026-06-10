from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from database import (
    get_stats, get_all_users, get_pending_payments, get_all_cli,
    get_setting, get_payment_methods, get_plans, ban_user,
    add_subscription, revoke_subscription, update_payment_status,
    get_payment_request, add_payment_method, delete_payment_method,
    update_plan_price, set_setting, clear_all_cli, delete_cli
)
import logging

logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Access denied.")
        return
    await show_admin_panel(update.message, context)

async def show_admin_panel(target, context, edit=False):
    stats = get_stats()
    text = (
        f"⚙️ *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: *{stats['total_users']}*\n"
        f"✅ Active Subs: *{stats['active_subs']}*\n"
        f"⏳ Pending Payments: *{stats['pending_payments']}*\n"
        f"📋 CLI Count: *{stats['total_cli']}*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Users", callback_data="adm_users"),
            InlineKeyboardButton("📋 CLI List", callback_data="adm_cli"),
        ],
        [
            InlineKeyboardButton("💳 Payments", callback_data="adm_payments"),
            InlineKeyboardButton("📦 Plans", callback_data="adm_plans"),
        ],
        [
            InlineKeyboardButton("💰 Pay Methods", callback_data="adm_methods"),
            InlineKeyboardButton("⚙️ Settings", callback_data="adm_settings"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ])

    if edit:
        await target.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await target.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Users ────────────────────────────────────────────────
async def show_users(query, context):
    users = get_all_users()
    if not users:
        text = "👥 No users yet."
    else:
        lines = ["👥 *All Users*\n"]
        for u in users[:20]:
            status = "🚫" if u["is_banned"] else "✅"
            uname = f"@{u['username']}" if u["username"] else "No username"
            lines.append(f"{status} `{u['user_id']}` — {u['full_name']} ({uname})")
        if len(users) > 20:
            lines.append(f"\n...and {len(users)-20} more")
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find User", callback_data="adm_find_user"),
         InlineKeyboardButton("➕ Give Sub", callback_data="adm_give_sub")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban_user"),
         InlineKeyboardButton("✅ Unban", callback_data="adm_unban_user")],
        [InlineKeyboardButton("❌ Revoke Sub", callback_data="adm_revoke_sub")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── CLI Management ───────────────────────────────────────
async def show_cli(query, context):
    cli_list = get_all_cli()
    count = len(cli_list)
    preview = ", ".join(cli_list[:30]) if cli_list else "Empty"
    if len(cli_list) > 30:
        preview += f"... (+{len(cli_list)-30} more)"

    text = (
        f"📋 *CLI Management*\n\n"
        f"Total CLIs: *{count}*\n\n"
        f"Preview: `{preview}`"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add CLI", callback_data="adm_add_cli"),
         InlineKeyboardButton("📤 Upload File", callback_data="adm_upload_cli")],
        [InlineKeyboardButton("❌ Delete CLI", callback_data="adm_del_cli"),
         InlineKeyboardButton("🗑 Clear All", callback_data="adm_clear_cli")],
        [InlineKeyboardButton("📋 View All", callback_data="adm_view_cli")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Payments ─────────────────────────────────────────────
async def show_payments(query, context):
    pending = get_pending_payments()
    if not pending:
        text = "💳 *Pending Payments*\n\nNo pending payments! ✅"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        return

    text = f"💳 *Pending Payments* ({len(pending)})\n\n"
    buttons = []
    for p in pending[:10]:
        uname = p["username"] or p["full_name"] or str(p["user_id"])
        buttons.append([
            InlineKeyboardButton(
                f"#{p['id']} {uname} — {p['plan']} ${p['amount']:.2f}",
                callback_data=f"adm_pay_{p['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_payment_detail(query, payment_id):
    p = get_payment_request(payment_id)
    if not p:
        await query.answer("Payment not found")
        return

    text = (
        f"💳 *Payment #{p['id']}*\n\n"
        f"👤 User ID: `{p['user_id']}`\n"
        f"📦 Plan: *{p['plan']}*\n"
        f"💵 Amount: *${p['amount']:.2f}*\n"
        f"💳 Method: *{p['method']}*\n"
        f"🔑 TRX ID: `{p['trx_id']}`\n"
        f"📅 Date: {p['requested_at'][:16]}\n"
        f"📊 Status: *{p['status'].upper()}*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_approve_{payment_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_{payment_id}")
        ],
        [InlineKeyboardButton("🔙 Payments", callback_data="adm_payments")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Settings ─────────────────────────────────────────────
async def show_settings(query, context):
    interval = get_setting("check_interval", "10")
    min_hits = get_setting("min_hits", "4")
    max_hits = get_setting("max_hits", "10")
    top_n = get_setting("top_ranges", "20")
    window = get_setting("window_minutes", "30")
    bot_active = get_setting("bot_active", "1")
    support = get_setting("support_username", "@support")

    status_emoji = "🟢 ON" if bot_active == "1" else "🔴 OFF"

    text = (
        f"⚙️ *Bot Settings*\n\n"
        f"🤖 Bot Status: *{status_emoji}*\n"
        f"⏱ Check Interval: *{interval} min*\n"
        f"📊 Hit Range: *{min_hits} – {max_hits}*\n"
        f"🏆 Top Ranges: *{top_n}*\n"
        f"🕒 Window: *{window} min*\n"
        f"🛠 Support: *{support}*"
    )

    toggle = "🔴 Turn OFF" if bot_active == "1" else "🟢 Turn ON"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏱ Interval ({interval}m)", callback_data="adm_set_interval"),
         InlineKeyboardButton(toggle, callback_data="adm_toggle_bot")],
        [InlineKeyboardButton(f"📊 Min Hits ({min_hits})", callback_data="adm_set_minhits"),
         InlineKeyboardButton(f"📊 Max Hits ({max_hits})", callback_data="adm_set_maxhits")],
        [InlineKeyboardButton(f"🏆 Top N ({top_n})", callback_data="adm_set_topn"),
         InlineKeyboardButton(f"🕒 Window ({window}m)", callback_data="adm_set_window")],
        [InlineKeyboardButton("🛠 Support Link", callback_data="adm_set_support")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Plans ────────────────────────────────────────────────
async def show_plans(query, context):
    plans = get_plans()
    text = "📦 *Subscription Plans*\n\n"
    for p in plans:
        text += f"• {p['name']} ({p['months']}m) — *${p['price']:.2f}*\n"

    buttons = [[InlineKeyboardButton(f"✏️ {p['name']}", callback_data=f"adm_editplan_{p['id']}")] for p in plans]
    buttons.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ─── Payment Methods ──────────────────────────────────────
async def show_methods(query, context):
    methods = get_payment_methods()
    text = "💰 *Payment Methods*\n\n"
    if methods:
        for m in methods:
            text += f"• *{m['name']}*: `{m['details']}`\n"
    else:
        text += "No methods added yet."

    buttons = [
        [InlineKeyboardButton("➕ Add Method", callback_data="adm_add_method"),
         InlineKeyboardButton("❌ Delete Method", callback_data="adm_del_method")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ─── Stats ────────────────────────────────────────────────
async def show_stats(query, context):
    stats = get_stats()
    text = (
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: *{stats['total_users']}*\n"
        f"✅ Active Subscribers: *{stats['active_subs']}*\n"
        f"⏳ Pending Payments: *{stats['pending_payments']}*\n"
        f"📋 CLI in List: *{stats['total_cli']}*"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Broadcast ────────────────────────────────────────────
async def show_broadcast(query, context):
    text = (
        "📢 *Broadcast Message*\n\n"
        "Choose who to send to:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 All Users", callback_data="adm_bc_all"),
         InlineKeyboardButton("✅ Subscribers Only", callback_data="adm_bc_subs")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
