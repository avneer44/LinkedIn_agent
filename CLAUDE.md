# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinkedIn Job Scout – a Python agent that periodically scrapes LinkedIn for job listings, scores them for relevance using Claude AI, and emails matching jobs to the user. The user applies manually via the provided links.

## Commands

### Setup
```bash
pip install -r requirements.txt
python -m playwright install chromium

# Copy and fill in credentials
cp .env.example .env
```

### Running the Agent
```bash
python main.py --dry-run   # Search + score, print results, skip email
python main.py --once      # Single run with email
python main.py             # Scheduler mode (runs every schedule_hours from config.yaml)
```

### Required Files Before Running
- `.env` – credentials (see `.env.example`)
- `cv.txt` – plain text CV content used for AI scoring
- `config.yaml` – search keywords, location, experience levels, email addresses

## Architecture

The pipeline runs in a fixed sequence inside `run_agent()` in [main.py](main.py):

```
ensure_logged_in() → search_jobs() → [browser closes] → filter_jobs() → send_digest()
```

**Key design decisions:**
- The Playwright browser is opened and closed within a single `with sync_playwright()` block. All scraping happens inside this block; Claude API calls happen after the browser closes.
- Jobs are written to the SQLite DB as "seen" **before** filtering, so a job that scores below threshold is never re-evaluated in future runs.
- `already_seen` is a plain Python `set[str]` passed into `search_jobs()` and populated during scraping to deduplicate within a single run (across multiple keyword searches).

### Module Responsibilities

| File | Responsibility |
|------|---------------|
| [src/auth.py](src/auth.py) | LinkedIn login, cookie save/load, session validation |
| [src/searcher.py](src/searcher.py) | Build search URLs, scrape job cards, fetch full descriptions |
| [src/filter.py](src/filter.py) | Load CV, call Claude API per job, return `(Job, score, reason)` tuples |
| [src/notifier.py](src/notifier.py) | Build HTML + plain-text email digest, send via Gmail SMTP SSL |
| [src/tracker.py](src/tracker.py) | SQLite CRUD – `is_seen`, `mark_seen`, `mark_emailed`, `get_stats` |

### Data Model

The `Job` dataclass (defined in [src/searcher.py](src/searcher.py)) is the shared data structure passed between all modules:
```python
@dataclass
class Job:
    job_id: str       # LinkedIn numeric ID extracted from URL
    title: str
    company: str
    location: str
    description: str  # empty until get_job_description() fills it
    apply_url: str    # always https://www.linkedin.com/jobs/view/{job_id}/
    is_easy_apply: bool
```

### Configuration Keys

`config.yaml` drives all runtime behavior:
- `search.experience_levels` – LinkedIn numeric codes (1=Internship … 6=Executive)
- `search.max_jobs_per_run` – caps total jobs scraped across all keywords
- `filter.min_relevance_score` – Claude scores 0–100; only jobs ≥ this are emailed
- `notifications.send_if_empty` – set to `true` to always send email even with no results

### Environment Variables (`.env`)

| Variable | Used in |
|----------|---------|
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | `src/auth.py` |
| `ANTHROPIC_API_KEY` | `src/filter.py` |
| `GMAIL_SENDER` / `GMAIL_APP_PASSWORD` | `src/notifier.py` |

### Anti-Detection Notes

- Browser runs with `headless=False` and a realistic `user_agent` string
- Random delays (`_random_delay()`) are used between every page action in both `auth.py` and `searcher.py`
- LinkedIn session cookies are persisted to `data/session.json` to avoid repeated logins
- If a security checkpoint/2FA is detected, the agent pauses for 60 seconds for manual completion

### Persistent State

- `data/jobs.db` – SQLite, single `jobs` table; persists across runs
- `data/session.json` – LinkedIn cookies; auto-refreshed on session expiry
- `logs/agent.log` – append-only log of all runs

## User Preferences & Feature Requirements

### 1. Job Relevance Scoring
- Scoring must consider **both** the CV content **and** general domain knowledge about the field
- Do not limit scoring only to strict CV matches — also score based on whether the role is relevant to the user's professional domain, industry trends, and role type
- Example: if the user is a data scientist, a "ML Engineer" role should score high even if the exact title isn't in the CV

### 2. No Duplicate Emails (One-Time Send Guarantee)
- Each job must be emailed **at most once**, ever
- The `tracker.py` module tracks `mark_emailed` status in the DB — this must be checked in `notifier.py` before sending
- If a job was already emailed in a previous run, skip it silently — do not include it in any future digest
- The `filter_jobs()` pipeline must exclude jobs where `tracker.is_emailed(job_id)` returns `True`

### 3. Web-Based Control UI
- A local web UI must allow the user to control and monitor the agent without editing config files
- The UI should support:
  - Starting / stopping the agent scheduler
  - Triggering a single run (equivalent to `--once`)
  - Triggering a dry run (equivalent to `--dry-run`)
  - Viewing recent run logs
  - Viewing jobs found, scored, and emailed in the last run
  - Editing key config values (keywords, min score threshold, schedule interval)
- Recommended implementation: Flask or FastAPI with a simple HTML frontend served locally
- New file: `src/ui.py` or `app.py` — runs a local server (default port 5000)
- The scheduler and UI should be able to run concurrently (e.g., using threads or async)
