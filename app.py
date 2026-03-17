"""
app.py - Web UI for LinkedIn Job Scout

Run with:
    python app.py

Opens a local dashboard at http://localhost:5000
The agent can be triggered and scheduled from the UI.
"""

import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from main import load_config, run_agent
from src import tracker

LOG_PATH = Path(__file__).parent / "logs" / "agent.log"
CONFIG_PATH = Path(__file__).parent / "config.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH.parent / "agent.log", encoding="utf-8"),
    ],
)

app = Flask(__name__)

# ── Shared state (thread-safe) ────────────────────────────────────────────────
_lock = threading.Lock()
_state: dict = {
    "status": "idle",   # idle | running | error
    "last_run_at": None,
    "last_run_dry": False,
    "last_results": None,
    "error": None,
    "scheduler_running": False,
    "next_run_at": None,
}
_run_thread: threading.Thread | None = None
_scheduler = None


def _set_state(**kwargs) -> None:
    with _lock:
        _state.update(kwargs)


def _get_state() -> dict:
    with _lock:
        return dict(_state)


# ── Agent runner ──────────────────────────────────────────────────────────────
def _run_agent_task(dry_run: bool = False) -> None:
    _set_state(status="running", error=None)
    try:
        config = load_config()
        results = run_agent(config, dry_run=dry_run)
        _set_state(
            status="idle",
            last_run_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            last_run_dry=dry_run,
            last_results=results,
            error=None,
        )
    except Exception as exc:
        logging.exception("Agent run failed")
        _set_state(status="error", error=str(exc))


def _start_run(dry_run: bool = False) -> bool:
    global _run_thread
    with _lock:
        if _state["status"] == "running":
            return False
    _run_thread = threading.Thread(target=_run_agent_task, args=(dry_run,), daemon=True)
    _run_thread.start()
    return True


# ── Scheduler ─────────────────────────────────────────────────────────────────
def _start_scheduler() -> None:
    global _scheduler
    from apscheduler.schedulers.background import BackgroundScheduler

    config = load_config()
    hours = config["search"].get("schedule_hours", 1)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_agent_task,
        "interval",
        hours=hours,
        id="linkedin_scout",
        next_run_time=datetime.now(),  # run immediately on first start
    )
    _scheduler.start()

    next_dt = _scheduler.get_job("linkedin_scout").next_run_time
    _set_state(
        scheduler_running=True,
        next_run_at=next_dt.strftime("%d/%m/%Y %H:%M:%S") if next_dt else None,
    )


def _stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    _set_state(scheduler_running=False, next_run_at=None)


# ── Log tail ──────────────────────────────────────────────────────────────────
def _tail_log(n: int = 120) -> str:
    if not LOG_PATH.exists():
        return "No log file yet."
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


# ── HTML template ─────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LinkedIn Job Scout</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #f0f2f5; --card: #fff; --border: #dde1e7;
    --primary: #0077b5; --primary-dark: #005f91;
    --green: #2ecc71; --orange: #f39c12; --red: #e74c3c;
    --text: #1a1a2e; --muted: #6b7280; --code-bg: #1e1e2e; --code-text: #cdd6f4;
  }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }
  a { color: var(--primary); text-decoration: none; }
  a:hover { text-decoration: underline; }

  header {
    background: var(--primary); color: #fff;
    padding: 14px 28px; display: flex; align-items: center; gap: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
  }
  header h1 { font-size: 1.25rem; font-weight: 700; }
  header .badge {
    padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
    background: rgba(255,255,255,.2); letter-spacing: .04em;
  }
  header .badge.running { background: #f39c12; }
  header .badge.error   { background: #e74c3c; }

  .container { max-width: 1100px; margin: 24px auto; padding: 0 20px; display: grid; gap: 20px; }

  .card { background: var(--card); border-radius: 10px; border: 1px solid var(--border);
          box-shadow: 0 1px 4px rgba(0,0,0,.06); padding: 20px; }
  .card h2 { font-size: .95rem; font-weight: 700; color: var(--muted); text-transform: uppercase;
             letter-spacing: .06em; margin-bottom: 14px; }

  .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
  .stat { background: var(--bg); border-radius: 8px; padding: 14px 16px; text-align: center; }
  .stat .value { font-size: 1.8rem; font-weight: 700; color: var(--primary); }
  .stat .label { font-size: .75rem; color: var(--muted); margin-top: 2px; }

  .controls { display: flex; flex-wrap: wrap; gap: 10px; }
  button {
    padding: 9px 18px; border-radius: 6px; border: none; font-size: .875rem; font-weight: 600;
    cursor: pointer; transition: background .15s, transform .1s;
  }
  button:active { transform: scale(.97); }
  .btn-primary  { background: var(--primary); color: #fff; }
  .btn-primary:hover  { background: var(--primary-dark); }
  .btn-success  { background: var(--green); color: #fff; }
  .btn-success:hover  { background: #27ae60; }
  .btn-warning  { background: var(--orange); color: #fff; }
  .btn-warning:hover  { background: #d68910; }
  .btn-danger   { background: var(--red); color: #fff; }
  .btn-danger:hover   { background: #c0392b; }
  .btn-outline  { background: transparent; color: var(--primary); border: 1px solid var(--primary); }
  .btn-outline:hover  { background: #e8f4fb; }
  button:disabled { opacity: .5; cursor: not-allowed; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 680px) { .two-col { grid-template-columns: 1fr; } }

  .form-group { margin-bottom: 14px; }
  .form-group label { display: block; font-size: .8rem; font-weight: 600; color: var(--muted); margin-bottom: 5px; }
  .form-group input, .form-group textarea {
    width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px;
    font-size: .875rem; font-family: inherit; background: var(--bg);
  }
  .form-group input:focus, .form-group textarea:focus { outline: 2px solid var(--primary); border-color: transparent; }
  .form-group textarea { resize: vertical; min-height: 70px; }

  table { width: 100%; border-collapse: collapse; }
  thead th { text-align: right; padding: 10px 12px; background: var(--bg);
             font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
  tbody tr:hover { background: #f9fafb; }
  tbody td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  .score-badge {
    display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: .8rem; font-weight: 700; color: #fff;
  }
  .emailed-yes { color: var(--green); font-weight: 700; }
  .emailed-no  { color: var(--muted); }

  #log-box {
    background: var(--code-bg); color: var(--code-text); border-radius: 8px; padding: 14px;
    font-family: 'Consolas', 'Courier New', monospace; font-size: .75rem;
    line-height: 1.55; max-height: 340px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;
  }
  .log-actions { display: flex; justify-content: flex-end; margin-bottom: 8px; gap: 8px; }

  #toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: #1a1a2e; color: #fff; padding: 10px 22px; border-radius: 8px;
    font-size: .875rem; opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 999;
  }
  #toast.show { opacity: 1; }

  .info-row { display: flex; flex-wrap: wrap; gap: 18px; font-size: .82rem; color: var(--muted); }
  .info-row span strong { color: var(--text); }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 6px; }
  .dot.idle    { background: var(--green); }
  .dot.running { background: var(--orange); animation: pulse 1s infinite; }
  .dot.error   { background: var(--red); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
</style>
</head>
<body>

<header>
  <span style="font-size:1.5rem;">🔍</span>
  <h1>LinkedIn Job Scout</h1>
  <span class="badge {{ state.status }}" id="status-badge">{{ state.status | upper }}</span>
</header>

<div class="container">

  <!-- Stats row -->
  <div class="card">
    <h2>סטטיסטיקות</h2>
    <div class="stats-row" id="stats-row">
      <div class="stat"><div class="value">{{ stats.total_seen }}</div><div class="label">משרות שנצפו</div></div>
      <div class="stat"><div class="value">{{ stats.total_emailed }}</div><div class="label">משרות שנשלחו</div></div>
      <div class="stat">
        <div class="value" style="font-size:1rem; margin-top:4px;" id="last-run-val">
          {{ state.last_run_at or '—' }}
        </div>
        <div class="label">הרצה אחרונה</div>
      </div>
      <div class="stat">
        <div class="value" style="font-size:1rem; margin-top:4px;" id="next-run-val">
          {{ state.next_run_at or '—' }}
        </div>
        <div class="label">הרצה הבאה (scheduler)</div>
      </div>
    </div>
    {% if state.error %}
    <p style="color:var(--red); margin-top:12px; font-size:.85rem;">⚠️ שגיאה: {{ state.error }}</p>
    {% endif %}
  </div>

  <!-- Controls + Config -->
  <div class="two-col">

    <!-- Controls -->
    <div class="card">
      <h2>שליטה</h2>
      <div class="controls" style="margin-bottom:20px;">
        <button class="btn-primary" id="btn-run" onclick="triggerRun(false)">▶ הרץ עכשיו</button>
        <button class="btn-outline" id="btn-dry" onclick="triggerRun(true)">🔍 Dry Run</button>
      </div>
      <hr style="border:none; border-top:1px solid var(--border); margin-bottom:16px;">
      <div class="controls">
        <button class="btn-success" id="btn-sched-start" onclick="schedulerAction('start')">⏰ הפעל Scheduler</button>
        <button class="btn-danger"  id="btn-sched-stop"  onclick="schedulerAction('stop')">⛔ עצור Scheduler</button>
      </div>
      <p style="font-size:.78rem; color:var(--muted); margin-top:10px;">
        Scheduler מריץ את הסוכן אוטומטית כל N שעות (מוגדר ב-config).
      </p>

      {% if state.last_results %}
      <hr style="border:none; border-top:1px solid var(--border); margin:16px 0;">
      <h2>תוצאות הרצה אחרונה</h2>
      <div class="info-row" style="margin-top:6px;">
        <span>נמצאו: <strong>{{ state.last_results.found }}</strong></span>
        <span>רלוונטיות: <strong>{{ state.last_results.relevant }}</strong></span>
        <span>נשלחו: <strong>{{ '—' if state.last_results.dry_run else state.last_results.emailed }}</strong></span>
        {% if state.last_results.dry_run %}<span style="color:var(--orange);">⚠️ Dry Run – מייל לא נשלח</span>{% endif %}
      </div>
      {% endif %}
    </div>

    <!-- Config editor -->
    <div class="card">
      <h2>הגדרות</h2>
      <div class="form-group">
        <label>מילות חיפוש (שורה לכל מילה)</label>
        <textarea id="cfg-keywords" rows="4">{{ config.search.keywords | join('\\n') }}</textarea>
      </div>
      <div class="form-group">
        <label>ציון מינימלי לשליחה (0–100)</label>
        <input type="number" id="cfg-score" min="0" max="100" value="{{ config.filter.min_relevance_score }}">
      </div>
      <div class="form-group">
        <label>Scheduler – כל כמה שעות?</label>
        <input type="number" id="cfg-hours" min="1" max="24" value="{{ config.search.schedule_hours }}">
      </div>
      <div class="form-group">
        <label>מקסימום משרות לריצה</label>
        <input type="number" id="cfg-maxjobs" min="1" max="200" value="{{ config.search.max_jobs_per_run }}">
      </div>
      <button class="btn-primary" onclick="saveConfig()">💾 שמור הגדרות</button>
    </div>

  </div>

  <!-- Recent jobs -->
  <div class="card">
    <h2>משרות אחרונות ({{ recent_jobs | length }})</h2>
    {% if recent_jobs %}
    <div style="overflow-x:auto;">
    <table>
      <thead>
        <tr>
          <th>תפקיד</th>
          <th>חברה</th>
          <th>מיקום</th>
          <th style="text-align:center;">ציון</th>
          <th>סיבה</th>
          <th style="text-align:center;">נשלח?</th>
          <th>נצפה ב</th>
        </tr>
      </thead>
      <tbody>
        {% for job in recent_jobs %}
        <tr>
          <td><a href="{{ job.apply_url }}" target="_blank">{{ job.title }}</a></td>
          <td>{{ job.company }}</td>
          <td style="color:var(--muted); font-size:.8rem;">{{ job.location }}</td>
          <td style="text-align:center;">
            {% if job.score %}
              {% set color = '#2ecc71' if job.score >= 85 else '#f39c12' if job.score >= 70 else '#e74c3c' %}
              <span class="score-badge" style="background:{{ color }};">{{ job.score }}</span>
            {% else %}
              <span style="color:var(--muted);">—</span>
            {% endif %}
          </td>
          <td style="font-size:.8rem; color:var(--muted);">{{ job.reason or '—' }}</td>
          <td style="text-align:center;">
            {% if job.emailed %}
              <span class="emailed-yes">✓</span>
            {% else %}
              <span class="emailed-no">—</span>
            {% endif %}
          </td>
          <td style="font-size:.75rem; color:var(--muted); white-space:nowrap;">{{ job.seen_at[:16] if job.seen_at else '—' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    </div>
    {% else %}
    <p style="color:var(--muted);">אין משרות במסד הנתונים עדיין.</p>
    {% endif %}
  </div>

  <!-- Logs -->
  <div class="card">
    <h2>לוג</h2>
    <div class="log-actions">
      <button class="btn-outline" onclick="refreshLog()">🔄 רענן</button>
    </div>
    <div id="log-box">{{ log }}</div>
  </div>

</div>

<div id="toast"></div>

<script>
  function toast(msg, ms=2800) {
    const el = document.getElementById('toast');
    el.textContent = msg; el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), ms);
  }

  async function triggerRun(dry) {
    const id = dry ? 'btn-dry' : 'btn-run';
    document.getElementById(id).disabled = true;
    toast(dry ? '🔍 Dry run מתחיל...' : '▶ הרצה מתחילה...');
    await fetch('/api/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({dry_run: dry}) });
    pollState();
  }

  async function schedulerAction(action) {
    await fetch('/api/scheduler/' + action, { method:'POST' });
    toast(action === 'start' ? '⏰ Scheduler הופעל' : '⛔ Scheduler עצר');
    pollState();
  }

  async function saveConfig() {
    const keywords = document.getElementById('cfg-keywords').value
      .split('\\n').map(k => k.trim()).filter(Boolean);
    const payload = {
      keywords,
      min_relevance_score: parseInt(document.getElementById('cfg-score').value),
      schedule_hours: parseInt(document.getElementById('cfg-hours').value),
      max_jobs_per_run: parseInt(document.getElementById('cfg-maxjobs').value),
    };
    const r = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const d = await r.json();
    toast(d.saved ? '✅ הגדרות נשמרו' : '❌ שגיאה בשמירה');
  }

  async function refreshLog() {
    const r = await fetch('/api/logs');
    const d = await r.json();
    const box = document.getElementById('log-box');
    box.textContent = d.log;
    box.scrollTop = box.scrollHeight;
  }

  let _polling = false;
  async function pollState() {
    if (_polling) return;
    _polling = true;
    const tick = async () => {
      try {
        const r = await fetch('/api/state');
        const s = await r.json();

        // Badge
        const badge = document.getElementById('status-badge');
        badge.textContent = s.status.toUpperCase();
        badge.className = 'badge ' + s.status;

        document.getElementById('last-run-val').textContent = s.last_run_at || '—';
        document.getElementById('next-run-val').textContent = s.next_run_at || '—';

        // Buttons
        const running = s.status === 'running';
        document.getElementById('btn-run').disabled = running;
        document.getElementById('btn-dry').disabled = running;
        document.getElementById('btn-sched-start').disabled = s.scheduler_running;
        document.getElementById('btn-sched-stop').disabled = !s.scheduler_running;

        if (running) {
          setTimeout(tick, 3000);
        } else {
          _polling = false;
          if (s.status === 'idle' && s.last_results) {
            refreshLog();
            setTimeout(() => location.reload(), 1500); // reload to update jobs table
          }
        }
      } catch { _polling = false; }
    };
    tick();
  }

  // Scroll log to bottom on load
  window.addEventListener('load', () => {
    const box = document.getElementById('log-box');
    box.scrollTop = box.scrollHeight;
    // Disable buttons based on initial state
    const schedulerRunning = {{ 'true' if state.scheduler_running else 'false' }};
    document.getElementById('btn-sched-start').disabled = schedulerRunning;
    document.getElementById('btn-sched-stop').disabled = !schedulerRunning;
  });
</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    tracker.init_db()
    return render_template_string(
        HTML,
        state=_get_state(),
        stats=tracker.get_stats(),
        recent_jobs=tracker.get_recent_jobs(limit=30),
        config=load_config(),
        log=_tail_log(120),
    )


@app.route("/api/run", methods=["POST"])
def api_run():
    dry_run = (request.get_json(silent=True) or {}).get("dry_run", False)
    started = _start_run(dry_run=dry_run)
    return jsonify({"started": started, "dry_run": dry_run})


@app.route("/api/scheduler/start", methods=["POST"])
def api_scheduler_start():
    state = _get_state()
    if not state["scheduler_running"]:
        _start_scheduler()
    return jsonify({"scheduler_running": True})


@app.route("/api/scheduler/stop", methods=["POST"])
def api_scheduler_stop():
    _stop_scheduler()
    return jsonify({"scheduler_running": False})


@app.route("/api/config", methods=["GET"])
def api_config_get():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def api_config_save():
    data = request.get_json(silent=True) or {}
    config = load_config()
    if "keywords" in data:
        config["search"]["keywords"] = data["keywords"]
    if "min_relevance_score" in data:
        config["filter"]["min_relevance_score"] = int(data["min_relevance_score"])
    if "schedule_hours" in data:
        config["search"]["schedule_hours"] = int(data["schedule_hours"])
    if "max_jobs_per_run" in data:
        config["search"]["max_jobs_per_run"] = int(data["max_jobs_per_run"])
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return jsonify({"saved": True})


@app.route("/api/state")
def api_state():
    return jsonify(_get_state())


@app.route("/api/logs")
def api_logs():
    return jsonify({"log": _tail_log(120)})


@app.route("/api/stats")
def api_stats():
    tracker.init_db()
    return jsonify(tracker.get_stats())


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tracker.init_db()
    LOG_PATH.parent.mkdir(exist_ok=True)
    print("LinkedIn Job Scout UI running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
