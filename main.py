import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_ABSOLUTE_FINAL_BUILD_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE PBE WORLD MATRIX ---
PBE_GUILDS = [
    "ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", 
    "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", 
    "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", 
    "FASHION DESIGN", "GENERAL TECHNICAL"
]

# --- 3. DATABASE & AUDIT ENGINE ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE,
            issuance_date DATE, expiry_date DATE, rank TEXT, department TEXT,
            phone_no TEXT, photo_url TEXT, ghana_card_url TEXT, status TEXT DEFAULT 'PENDING',
            otp_code TEXT, region TEXT, station TEXT, scans INT DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, details TEXT, ip_address TEXT, device_info TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info) VALUES (%s, %s, %s, %s)",
                (action, details, request.remote_addr, device))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

def generate_15_char(name):
    clean = re.sub(r'[^A-Z]', '', name.upper())
    part = clean[:6]
    needed = 15 - len(part)
    return f"{part}{''.join(random.choices(string.digits + string.ascii_uppercase, k=needed))}"

# --- 4. EXECUTIVE UI DESIGN (Layered) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command Center</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --bg: #f1f5f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 100px; }
        
        /* LOGO & HEADER ENGINE */
        .header { background: var(--navy); color: white; padding: 35px 20px; text-align: center; border-bottom: 5px solid var(--gold); display: flex; flex-direction: column; align-items: center; }
        .logo-box { width: 90px; height: 90px; background: white; border-radius: 50%; padding: 5px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); border: 2px solid var(--gold); display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .logo-img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .header h1 { font-size: 26px; font-weight: 900; letter-spacing: 2px; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        
        /* LAYERED CARDS */
        .layer-card { background: white; border-radius: 15px; padding: 25px; margin-bottom: 25px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .layer-title { font-size: 13px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 12px; }
        
        .guild-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
        .guild-btn { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 5px; text-align: center; text-decoration: none; color: var(--navy); font-size: 10px; font-weight: 800; transition: 0.3s; }
        .guild-btn:hover, .active-guild { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th { text-align: left; padding: 12px; border-bottom: 2px solid #f1f5f9; color: #64748b; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #f1f5f9; }
        
        /* COMMAND BUTTONS */
        .btn-suite { padding: 8px 10px; border-radius: 6px; color: white; text-decoration: none; font-size: 11px; margin-right: 3px; display: inline-block; border: none; cursor: pointer; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-warn { background: #f59e0b; }
        
        .terminal { background: #000; color: #22c55e; padding: 15px; border-radius: 10px; font-family: monospace; height: 160px; overflow-y: auto; font-size: 12px; border: 2px solid #334155; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 65px; height: 65px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); text-decoration: none; z-index: 1001; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-box">
            <img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.parentElement.style.display='none'">
        </div>
        <h1>PBE COMMAND CENTER</h1>
        <p style="color:var(--gold); font-size:10px; letter-spacing:1px; margin-top:5px;">ABSOLUTE INFRASTRUCTURE CONTROL</p>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    {% if session.get('logged_in') %}<a href="/admin/invite" class="fab">＋</a>{% endif %}
</body>
</html>
"""

# --- 6. ROUTES ---

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("SECURITY_LOGIN", "Master authenticated.")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:380px; margin: 80px auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input type="password" name="password" style="width:100%; padding:15px; margin-bottom:15px; border-radius:10px; border:1px solid #ddd; box-sizing:border-box;" placeholder="Enter Master Key" required><button class="btn-suite bg-navy" style="width:100%; padding:15px;">UNLOCK SYSTEM</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db(); cur = conn.cursor()
    dept = request.args.get('dept')
    if dept: cur.execute("SELECT * FROM pbe_master_registry WHERE department = %s ORDER BY id DESC", (dept,))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY timestamp DESC LIMIT 20")
    logs = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="layer-card">
            <div class="layer-title">🛠️ Sector Matrix (Layers)</div>
            <div class="guild-grid">
                <a href="/admin-dashboard" class="guild-btn {{{{ 'active-guild' if not current_dept }}}}">GLOBAL REGISTRY</a>
                {{% for g in guilds %}}
                <a href="/admin-dashboard?dept={{{{ g }}}}" class="guild-btn {{{{ 'active-guild' if current_dept == g }}}}">{{{{ g }}}}</a>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">👥 Registry Data: {{{{ current_dept or 'GLOBAL' }}}}</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID / LIC</th><th>NAME</th><th>RANK</th><th>COMMAND SUITE</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr>
                            <td><b>{{{{ w[6] }}}}</b><br><small>{{{{ w[7] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td>{{{{ w[10] }}}}</td>
                            <td>
                                <a href="/admin/print-id/{{{{ w[6] }}}}" class="btn-suite bg-navy"><i class="fas fa-print"></i> Print</a>
                                <a href="https://wa.me/{{{{ w[12] }}}}" class="btn-suite bg-wa" target="_blank"><i class="fab fa-whatsapp"></i></a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-suite bg-red" onclick="return confirm('Erase from Registry?')"><i class="fas fa-trash"></i></a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">🛡️ Live Tracking Terminal</div>
            <div class="terminal">
                {{% for log in logs %}}
                <p>[{{{{ log[1].strftime('%H:%M:%S') }}}}] {{{{ log[2] }}}}: {{{{ log[3] }}}}</p>
                {{% endfor %}}
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname, sname = request.form.get('firstname').upper().replace(" ", "_"), request.form.get('surname').upper().replace(" ", "_")
            photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PP_{fname}_{sname}")
            uid, lic = generate_15_char(fname), generate_15_char(sname)
            
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, 
                        status='ACTIVE' WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        request.form.get('rank'), request.form.get('department'), photo['secure_url'], otp))
            conn.commit(); cur.close(); conn.close()
            log_soul_action("NEW_REGISTRY", f"Personnel {fname} successfully enrolled.")
            return "<div style='text-align:center; padding:100px;'><h1>REGISTRY COMPLETE ✅</h1></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-card" style="max-width:500px; margin: auto;">
            <h3>PERSONNEL REGISTRY FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP Code" style="width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #ddd;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #ddd;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #ddd;" required>
                <select name="department" style="width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #ddd;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Rank (e.g. Master Mason)" style="width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #ddd;" required>
                <p style="font-size:11px; color:gray; margin-top:10px;">ID Photo Upload:</p>
                <input type="file" name="photo" required><br>
                <button class="btn-suite bg-navy" style="width:100%; padding:15px; margin-top:20px; border-radius:8px; color:white; width:100%;">COMPLETE REGISTRY</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS)

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    tpl = os.path.join(app.root_path, 'static', 'Power Bridge Engineering ID Identity Template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[13]: c.drawImage(w[13], 0.18*inch, 0.55*inch, width=1.02*inch, height=1.22*inch)

    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    c.drawString(1.35*inch, 1.55*inch, f"Surname: {w[1]}")
    c.drawString(1.35*inch, 1.40*inch, f"Firstname: {w[2]}")
    c.drawString(1.35*inch, 1.25*inch, f"ID: {w[6]}")
    c.drawString(1.35*inch, 1.10*inch, f"Rank: {w[10]}")
    
    expiry = w[9].strftime('%Y-%m-%d') if w[9] else "N/A"
    c.drawString(1.35*inch, 0.55*inch, f"EXP: {expiry}")
    
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[6]}")
    bounds = qr_code.getBounds(); d = Drawing(40, 40, transform=[40./(bounds[2]-bounds[0]),0,0,40./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch)
    c.showPage(); c.save(); buffer.seek(0)
    log_soul_action("PRINT", f"Staff ID card generated for {w[2]}")
    return send_file(buffer, mimetype='application/pdf')

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp)); conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Your Registry OTP is {otp}. Fill form at: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:400px; margin:auto;"><h3>SEND REGISTRY OTP</h3><form method="POST"><input name="phone" placeholder="233..." style="width:100%; padding:15px; border-radius:10px; border:1px solid #ddd;"><button class="btn-suite bg-navy" style="width:100%; padding:15px; margin-top:10px;">SEND SMS</button></form></div>'))

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
