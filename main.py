import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO

# --- 1. CORE INTEGRATION (Environment Variables) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026"
OFFICIAL_WA = "233245630637"

app = Flask(__name__)
app.secret_key = "PBE_ABSOLUTE_FINAL_COMMAND_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. GLOBAL MATRIX ---
PBE_GUILDS = ["Electrical Engineering", "Solar & Energy", "Plumbing & Hydraulics", "Masonry & Construction", "Mechanical & Auto", "PBE TV", "CCTV & Security", "ICT & Software", "HVAC & Cooling", "General Technical", "ETC"]
GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 3. DATABASE & TERRITORIAL GPS TRACKER ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, nationality TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, issuance_date DATE, expiry_date DATE, 
            rank TEXT, department TEXT, phone_no TEXT, photo_url TEXT, status TEXT DEFAULT 'PENDING', 
            otp_code TEXT, region TEXT, station TEXT, scans INT DEFAULT 0
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
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    ip = request.remote_addr
    location = "HQ_SECURE_ZONE"
    try:
        # REAL-TIME TERRITORIAL GPS PINPOINT
        geo = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,lat,lon", timeout=3).json()
        if geo['status'] == 'success':
            location = f"{geo['city']}, {geo['regionName']} ({geo['lat']}, {geo['lon']})"
    except: location = "LOC_MASKED"
    device = f"{request.user_agent.platform} | {request.user_agent.browser} | {request.remote_addr}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info, geo_location) VALUES (%s, %s, %s, %s, %s)",
                (action, details, ip, device, location))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 4. GHOST PROTOCOL SECURITY ---
def is_blocked(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT blocked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def engage_lockout(ip):
    until = datetime.datetime.now() + datetime.timedelta(hours=72)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, blocked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s", (ip, until, until))
    conn.commit(); cur.close(); conn.close()

# --- 5. INTERFACE DESIGN ---
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
        .logo { height: 75px; margin-bottom: 10px; background: transparent !important; }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .layer { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .btn-cmd { padding: 12px 18px; border-radius: 8px; color: white; text-decoration: none; font-size: 12px; font-weight: bold; border: none; cursor: pointer; display: inline-block; }
        .bg-navy { background: var(--navy); } .bg-blue { background: var(--blue); } .bg-red { background: var(--red); }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        .geo-tag { color: var(--red); font-weight: bold; font-family: monospace; }
        input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo">
        <div style="font-size: 24px; font-weight: 900; letter-spacing: 1px;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 6. ROUTES: CORE COMMAND ---

@app.route("/")
def home(): 
    return redirect(url_for('enrollment'))

@app.route("/enrollment", methods=['GET', 'POST'])
def enrollment():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper(), request.form.get('surname').upper()
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{sname}_{fname}")
            # 15-CHAR NAME-MIX CREDENTIALS
            uid = f"{fname[:3]}{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"
            lic = f"{sname[:3]}{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        rank=%s, department=%s, photo_url=%s, status='PENDING', region=%s WHERE otp_code=%s""",
                        (sname, fname, request.form.get('dob'), uid, lic, request.form.get('rank'), 
                         request.form.get('department'), photo['secure_url'], request.form.get('region'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>REGISTRATION SUBMITTED ✅ awaiting Admin approval.</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer" style="max-width:500px; margin:auto;">
            <h3>PERSONNEL ENROLLMENT</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP Code" required>
                <input name="surname" placeholder="Surname" required>
                <input name="firstname" placeholder="First Name" required>
                <input name="dob" placeholder="DOB (DD/MM/YYYY)" required>
                <select name="department">{% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}</select>
                <input name="rank" placeholder="Job Title" required>
                <select name="region">{% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}</select>
                <input type="file" name="photo" required>
                <button class="btn-cmd bg-navy" style="width:100%;">SUBMIT</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GHANA_REGIONS)

@app.route("/admin", methods=['GET', 'POST'])
def admin_login():
    if is_blocked(request.remote_addr): abort(404)
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("LOGIN", "Admin Entered Dashboard")
            return redirect(url_for('admin_dashboard'))
        else:
            engage_lockout(request.remote_addr)
            return "<h2>SYSTEM LOCKED ❌ Incorrect Key.</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer" style="max-width:350px; margin: 100px auto; text-align:center;"><h3>HQ AUTH</h3><form method="POST"><input type="password" name="password" placeholder="Key" required><button class="btn-cmd bg-navy" style="width:100%;">UNLOCK</button></form></div>'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    sms_bal = "OFFLINE"
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=5)
        sms_bal = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: pass
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="layer" style="display:flex; justify-content:space-between; align-items:center;">
            <div><b>SMS: {sms_bal}</b></div>
            <div>
                <a href="/admin/audit" class="btn-cmd bg-navy">TERRITORIAL AUDIT</a>
                <a href="/admin/invite" class="btn-cmd bg-blue">INVITE</a>
            </div>
        </div>
        <div class="layer">
            <table>
                <tr><th>ID/LIC</th><th>NAME</th><th>RANK</th><th>ACTIONS</th></tr>
                {{% for w in workers %}}
                <tr>
                    <td><b>{{{{w[6]}}}}</b><br><small>{{{{w[7]}}}}</small></td>
                    <td>{{{{w[1]}}}}, {{{{w[2]}}}}</td>
                    <td>{{{{w[10]}}}}</td>
                    <td>
                        <a href="/admin/print/{{{{w[6]}}}}" class="btn-cmd bg-blue">Print</a>
                        <a href="/admin/delete/{{{{w[0]}}}}" class="btn-cmd bg-red" onclick="return confirm('Erase?')">Del</a>
                    </td>
                </tr>
                {{% endfor %}}
            </table>
        </div>
    """), workers=workers)

@app.route("/admin/audit")
def admin_audit():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer">
            <h3>Territorial Audit</h3>
            <table>
                <tr><th>Time</th><th>Action</th><th>📍 Location</th><th>Cmd</th></tr>
                {% for l in logs %}
                <tr><td>{{l[1].strftime('%H:%M:%S')}}</td><td>{{l[2]}}</td><td class="geo-tag">{{l[6]}}</td><td><a href="/admin/audit/del/{{l[0]}}" style="color:red;">X</a></td></tr>
                {% endfor %}
            </table>
            <br><a href="/admin/dashboard" class="btn-cmd bg-navy">Return</a>
        </div>
    """), logs=logs)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        # SENDER PBE_OTP
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_OTP", "message": f"PBE: Use code {otp} at {request.url_root}enrollment", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer" style="max-width:400px; margin:auto;"><h3>Invite</h3><form method="POST"><input name="phone" placeholder="233..."><button class="btn-cmd bg-blue" style="width:100%;">SEND OTP</button></form></div>'))

@app.route("/admin/print/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    
    if w[13]: # Photo Layering (Main & Ghost Watermark)
        c.drawImage(w[13], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch, mask='auto')
        c.saveState(); c.setFillAlpha(0.15); c.drawImage(w[13], 2.3*inch, 0.55*inch, width=0.7*inch, height=0.9*inch, mask='auto'); c.restoreState()

    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"{w[1]}") # Surname
    c.drawString(1.35*inch, 1.40*inch, f"{w[2]}") # Firstname
    c.drawString(1.35*inch, 1.25*inch, f"{w[6]}") # ID
    c.drawString(1.35*inch, 1.10*inch, f"{w[7]}") # License
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/audit/del/<int:id>")
def delete_audit(id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_soul_audit WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_audit'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
