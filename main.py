"""
main.py - LinkedIn Job Scout Agent
Entry point + scheduler orchestration.

Usage:
  python main.py              # Run scheduler (every N hours as configured)
  python main.py --once       # Run once and send email
  python main.py --dry-run    # Run once, print results, NO email sent
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from src.auth import ensure_logged_in, save_cookies
from src.searcher import search_jobs
from src.filter import filter_jobs
from src.notifier import send_digest
from src import tracker

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8"),
    ],
)
# Keep noisy libraries at INFO to avoid log spam
logging.getLogger("werkzeug").setLevel(logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logger = logging.getLogger("main")


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_agent(config: dict, dry_run: bool = False) -> dict:
    """Single agent run: search → filter → notify. Returns a results summary dict."""
    logger.info("=" * 60)
    logger.info("Agent run started%s", " [DRY RUN]" if dry_run else "")
    logger.info("=" * 60)

    tracker.init_db()
    stats_before = tracker.get_stats()
    logger.info("Tracker stats: %s", stats_before)

    # Pre-populate already_seen from DB so previously-seen jobs are not re-scraped
    already_seen: set[str] = tracker.get_all_seen_ids()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,  # visible helps avoid bot detection
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            ensure_logged_in(page, context)
            save_cookies(context)

            new_jobs = search_jobs(page, config, already_seen)
            logger.info("Found %d new jobs to evaluate", len(new_jobs))

        finally:
            browser.close()

    # Mark all found jobs as seen (before filtering, to avoid re-processing later)
    for job in new_jobs:
        tracker.mark_seen(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            location=job.location,
            apply_url=job.apply_url,
        )

    # Filter with Claude AI
    relevant = filter_jobs(new_jobs, config)
    logger.info("%d jobs passed relevance filter", len(relevant))

    # Update scores/reasons in DB
    for job, score, reason in relevant:
        tracker.mark_seen(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            location=job.location,
            apply_url=job.apply_url,
            score=score,
            reason=reason,
        )

    # Print results (always)
    if relevant:
        logger.info("\n--- Relevant Jobs ---")
        for job, score, reason in relevant:
            logger.info("  [%d] %s @ %s", score, job.title, job.company)
            logger.info("       %s", reason)
            logger.info("       %s", job.apply_url)
    else:
        logger.info("No relevant jobs found this run.")

    # Send email (unless dry-run)
    if not dry_run:
        send_digest(relevant, config)
        if relevant:
            tracker.mark_emailed([job.job_id for job, _, _ in relevant])
    else:
        logger.info("[DRY RUN] Email not sent.")

    final_stats = tracker.get_stats()
    logger.info("Agent run complete. Total seen: %s", final_stats)

    return {
        "dry_run": dry_run,
        "found": len(new_jobs),
        "relevant": len(relevant),
        "emailed": 0 if dry_run else len(relevant),
        "jobs": [
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "score": score,
                "reason": reason,
                "apply_url": job.apply_url,
            }
            for job, score, reason in relevant
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Job Scout Agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run once, print results, skip email")
    args = parser.parse_args()

    load_dotenv()
    config = load_config()

    if args.dry_run or args.once:
        run_agent(config, dry_run=args.dry_run)
        return

    # Scheduler mode
    from apscheduler.schedulers.blocking import BlockingScheduler

    schedule_hours: int = config["search"].get("schedule_hours", 1)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_agent,
        "interval",
        hours=schedule_hours,
        args=[config],
        id="linkedin_scout",
    )

    logger.info("Scheduler started. Running every %d hour(s). Press Ctrl+C to stop.", schedule_hours)

    # Run immediately on startup, then on schedule
    run_agent(config)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
