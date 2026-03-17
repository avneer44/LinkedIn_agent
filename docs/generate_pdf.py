"""
generate_pdf.py - Generate a Hebrew architecture PDF for LinkedIn Job Scout
Uses Google Chrome headless to render HTML → PDF.
"""

import subprocess
import tempfile
from pathlib import Path

HTML_CONTENT = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;800&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Heebo', Arial, sans-serif;
    color: #1a1a2e;
    background: #fff;
    font-size: 13px;
    line-height: 1.7;
    direction: rtl;
  }

  /* ── Cover Page ── */
  .cover {
    height: 100vh;
    background: linear-gradient(135deg, #0077b5 0%, #005f91 60%, #003d60 100%);
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 60px;
    page-break-after: always;
  }
  .cover .icon { font-size: 80px; margin-bottom: 24px; }
  .cover h1 { font-size: 42px; font-weight: 800; margin-bottom: 12px; letter-spacing: -0.5px; }
  .cover .subtitle { font-size: 20px; font-weight: 300; opacity: 0.9; margin-bottom: 40px; }
  .cover .divider { width: 80px; height: 3px; background: rgba(255,255,255,0.4); margin: 0 auto 40px; }
  .cover .desc {
    font-size: 15px; font-weight: 300; opacity: 0.85; max-width: 600px;
    line-height: 1.8;
  }
  .cover .date { margin-top: 50px; font-size: 12px; opacity: 0.6; }

  /* ── Page layout ── */
  .page {
    max-width: 780px;
    margin: 0 auto;
    padding: 50px 60px;
  }

  /* ── TOC ── */
  .toc-page { page-break-after: always; }
  .toc-title {
    font-size: 28px; font-weight: 800; color: #0077b5;
    border-bottom: 3px solid #0077b5; padding-bottom: 12px; margin-bottom: 30px;
  }
  .toc-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px dotted #ddd; font-size: 14px;
  }
  .toc-item .num { color: #0077b5; font-weight: 700; margin-left: 12px; }
  .toc-section { font-weight: 600; color: #1a1a2e; }
  .toc-sub { padding-right: 20px; color: #555; font-size: 13px; }

  /* ── Section headers ── */
  .section-header {
    background: linear-gradient(135deg, #0077b5, #005f91);
    color: white;
    padding: 18px 24px;
    border-radius: 10px;
    margin-bottom: 24px;
    margin-top: 40px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .section-header .icon { font-size: 26px; }
  .section-header h2 { font-size: 22px; font-weight: 700; }
  .section-header .num { font-size: 13px; opacity: 0.8; margin-top: 2px; }

  h3 {
    font-size: 16px; font-weight: 700; color: #0077b5;
    margin: 24px 0 10px; border-right: 4px solid #0077b5; padding-right: 10px;
  }
  h4 { font-size: 14px; font-weight: 600; color: #333; margin: 16px 0 8px; }
  p { margin-bottom: 12px; color: #333; }

  /* ── Component cards ── */
  .component-card {
    border: 1px solid #e0e7ef;
    border-radius: 12px;
    padding: 22px 24px;
    margin-bottom: 24px;
    background: #f9fbfd;
    page-break-inside: avoid;
  }
  .component-card .card-header {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
  }
  .component-card .card-icon {
    width: 44px; height: 44px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
  }
  .component-card .card-title { font-size: 17px; font-weight: 700; color: #1a1a2e; }
  .component-card .card-file { font-size: 11px; color: #0077b5; font-family: 'Courier New', monospace; }

  /* ── Highlight boxes ── */
  .highlight-box {
    border-radius: 8px; padding: 14px 18px; margin: 14px 0;
  }
  .highlight-box.info { background: #e8f4fb; border-right: 4px solid #0077b5; }
  .highlight-box.success { background: #eafaf1; border-right: 4px solid #2ecc71; }
  .highlight-box.warning { background: #fef9e7; border-right: 4px solid #f39c12; }
  .highlight-box.danger { background: #fdedec; border-right: 4px solid #e74c3c; }
  .highlight-box p { margin: 0; font-size: 13px; }
  .highlight-box strong { display: block; margin-bottom: 4px; font-size: 13px; }

  /* ── Code blocks ── */
  .code-block {
    background: #1e1e2e; color: #cdd6f4;
    border-radius: 8px; padding: 14px 18px;
    font-family: 'Courier New', monospace; font-size: 11.5px;
    line-height: 1.6; margin: 14px 0; direction: ltr; text-align: left;
    overflow: hidden;
  }
  .code-block .comment { color: #6272a4; }
  .code-block .keyword { color: #ff79c6; }
  .code-block .string { color: #f1fa8c; }

  /* ── Tables ── */
  table {
    width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 12.5px;
  }
  th {
    background: #0077b5; color: white; padding: 10px 12px; text-align: right;
    font-weight: 600;
  }
  td { padding: 9px 12px; border-bottom: 1px solid #e8ecf0; color: #333; }
  tr:nth-child(even) td { background: #f5f8fb; }
  tr:hover td { background: #e8f4fb; }

  /* ── Flow diagram ── */
  .flow {
    display: flex; align-items: center; gap: 0;
    background: #f0f7ff; border-radius: 10px; padding: 20px; margin: 20px 0;
    flex-wrap: wrap; justify-content: center;
  }
  .flow-step {
    background: white; border: 2px solid #0077b5; border-radius: 8px;
    padding: 10px 16px; text-align: center; font-size: 12px; font-weight: 600;
    color: #0077b5; min-width: 100px;
  }
  .flow-step .step-icon { font-size: 18px; display: block; margin-bottom: 4px; }
  .flow-arrow { font-size: 20px; color: #0077b5; margin: 0 6px; }

  /* ── List styles ── */
  ul, ol { padding-right: 20px; margin: 10px 0; }
  li { margin-bottom: 6px; color: #333; }
  li::marker { color: #0077b5; }

  /* ── Badge ── */
  .badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; color: white; margin: 2px;
  }
  .badge.blue { background: #0077b5; }
  .badge.green { background: #2ecc71; }
  .badge.orange { background: #f39c12; }
  .badge.red { background: #e74c3c; }
  .badge.gray { background: #6b7280; }

  /* ── Score indicator ── */
  .score-row {
    display: flex; align-items: center; gap: 10px; margin: 6px 0; font-size: 13px;
  }
  .score-bar {
    flex: 1; height: 8px; border-radius: 4px; background: #e0e0e0; overflow: hidden;
  }
  .score-fill { height: 100%; border-radius: 4px; }

  /* ── File tree ── */
  .file-tree {
    background: #1e1e2e; color: #cdd6f4; border-radius: 8px;
    padding: 16px 20px; font-family: 'Courier New', monospace; font-size: 12px;
    line-height: 1.8; direction: ltr; text-align: left;
  }
  .file-tree .folder { color: #89dceb; }
  .file-tree .py-file { color: #a6e3a1; }
  .file-tree .yaml-file { color: #f9e2af; }
  .file-tree .txt-file { color: #cba6f7; }
  .file-tree .comment { color: #6272a4; }

  /* ── Page break ── */
  .page-break { page-break-before: always; }

  /* ── Two column ── */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 14px 0; }

  /* ── Summary box ── */
  .summary-box {
    background: linear-gradient(135deg, #0077b5 0%, #005f91 100%);
    color: white; border-radius: 12px; padding: 24px; margin: 20px 0;
  }
  .summary-box h3 { color: white; border: none; padding: 0; margin-top: 0; }
  .summary-box p { color: rgba(255,255,255,0.9); }
  .summary-box ul { padding-right: 16px; }
  .summary-box li { color: rgba(255,255,255,0.9); }

  /* ── Print ── */
  @media print {
    .page-break { page-break-before: always; }
    .cover { page-break-after: always; }
  }
</style>
</head>
<body>

<!-- ══════════════════════════════════════════════════════════
     COVER PAGE
══════════════════════════════════════════════════════════ -->
<div class="cover">
  <div class="icon">🔍</div>
  <h1>LinkedIn Job Scout</h1>
  <div class="subtitle">סוכן חיפוש עבודה אוטומטי מבוסס בינה מלאכותית</div>
  <div class="divider"></div>
  <div class="desc">
    מסמך ארכיטקטורה מפורט המתאר את מבנה המוצר, רכיביו,
    וכיצד הם עובדים יחד כדי למצוא, לדרג ולשלוח עדכוני משרות
    באופן אוטומטי — בלי שתצטרך לחפש בעצמך.
  </div>
  <div class="date">מרץ 2026</div>
</div>


<!-- ══════════════════════════════════════════════════════════
     TABLE OF CONTENTS
══════════════════════════════════════════════════════════ -->
<div class="page toc-page">
  <div class="toc-title">תוכן עניינים</div>

  <div class="toc-item">
    <span><span class="num">1.</span><span class="toc-section"> מה זה LinkedIn Job Scout?</span></span>
    <span style="color:#999">3</span>
  </div>
  <div class="toc-item toc-sub">
    <span>המטרה והבעיה שהוא פותר</span>
  </div>
  <div class="toc-item toc-sub">
    <span>איך זה עובד ברמה הגבוהה</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">2.</span><span class="toc-section"> ארכיטקטורה ומבנה הקבצים</span></span>
    <span style="color:#999">4</span>
  </div>
  <div class="toc-item toc-sub">
    <span>מבנה תיקיות הפרויקט</span>
  </div>
  <div class="toc-item toc-sub">
    <span>תרשים זרימה — מה קורה בכל ריצה</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">3.</span><span class="toc-section"> רכיב 1: main.py — המוח המרכזי</span></span>
    <span style="color:#999">5</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">4.</span><span class="toc-section"> רכיב 2: auth.py — מודול ההתחברות</span></span>
    <span style="color:#999">6</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">5.</span><span class="toc-section"> רכיב 3: searcher.py — מנוע החיפוש</span></span>
    <span style="color:#999">7</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">6.</span><span class="toc-section"> רכיב 4: filter.py — מנוע הדירוג (AI)</span></span>
    <span style="color:#999">9</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">7.</span><span class="toc-section"> רכיב 5: notifier.py — שולח המיילים</span></span>
    <span style="color:#999">11</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">8.</span><span class="toc-section"> רכיב 6: tracker.py — מסד הנתונים</span></span>
    <span style="color:#999">12</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">9.</span><span class="toc-section"> רכיב 7: app.py — ממשק הניהול</span></span>
    <span style="color:#999">13</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">10.</span><span class="toc-section"> config.yaml ו-‎.env — קבצי ההגדרות</span></span>
    <span style="color:#999">15</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">11.</span><span class="toc-section"> הגנה מפני זיהוי כבוט</span></span>
    <span style="color:#999">16</span>
  </div>

  <div class="toc-item" style="margin-top:8px;">
    <span><span class="num">12.</span><span class="toc-section"> מדריך התקנה והפעלה</span></span>
    <span style="color:#999">17</span>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 1 — WHAT IS IT
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">💡</span>
    <div>
      <div class="num">פרק 1</div>
      <h2>מה זה LinkedIn Job Scout?</h2>
    </div>
  </div>

  <h3>הבעיה שהמוצר פותר</h3>
  <p>
    חיפוש עבודה ב-LinkedIn הוא תהליך מתסכל: צריך להיכנס מדי יום, לחפש, לסנן,
    ולקרוא דסות פרסומים — רובם לא מתאימים. LinkedIn Job Scout אוטומט את כל הפרק הזה.
  </p>
  <p>
    הסוכן מתחבר ל-LinkedIn בשמך, מחפש משרות לפי הקריטריונים שלך, שולח כל משרה
    לבינה מלאכותית שמדרגת אותה מ-0 עד 100 ביחס ל-CV שלך, ואז שולח לך מייל
    עם רק המשרות הכי רלוונטיות — אתה רק בוחר לאיזה מהן להגיש מועמדות.
  </p>

  <div class="highlight-box success">
    <strong>✅ מה הסוכן עושה בשבילך:</strong>
    <p>מחפש משרות חדשות → קורא את תיאור כל משרה → מדרג כל משרה עם Claude AI → שולח מייל עם המשרות הטובות ביותר → לא שולח את אותה משרה פעמיים</p>
  </div>

  <div class="highlight-box warning">
    <strong>⚠️ מה הסוכן לא עושה:</strong>
    <p>הסוכן לא מגיש מועמדות בשמך. הוא רק מוצא ומסנן משרות. ההחלטה אם להגיש ואיך להגיש — נשארת אצלך.</p>
  </div>

  <h3>איך זה עובד ברמה הגבוהה</h3>
  <p>פעם אחת בשעה (או לפי הגדרה), הסוכן מבצע את הצעדים הבאים:</p>

  <div style="display:flex; flex-direction:column; gap:10px; margin:16px 0;">
    <div style="display:flex; align-items:flex-start; gap:12px; background:#f0f7ff; border-radius:8px; padding:12px 16px;">
      <span style="font-size:22px; flex-shrink:0;">1️⃣</span>
      <div><strong>מתחבר ל-LinkedIn</strong> — נפתח דפדפן (Chromium) ומתחבר עם הפרטים שלך. אם כבר מחובר מריצה קודמת, משתמש בעוגיות השמורות.</div>
    </div>
    <div style="display:flex; align-items:flex-start; gap:12px; background:#f0f7ff; border-radius:8px; padding:12px 16px;">
      <span style="font-size:22px; flex-shrink:0;">2️⃣</span>
      <div><strong>מחפש משרות</strong> — מבצע חיפוש לפי מילות המפתח שהגדרת (לדוגמה: "Software Engineer", "Python Developer") ומסנן לפי מיקום ורמת ניסיון.</div>
    </div>
    <div style="display:flex; align-items:flex-start; gap:12px; background:#f0f7ff; border-radius:8px; padding:12px 16px;">
      <span style="font-size:22px; flex-shrink:0;">3️⃣</span>
      <div><strong>אוסף פרטים</strong> — לכל משרה חדשה שלא ראה בעבר, נכנס לדף המשרה וקורא את התיאור המלא.</div>
    </div>
    <div style="display:flex; align-items:flex-start; gap:12px; background:#f0f7ff; border-radius:8px; padding:12px 16px;">
      <span style="font-size:22px; flex-shrink:0;">4️⃣</span>
      <div><strong>מדרג עם AI</strong> — שולח כל משרה + ה-CV שלך לבינה המלאכותית Claude, שמחזירה ציון 0-100 והסבר בעברית.</div>
    </div>
    <div style="display:flex; align-items:flex-start; gap:12px; background:#f0f7ff; border-radius:8px; padding:12px 16px;">
      <span style="font-size:22px; flex-shrink:0;">5️⃣</span>
      <div><strong>שולח מייל</strong> — רק משרות עם ציון גבוה מהסף שהגדרת נשלחות אליך במייל מעוצב. כל משרה נשלחת רק פעם אחת.</div>
    </div>
  </div>

  <div class="highlight-box info">
    <strong>🤖 הטכנולוגיות בשימוש:</strong>
    <p>
      <span class="badge blue">Python</span>
      <span class="badge blue">Playwright</span>
      <span class="badge blue">Claude AI</span>
      <span class="badge blue">SQLite</span>
      <span class="badge blue">Flask</span>
      <span class="badge blue">Gmail SMTP</span>
    </p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 2 — ARCHITECTURE
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🏗️</span>
    <div>
      <div class="num">פרק 2</div>
      <h2>ארכיטקטורה ומבנה הקבצים</h2>
    </div>
  </div>

  <h3>מבנה תיקיות הפרויקט</h3>

  <div class="file-tree">
<span class="folder">LinkedIn/                        </span><span class="comment"># תיקיית הפרויקט הראשית</span>
│
├── <span class="py-file">main.py</span>                      <span class="comment"># נקודת הכניסה — מריץ הכל</span>
├── <span class="py-file">app.py</span>                       <span class="comment"># ממשק ניהול ווב (Flask)</span>
├── <span class="yaml-file">config.yaml</span>                  <span class="comment"># הגדרות: מילות חיפוש, ציון מינימלי...</span>
├── <span class="txt-file">.env</span>                         <span class="comment"># סיסמאות ומפתחות API (פרטי!)</span>
├── <span class="txt-file">cv.txt</span>                       <span class="comment"># ה-CV שלך (טקסט פשוט)</span>
├── <span class="txt-file">requirements.txt</span>             <span class="comment"># רשימת ספריות Python</span>
│
├── <span class="folder">src/                         </span><span class="comment"># מודולים עיקריים</span>
│   ├── <span class="py-file">auth.py</span>              <span class="comment"># התחברות ל-LinkedIn</span>
│   ├── <span class="py-file">searcher.py</span>          <span class="comment"># חיפוש וסריקת משרות</span>
│   ├── <span class="py-file">filter.py</span>            <span class="comment"># דירוג עם Claude AI</span>
│   ├── <span class="py-file">notifier.py</span>          <span class="comment"># שליחת מיילים</span>
│   └── <span class="py-file">tracker.py</span>           <span class="comment"># מסד נתונים SQLite</span>
│
├── <span class="folder">data/</span>                        <span class="comment"># נתונים שנוצרים בזמן ריצה</span>
│   ├── <span class="txt-file">jobs.db</span>              <span class="comment"># מסד נתונים של כל המשרות</span>
│   └── <span class="txt-file">session.json</span>         <span class="comment"># עוגיות LinkedIn שמורות</span>
│
└── <span class="folder">logs/</span>
    └── <span class="txt-file">agent.log</span>            <span class="comment"># לוג של כל הריצות</span>
  </div>

  <h3>תרשים זרימה — מה קורה בכל ריצה</h3>
  <p>הפייפליין הוא רצף קבוע שמריץ כל רכיב בזה אחר זה:</p>

  <div style="margin: 20px 0;">
    <div style="display:flex; flex-direction:column; gap:0; align-items:center;">

      <div style="background:white; border:2px solid #0077b5; border-radius:10px; padding:14px 20px; width:380px; text-align:center; box-shadow:0 2px 6px rgba(0,119,181,0.15);">
        <div style="font-size:22px;">🌐</div>
        <div style="font-weight:700; color:#0077b5; font-size:14px;">auth.py — ensure_logged_in()</div>
        <div style="font-size:11px; color:#666; margin-top:4px;">פותח דפדפן ומתחבר ל-LinkedIn</div>
      </div>

      <div style="font-size:24px; color:#0077b5; line-height:1.2;">↓</div>

      <div style="background:white; border:2px solid #0077b5; border-radius:10px; padding:14px 20px; width:380px; text-align:center; box-shadow:0 2px 6px rgba(0,119,181,0.15);">
        <div style="font-size:22px;">🔎</div>
        <div style="font-weight:700; color:#0077b5; font-size:14px;">searcher.py — search_jobs()</div>
        <div style="font-size:11px; color:#666; margin-top:4px;">מחפש משרות חדשות ואוסף תיאורים</div>
      </div>

      <div style="font-size:24px; color:#0077b5; line-height:1.2;">↓</div>

      <div style="background:#fef9e7; border:2px dashed #f39c12; border-radius:10px; padding:10px 20px; width:380px; text-align:center;">
        <div style="font-size:11px; color:#888;">🔒 הדפדפן נסגר כאן — המשך ללא דפדפן</div>
      </div>

      <div style="font-size:24px; color:#0077b5; line-height:1.2;">↓</div>

      <div style="background:white; border:2px solid #0077b5; border-radius:10px; padding:14px 20px; width:380px; text-align:center; box-shadow:0 2px 6px rgba(0,119,181,0.15);">
        <div style="font-size:22px;">💾</div>
        <div style="font-weight:700; color:#0077b5; font-size:14px;">tracker.py — mark_seen()</div>
        <div style="font-size:11px; color:#666; margin-top:4px;">שומר את כל המשרות שנמצאו ב-DB</div>
      </div>

      <div style="font-size:24px; color:#0077b5; line-height:1.2;">↓</div>

      <div style="background:white; border:2px solid #0077b5; border-radius:10px; padding:14px 20px; width:380px; text-align:center; box-shadow:0 2px 6px rgba(0,119,181,0.15);">
        <div style="font-size:22px;">🤖</div>
        <div style="font-weight:700; color:#0077b5; font-size:14px;">filter.py — filter_jobs()</div>
        <div style="font-size:11px; color:#666; margin-top:4px;">שולח לClaude AI לדירוג — מסנן מה מתחת לסף</div>
      </div>

      <div style="font-size:24px; color:#0077b5; line-height:1.2;">↓</div>

      <div style="background:white; border:2px solid #0077b5; border-radius:10px; padding:14px 20px; width:380px; text-align:center; box-shadow:0 2px 6px rgba(0,119,181,0.15);">
        <div style="font-size:22px;">📧</div>
        <div style="font-weight:700; color:#0077b5; font-size:14px;">notifier.py — send_digest()</div>
        <div style="font-size:11px; color:#666; margin-top:4px;">בונה ושולח מייל HTML עם המשרות הרלוונטיות</div>
      </div>

    </div>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 3 — main.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🧠</span>
    <div>
      <div class="num">פרק 3</div>
      <h2>main.py — המוח המרכזי</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#e8f4fb;">🧠</div>
      <div>
        <div class="card-title">main.py — האורכסטרטור</div>
        <div class="card-file">📄 main.py (192 שורות)</div>
      </div>
    </div>
    <p>
      זהו הקובץ הראשי — "המנהל" שמפעיל את כל שאר הרכיבים בסדר הנכון.
      הוא לא עושה שום דבר בעצמו — הוא רק מתאם בין כל המודולים.
    </p>
  </div>

  <h3>שלושה מצבי הפעלה</h3>

  <div class="two-col">
    <div class="highlight-box info">
      <strong>🔁 מצב Scheduler (ברירת מחדל)</strong>
      <p><code>python main.py</code></p>
      <p>מריץ את הסוכן מיד ואז שוב כל N שעות (לפי הגדרה). רץ ברקע עד שמפסיקים ידנית.</p>
    </div>
    <div class="highlight-box success">
      <strong>▶ ריצה חד-פעמית</strong>
      <p><code>python main.py --once</code></p>
      <p>מריץ פעם אחת, שולח מייל, ומסיים. שימושי לבדיקה ידנית.</p>
    </div>
  </div>
  <div class="highlight-box warning">
    <strong>🔍 Dry Run — ריצת בדיקה ללא מייל</strong>
    <p><code>python main.py --dry-run</code></p>
    <p>עושה הכל — חיפוש, דירוג — אך לא שולח מייל. מדפיס את התוצאות לטרמינל. מצוין לבדיקת הגדרות לפני שמתחילים "אמיתי".</p>
  </div>

  <h3>הפונקציה run_agent() — לוגיקת הריצה</h3>
  <p>זוהי הפונקציה המרכזית שמנהלת כל ריצה. הנה מה שהיא עושה שלב אחר שלב:</p>

  <table>
    <thead>
      <tr><th>#</th><th>שלב</th><th>מה קורה</th><th>מי עושה</th></tr>
    </thead>
    <tbody>
      <tr><td>1</td><td>אתחול DB</td><td>מוודא שמסד הנתונים קיים ותקין</td><td>tracker.init_db()</td></tr>
      <tr><td>2</td><td>טעינת משרות ידועות</td><td>טוען את כל המזהים של משרות שכבר נראו</td><td>tracker.get_all_seen_ids()</td></tr>
      <tr><td>3</td><td>פתיחת דפדפן</td><td>מפעיל Chromium גלוי (לא headless)</td><td>Playwright</td></tr>
      <tr><td>4</td><td>התחברות</td><td>מחובר ל-LinkedIn (עם עוגיות שמורות)</td><td>auth.ensure_logged_in()</td></tr>
      <tr><td>5</td><td>חיפוש</td><td>מחפש משרות חדשות לפי כל מילת מפתח</td><td>searcher.search_jobs()</td></tr>
      <tr><td>6</td><td>סגירת דפדפן</td><td>הדפדפן נסגר — שאר הפעולות ללא דפדפן</td><td>browser.close()</td></tr>
      <tr><td>7</td><td>שמירת משרות</td><td>כל משרה שנמצאה נשמרת כ-"נראתה" בDB</td><td>tracker.mark_seen()</td></tr>
      <tr><td>8</td><td>דירוג AI</td><td>Claude מדרג כל משרה — מסנן לפי ציון</td><td>filter.filter_jobs()</td></tr>
      <tr><td>9</td><td>שליחת מייל</td><td>שולח מייל עם המשרות שעברו את הסף</td><td>notifier.send_digest()</td></tr>
      <tr><td>10</td><td>עדכון DB</td><td>מסמן את המשרות שנשלחו כ-"נשלח"</td><td>tracker.mark_emailed()</td></tr>
    </tbody>
  </table>

  <h3>ה-Scheduler האוטומטי</h3>
  <p>
    כשמריצים ללא דגלים, הסוכן משתמש בספריית <strong>APScheduler</strong> כדי לרוץ
    אוטומטית כל N שעות (לפי <code>schedule_hours</code> ב-config.yaml).
    הריצה הראשונה מתחילה מיידית, ואז ממשיכה לפי לוח הזמנים.
  </p>

  <div class="highlight-box info">
    <strong>📋 לוגינג — כל ריצה מתועדת</strong>
    <p>כל פעולה מוקלטת בלוג <code>logs/agent.log</code> ובנוסף מוצגת בטרמינל.
    הלוג הוא append-only — לא נמחק בין ריצות.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 4 — auth.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🔐</span>
    <div>
      <div class="num">פרק 4</div>
      <h2>auth.py — מודול ההתחברות</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#eafaf1;">🔐</div>
      <div>
        <div class="card-title">auth.py — ניהול סשן LinkedIn</div>
        <div class="card-file">📄 src/auth.py</div>
      </div>
    </div>
    <p>
      מטפל בכל הנוגע לכניסה לחשבון LinkedIn: שמירת עוגיות,
      טעינת סשן קיים, ביצוע התחברות כשצריך, וזיהוי מצבי 2FA.
    </p>
  </div>

  <h3>לוגיקת ה-"Smart Login"</h3>
  <p>
    המודול חכם מספיק לדעת שאין צורך להתחבר בכל פעם.
    הנה הלוגיקה שהוא עוקב אחריה:
  </p>

  <div style="display:flex; flex-direction:column; gap:8px; margin:16px 0;">
    <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#f5f5f5; border-radius:8px;">
      <span style="font-size:18px;">1️⃣</span>
      <div>מנסה לטעון עוגיות שמורות מ-<strong>data/session.json</strong></div>
    </div>
    <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#f5f5f5; border-radius:8px;">
      <span style="font-size:18px;">2️⃣</span>
      <div>נכנס לדף ה-Feed של LinkedIn ובודק אם המשתמש מחובר</div>
    </div>
    <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#eafaf1; border-radius:8px;">
      <span style="font-size:18px;">✅</span>
      <div><strong>אם מחובר:</strong> ממשיך ישר לחיפוש — חוסך זמן וחשד</div>
    </div>
    <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#fef9e7; border-radius:8px;">
      <span style="font-size:18px;">🔑</span>
      <div><strong>אם לא מחובר:</strong> ממלא אוטומטית את שדות המייל וסיסמה ולוחץ כניסה</div>
    </div>
    <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#fdedec; border-radius:8px;">
      <span style="font-size:18px;">🔒</span>
      <div><strong>אם יש 2FA/CAPTCHA:</strong> מחכה 60 שניות לסיום ידני של האימות</div>
    </div>
  </div>

  <h3>עוגיות — מה הן ולמה חשובות</h3>
  <p>
    "עוגיות" (Cookies) הן קבצוני מידע קטנים שהדפדפן שומר אחרי התחברות מוצלחת.
    LinkedIn משתמשת בהן כדי לזהות שאתה מחובר — בלי שתצטרך להתחבר שוב.
  </p>
  <p>
    הסוכן שומר את העוגיות בקובץ JSON אחרי כל התחברות מוצלחת.
    בריצה הבאה הוא "מעמיס" אותן לדפדפן — כאילו נפתח הדפדפן עם הסשן הקיים.
    זה חוסך זמן ומקטין את הסיכוי שLinkedIn "יתפוס" שזה בוט.
  </p>

  <h3>פונקציות עיקריות</h3>
  <table>
    <thead>
      <tr><th>פונקציה</th><th>מה עושה</th></tr>
    </thead>
    <tbody>
      <tr><td><code>ensure_logged_in()</code></td><td>פונקציה ראשית — מריצה את כל הלוגיקה הנ"ל</td></tr>
      <tr><td><code>save_cookies()</code></td><td>שומרת עוגיות לקובץ data/session.json</td></tr>
      <tr><td><code>load_cookies()</code></td><td>טוענת עוגיות מהקובץ לדפדפן</td></tr>
      <tr><td><code>is_logged_in()</code></td><td>בודקת אם הדף הנוכחי מראה משתמש מחובר</td></tr>
      <tr><td><code>login()</code></td><td>מבצעת התחברות מלאה עם שם משתמש וסיסמה</td></tr>
      <tr><td><code>_random_delay()</code></td><td>ממתינה זמן אקראי בין פעולות — נראה אנושי יותר</td></tr>
    </tbody>
  </table>

  <div class="highlight-box warning">
    <strong>⚠️ אבטחה חשובה:</strong>
    <p>פרטי ההתחברות (מייל + סיסמה) לעולם לא מאוחסנים בקוד — הם נקראים רק מקובץ ה-.env שנמצא אצלך בלבד.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 5 — searcher.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🔎</span>
    <div>
      <div class="num">פרק 5</div>
      <h2>searcher.py — מנוע החיפוש</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#f0e6ff;">🔎</div>
      <div>
        <div class="card-title">searcher.py — Web Scraper</div>
        <div class="card-file">📄 src/searcher.py</div>
      </div>
    </div>
    <p>
      המודול שאחראי על חיפוש משרות ב-LinkedIn וקריאת תיאוריהן.
      משתמש ב-<strong>Playwright</strong> — ספרייה שמפעילה דפדפן אמיתי כדי לגלוש
      ב-LinkedIn, ממש כמו שאתה היית עושה — רק אוטומטי.
    </p>
  </div>

  <h3>מה זה Playwright ולמה משתמשים בו?</h3>
  <p>
    Playwright היא ספרייה שמאפשרת לשלוט בדפדפן (Chrome, Firefox) מקוד Python.
    אפשר לנווט לכתובות, ללחוץ כפתורים, למלא טפסים ולקרוא תוכן עמודים —
    הכל אוטומטי. LinkedIn לא מאפשרת גישה ישירה לנתונים שלה דרך API,
    לכן משתמשים בשיטה זו לקרוא את התוכן מהדף עצמו.
  </p>

  <h3>מבנה הנתונים — Job Dataclass</h3>
  <p>כל משרה שנמצאת מיוצגת כאובייקט Python עם השדות הבאים:</p>

  <div class="code-block">
@dataclass
<span class="keyword">class</span> Job:
    job_id: str          <span class="comment"># מזהה ייחודי של LinkedIn (מספרי)</span>
    title: str           <span class="comment"># שם התפקיד</span>
    company: str         <span class="comment"># שם החברה</span>
    location: str        <span class="comment"># מיקום</span>
    description: str     <span class="comment"># תיאור המשרה (מלא)</span>
    apply_url: str       <span class="comment"># קישור להגשת מועמדות</span>
    is_easy_apply: bool  <span class="comment"># האם יש כפתור "Easy Apply" של LinkedIn</span>
  </div>

  <h3>תהליך החיפוש — שלב אחר שלב</h3>

  <h4>שלב א׳ — בניית כתובת החיפוש</h4>
  <p>
    עבור כל מילת מפתח ב-config, הסוכן בונה כתובת URL של LinkedIn עם
    פרמטרים של מיקום, רמת ניסיון, ומשרות שפורסמו בשעה האחרונה:
  </p>
  <div class="code-block">
<span class="comment"># דוגמה לכתובת שנבנית:</span>
https://www.linkedin.com/jobs/search/
  ?keywords=Software+Engineer
  &location=Israel
  &f_E=2%2C3%2C4         <span class="comment"># רמות ניסיון: Entry, Associate, Mid-Senior</span>
  &f_TPR=r3600           <span class="comment"># פורסם בשעה האחרונה</span>
  &sortBy=DD             <span class="comment"># מסודר לפי תאריך (חדש ראשון)</span>
  </div>

  <h4>שלב ב׳ — גלילת הדף וסריקת כרטיסיות</h4>
  <p>
    הסוכן גולל את דף תוצאות החיפוש למטה (כדי שLinkedIn יטען עוד משרות)
    ואז קורא את כל כרטיסיות המשרות שמוצגות.
  </p>

  <h4>שלב ג׳ — סינון כפילויות</h4>
  <p>
    לכל משרה שנמצאת, הסוכן בודק את ה-job_id שלה. אם המזהה כבר קיים
    ב-already_seen (שנטען מה-DB), הוא מדלג עליה. כך לא מבזבזים זמן על
    משרות שכבר עובדו בעבר.
  </p>

  <h4>שלב ד׳ — קריאת תיאורים מלאים</h4>
  <p>
    כרטיסיית המשרה מכילה רק פרטים בסיסיים. כדי שה-AI יוכל לדרג,
    צריך את התיאור המלא. הסוכן נכנס לדף כל משרה בנפרד ומחלץ את הטקסט.
  </p>

  <div class="highlight-box info">
    <strong>⏱️ מגבלת זמן — max_jobs_per_run</strong>
    <p>כדי שהסוכן לא ירוץ יותר מדי זמן, יש מגבלה על כמות המשרות שיעבד בכל ריצה
    (ברירת מחדל: 30). אפשר לשנות ב-config.yaml.</p>
  </div>

  <h3>פונקציות עיקריות</h3>
  <table>
    <thead>
      <tr><th>פונקציה</th><th>מה עושה</th></tr>
    </thead>
    <tbody>
      <tr><td><code>search_jobs()</code></td><td>הפונקציה הראשית — מחזירה רשימת Job objects חדשים</td></tr>
      <tr><td><code>get_job_description()</code></td><td>נכנסת לדף המשרה וחולצת את התיאור המלא</td></tr>
      <tr><td><code>_scrape_job_card()</code></td><td>קוראת נתוני בסיס מכרטיסיית משרה</td></tr>
      <tr><td><code>_build_search_url()</code></td><td>בונה כתובת URL לחיפוש</td></tr>
      <tr><td><code>_extract_job_id()</code></td><td>מחלצת את המזהה המספרי מ-URL</td></tr>
    </tbody>
  </table>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 6 — filter.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🤖</span>
    <div>
      <div class="num">פרק 6</div>
      <h2>filter.py — מנוע הדירוג (AI)</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#fef0e6;">🤖</div>
      <div>
        <div class="card-title">filter.py — Claude AI Scoring</div>
        <div class="card-file">📄 src/filter.py</div>
      </div>
    </div>
    <p>
      זהו "הלב החכם" של הסוכן. עבור כל משרה חדשה, מודול זה שולח בקשה
      ל-Claude AI עם ה-CV שלך ותיאור המשרה. Claude מחזיר ציון 0-100
      והסבר בעברית. רק משרות שמקבלות ציון מעל הסף עוברות לשליחה במייל.
    </p>
  </div>

  <h3>איך Claude מדרג משרות?</h3>
  <p>
    הסוכן שולח ל-Claude הנחיה מדויקת (Prompt) שמבקשת ממנו לפעול כ"יועץ קריירה"
    ולדרג את ההתאמה לפי שני קריטריונים:
  </p>

  <div class="two-col">
    <div class="highlight-box info">
      <strong>📋 קריטריון 1 — התאמת CV</strong>
      <p>עד כמה הכישורים, הניסיון והרקע של המועמד תואמים לדרישות המשרה הספציפית.</p>
    </div>
    <div class="highlight-box success">
      <strong>🌍 קריטריון 2 — רלוונטיות לתחום</strong>
      <p>האם התפקיד שייך לאותו תחום מקצועי? גם אם הכלים לא מוזכרים ב-CV, משרה בתחום קרוב תקבל ציון גבוה.</p>
    </div>
  </div>

  <h3>סולם הציונים</h3>
  <table>
    <thead>
      <tr><th>טווח ציון</th><th>משמעות</th><th>צבע</th></tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>90–100</strong></td>
        <td>התאמה מצוינת — CV תואם ישירות + תחום מדויק</td>
        <td><span class="badge green">ירוק</span></td>
      </tr>
      <tr>
        <td><strong>70–89</strong></td>
        <td>התאמה טובה — רוב הדרישות מתאימות, תחום רלוונטי</td>
        <td><span class="badge orange">כתום</span></td>
      </tr>
      <tr>
        <td><strong>50–69</strong></td>
        <td>התאמה חלקית — תחום סמוך, חפיפה חלקית</td>
        <td>מתחת לסף ← לא נשלח</td>
      </tr>
      <tr>
        <td><strong>0–49</strong></td>
        <td>לא מתאים — תחום לא קשור</td>
        <td>מתחת לסף ← לא נשלח</td>
      </tr>
    </tbody>
  </table>

  <div class="highlight-box info">
    <strong>📝 ברירת המחדל — ציון מינימלי 70</strong>
    <p>ניתן לשנות את הסף ב-config.yaml. ככל שהסף גבוה יותר, כך יגיעו אליך פחות משרות אך איכותיות יותר.</p>
  </div>

  <h3>הדיאלוג עם Claude (Prompt)</h3>
  <p>
    Claude מקבל הנחיה מדויקת ומחזיר תשובה בפורמט JSON בלבד,
    שמכיל ציון ומשפט הסבר בעברית:
  </p>

  <div class="code-block">
<span class="comment">// דוגמה לתשובה שClaude מחזיר:</span>
{
  <span class="string">"score"</span>: 85,
  <span class="string">"reason"</span>: <span class="string">"תפקיד Python Backend המתאים לניסיון של 3 שנים
               בפיתוח API ו-Data Engineering שמופיע ב-CV"</span>
}
  </div>

  <h3>הגנה מפני שליחה כפולה</h3>
  <p>
    לפני שסוכן שולח משרה לדירוג, הוא בודק ב-tracker אם המשרה כבר נשלחה
    בעבר. אם כן — היא מדולגת לגמרי ולא נשלחת שוב.
  </p>

  <h3>פונקציות עיקריות</h3>
  <table>
    <thead>
      <tr><th>פונקציה</th><th>מה עושה</th></tr>
    </thead>
    <tbody>
      <tr><td><code>filter_jobs()</code></td><td>הפונקציה הראשית — מדרגת את כל המשרות ומחזירה רק הרלוונטיות</td></tr>
      <tr><td><code>score_job()</code></td><td>שולחת משרה בודדת לClaude ומחזירה (score, reason)</td></tr>
      <tr><td><code>_load_cv()</code></td><td>קוראת את קובץ cv.txt</td></tr>
    </tbody>
  </table>

  <div class="highlight-box warning">
    <strong>💰 עלות API:</strong>
    <p>כל משרה שנשלחת ל-Claude עולה כסף (מאוד קטן — כמה סנטים לריצה שלמה).
    לכן, המודול מעביר רק את 3,000 התווים הראשונים של תיאור המשרה כדי לחסוך.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 7 — notifier.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">📧</span>
    <div>
      <div class="num">פרק 7</div>
      <h2>notifier.py — שולח המיילים</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#eafaf1;">📧</div>
      <div>
        <div class="card-title">notifier.py — Email Digest</div>
        <div class="card-file">📄 src/notifier.py</div>
      </div>
    </div>
    <p>
      מודול זה אחראי על בניית המייל המעוצב ושליחתו.
      הוא יוצר מייל עם עיצוב HTML יפה (רגיל + גרסת טקסט לגיבוי)
      ושולח דרך Gmail SMTP.
    </p>
  </div>

  <h3>מבנה המייל שנשלח</h3>
  <p>המייל כולל טבלה עם כל המשרות הרלוונטיות, כשלכל משרה יש:</p>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:14px 0;">
    <div style="background:#f0f7ff; border-radius:8px; padding:12px; text-align:center;">
      <div style="font-size:22px;">💼</div>
      <div style="font-weight:600; font-size:13px;">שם התפקיד</div>
      <div style="font-size:11px; color:#666;">קישור לדף המשרה</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:12px; text-align:center;">
      <div style="font-size:22px;">🏢</div>
      <div style="font-weight:600; font-size:13px;">שם החברה</div>
      <div style="font-size:11px; color:#666;">מיקום המשרה</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:12px; text-align:center;">
      <div style="font-size:22px;">🎯</div>
      <div style="font-weight:600; font-size:13px;">ציון AI (0–100)</div>
      <div style="font-size:11px; color:#666;">ירוק / כתום לפי ציון</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:12px; text-align:center;">
      <div style="font-size:22px;">💡</div>
      <div style="font-weight:600; font-size:13px;">הסבר בעברית</div>
      <div style="font-size:11px; color:#666;">למה המשרה רלוונטית</div>
    </div>
  </div>

  <h3>צבעי הציון במייל</h3>
  <div style="display:flex; gap:14px; margin:14px 0;">
    <div style="display:flex; align-items:center; gap:8px;">
      <span style="background:#2ecc71; color:white; padding:4px 12px; border-radius:12px; font-weight:700;">85+</span>
      <span style="font-size:13px; color:#333;">מצוין</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <span style="background:#f39c12; color:white; padding:4px 12px; border-radius:12px; font-weight:700;">70–84</span>
      <span style="font-size:13px; color:#333;">טוב</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <span style="background:#e74c3c; color:white; padding:4px 12px; border-radius:12px; font-weight:700;">&lt;70</span>
      <span style="font-size:13px; color:#333;">לא נשלח</span>
    </div>
  </div>

  <h3>שיטת השליחה — Gmail SMTP</h3>
  <p>
    SMTP הוא הפרוטוקול הסטנדרטי לשליחת מיילים באינטרנט.
    המודול מתחבר לשרת Gmail (<code>smtp.gmail.com:465</code>) עם
    "App Password" (סיסמה ייעודית לאפליקציות חיצוניות, לא סיסמת Gmail רגילה)
    ושולח את המייל בצורה מוצפנת (SSL).
  </p>

  <h3>לוגיקת "מה שולחים"</h3>
  <table>
    <thead>
      <tr><th>מצב</th><th>send_if_empty</th><th>מה קורה?</th></tr>
    </thead>
    <tbody>
      <tr><td>נמצאו משרות רלוונטיות</td><td>כל מצב</td><td>מייל נשלח עם הטבלה</td></tr>
      <tr><td>אין משרות רלוונטיות</td><td>false (ברירת מחדל)</td><td>מייל לא נשלח בכלל</td></tr>
      <tr><td>אין משרות רלוונטיות</td><td>true</td><td>מייל נשלח עם הודעה שלא נמצא כלום</td></tr>
      <tr><td>dry-run</td><td>כל מצב</td><td>מייל לא נשלח בכלל</td></tr>
    </tbody>
  </table>

  <div class="highlight-box success">
    <strong>✅ ערובה לשליחה חד-פעמית:</strong>
    <p>אחרי שמייל נשלח, כל המשרות שנכללו בו מסומנות ב-DB כ"נשלחו".
    ה-filter.py בודק זאת בריצות הבאות ומדלג עליהן אוטומטית — לעולם לא תקבל אותה משרה פעמיים.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 8 — tracker.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">💾</span>
    <div>
      <div class="num">פרק 8</div>
      <h2>tracker.py — מסד הנתונים</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#fef0e6;">💾</div>
      <div>
        <div class="card-title">tracker.py — SQLite Database</div>
        <div class="card-file">📄 src/tracker.py → data/jobs.db</div>
      </div>
    </div>
    <p>
      מודול זה הוא "הזיכרון" של הסוכן — מנהל מסד נתונים SQLite שמאפשר לסוכן
      לדעת אילו משרות כבר ראה, אילו דרג, ואילו כבר שלח למשתמש.
      בלעדיו, הסוכן היה שולח את אותן משרות שוב ושוב.
    </p>
  </div>

  <h3>מה זה SQLite?</h3>
  <p>
    SQLite הוא מסד נתונים קל-משקל שמאוחסן כקובץ יחיד (<code>data/jobs.db</code>).
    אין צורך בשרת נפרד — הקובץ הוא מסד הנתונים כולו. מתאים בדיוק לפרויקטים
    שרצים על מחשב אחד ולא צריכים להתמודד עם כמות עצומה של נתונים.
  </p>

  <h3>מבנה טבלת ה-jobs</h3>
  <table>
    <thead>
      <tr><th>עמודה</th><th>סוג</th><th>תיאור</th></tr>
    </thead>
    <tbody>
      <tr><td><code>job_id</code></td><td>TEXT (מפתח ראשי)</td><td>מזהה ייחודי של המשרה ב-LinkedIn</td></tr>
      <tr><td><code>title</code></td><td>TEXT</td><td>שם התפקיד</td></tr>
      <tr><td><code>company</code></td><td>TEXT</td><td>שם החברה</td></tr>
      <tr><td><code>location</code></td><td>TEXT</td><td>מיקום</td></tr>
      <tr><td><code>apply_url</code></td><td>TEXT</td><td>קישור להגשת מועמדות</td></tr>
      <tr><td><code>score</code></td><td>INTEGER</td><td>ציון שנתן Claude (0 = לא דורג)</td></tr>
      <tr><td><code>reason</code></td><td>TEXT</td><td>הסבר בעברית מ-Claude</td></tr>
      <tr><td><code>emailed</code></td><td>INTEGER (0/1)</td><td>האם נשלח במייל? 0=לא, 1=כן</td></tr>
      <tr><td><code>seen_at</code></td><td>TEXT</td><td>תאריך ושעה של זיהוי המשרה</td></tr>
    </tbody>
  </table>

  <h3>פונקציות עיקריות</h3>
  <table>
    <thead>
      <tr><th>פונקציה</th><th>מה עושה</th></tr>
    </thead>
    <tbody>
      <tr><td><code>init_db()</code></td><td>יוצרת את הטבלה אם לא קיימת (בטוח לקריאה חוזרת)</td></tr>
      <tr><td><code>mark_seen()</code></td><td>מוסיפה משרה חדשה ל-DB (INSERT OR IGNORE — לא דורסת)</td></tr>
      <tr><td><code>is_seen()</code></td><td>האם המשרה כבר ב-DB?</td></tr>
      <tr><td><code>mark_emailed()</code></td><td>מסמנת רשימת job_ids כ-"נשלחו"</td></tr>
      <tr><td><code>is_emailed()</code></td><td>האם המשרה כבר נשלחה בעבר?</td></tr>
      <tr><td><code>get_all_seen_ids()</code></td><td>מחזירה SET של כל המזהים — לסינון מהיר</td></tr>
      <tr><td><code>get_recent_jobs()</code></td><td>מחזירה 50 המשרות האחרונות (לממשק הווב)</td></tr>
      <tr><td><code>get_stats()</code></td><td>מחזירה סטטיסטיקות: כמה נראו, כמה נשלחו</td></tr>
    </tbody>
  </table>

  <div class="highlight-box success">
    <strong>🛡️ הגנה מפני כפילויות — INSERT OR IGNORE</strong>
    <p>
      כשמנסים להוסיף משרה שכבר קיימת (לפי job_id), מסד הנתונים פשוט מתעלם
      מהבקשה מבלי לגרום לשגיאה. זה מבטיח שאין כפילויות אפילו אם אותה משרה
      מופיעה בחיפושים שונים.
    </p>
  </div>

  <h3>ההבדל בין "נראה" ל"נשלח"</h3>
  <div class="two-col">
    <div class="highlight-box warning">
      <strong>👁️ "נראה" (seen)</strong>
      <p>משרה שהסוכן גילה בחיפוש. גם משרות שדורגו נמוך מסומנות כנראו — הסוכן לא יעבד אותן שוב.</p>
    </div>
    <div class="highlight-box success">
      <strong>📤 "נשלח" (emailed)</strong>
      <p>משרה שדורגה גבוה וכלולה במייל שנשלח בפועל. לעולם לא תיכלל במייל עתידי.</p>
    </div>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 9 — app.py
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🖥️</span>
    <div>
      <div class="num">פרק 9</div>
      <h2>app.py — ממשק הניהול (Web UI)</h2>
    </div>
  </div>

  <div class="component-card">
    <div class="card-header">
      <div class="card-icon" style="background:#e8f4fb;">🖥️</div>
      <div>
        <div class="card-title">app.py — Flask Web Dashboard</div>
        <div class="card-file">📄 app.py → http://localhost:5000</div>
      </div>
    </div>
    <p>
      ממשק גרפי מקומי (רץ בדפדפן שלך) שמאפשר לשלוט בסוכן
      ולראות את כל הנתונים — בלי לפתוח טרמינל ולהקליד פקודות.
    </p>
  </div>

  <h3>מה ניתן לעשות בממשק?</h3>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:14px 0;">
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">▶ הרץ עכשיו</div>
      <div style="font-size:13px; color:#333;">מפעיל ריצה מיידית עם שליחת מייל אמיתית</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">🔍 Dry Run</div>
      <div style="font-size:13px; color:#333;">ריצת בדיקה — מחפש ומדרג, לא שולח מייל</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">⏰ Scheduler</div>
      <div style="font-size:13px; color:#333;">הפעלה/עצירה של ריצות אוטומטיות</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">⚙️ הגדרות</div>
      <div style="font-size:13px; color:#333;">עריכת מילות חיפוש, ציון מינימלי, תדירות</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">📊 סטטיסטיקות</div>
      <div style="font-size:13px; color:#333;">כמה משרות נראו, נשלחו, ומתי הריצה האחרונה</div>
    </div>
    <div style="background:#f0f7ff; border-radius:8px; padding:14px;">
      <div style="font-size:20px; margin-bottom:6px;">📋 לוג חי</div>
      <div style="font-size:13px; color:#333;">צפייה ב-120 שורות אחרונות של הלוג בזמן אמת</div>
    </div>
  </div>

  <h3>ארכיטקטורה טכנית — Flask + Threads</h3>
  <p>
    ממשק הווב בנוי על Flask — ספריית Python פשוטה לבניית אתרים.
    הסוכן והממשק רצים <strong>במקביל</strong> באמצעות Threads (תהליכי ריצה מקביליים):
  </p>

  <div style="display:flex; gap:14px; align-items:stretch; margin:16px 0;">
    <div style="flex:1; background:#1e1e2e; color:#cdd6f4; border-radius:8px; padding:14px; font-size:12px; font-family:'Courier New',monospace; direction:ltr; text-align:left;">
      Thread 1: Flask web server<br>
      → מגיב לבקשות HTTP<br>
      → מציג את ממשק הווב<br>
      → מקבל פקודות מהמשתמש
    </div>
    <div style="display:flex; align-items:center; font-size:24px; color:#0077b5;">⇄</div>
    <div style="flex:1; background:#1e1e2e; color:#cdd6f4; border-radius:8px; padding:14px; font-size:12px; font-family:'Courier New',monospace; direction:ltr; text-align:left;">
      Thread 2: Agent runner<br>
      → מריץ את הסוכן<br>
      → מעדכן state מרכזי<br>
      → הממשק רואה את הסטטוס
    </div>
  </div>

  <p>
    הממשק לא "קופא" כשהסוכן רץ — הוא ממשיך לאפשר גלישה וצפייה בסטטוס
    בזמן שהסוכן עובד ברקע. ה-state המרכזי (סטטוס, תוצאות אחרונות)
    מוגן עם Lock כדי למנוע בעיות של כתיבה מקבילה.
  </p>

  <h3>API Endpoints</h3>
  <table>
    <thead>
      <tr><th>נתיב</th><th>מתודה</th><th>פעולה</th></tr>
    </thead>
    <tbody>
      <tr><td><code>/</code></td><td>GET</td><td>דף הבית — מציג את כל הממשק</td></tr>
      <tr><td><code>/api/run</code></td><td>POST</td><td>מפעיל ריצה (dry_run=true/false)</td></tr>
      <tr><td><code>/api/scheduler/start</code></td><td>POST</td><td>מפעיל את ה-Scheduler</td></tr>
      <tr><td><code>/api/scheduler/stop</code></td><td>POST</td><td>עוצר את ה-Scheduler</td></tr>
      <tr><td><code>/api/config</code></td><td>GET/POST</td><td>קריאה/שמירה של הגדרות</td></tr>
      <tr><td><code>/api/state</code></td><td>GET</td><td>סטטוס נוכחי (בשימוש polling)</td></tr>
      <tr><td><code>/api/logs</code></td><td>GET</td><td>120 שורות אחרונות של הלוג</td></tr>
      <tr><td><code>/api/stats</code></td><td>GET</td><td>סטטיסטיקות DB</td></tr>
    </tbody>
  </table>

  <div class="highlight-box info">
    <strong>🔄 Polling בזמן ריצה:</strong>
    <p>כשהסוכן רץ, הממשק שואל את ה-API כל 3 שניות (<code>/api/state</code>) לסטטוס עדכני.
    ברגע שהריצה מסתיימת, הדף מתרענן אוטומטית.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 10 — CONFIG & ENV
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">⚙️</span>
    <div>
      <div class="num">פרק 10</div>
      <h2>config.yaml ו-‎.env — קבצי ההגדרות</h2>
    </div>
  </div>

  <h3>config.yaml — הגדרות הריצה</h3>
  <p>קובץ זה שולט בהתנהגות הסוכן. אפשר לערוך אותו ישירות או דרך ממשק הווב.</p>

  <div class="code-block">
<span class="comment"># config.yaml — הגדרות חיפוש</span>
search:
  keywords:
    - <span class="string">"Software Engineer"</span>   <span class="comment"># מילות חיפוש ב-LinkedIn</span>
    - <span class="string">"Python Developer"</span>
  location: <span class="string">"Israel"</span>          <span class="comment"># מיקום לחיפוש</span>
  experience_levels:            <span class="comment"># רמות ניסיון:</span>
    - <span class="string">"2"</span>                     <span class="comment"># 2=Entry Level</span>
    - <span class="string">"3"</span>                     <span class="comment"># 3=Associate</span>
    - <span class="string">"4"</span>                     <span class="comment"># 4=Mid-Senior</span>
  max_jobs_per_run: 30          <span class="comment"># מקסימום משרות לריצה</span>
  schedule_hours: 1             <span class="comment"># כל כמה שעות לרוץ</span>

filter:
  min_relevance_score: 70       <span class="comment"># ציון מינימלי לשליחה</span>
  cv_path: <span class="string">"cv.txt"</span>           <span class="comment"># נתיב ל-CV</span>

notifications:
  email_to: <span class="string">"you@gmail.com"</span>    <span class="comment"># לאיזה מייל לשלוח</span>
  email_from: <span class="string">"bot@gmail.com"</span>  <span class="comment"># מאיזה מייל לשלוח</span>
  send_if_empty: false          <span class="comment"># שלח גם אם לא נמצא?</span>
  </div>

  <h3>רמות ניסיון של LinkedIn</h3>
  <table>
    <thead>
      <tr><th>קוד</th><th>רמה בעברית</th><th>משמעות</th></tr>
    </thead>
    <tbody>
      <tr><td>1</td><td>Internship</td><td>סטאז' / תוכניות סטודנטים</td></tr>
      <tr><td>2</td><td>Entry Level</td><td>ללא ניסיון / עד שנתיים</td></tr>
      <tr><td>3</td><td>Associate</td><td>1–3 שנות ניסיון</td></tr>
      <tr><td>4</td><td>Mid-Senior</td><td>3–10 שנות ניסיון</td></tr>
      <tr><td>5</td><td>Director</td><td>תפקיד ניהולי בכיר</td></tr>
      <tr><td>6</td><td>Executive</td><td>VP / C-Level</td></tr>
    </tbody>
  </table>

  <h3>.env — קובץ הסיסמאות</h3>
  <div class="highlight-box danger">
    <strong>🔒 חשוב מאוד — קובץ .env לעולם לא מועלה לאינטרנט!</strong>
    <p>הקובץ מכיל סיסמאות ומפתחות API. הוא נמצא ברשימת .gitignore ולא יועלה ל-GitHub.</p>
  </div>

  <div class="code-block">
<span class="comment"># .env — פרטי גישה (פרטי לחלוטין!)</span>

<span class="comment"># LinkedIn account</span>
LINKEDIN_EMAIL=your_email@gmail.com
LINKEDIN_PASSWORD=your_password

<span class="comment"># Claude AI API key (מ-console.anthropic.com)</span>
ANTHROPIC_API_KEY=sk-ant-...

<span class="comment"># Gmail for sending emails</span>
GMAIL_SENDER=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx    <span class="comment"># לא סיסמת Gmail רגילה!</span>
  </div>

  <div class="highlight-box info">
    <strong>🔑 Gmail App Password — מה זה?</strong>
    <p>Google לא מאפשר לאפליקציות צד שלישי להשתמש בסיסמה הרגילה שלך. צריך ליצור "App Password" ייעודי ב-Google Account &gt; Security &gt; 2-Step Verification &gt; App passwords.</p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 11 — ANTI-DETECTION
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🛡️</span>
    <div>
      <div class="num">פרק 11</div>
      <h2>הגנה מפני זיהוי כבוט</h2>
    </div>
  </div>

  <p>
    LinkedIn (כמו רוב האתרים הגדולים) מנסה לזהות ולחסום תוכנות אוטומטיות.
    הסוכן מיישם מספר טכניקות כדי להיראות כגולש אנושי אמיתי:
  </p>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>1. דפדפן גלוי (Non-Headless)</h4>
    <p>
      רוב הבוטים משתמשים ב-"headless browser" — דפדפן ללא חלון גרפי.
      LinkedIn יודע לזהות זאת. הסוכן מריץ דפדפן <strong>עם חלון גרפי גלוי</strong>,
      בדיוק כמו גלישה רגילה.
    </p>
  </div>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>2. User Agent אמיתי</h4>
    <p>
      כל בקשת HTTP כוללת מחרוזת שמזהה את הדפדפן (User Agent).
      הסוכן מגדיר User Agent זהה לChrome אמיתי:
    </p>
    <div class="code-block" style="font-size:10px;">Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36</div>
  </div>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>3. השהיות אקראיות</h4>
    <p>
      בין כל פעולה ופעולה, הסוכן ממתין זמן <strong>אקראי</strong> (לא קבוע).
      אדם אמיתי לא קורא/לוחץ בקצב מדוייק — הסוכן מחקה זאת:
    </p>
    <div class="two-col">
      <div style="background:#f5f5f5; border-radius:6px; padding:10px; text-align:center; font-size:13px;">
        <strong>בין כרטיסיות:</strong><br>0.3 – 0.8 שניות
      </div>
      <div style="background:#f5f5f5; border-radius:6px; padding:10px; text-align:center; font-size:13px;">
        <strong>בין דפים:</strong><br>1.5 – 4 שניות
      </div>
    </div>
  </div>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>4. עוגיות שמורות</h4>
    <p>
      במקום להתחבר מחדש בכל ריצה (התנהגות חשודה),
      הסוכן שומר את ה-session cookies ומשתמש בהן בריצות הבאות —
      בדיוק כמו שדפדפן רגיל עושה.
    </p>
  </div>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>5. ביטול דגל האוטומציה</h4>
    <p>
      Chromium מוסיף ב-default דגל <code>--enable-automation</code> שאתרים יכולים לזהות.
      הסוכן מבטל זאת עם הדגל <code>--disable-blink-features=AutomationControlled</code>.
    </p>
  </div>

  <div class="component-card" style="page-break-inside:avoid;">
    <h4>6. טיפול ב-2FA / CAPTCHA</h4>
    <p>
      אם LinkedIn מזהה כניסה חשודה ומציג אתגר אבטחה, הסוכן
      <strong>עוצר 60 שניות</strong> ומאפשר לך להשלים את האימות ידנית
      (בחלון הדפדפן הגלוי) לפני שממשיך.
    </p>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════════
     SECTION 12 — SETUP
══════════════════════════════════════════════════════════ -->
<div class="page page-break">
  <div class="section-header">
    <span class="icon">🚀</span>
    <div>
      <div class="num">פרק 12</div>
      <h2>מדריך התקנה והפעלה</h2>
    </div>
  </div>

  <h3>דרישות מוקדמות</h3>
  <div class="highlight-box info">
    <p>✅ Python 3.11 ומעלה | ✅ חשבון LinkedIn | ✅ מפתח API של Anthropic (claude.ai/api) | ✅ Gmail עם App Password</p>
  </div>

  <h3>שלבי התקנה</h3>

  <div style="display:flex; flex-direction:column; gap:12px; margin:16px 0;">
    <div style="border:1px solid #e0e7ef; border-radius:8px; padding:14px;">
      <div style="font-weight:700; color:#0077b5; margin-bottom:8px;">📥 שלב 1 — התקנת ספריות</div>
      <div class="code-block" style="margin:0;">pip install -r requirements.txt
python -m playwright install chromium</div>
    </div>

    <div style="border:1px solid #e0e7ef; border-radius:8px; padding:14px;">
      <div style="font-weight:700; color:#0077b5; margin-bottom:8px;">📝 שלב 2 — יצירת קובץ .env</div>
      <p style="font-size:12px; margin-bottom:6px;">העתק את .env.example ל-.env ומלא את הפרטים:</p>
      <div class="code-block" style="margin:0;">LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_SENDER=sender@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx</div>
    </div>

    <div style="border:1px solid #e0e7ef; border-radius:8px; padding:14px;">
      <div style="font-weight:700; color:#0077b5; margin-bottom:8px;">📄 שלב 3 — הכנת CV</div>
      <p style="font-size:12px;">שמור את ה-CV שלך כ-<strong>cv.txt</strong> בתיקיית הפרויקט. טקסט רגיל, לא Word/PDF.</p>
    </div>

    <div style="border:1px solid #e0e7ef; border-radius:8px; padding:14px;">
      <div style="font-weight:700; color:#0077b5; margin-bottom:8px;">⚙️ שלב 4 — הגדרת config.yaml</div>
      <p style="font-size:12px;">ערוך את מילות החיפוש, המיקום, רמות הניסיון וכתובת המייל לקבלה.</p>
    </div>
  </div>

  <h3>אפשרויות הפעלה</h3>
  <table>
    <thead>
      <tr><th>פקודה</th><th>מתי להשתמש</th></tr>
    </thead>
    <tbody>
      <tr>
        <td><code>python app.py</code></td>
        <td>ממשק ווב — הדרך המומלצת. פתח http://localhost:5000</td>
      </tr>
      <tr>
        <td><code>python main.py --dry-run</code></td>
        <td>בדיקה ראשונה — לראות שהכל עובד בלי לשלוח מייל</td>
      </tr>
      <tr>
        <td><code>python main.py --once</code></td>
        <td>ריצה חד-פעמית עם שליחת מייל</td>
      </tr>
      <tr>
        <td><code>python main.py</code></td>
        <td>מצב Scheduler — רץ כל שעה אוטומטית</td>
      </tr>
    </tbody>
  </table>

  <div class="summary-box">
    <h3>📌 סיכום — מה הסוכן עושה בשבילך</h3>
    <ul style="margin-top:10px;">
      <li>🔍 <strong>מחפש</strong> משרות ב-LinkedIn לפי הקריטריונים שהגדרת</li>
      <li>🤖 <strong>מדרג</strong> כל משרה עם AI ביחס ל-CV שלך</li>
      <li>📧 <strong>שולח</strong> מייל עם רק המשרות הכי רלוונטיות</li>
      <li>💾 <strong>זוכר</strong> מה שלח — לעולם לא שולח אותה משרה פעמיים</li>
      <li>⏰ <strong>פועל אוטומטית</strong> כל שעה (או לפי הגדרה)</li>
      <li>🖥️ <strong>נשלט</strong> דרך ממשק ווב נוח ב-localhost:5000</li>
    </ul>
  </div>
</div>

</body>
</html>"""


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def generate_pdf():
    output_path = Path(__file__).parent / "LinkedIn_Job_Scout_Architecture.pdf"

    # Write HTML to a temp file
    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(HTML_CONTENT)
        html_path = Path(f.name)

    print("Creating PDF...")

    result = subprocess.run(
        [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            "--print-to-pdf-no-header",
            str(html_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    html_path.unlink(missing_ok=True)

    if output_path.exists():
        print(f"PDF created successfully: {output_path}")
    else:
        print("ERROR creating PDF:")
        print(result.stderr)

    return output_path


if __name__ == "__main__":
    generate_pdf()
