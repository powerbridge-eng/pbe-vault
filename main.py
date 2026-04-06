import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv, json
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
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_CORE_2026_FINAL_V3"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE PBE WORLD MATRIX (Updated to PBE TV) ---
PBE_GUILDS = [
    "ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", 
    "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", 
    "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", 
    "FASHION DESIGN", "GENERAL TECHNICAL"
]

GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 3. SELF-HEALING SYSTEM (Ensures 24/7 Stability) ---
def perform_self_heal():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
            photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
            region TEXT, issuance_date DATE, expiry_date DATE
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY);")
    cols = {"timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "action": "TEXT", "actor": "TEXT", "details": "TEXT", "ip": "TEXT", "device": "TEXT"}
    for col, defn in cols.items():
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='pbe_soul_audit' AND column_name='{col}';")
        if not cur.fetchone(): cur.execute(f"ALTER TABLE pbe_soul_audit ADD COLUMN {col} {defn};")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    perform_self_heal()

# --- 4. 15-CHAR LOGIC ---
def generate_pbe_id(firstname):
    now = datetime.datetime.now()
    prefix = f"PBE{now.strftime('%y%m')}"
    name_part = re.sub(r'[^A-Z]', '', firstname.upper())[:3]
    needed = 15 - len(prefix) - len(name_part)
    nums = ''.join(random.choices(string.digits, k=needed))
    return f"{prefix}{name_part}{nums}"

def generate_pbe_lic(surname):
    name_part = re.sub(r'[^A-Z]', '', surname.upper())[:3]
    prefix = "PBELIC"
    needed = 15 - len(prefix) - len(name_part)
    nums = ''.join(random.choices(string.digits, k=needed))
    return f"{prefix}{name_part}{nums}"

# --- 5. UI DESIGN (WITH SEARCH & INVITE) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Supreme Command</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --navy: #343a40; --gold: #ffc107; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 80px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); }
        .logo-box { width: 70px; height: 70px; background: white; border-radius: 50%; margin: 0 auto 10px; border: 2px solid var(--gold); display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .container { max-width: 1300px; margin: auto; padding: 15px; }
        .layer-card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .layer-title { font-size: 11px; font-weight: 800; color: #555; text-transform: uppercase; margin-bottom: 15px; border-left: 5px solid var(--navy); padding-left: 10px; }
        
        .search-row { display: flex; gap: 15px; margin-bottom: 20px; align-items: center; }
        .search-input { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; outline: none; }
        .balance-box { background: white; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-weight: bold; font-size: 14px; white-space: nowrap; }

        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-btn { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; text-decoration: none; color: #333; font-size: 10px; font-weight: 700; }
        .active-layer { background: #333 !important; color: var(--gold) !important; border-color: var(--gold) !important; }
        
        .registry-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .registry-table th { background: #f1f1f1; padding: 12px; text-align: left; border-bottom: 2px solid #ddd; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #eee; }
        
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: 800; margin: 2px; display: inline-block; border: none; cursor: pointer; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--gold); color: #000; }
        
        .audit-scroll { height: 160px; overflow-y: auto; background: #fff; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 12px; border: 1px solid #ddd; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; background: #333; color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; text-decoration: none; border: 2px solid var(--gold); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-box"><img src="{{ url_for('static', filename='logo.png') }}" style="max-width:100%;" onerror="this.parentElement.style.display='none'"></div>
        <div style="font-size: 20px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    {% if session.get('role') == 'ADMIN' %}<a href="/admin/invite" class="fab" title="Invite Worker">+</a>{% endif %}
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

# --- 6. CORE ROUTES ---

@app.route("/")
def index(): return redirect(url_for('admin_login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd, name = request.form.get('password'), request.form.get('name')
        if pwd == ADMIN_PASSWORD:
            session['role'], session['name'] = 'ADMIN', name
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD:
            session['role'], session['name'] = 'SUPERVISOR', name
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:380px; margin: 80px auto; text-align:center;"><h3>SYSTEM LOCK</h3><form method="POST"><input name="name" class="search-input" style="width:100%; margin-bottom:10px;" placeholder="Authorized Name" required><input type="password" name="password" class="search-input" style="width:100%; margin-bottom:15px;" placeholder="Master Key" required><button class="btn-6 bg-navy" style="width:100%; padding:15px; font-size:12px;">UNLOCK SYSTEM</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    sms_bal = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=2)
        sms_bal = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_bal = "Offline"

    conn = get_db(); cur = conn.cursor()
    
    # Region Workforce stats
    reg_counts = {}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        reg_counts[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall()
    cur.execute("SELECT * FROM pbe_soul_audit ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-row">
            <input type="text" id="gSearch" class="search-input" placeholder="Global Search Registry (Name, ID, Phone, Guild)..." onkeyup="runSearch()">
            <div class="balance-box">SMS Balance: <span style="color:#22c55e;">{sms_bal}</span></div>
        </div>

        <div class="layer-card">
            <div class="layer-title">🛠️ TECHNICAL GUILDS (MATRIX)</div>
            <div class="matrix-grid">
                <a href="/admin-dashboard" class="matrix-btn active-layer">GLOBAL VIEW</a>
                {{% for g in guilds %}}<a href="#" class="matrix-btn">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">🌍 GHANA REGIONAL DISTRIBUTION (16 REGIONS)</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-btn" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-card">
            <div class="layer-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>COMMAND SUITE (6)</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr class="worker-row">
                            <td><b>{{{{ w[5] }}}}</b></td>
                            <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                            <td>{{{{ w[7] }}}}</td>
                            <td>
                                <a href="/admin/print/{{{{ w[5] }}}}" class="btn-6 bg-navy">PRINT</a>
                                <a href="/admin/renew/{{{{ w[0] }}}}" class="btn-6 bg-gold">RENEW</a>
                                <a href="/admin/suspend/{{{{ w[0] }}}}" class="btn-6 bg-navy" style="background:#64748b;">SUSPEND</a>
                                <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                                {{% if session['role'] == 'ADMIN' %}}
                                <a href="/admin/approve/{{{{ w[0] }}}}" class="btn-6 bg-navy">APPROVE</a>
                                <a href="/admin/delete/{{{{ w[0] }}}}" class="btn-6 bg-red" onclick="return confirm('ERASE?')">DELETE</a>
                                {{% endif %}}
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🛡️ AUDIT LOGS & BRIEF REPORT</div>
            <div class="audit-scroll">
                {{% for l in logs %}}
                <div style="border-bottom:1px solid #eee; padding:5px;">[{{{{ l[1].strftime('%H:%M:%S') }}}}] {{{{ l[3] }}}}: {{{{ l[4] }}}}</div>
                {{% endfor %}}
            </div>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, logs=logs, stats=reg_counts)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if session.get('role') != 'ADMIN': return redirect(url_for('admin_login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        # Arkesel SMS logic using PBE_OTP
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                     json={"sender": "PBE_OTP", "message": f"PBE: Your Registry OTP is {otp}. Register here: {request.url_root}register", "recipients": [phone]}, 
                     headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-card" style="max-width:400px; margin:auto;"><h3>SEND REGISTRY INVITE</h3><form method="POST"><input name="phone" class="search-input" placeholder="233..." style="width:100%;"><button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">SEND SMS INVITE</button></form></div>'))

# [Keep existing ID Print Mapping logic here...]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
