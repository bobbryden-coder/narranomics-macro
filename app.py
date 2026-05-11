"""
Narranomics — Macro Narrative Sentiment Dashboard
===================================================
Standalone read-only dashboard for external presentation.
Connects to the shared Supabase instance for macro sentiment data.

Environment variables:
    SUPABASE_URL    — Supabase project URL
    SUPABASE_KEY    — Supabase anon/service key
    DASH_USERNAME   — login username
    DASH_PASSWORD   — login password (comma-separated for multiple)
    SECRET_KEY      — Flask secret key
"""
import os
import json
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, Response)
import requests as http_requests

# ── Config ────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jriduffggpmmjcgwsqxj.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.permanent_session_lifetime = timedelta(days=7)

DASH_USERNAME = os.environ.get('DASH_USERNAME', 'narranomics')
DASH_PASSWORDS = [p.strip() for p in os.environ.get('DASH_PASSWORD', 'demo2026').split(',')]


# ── Auth ──────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == DASH_USERNAME and any(password == p for p in DASH_PASSWORDS):
            session.permanent = True
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Supabase helper ──────────────────────────────────────────────────────
def _sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }


# ── Dashboard ────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


# ── API: macro summaries ─────────────────────────────────────────────────
@app.route('/api/macro/summaries')
@login_required
def api_macro_summaries():
    """Paginated fetch of all macro daily summaries."""
    if not SUPABASE_KEY:
        return jsonify({'error': 'Not configured'}), 500

    all_rows = []
    offset = 0
    batch = 1000
    while True:
        resp = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/dj_macro_daily_summary",
            headers=_sb_headers(),
            params={
                'select': 'date,category,composite_score,article_count,summary_text',
                'order': 'date.desc,category.asc',
                'limit': batch,
                'offset': offset,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            return jsonify({'error': f'Database error {resp.status_code}'}), 500
        rows = resp.json()
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < batch:
            break
        offset += batch

    # Exclude weekends, sanitise
    all_rows = [r for r in all_rows
                if datetime.strptime(r['date'], '%Y-%m-%d').weekday() < 5]
    for r in all_rows:
        if r.get('summary_text'):
            r['summary_text'] = r['summary_text'].replace('\u0000', '')

    return app.response_class(
        response=json.dumps({'summaries': all_rows}, ensure_ascii=False),
        status=200,
        mimetype='application/json',
    )


@app.route('/api/macro/summaries/csv')
@login_required
def api_macro_csv():
    """Export all macro summaries as CSV."""
    import csv, io

    all_rows = []
    offset = 0
    batch = 1000
    while True:
        resp = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/dj_macro_daily_summary",
            headers=_sb_headers(),
            params={
                'select': 'date,category,composite_score,article_count,summary_text',
                'order': 'date.desc,category.asc',
                'limit': batch,
                'offset': offset,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            break
        rows = resp.json()
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < batch:
            break
        offset += batch

    all_rows = [r for r in all_rows
                if datetime.strptime(r['date'], '%Y-%m-%d').weekday() < 5]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Composite Score', 'Article Count', 'Summary'])
    for r in all_rows:
        writer.writerow([r.get('date',''), r.get('category',''),
                         r.get('composite_score',''), r.get('article_count',''),
                         r.get('summary_text','')])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=narranomics_macro_sentiment.csv'})


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  Narranomics Macro Dashboard")
    print(f"  http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=True)
