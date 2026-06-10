import asyncio
import logging
from datetime import datetime, timedelta
from database import get_all_cli, get_active_subscribers, get_setting
from scraper import scrape_active_ranges
from formatter import format_active_ranges

logger = logging.getLogger(__name__)

_scheduler_task = None

async def run_check(app):
    try:
        bot_active = get_setting("bot_active", "1")
        if bot_active != "1":
            return

        cli_list = get_all_cli()
        if not cli_list:
            logger.info("No CLI list found, skipping check")
            return

        min_hits = int(get_setting("min_hits", "4"))
        max_hits = int(get_setting("max_hits", "10"))
        top_n = int(get_setting("top_ranges", "20"))
        window = int(get_setting("window_minutes", "30"))

        logger.info(f"Running check with {len(cli_list)} CLIs...")
        results, error = scrape_active_ranges(cli_list, min_hits, max_hits, top_n, window)

        if error:
            logger.error(f"Scrape error: {error}")
            return

        if not results:
            logger.info("No results found")
            return

        message = format_active_ranges(results, window)

        # Send to all active subscribers
        subscribers = get_active_subscribers()
        from config import ADMIN_IDS
        targets = list(set(subscribers + ADMIN_IDS))

        for uid in targets:
            try:
                await app.bot.send_message(chat_id=uid, text=message, parse_mode="Markdown")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Failed to send to {uid}: {e}")

    except Exception as e:
        logger.error(f"Scheduler error: {e}")

async def scheduler_loop(app):
    while True:
        interval = int(get_setting("check_interval", "10"))
        await asyncio.sleep(interval * 60)
        await run_check(app)

async def start_scheduler(app):
    global _scheduler_task
    loop = asyncio.get_event_loop()
    _scheduler_task = loop.create_task(scheduler_loop(app))
    logger.info("Scheduler started")
