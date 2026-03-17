"""
searcher.py - Search LinkedIn for jobs and scrape listings.
"""

import base64
import logging
import random
import re
import time
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from playwright.sync_api import Page

from src.control import push_screenshot, stop_event

logger = logging.getLogger(__name__)


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: str
    is_easy_apply: bool = False


def _random_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _capture(page: Page) -> None:
    """Take a JPEG screenshot and push it to the live-preview stream."""
    try:
        raw = page.screenshot(type="jpeg", quality=55, full_page=False)
        push_screenshot(base64.b64encode(raw).decode())
    except Exception:
        pass


def _build_search_url(keyword: str, location: str, experience_levels: list[str], max_age_hours: int = 10) -> str:
    f_E = "%2C".join(experience_levels)
    r_seconds = max_age_hours * 3600
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(keyword)}"
        f"&location={quote_plus(location)}"
        f"&f_E={f_E}"
        f"&f_TPR=r{r_seconds}"
        f"&sortBy=DD"          # date descending
    )


def _extract_job_id(url: str) -> str | None:
    match = re.search(r"/jobs/view/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"currentJobId=(\d+)", url)
    return match.group(1) if match else None


def _scrape_job_card(page: Page, card) -> Job | None:
    """Extract job data from a search result card."""
    try:
        # ── Job ID ──────────────────────────────────────────────────────────
        # Prefer the data attribute (stable across DOM changes)
        job_id = (
            card.get_attribute("data-occludable-job-id")
            or card.get_attribute("data-job-id")
        )

        # Title link – try multiple known selectors
        title_el = card.query_selector(
            "a.job-card-list__title--link, "   # 2024+
            "a.job-card-list__title, "         # classic
            "a.job-card-container__link, "     # older
            "a[href*='/jobs/view/']"            # generic fallback
        )
        if not title_el:
            return None

        href = title_el.get_attribute("href") or ""
        if not job_id:
            job_id = _extract_job_id(href)
        if not job_id:
            return None

        title = title_el.inner_text().strip()

        # ── Company ─────────────────────────────────────────────────────────
        company = ""
        company_el = card.query_selector(
            ".job-card-container__company-name, "
            ".job-card-container__primary-description, "
            ".artdeco-entity-lockup__subtitle span, "
            "span.job-search-card__company-name"
        )
        if company_el:
            company = company_el.inner_text().strip()

        # ── Location ─────────────────────────────────────────────────────────
        location = ""
        location_el = card.query_selector(
            ".job-card-container__metadata-item, "
            ".job-card-container__metadata-wrapper li, "
            "li.job-search-card__location, "
            "span.job-search-card__location"
        )
        if location_el:
            location = location_el.inner_text().strip()

        apply_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

        is_easy_apply = card.query_selector(
            ".job-card-container__apply-method, "
            "li-icon[type='linkedin-bug']"
        ) is not None

        return Job(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            description="",  # filled in get_job_description()
            apply_url=apply_url,
            is_easy_apply=is_easy_apply,
        )
    except Exception as e:
        logger.debug("Error scraping card: %s", e)
        return None


def get_job_description(page: Page, job: Job) -> str:
    """Navigate to job page and extract full description."""
    try:
        page.goto(job.apply_url, wait_until="domcontentloaded")
        _random_delay(1.5, 3)

        desc_el = page.query_selector(
            ".jobs-description__content, "
            ".jobs-box__html-content, "
            "#job-details"
        )
        if desc_el:
            return desc_el.inner_text().strip()
    except Exception as e:
        logger.debug("Could not fetch description for %s: %s", job.job_id, e)
    return ""


def search_jobs(page: Page, config: dict, already_seen: set[str]) -> list[Job]:
    """
    Search LinkedIn for new jobs matching config criteria.
    Returns a list of Job objects not yet in already_seen.
    """
    search_cfg = config["search"]
    keywords: list[str] = search_cfg["keywords"]
    location: str = search_cfg["location"]
    experience_levels: list[str] = [str(e) for e in search_cfg.get("experience_levels", ["2", "3"])]
    max_jobs: int = search_cfg.get("max_jobs_per_run", 30)

    max_age_hours: int = search_cfg.get("max_age_hours", 10)
    found: list[Job] = []

    for keyword in keywords:
        if len(found) >= max_jobs:
            break
        if stop_event.is_set():
            logger.info("Stop requested – aborting keyword loop.")
            break

        url = _build_search_url(keyword, location, experience_levels, max_age_hours)
        logger.info("Searching: keyword=%r location=%r", keyword, location)

        try:
            page.goto(url, wait_until="domcontentloaded")
            _capture(page)
            _random_delay(2, 4)

            # Scroll to load more results
            for _ in range(3):
                page.keyboard.press("End")
                _random_delay(0.8, 1.5)

            _capture(page)

            # LinkedIn periodically renames CSS classes; try several known patterns
            CARD_SELECTORS = [
                "li[data-occludable-job-id]",             # most reliable – data attribute
                "li.jobs-search-results__list-item",      # classic
                "li.scaffold-layout__list-item",          # 2024 layout
                "div.job-search-card",                    # public/guest view
                ".job-card-container",                    # fallback
            ]
            cards = []
            for sel in CARD_SELECTORS:
                cards = page.query_selector_all(sel)
                if cards:
                    logger.debug("Card selector matched: %r (%d cards)", sel, len(cards))
                    break

            logger.info("Found %d cards for keyword %r", len(cards), keyword)

            if not cards:
                # Dump a snippet of the page source so you can identify the right selector
                html_snippet = (page.content() or "")[:3000]
                logger.debug("Page HTML snippet (first 3000 chars):\n%s", html_snippet)

            for card in cards:
                if len(found) >= max_jobs or stop_event.is_set():
                    break

                job = _scrape_job_card(page, card)
                if job is None or job.job_id in already_seen:
                    continue

                already_seen.add(job.job_id)
                found.append(job)
                _random_delay(0.3, 0.8)

        except Exception as e:
            logger.error("Error during search for %r: %s", keyword, e)

    # Fetch full descriptions
    logger.info("Fetching descriptions for %d new jobs...", len(found))
    for job in found:
        if stop_event.is_set():
            logger.info("Stop requested – aborting description fetch.")
            break
        job.description = get_job_description(page, job)
        _capture(page)
        _random_delay(1, 2.5)

    return found
