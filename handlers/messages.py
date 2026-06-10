from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_cli, delete_cli, set_setting, add_payment_method,
    update_plan_price, ban_user, add_subscription, revoke_subscription,
    add_payment_request, get_all_users, get_active_subscribers,
    get_plans, get_user
)
from config import ADMIN_IDS
from handlers.admin import is_admin
import logging, io

logger = logging.getLogger(__name__)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get("state")
    text = update.message.text or ""

    # ─── File Upload (CLI) ───────────────────────────────
    if update.message.document and state == "waiting_cli_file":
        await handle_cli_file(update, context)
        return

    if not state:
        return

    # ─── Transaction ID Submission ───────────────────────
    if state == "waiting_trx":
        pending = context.user_data.get("pending_payment")
        if not pending:
            await update.message.reply_text("❌ Session expired. Please start again.")
            context.user_data.clear()
            return

        trx_id = text.strip()
        add_payment_request(
            user.id, pending["plan_name"], pending["amount"],
            pending["method"], trx_id
        )

        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"💳 *New Payment Request!*\n\n"
                    f"👤 User: {user.full_name} (`{user.id}`)\n"
                    f"📦 Plan: *{pending['plan_name']}*\n"
                    f"💵 Amount: *${pending['amount']:.2f}*\n"
                    f"💳 Method: *{pending['method']}*\n"
                    f"🔑 TRX ID: `{trx_id}`\n\n"
                    f"Go to Admin Panel → Payments to approve.",
                    parse_mode="Markdown"
                )
            except: pass

        await update.message.reply_text(
            f"✅ *Payment submitted!*\n\n"
            f"TRX ID: `{trx_id}`\n\n"
            f"Admin will verify and activate your subscription shortly.",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return

    # ─── Admin: Add CLI ───────────────────────────────────
    if state == "waiting_add_cli" and is_admin(user.id):
        import re
        raw = text.replace("\n", ",").replace(";", ",")
        prefixes = [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]
        count = 0
        for p in prefixes:
            add_cli(p)
            count += 1
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 CLI List", callback_data="adm_cli")]])
        await update.message.reply_text(f"✅ Added *{count}* CLI prefix(es)!", parse_mode="Markdown", reply_markup=keyboard)
        context.user_data.clear()

    # ─── Admin: Delete CLI ────────────────────────────────
    elif state == "waiting_del_cli" and is_admin(user.id):
        prefix = text.strip()
        delete_cli(prefix)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 CLI List", callback_data="adm_cli")]])
        await update.message.reply_text(f"✅ Deleted CLI: `{prefix}`", parse_mode="Markdown", reply_markup=keyboard)
        context.user_data.clear()

    # ─── Admin: Add Payment Method ────────────────────────
    elif state == "waiting_add_method" and is_admin(user.id):
        if "|" not in text:
            await update.message.reply_text("❌ Wrong format! Use: `Name | Details`", parse_mode="Markdown")
            return
        parts = text.split("|", 1)
        name = parts[0].strip()
        details = parts[1].strip()
        add_payment_method(name, details)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Methods", callback_data="adm_methods")]])
        await update.message.reply_text(f"✅ Added: *{name}*", parse_mode="Markdown", reply_markup=keyboard)
        context.user_data.clear()

    # ─── Admin: Edit Plan Price ───────────────────────────
    elif state and state.startswith("waiting_plan_price_") and is_admin(user.id):
        plan_id = int(state.split("_")[-1])
        try:
            price = float(text.strip())
            update_plan_price(plan_id, price)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Plans", callback_data="adm_plans")]])
            await update.message.reply_text(f"✅ Price updated to *${price:.2f}*", parse_mode="Markdown", reply_markup=keyboard)
        except:
            await update.message.reply_text("❌ Invalid price. Send a number like `15.00`", parse_mode="Markdown")
            return
        context.user_data.clear()

    # ─── Admin: Settings ──────────────────────────────────
    elif state and state.startswith("waiting_setting_") and is_admin(user.id):
        key = state.replace("waiting_setting_", "")
        value = text.strip()
        set_setting(key, value)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Settings", callback_data="adm_settings")]])
        await update.message.reply_text(f"✅ *{key}* updated to `{value}`", parse_mode="Markdown", reply_markup=keyboard)
        context.user_data.clear()

    # ─── Admin: Give Subscription ─────────────────────────
    elif state == "waiting_give_sub_id" and is_admin(user.id):
        try:
            target_id = int(text.strip())
        except:
            await update.message.reply_text("❌ Invalid User ID.")
            return
        context.user_data["give_sub_target"] = target_id
        context.user_data["state"] = "waiting_give_sub_plan"
        plans = get_plans()
        buttons = [[InlineKeyboardButton(f"{p['name']} ({p['months']}m)", callback_data=f"gs_{p['id']}_{target_id}")] for p in plans]
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")])
        await update.message.reply_text("Select plan:", reply_markup=InlineKeyboardMarkup(buttons))

    # ─── Admin: Revoke Sub ────────────────────────────────
    elif state == "waiting_revoke_sub_id" and is_admin(user.id):
        try:
            target_id = int(text.strip())
            revoke_subscription(target_id)
            try:
                await context.bot.send_message(target_id, "⚠️ Your subscription has been revoked.")
            except: pass
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Users", callback_data="adm_users")]])
            await update.message.reply_text(f"✅ Subscription revoked for `{target_id}`", parse_mode="Markdown", reply_markup=keyboard)
        except:
            await update.message.reply_text("❌ Invalid User ID.")
        context.user_data.clear()

    # ─── Admin: Ban ───────────────────────────────────────
    elif state == "waiting_ban_id" and is_admin(user.id):
        try:
            target_id = int(text.strip())
            ban_user(target_id, True)
            try:
                await context.bot.send_message(target_id, "🚫 You have been banned.")
            except: pass
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Users", callback_data="adm_users")]])
            await update.message.reply_text(f"✅ Banned user `{target_id}`", parse_mode="Markdown", reply_markup=keyboard)
        except:
            await update.message.reply_text("❌ Invalid User ID.")
        context.user_data.clear()

    # ─── Admin: Unban ─────────────────────────────────────
    elif state == "waiting_unban_id" and is_admin(user.id):
        try:
            target_id = int(text.strip())
            ban_user(target_id, False)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Users", callback_data="adm_users")]])
            await update.message.reply_text(f"✅ Unbanned user `{target_id}`", parse_mode="Markdown", reply_markup=keyboard)
        except:
            await update.message.reply_text("❌ Invalid User ID.")
        context.user_data.clear()

    # ─── Admin: Find User ─────────────────────────────────
    elif state == "waiting_find_user" and is_admin(user.id):
        query_text = text.strip().lstrip("@")
        users = get_all_users()
        found = None
        for u in users:
            if str(u["user_id"]) == query_text or (u["username"] and u["username"].lower() == query_text.lower()):
                found = u
                break
        if found:
            from database import get_active_subscription
            sub = get_active_subscription(found["user_id"])
            sub_status = f"✅ Until {sub['end_date'][:10]}" if sub else "❌ None"
            ban_status = "🚫 Banned" if found["is_banned"] else "✅ Active"
            text_out = (
                f"👤 *User Info*\n\n"
                f"ID: `{found['user_id']}`\n"
                f"Name: {found['full_name']}\n"
                f"Username: @{found['username'] or 'N/A'}\n"
                f"Joined: {found['joined_at'][:10]}\n"
                f"Status: {ban_status}\n"
                f"Subscription: {sub_status}"
            )
        else:
            text_out = "❌ User not found."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Users", callback_data="adm_users")]])
        await update.message.reply_text(text_out, parse_mode="Markdown", reply_markup=keyboard)
        context.user_data.clear()

    # ─── Admin: Broadcast ────────────────────────────────
    elif state and state.startswith("waiting_bc_") and is_admin(user.id):
        target_type = state.split("_")[2]  # all or subs
        broadcast_msg = text

        if target_type == "all":
            targets = [u["user_id"] for u in get_all_users()]
        else:
            targets = get_active_subscribers()

        sent = 0
        failed = 0
        for uid in targets:
            try:
                await context.bot.send_message(uid, broadcast_msg, parse_mode="Markdown")
                sent += 1
            except:
                failed += 1

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
        await update.message.reply_text(
            f"📢 *Broadcast Complete!*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="Markdown", reply_markup=keyboard
        )
        context.user_data.clear()


async def handle_cli_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    doc = update.message.document
    if not doc.file_name.endswith((".txt", ".csv")):
        await update.message.reply_text("❌ Only .txt or .csv files accepted.")
        return

    await update.message.reply_text("⏳ Processing file...")

    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    content = file_bytes.decode("utf-8", errors="ignore")

    import re
    raw = content.replace("\n", ",").replace(";", ",").replace("\r", "")
    prefixes = [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]

    count = 0
    for p in prefixes:
        add_cli(p)
        count += 1

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 CLI List", callback_data="adm_cli")]])
    await update.message.reply_text(
        f"✅ Imported *{count}* CLI prefixes from file!",
        parse_mode="Markdown", reply_markup=keyboard
    )
    context.user_data.clear()
