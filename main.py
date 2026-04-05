import os, random, string, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. THE FOUNDATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP"
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_GLOBAL_ULITMATUM_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. SELF-HEALING DATABASE (Fixes the 500 Errors) ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT, 
            phone_no TEXT, photo_url TEXT, status TEXT DEFAULT 'ACTIVE', otp_code TEXT, region TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, details TEXT, ip_address TEXT, device_info TEXT, geo_location TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_blacklist (
            id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP
        );
    """)
    # Automatic repairs
    cur.execute("ALTER TABLE pbe_soul_audit ADD COLUMN IF NOT EXISTS geo_location TEXT;")
    cur.execute("ALTER TABLE pbe_master_registry ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ACTIVE';")
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    ip = request.remote_addr
    location = "HQ_ZONE"
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,lat,lon", timeout=3).json()
        if geo['status'] == 'success':
            location = f"{geo['city']}, {geo['regionName']} ({geo['lat']}, {geo['lon']})"
    except: location = "LOC_ERR"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info, geo_location) VALUES (%s, %s, %s, %s, %s)",
                (action, details, ip, f"{request.user_agent.platform}", location))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. UI LAYERS ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --slate: #f1f5f9; }
        body { font-family: sans-serif; background: var(--slate); margin: 0; padding-bottom: 60px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); }
        .card { background: white; border-radius: 15px; padding: 20px; margin: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .btn-cmd { padding: 10px 14px; border-radius: 6px; color: white; text-decoration: none; font-size: 11px; font-weight: bold; border: none; cursor: pointer; }
        .bg-navy { background: var(--navy); } .bg-blue { background: #007bff; } .bg-red { background: #e63946; } .bg-orange { background: #fd7e14; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 15px; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
        .geo-tag { color: var(--red); font-weight: bold; font-family: monospace; }
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-top: 10px; }
        .guild-btn { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 8px; text-align: center; font-size: 10px; text-decoration: none; color: var(--navy); border-radius: 6px; }
    </style>
</head>
<body>
    <div class="header"><h1>PBE COMMAND CENTER</h1></div>
    {% block content %}{% endblock %}
</body>
</html>
"""

# --- 4. COMMAND ROUTES ---

@app.route("/")
def home(): return redirect(url_for('register'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    # Day 1 Enrollment Form logic here
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="card"><h3>Personnel Registration</h3></div>'))

@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("LOGIN", "Admin Authorized")
            return redirect(url_for('dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="card" style="max-width:320px; margin: 60px auto; text-align:center;"><h3>HQ AUTH</h3><form method="POST"><input type="password" name="password" placeholder="Master Key" required style="width:85%; padding:10px; margin-bottom:10px;"><button class="btn-cmd bg-navy" style="width:100%;">UNLOCK</button></form></div>'))

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin'))
    
    # SMS Balance Logic
    sms_bal = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=5)
        sms_bal = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_bal = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="card" style="display:flex; justify-content:space-between; align-items:center;">
            <div><b>SMS BALANCE: {sms_bal}</b></div>
            <div>
                <a href="/audit" class="btn-cmd bg-navy">AUDIT LOG (GPS)</a>
                <a href="/invite" class="btn-cmd bg-blue">INVITE</a>
            </div>
        </div>

        <div class="card">
            <input type="text" id="pbeSearch" placeholder="Search Names, IDs, or Guilds..." style="width:100%; padding:12px; border-radius:8px; border:1px solid #ddd;">
            <div class="guild-grid">
                {{% for g in ["Electrical", "Solar", "Plumbing", "Masonry", "Mechanical", "Security", "ICT", "HVAC"] %}}
                <a href="#" class="guild-btn">{{{{g}}}}</a>
                {{% endfor %}}
            </div>
        </div>

        <div class="card">
            <table>
                <tr><th>ID/LICENSE</th><th>NAME</th><th>STATUS</th><th>ACTIONS</th></tr>
                {{% for w in workers %}}
                <tr>
                    <td><b>{{{{w[4]}}}}</b><br><small>{{{{w[5]}}}}</small></td>
                    <td>{{{{w[1]}}}}, {{{{w[2]}}}}</td>
                    <td>{{{{w[10]}}}}</td>
                    <td>
                        <a href="/print/{{{{w[4]}}}}" class="btn-cmd bg-blue">PRINT</a>
                        <a href="/suspend/{{{{w[0]}}}}" class="btn-cmd bg-orange">SUSP</a>
                        <a href="/delete/{{{{w[0]}}}}" class="btn-cmd bg-red">DEL</a>
                    </td>
                </tr>
                {{% endfor %}}
            </table>
        </div>
    """), workers=workers)

@app.route("/audit")
def audit():
    if not session.get('logged_in'): return redirect(url_for('admin'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="card">
            <h3>📍 Territorial Audit & Live Location Tracking</h3>
            <table>
                <tr><th>Time</th><th>Action</th><th>📍 Live Location Tracking (GPS)</th><th>IP/Device</th></tr>
                {% for l in logs %}
                <tr>
                    <td>{{l[1].strftime('%H:%M:%S')}}</td>
                    <td><b>{{l[2]}}</b></td>
                    <td class="geo-tag">{{l[6]}}</td>
                    <td><small>{{l[4]}}</small></td>
                </tr>
                {% endfor %}
            </table>
            <br><a href="/dashboard" class="btn-cmd bg-navy">Return to Dashboard</a>
        </div>
    """), logs=logs)

# --- 5. PRINTING ENGINE (ID TEMPLATE LOGIC) ---
@app.route("/print/<uid>")
def print_id(uid):
    if not session.get('logged_in'): return redirect(url_for('admin'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    
    if w[9]: # Image Layering: Strip Background + 15% Ghost Photo
        c.drawImage(w[9], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch, mask='auto')
        c.saveState(); c.setFillAlpha(0.15); c.drawImage(w[9], 2.3*inch, 0.55*inch, width=0.7*inch, height=0.9*inch, mask='auto'); c.restoreState()

    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"{w[1]}") # Surname
    c.drawString(1.35*inch, 1.40*inch, f"{w[2]}") # Firstname
    c.drawString(1.35*inch, 1.25*inch, f"{w[4]}") # UID
    c.drawString(1.35*inch, 1.08*inch, f"{w[5]}") # License
    
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
