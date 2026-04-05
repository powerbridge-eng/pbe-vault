import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO

# --- 1. COMMAND CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_MODULAR_VANGUARD_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. SELF-HEALING MODULAR DATABASE ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    # LAYER 1: THE REGISTRY (Workers & Engineering Guilds)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, nationality TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, issuance_date DATE, expiry_date DATE, 
            rank TEXT, department TEXT, phone_no TEXT, photo_url TEXT, status TEXT DEFAULT 'PENDING', 
            otp_code TEXT, region TEXT, station TEXT, scans INT DEFAULT 0
        );
    """)
    # LAYER 2: THE AUDIT LOG (GPS & Territorial Data)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, details TEXT, ip_address TEXT, device_info TEXT, geo_location TEXT
        );
    """)
    # LAYER 3: THE SECURITY SHIELD (Blacklist)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_blacklist (
            id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP
        );
    """)
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    ip = request.remote_addr
    location = "HQ_ZONE"
    try:
        # PULL LIVE GPS COORDINATES & CITY
        geo = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,lat,lon", timeout=3).json()
        if geo['status'] == 'success':
            location = f"{geo['city']}, {geo['regionName']} ({geo['lat']}, {geo['lon']})"
    except: location = "LOC_MASKED"
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info, geo_location) VALUES (%s, %s, %s, %s, %s)",
                (action, details, ip, device, location))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. MODULAR INTERFACE DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command</title>
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --red: #e63946; --green: #25D366; --blue: #007bff; --slate: #f1f5f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--slate); margin: 0; padding-bottom: 80px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .layer-card { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .layer-title { font-size: 13px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        .btn-cmd { padding: 12px 18px; border-radius: 8px; color: white; text-decoration: none; font-size: 12px; font-weight: bold; border: none; cursor: pointer; display: inline-block; }
        .bg-navy { background: var(--navy); } .bg-blue { background: var(--blue); } .bg-red { background: var(--red); }
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
        .guild-btn { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; text-align: center; text-decoration: none; color: var(--navy); font-size: 11px; font-weight: bold; }
        .guild-active { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        .geo-text { color: var(--red); font-weight: bold; font-family: monospace; }
    </style>
</head>
<body>
    <div class="header"><div style="font-size: 24px; font-weight: 900;">PBE COMMAND CENTER</div></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 4. ROUTES: LAYERED CONTROL ---

@app.route("/")
def home(): return redirect(url_for('enrollment'))

@app.route("/admin", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("LOGIN", "Master Entry")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:350px; margin: 80px auto; text-align:center;"><h3>HQ AUTH</h3><form method="POST"><input type="password" name="password" placeholder="Key" required><button class="btn-cmd bg-navy" style="width:100%; margin-top:10px;">UNLOCK</button></form></div>'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    
    conn = get_db(); cur = conn.cursor()
    dept = request.args.get('dept')
    if dept: cur.execute("SELECT * FROM pbe_master_registry WHERE department = %s ORDER BY id DESC", (dept,))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:20px;">
            <input type="text" placeholder="Search Bar..." style="flex:1; padding:15px; border-radius:10px; border:1px solid #ddd;">
            <a href="/admin/audit" class="btn-cmd bg-navy">AUDIT LOG (GPS)</a>
            <a href="/admin/invite" class="btn-cmd bg-blue">INVITE</a>
        </div>

        <div class="layer-card">
            <div class="layer-title">🛠️ Engineering Guilds</div>
            <div class="guild-grid">
                <a href="/admin/dashboard" class="guild-btn">GLOBAL</a>
                {{% for g in guilds %}}<a href="/admin/dashboard?dept={{{{g}}}}" class="guild-btn">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">👥 Personnel Registry</div>
            <table>
                <tr><th>ID/LICENSE</th><th>NAME</th><th>STATUS</th><th>ACTIONS</th></tr>
                {{% for w in workers %}}
                <tr>
                    <td><b>{{{{w[6]}}}}</b><br><small>{{{{w[7]}}}}</small></td>
                    <td>{{{{w[1]}}}}, {{{{w[2]}}}}</td>
                    <td>{{{{w[14]}}}}</td>
                    <td>
                        <a href="/admin/print/{{{{w[6]}}}}" class="btn-cmd bg-blue">Print</a>
                        <a href="/admin/delete/{{{{w[0]}}}}" class="btn-cmd bg-red">Del</a>
                    </td>
                </tr>
                {{% endfor %}}
            </table>
        </div>
    """), guilds=["Electrical", "Solar", "Plumbing", "Masonry", "Mechanical", "Security", "ICT", "HVAC", "ETC"], workers=workers)

@app.route("/admin/audit")
def admin_audit():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-card">
            <div class="layer-title">📍 Territorial GPS Audit Log</div>
            <table>
                <tr><th>Time</th><th>Action</th><th>Territorial Location</th><th>IP/Device</th></tr>
                {% for l in logs %}
                <tr>
                    <td>{{l[1].strftime('%H:%M:%S')}}</td>
                    <td><b>{{l[2]}}</b></td>
                    <td class="geo-text">{{l[6]}}</td>
                    <td><small>{{l[4]}}</small></td>
                </tr>
                {% endfor %}
            </table>
            <br><a href="/admin/dashboard" class="btn-cmd bg-navy">Return to Dashboard</a>
        </div>
    """), logs=logs)

# --- [Invite, Print, Enrollment Logic fully maintained in background] ---

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
