from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from database import (
    get_active_subscription, get_setting, get_all_cli,
    ban_user, add_subscription, revoke_subscription,
    update_payment_status, get_payment_request,
    add_payment_method, delete_payment_method,
    update_plan_price, set_setting, clear_all_cli, delete_cli,
    get_all_users, get_active_subscribers, get_plans
)
from scraper import scrape_active_ranges
from formatter import format_active_ranges
from handlers.start import build_main_keyboard
from handlers.admin import (
    show_admin_panel, show_users, show_cli, show_payments,
    show_payment_detail, show_settings, show_plans, show_methods,
    show_stats, show_broadcast, is_admin
)
from handlers.subscription import (
    subscription_handler, show_plan_detail, show_payment_details
)
import logging, asyncio

logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # ─── Main Menu ───────────────────────────────────────
    if data == "main_menu":
        sub = get_active_subscription(user.id)
        admin = is_admin(user.id)
        text = (
            f"👋 *Welcome back, {user.full_name}!*\n\n"
            f"📡 Orange Carrier Active Range Bot\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 Subscription: {'✅ Active' if sub else '❌ None'}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=build_main_keyboard(admin, sub))

    # ─── View Ranges ─────────────────────────────────────
    elif data == "view_ranges":
        sub = get_active_subscription(user.id)
        if not sub and not is_admin(user.id):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Buy Subscription", callback_data="buy_sub")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
            await query.edit_message_text(
                "🔒 *Subscription Required*\n\nBuy a subscription to view active ranges.",
                parse_mode="Markdown", reply_markup=keyboard
            )
            return

        await query.edit_message_text("🔄 *Fetching active ranges...*\nPlease wait.", parse_mode="Markdown")

        cli_list = get_all_cli()
        if not cli_list:
            await query.edit_message_text(
                "⚠️ No CLI list configured.\nAdmin hasn't added CLIs yet.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
            )
            return

        min_hits = int(get_setting("min_hits", "4"))
        max_hits = int(get_setting("max_hits", "10"))
        top_n = int(get_setting("top_ranges", "20"))
        window = int(get_setting("window_minutes", "30"))

        results, error = scrape_active_ranges(cli_list, min_hits, max_hits, top_n, window)

        if error:
            await query.edit_message_text(
                f"❌ Error: {error}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
            )
            return

        if not results:
            msg = "📡 No active ranges found matching criteria."
        else:
            msg = format_active_ranges(results, window)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_ranges")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    # ─── Buy Subscription ─────────────────────────────────
    elif data == "buy_sub" or data == "select_plan":
        await subscription_handler(update, context)

    elif data.startswith("plan_"):
        plan_id = int(data.split("_")[1])
        await show_plan_detail(query, plan_id)

    elif data.startswith("paymethod_"):
        _, plan_id, method_id = data.split("_")
        await show_payment_details(query, context, int(plan_id), int(method_id))

    elif data == "submit_trx":
        context.user_data["state"] = "waiting_trx"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="buy_sub")]])
        await query.edit_message_text(
            "📤 *Submit Transaction ID*\n\nPlease type your Transaction ID:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    # ─── Our Service ──────────────────────────────────────
    elif data == "our_service":
        service_info = get_setting("service_info", "Orange Carrier Active Range Bot")
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        await query.edit_message_text(service_info, parse_mode="Markdown", reply_markup=keyboard)

    # ─── Support ──────────────────────────────────────────
    elif data == "support":
        support = get_setting("support_username", "@support")
        text = f"🛠 *Support*\n\nContact us: {support}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    # ─── Admin Panel ──────────────────────────────────────
    elif data == "admin_panel":
        if not is_admin(user.id):
            await query.answer("⛔ Access denied", show_alert=True)
            return
        await show_admin_panel(query, context, edit=True)

    elif data == "adm_users":
        if not is_admin(user.id): return
        await show_users(query, context)

    elif data == "adm_cli":
        if not is_admin(user.id): return
        await show_cli(query, context)

    elif data == "adm_payments":
        if not is_admin(user.id): return
        await show_payments(query, context)

    elif data.startswith("adm_pay_"):
        if not is_admin(user.id): return
        payment_id = int(data.split("_")[2])
        await show_payment_detail(query, payment_id)

    elif data.startswith("adm_approve_"):
        if not is_admin(user.id): return
        payment_id = int(data.split("_")[2])
        p = get_payment_request(payment_id)
        if p and p["status"] == "pending":
            plans = get_plans()
            plan = next((pl for pl in plans if pl["name"] == p["plan"]), None)
            months = plan["months"] if plan else 1
            add_subscription(p["user_id"], p["plan"], months)
            update_payment_status(payment_id, "approved")
            try:
                await context.bot.send_message(
                    p["user_id"],
                    f"✅ *Subscription Activated!*\n\nYour *{p['plan']}* subscription is now active!\n\nEnjoy your access to Orange Carrier Active Ranges! 📡",
                    parse_mode="Markdown"
                )
            except: pass
            await query.edit_message_text(
                f"✅ Payment #{payment_id} approved!\nSubscription activated for user {p['user_id']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Payments", callback_data="adm_payments")]])
            )
        else:
            await query.answer("Already processed")

    elif data.startswith("adm_reject_"):
        if not is_admin(user.id): return
        payment_id = int(data.split("_")[2])
        p = get_payment_request(payment_id)
        if p and p["status"] == "pending":
            update_payment_status(payment_id, "rejected")
            try:
                await context.bot.send_message(
                    p["user_id"],
                    f"❌ *Payment Rejected*\n\nYour payment for *{p['plan']}* was rejected.\n\nPlease contact support if you believe this is an error.",
                    parse_mode="Markdown"
                )
            except: pass
            await query.edit_message_text(
                f"❌ Payment #{payment_id} rejected.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Payments", callback_data="adm_payments")]])
            )

    elif data == "adm_settings":
        if not is_admin(user.id): return
        await show_settings(query, context)

    elif data == "adm_plans":
        if not is_admin(user.id): return
        await show_plans(query, context)

    elif data == "adm_methods":
        if not is_admin(user.id): return
        await show_methods(query, context)

    elif data == "adm_stats":
        if not is_admin(user.id): return
        await show_stats(query, context)

    elif data == "adm_broadcast":
        if not is_admin(user.id): return
        await show_broadcast(query, context)

    elif data == "adm_toggle_bot":
        if not is_admin(user.id): return
        current = get_setting("bot_active", "1")
        new_val = "0" if current == "1" else "1"
        set_setting("bot_active", new_val)
        await show_settings(query, context)

    elif data == "adm_clear_cli":
        if not is_admin(user.id): return
        context.user_data["state"] = "confirm_clear_cli"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Yes, Clear All", callback_data="adm_confirm_clear"),
             InlineKeyboardButton("🔙 Cancel", callback_data="adm_cli")]
        ])
        await query.edit_message_text("⚠️ *Are you sure you want to clear ALL CLIs?*", parse_mode="Markdown", reply_markup=keyboard)

    elif data == "adm_confirm_clear":
        if not is_admin(user.id): return
        clear_all_cli()
        await query.edit_message_text(
            "✅ All CLIs cleared!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 CLI List", callback_data="adm_cli")]])
        )

    elif data == "adm_add_cli":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_add_cli"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_cli")]])
        await query.edit_message_text(
            "📋 *Add CLI Prefixes*\n\nSend prefixes separated by comma, newline, or upload a .txt/.csv file.\n\nExample: `770, 371, 382, 855`",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_del_cli":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_del_cli"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_cli")]])
        await query.edit_message_text(
            "❌ *Delete CLI*\n\nSend the prefix to delete:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_view_cli":
        if not is_admin(user.id): return
        cli_list = get_all_cli()
        if not cli_list:
            text = "📋 CLI list is empty."
        else:
            chunks = [cli_list[i:i+50] for i in range(0, len(cli_list), 50)]
            text = f"📋 *CLI List ({len(cli_list)} total)*\n\n`" + ", ".join(chunks[0]) + "`"
            if len(chunks) > 1:
                text += f"\n\n...and {len(cli_list)-50} more"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_cli")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "adm_add_method":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_add_method"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_methods")]])
        await query.edit_message_text(
            "💰 *Add Payment Method*\n\nSend in this format:\n`Method Name | Account Details`\n\nExample:\n`bKash | 01XXXXXXXXX (Personal)`",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_del_method":
        if not is_admin(user.id): return
        from database import get_payment_methods
        methods = get_payment_methods()
        if not methods:
            await query.answer("No methods to delete")
            return
        buttons = [[InlineKeyboardButton(f"❌ {m['name']}", callback_data=f"adm_dmethod_{m['id']}")] for m in methods]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="adm_methods")])
        await query.edit_message_text("Select method to delete:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("adm_dmethod_"):
        if not is_admin(user.id): return
        method_id = int(data.split("_")[2])
        delete_payment_method(method_id)
        await query.answer("✅ Deleted")
        await show_methods(query, context)

    elif data.startswith("adm_editplan_"):
        if not is_admin(user.id): return
        plan_id = int(data.split("_")[2])
        context.user_data["state"] = f"waiting_plan_price_{plan_id}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_plans")]])
        await query.edit_message_text(
            f"✏️ *Edit Plan Price*\n\nSend new price (number only):\nExample: `15.00`",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data in ["adm_set_interval", "adm_set_minhits", "adm_set_maxhits", "adm_set_topn", "adm_set_window", "adm_set_support"]:
        if not is_admin(user.id): return
        setting_map = {
            "adm_set_interval": ("check_interval", "Check interval (minutes)", "10"),
            "adm_set_minhits": ("min_hits", "Minimum hits", "4"),
            "adm_set_maxhits": ("max_hits", "Maximum hits", "10"),
            "adm_set_topn": ("top_ranges", "Top N ranges to show", "20"),
            "adm_set_window": ("window_minutes", "Window in minutes", "30"),
            "adm_set_support": ("support_username", "Support username (@username)", "@support"),
        }
        key, label, default = setting_map[data]
        context.user_data["state"] = f"waiting_setting_{key}"
        current = get_setting(key, default)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_settings")]])
        await query.edit_message_text(
            f"⚙️ *{label}*\n\nCurrent: `{current}`\n\nSend new value:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_give_sub":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_give_sub_id"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")]])
        await query.edit_message_text(
            "➕ *Give Subscription*\n\nSend User ID:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_revoke_sub":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_revoke_sub_id"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")]])
        await query.edit_message_text(
            "❌ *Revoke Subscription*\n\nSend User ID:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data == "adm_ban_user":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_ban_id"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")]])
        await query.edit_message_text("🚫 *Ban User*\n\nSend User ID:", parse_mode="Markdown", reply_markup=keyboard)

    elif data == "adm_unban_user":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_unban_id"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")]])
        await query.edit_message_text("✅ *Unban User*\n\nSend User ID:", parse_mode="Markdown", reply_markup=keyboard)

    elif data == "adm_find_user":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_find_user"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_users")]])
        await query.edit_message_text("🔍 *Find User*\n\nSend User ID or @username:", parse_mode="Markdown", reply_markup=keyboard)

    elif data in ["adm_bc_all", "adm_bc_subs"]:
        if not is_admin(user.id): return
        context.user_data["state"] = f"waiting_bc_{data.split('_')[2]}"
        target_label = "All Users" if data == "adm_bc_all" else "Subscribers Only"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_broadcast")]])
        await query.edit_message_text(
            f"📢 *Broadcast to {target_label}*\n\nSend your message:",
            parse_mode="Markdown", reply_markup=keyboard
        )

    elif data.startswith("gs_"):
        if not is_admin(user.id): return
        _, plan_id, target_id = data.split("_")
        plan_id, target_id = int(plan_id), int(target_id)
        plans = get_plans()
        plan = next((p for p in plans if p["id"] == plan_id), None)
        if plan:
            add_subscription(target_id, plan["name"], plan["months"])
            try:
                await context.bot.send_message(
                    target_id,
                    f"🎉 *Subscription Activated!*\n\nAdmin gave you a *{plan['name']}* subscription!\n\nEnjoy your access! 📡",
                    parse_mode="Markdown"
                )
            except: pass
            await query.edit_message_text(
                f"✅ *{plan['name']}* subscription given to user `{target_id}`!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Users", callback_data="adm_users")]])
            )

    elif data == "adm_upload_cli":
        if not is_admin(user.id): return
        context.user_data["state"] = "waiting_cli_file"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="adm_cli")]])
        await query.edit_message_text(
            "📤 *Upload CLI File*\n\nSend a `.txt` or `.csv` file with one prefix per line.",
            parse_mode="Markdown", reply_markup=keyboard
        )
