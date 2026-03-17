"""
notifier.py - Send email digest of relevant jobs.
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .searcher import Job

logger = logging.getLogger(__name__)


def _build_html(job_results: list[tuple[Job, int, str]]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows = ""
    for job, score, reason in job_results:
        color = "#2ecc71" if score >= 85 else "#f39c12" if score >= 70 else "#e74c3c"
        rows += f"""
        <tr>
          <td style="padding:12px; border-bottom:1px solid #eee;">
            <strong><a href="{job.apply_url}" style="color:#0077b5; text-decoration:none;">{job.title}</a></strong><br>
            <span style="color:#555;">{job.company}</span><br>
            <small style="color:#888;">📍 {job.location}</small>
          </td>
          <td style="padding:12px; border-bottom:1px solid #eee; text-align:center;">
            <span style="background:{color}; color:white; padding:4px 10px; border-radius:12px; font-weight:bold;">{score}</span>
          </td>
          <td style="padding:12px; border-bottom:1px solid #eee; color:#444; font-size:0.9em;">{reason}</td>
          <td style="padding:12px; border-bottom:1px solid #eee; text-align:center;">
            <a href="{job.apply_url}" style="background:#0077b5; color:white; padding:6px 14px; border-radius:4px; text-decoration:none; font-size:0.85em;">הגש מועמדות</a>
          </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
      <div style="max-width:800px; margin:auto; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:#0077b5; color:white; padding:20px 24px;">
          <h2 style="margin:0;">🔍 LinkedIn Job Scout</h2>
          <p style="margin:4px 0 0; opacity:0.85;">{now} | {len(job_results)} משרות רלוונטיות נמצאו</p>
        </div>
        <div style="padding:16px 24px;">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:#f0f0f0; text-align:right;">
                <th style="padding:10px;">משרה</th>
                <th style="padding:10px; text-align:center;">ציון</th>
                <th style="padding:10px;">הסבר</th>
                <th style="padding:10px; text-align:center;">פעולה</th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
        <div style="padding:12px 24px; background:#f8f8f8; color:#888; font-size:0.8em; text-align:center;">
          LinkedIn Job Scout | הופעל אוטומטית
        </div>
      </div>
    </body>
    </html>
    """


def _build_plain(job_results: list[tuple[Job, int, str]]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [f"LinkedIn Job Scout - {now}", f"{len(job_results)} משרות רלוונטיות\n", "=" * 60]
    for job, score, reason in job_results:
        lines.append(f"\n✅ {job.title} @ {job.company}")
        lines.append(f"   📍 {job.location} | ציון: {score}/100")
        lines.append(f"   💡 {reason}")
        lines.append(f"   🔗 {job.apply_url}")
    return "\n".join(lines)


def send_digest(job_results: list[tuple[Job, int, str]], config: dict) -> None:
    """Send email digest. Skips if job_results is empty and send_if_empty is False."""
    notif_cfg = config["notifications"]
    send_if_empty: bool = notif_cfg.get("send_if_empty", False)

    if not job_results and not send_if_empty:
        logger.info("No relevant jobs found. Skipping email.")
        return

    email_to: str = notif_cfg["email_to"]
    email_from: str = notif_cfg["email_from"]
    app_password: str = os.environ["GMAIL_APP_PASSWORD"]

    subject = f"LinkedIn Scout: {len(job_results)} משרות רלוונטיות" if job_results \
        else "LinkedIn Scout: לא נמצאו משרות חדשות"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.attach(MIMEText(_build_plain(job_results), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(job_results), "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, app_password)
            server.sendmail(email_from, email_to, msg.as_string())
        logger.info("Email digest sent to %s (%d jobs)", email_to, len(job_results))
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        raise
