import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time
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
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_FORTIFIED_FINAL_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    for i in range(5):
        try:
            return psycopg2.connect(DATABASE_URL)
        except:
            time.sleep(2)
    return None

# --- 2. PBE WORLD MATRIX (UPDATED) ---
PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "ETC / GENERAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 3. ROBOT MAPPING & ID LOGIC ---
def gen_pbe_uid(name):
    now = datetime.datetime.now()
    return f"PBE{now.strftime('%y%m')}{name[:3].upper()}{''.join(random.choices(string.digits, k=4))}"

def gen_pbe_lic(name):
    return f"PBELIC{name[:3].upper()}{''.join(random.choices(string.digits, k=6))}"

# --- 4. UI ARCHITECTURE (STANDALONE LOGO & TRIPLE FAB) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Command Center</title>
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 120px; }
        .logo-standalone { text-align: center; padding: 30px; background: white; border-bottom: 2px solid #eee; }
        .logo-img { width: 100px; height: 100px; border-radius: 50%; border: 3px solid var(--pbe-gold); }
        .nav-bar { background: var(--pbe-grey); color: white; padding: 15px; text-align: center; border-bottom: 4px solid var(--pbe-gold); font-weight: 900; letter-spacing: 2px; }
        .container { max-width: 1300px; margin: auto; padding: 20px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-item { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; font-size: 10px; font-weight: 700; color: #333; text-decoration: none; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; }
        
        /* THE COMMAND FAB ZONE */
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .fab-invite { background: #333; color: var(--pbe-gold); }
        .fab-audit { background: var(--pbe-grey); color: white; }
        .fab-alert { background: #ff4d4d; color: white; }
    </style>
</head>
<body>
    <div class="logo-standalone"><img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.src='https://via.placeholder.com/100?text=PBE'"></div>
    <div class="nav-bar">PBE SUPREME COMMAND CENTER</div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>
        function runSearch() {
            let filter = document.getElementById('gSearch').value.toUpperCase();
            document.querySelectorAll('.worker-row').forEach(row => {
                row.style.display = row.innerText.toUpperCase().includes(filter) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/")
def home(): return redirect(url_for('admin_login'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    conn = get_db(); cur = conn.cursor()
    # Check for expiries (2 years)
    cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
    expiry_alerts = cur.fetchone()[0]

    stats = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        stats[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:15px;">
            <input type="text" id="gSearch" style="width:100%; padding:15px; border-radius:10px; border:1px solid #ddd;" placeholder="Search Personnel Registry..." onkeyup="runSearch()">
        </div>

        <div class="layer-box">
            <div style="font-size:11px; font-weight:800; margin-bottom:10px;">🌍 REGIONAL MATRIX</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-item" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div style="font-size:11px; font-weight:800; margin-bottom:10px;">🛠️ TECHNICAL GUILDS</div>
            <div class="matrix-grid">
                {{% for g in guilds %}}<a href="#" class="matrix-item">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div style="font-size:11px; font-weight:800; margin-bottom:10px;">👥 PERSONNEL REGISTRY</div>
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead><tr style="background:#f1f1f1;"><th style="padding:10px; text-align:left;">ID</th><th style="text-align:left;">NAME</th><th style="text-align:left;">ACTIONS (6)</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr class="worker-row" style="border-bottom:1px solid #eee;">
                        <td style="padding:12px;"><b>{{{{ w[5] }}}}</b></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td>
                            <a href="/print/{{{{w[5]}}}}" class="btn-6 bg-navy">PRINT</a>
                            <a href="#" class="btn-6 bg-gold">RENEW</a>
                            <a href="#" class="btn-6" style="background:#6c757d;">SUSPEND</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            <a href="#" class="btn-6 bg-navy">APPROVE</a>
                            <a href="#" class="btn-6 bg-red">DELETE</a>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>

        <div class="fab-zone">
            <div style="position:relative;">
                {{% if alerts > 0 %}}
                <span style="position:absolute; top:-5px; right:-5px; background:white; color:red; border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:bold; border:1px solid red;">{{{{alerts}}}}</span>
                {{% endif %}}
                <a href="/admin/alerts" class="fab fab-alert" title="Expiry Alerts">🔔</a>
            </div>
            <a href="/admin/audit" class="fab fab-audit" title="Soul Audit Logs">📜</a>
            <a href="/admin/invite" class="fab fab-invite" title="Send OTP Invite">+</a>
        </div>
    """), guilds=PBE_GUILDS, stats=stats, workers=workers, alerts=expiry_alerts)

# --- 6. ROBOT MAPPING ENGINE (PRINTING) ---
@app.route("/print/<uid>")
def print_id(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    
    # Template
    tpl = os.path.join(app.root_path, 'static', 'power bridge engineering identity template.png')
    if os.path.exists(tpl): c.drawImage(tpl, 0, 0, width=3.375*inch, height=2.125*inch)
    
    # Passport Photo (Right Side)
    if w[12]: c.drawImage(w[12], 2.2*inch, 0.6*inch, width=0.9*inch, height=1.1*inch)
    
    # Ghost Watermark Photo (Left Side - Low Alpha)
    c.saveState()
    c.setStrokeColorRGB(0,0,0)
    c.setFillAlpha(0.2)
    if w[12]: c.drawImage(w[12], 0.2*inch, 0.7*inch, width=0.5*inch, height=0.6*inch, mask='auto')
    c.restoreState()

    # QR Code Security
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[5]}")
    d = Drawing(45, 45, transform=[45./qr_code.getBounds()[2],0,0,45./qr_code.getBounds()[3],0,0])
    d.add(qr_code)
    d.drawOn(c, 2.8*inch, 0.1*inch)

    # Data Mapping
    c.setFont("Helvetica-Bold", 7)
    c.drawString(1.0*inch, 1.4*inch, f"{w[1]} {w[2]}")
    c.drawString(1.0*inch, 1.25*inch, f"ID: {w[5]}")
    c.drawString(1.0*inch, 1.10*inch, f"LIC: {w[6]}")
    c.drawString(1.0*inch, 0.95*inch, f"EXP: {w[17]}")

    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

# --- 7. INVITE SYSTEM (FIXED) ---
@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999))
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (request.form.get('phone'), otp))
            conn.commit(); cur.close(); conn.close()
            
            # Arkesel Handshake
            requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                         json={"sender": "PBE_OTP", "message": f"PBE: Use OTP {otp} to register here: {request.url_root}register", "recipients": [request.form.get('phone')]}, 
                         headers={"api-key": ARKESEL_API_KEY}, timeout=5)
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            return f"Database is waking up, try again in 5 seconds. Error: {e}"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:400px; margin:auto;"><h3>SEND INVITE</h3><form method="POST"><input name="phone" placeholder="233..." style="width:100%; padding:15px; margin-bottom:10px;" required><button class="btn-6 bg-navy" style="width:100%; padding:15px;">SEND OTP</button></form></div>'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'] = 'ADMIN'
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:380px; margin: 80px auto; text-align:center;"><form method="POST"><h3>PBE SYSTEM LOCK</h3><input type="password" name="password" style="width:100%; padding:15px; border-radius:8px; border:1px solid #ddd;" placeholder="Master Key" required><button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">UNLOCK</button></form></div>'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
