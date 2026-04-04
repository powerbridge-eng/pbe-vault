import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026" 
SUPERVISOR_PASSWORD = "PBE-Super-2026"
ADMIN_EMAIL = "Powerbridgee@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_RECOVERY_MODE_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE INITIALIZATION (Audit, Blacklist, Documents) ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, 
            ghana_card_photo TEXT, check_in_status TEXT DEFAULT 'OUT'
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_audit_logs (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT, details TEXT, ip_address TEXT, user_role TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_blacklist (
            id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP
        );
    """)
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. RECOVERY ENGINE (SHIELDS DEACTIVATED) ---
# Lockout functions are removed to allow General Imperial access.

def log_action(action, details):
    role = session.get('role', 'GUEST')
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_logs (action, details, ip_address, user_role) VALUES (%s, %s, %s, %s)", 
                (action, details, request.remote_addr, role))
    conn.commit(); cur.close(); conn.close()

@app.before_request
def recovery_gate():
    # SHIELDS ARE DOWN. NO 404 ERRORS WILL BE TRIGGERED.
    pass

# --- 4. THE VANGUARD INTERFACE ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head><title>PBE RECOVERY MODE</title>
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f7f9; margin: 0; }
    .header { background: #1a3a5a; color: white; padding: 30px; text-align: center; border-bottom: 6px solid #0056b3; }
    .container { max-width: 1200px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; }
    .btn { padding: 10px 20px; border-radius: 6px; text-decoration: none; color: white; font-weight: bold; border: none; cursor: pointer; }
    .btn-blue { background: #0056b3; } .btn-red { background: #dc3545; }
    input { padding: 12px; border: 1px solid #ddd; width: 100%; max-width: 400px; border-radius: 6px; }
</style>
</head>
<body>
    <div class="header"><h1>PBE RECOVERY CONSOLE</h1><p>SHIELDS DEACTIVATED</p></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. RECOVERY ROUTES ---

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['logged_in'], session['role'] = True, 'GENERAL'
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="text-align:center;">
            <h2>Emergency Authorization</h2>
            <form method="POST"><input type="password" name="password" placeholder="CEO Master Key" required><br><br><button class="btn btn-blue">Unlock Registry</button></form>
        </div>
    """))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Recovery Dashboard</h2>
        <div style="margin-bottom:20px;">
            <a href="/admin/clear-security" class="btn btn-red">⚠️ CLEAR ALL BLACKLISTS & LOGS</a>
            <a href="/logout" class="btn btn-blue" style="background:#333;">Exit Recovery</a>
        </div>
        <table>
            <tr><th>UID</th><th>Name</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr><td>{{ w[4] }}</td><td>{{ w[1] }}, {{ w[2] }}</td><td><a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a></td></tr>
            {% endfor %}
        </table>
    """), workers=workers)

@app.route("/admin/clear-security")
def clear_security():
    if session.get('role') != 'GENERAL': return "UNAUTHORIZED", 403
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM pbe_blacklist;")
    cur.execute("DELETE FROM pbe_audit_logs;")
    conn.commit(); cur.close(); conn.close()
    return "<h1>SHIELDS RESET ✅ All blacklists and logs have been wiped.</h1><br><a href='/admin-dashboard'>Back</a>"

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if session.get('role') != 'GENERAL': return "UNAUTHORIZED", 403
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
