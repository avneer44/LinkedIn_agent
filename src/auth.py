"""
auth.py - LinkedIn login and cookie/session management.
"""

import json
import logging
import os
import random
import time
from pathlib import Path

from playwright.sync_api import Page, BrowserContext

logger = logging.getLogger(__name__)

SESSION_PATH = Path(__file__).parent.parent / "data" / "session.json"


def _random_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def save_cookies(context: BrowserContext) -> None:
    SESSION_PATH.parent.mkdir(exist_ok=True)
    cookies = context.cookies()
    SESSION_PATH.write_text(json.dumps(cookies, indent=2))
    logger.info("Session cookies saved.")


def load_cookies(context: BrowserContext) -> bool:
    """Load saved cookies. Returns True if cookies were loaded."""
    if not SESSION_PATH.exists():
        return False
    cookies = json.loads(SESSION_PATH.read_text())
    if not cookies:
        return False
    context.add_cookies(cookies)
    logger.info("Session cookies loaded.")
    return True


def is_logged_in(page: Page) -> bool:
    """Check if the current page shows a logged-in state."""
    return page.locator("a[data-tracking-control-name='nav_settings_profile']").count() > 0 \
        or page.locator(".global-nav__me-photo").count() > 0 \
        or "feed" in page.url


def login(page: Page) -> None:
    """Perform LinkedIn login with credentials from environment."""
    email = os.environ["LINKEDIN_EMAIL"]
    password = os.environ["LINKEDIN_PASSWORD"]

    logger.info("Navigating to LinkedIn login page...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    _random_delay()

    page.fill("#username", email)
    _random_delay(0.5, 1.5)
    page.fill("#password", password)
    _random_delay(0.5, 1.0)
    page.click("button[type='submit']")

    page.wait_for_load_state("domcontentloaded")
    _random_delay(2, 4)

    if "checkpoint" in page.url or "challenge" in page.url:
        logger.warning("LinkedIn security challenge detected (2FA/CAPTCHA). "
                       "Please complete it manually within 60 seconds.")
        page.wait_for_url("**/feed**", timeout=60_000)

    if not is_logged_in(page):
        raise RuntimeError("Login failed. Check credentials in .env file.")

    logger.info("Login successful.")


def ensure_logged_in(page: Page, context: BrowserContext) -> None:
    """Load session or perform login if needed."""
    cookies_loaded = load_cookies(context)

    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    _random_delay(1, 2)

    if not is_logged_in(page):
        logger.info("Session expired or no saved session. Logging in...")
        login(page)
        save_cookies(context)
    else:
        logger.info("Already logged in via saved session.")
