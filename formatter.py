from datetime import datetime

def format_active_ranges(results, window_minutes=30):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    top_n = len(results)

    lines = [
        f"📡 *Active Ranges (Top {top_n})*",
        f"⏱ Window: {window_minutes} min\n"
    ]

    for i, (termination, data) in enumerate(results, 1):
        hits = data["hits"]
        cli_count = len(data["clis"])
        last_cli = data.get("last_cli", "?")

        lines.append(
            f"*{i}. {termination}*\n"
            f"   📊 {hits} hits • {cli_count} CLI\n"
            f"   🔍 Last CLI: `{last_cli}`"
        )

    lines.append(f"\n🕒 Updated: {now}")
    return "\n".join(lines)

def format_subscription_info(sub):
    if not sub:
        return "❌ No active subscription"
    end_date = sub["end_date"][:10]
    return f"✅ Active until: *{end_date}*\nPlan: *{sub['plan']}*"
