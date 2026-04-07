import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
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
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_ULTIMATE_SUPREME_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db(): return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 2. SELF-HEALING SYSTEM (The Doctor) ---
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
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

with app.app_context(): perform_self_heal()

# --- 3. HYBRID 15-CHAR LOGIC & SMS PULL ---
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

def get_live_balance():
    try:
        # Try V2 API First
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        if r.status_code == 200: return f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
        # Fallback to V1 if V2 fails
        r1 = requests.get(f"https://sms.arkesel.com/api/v1/check-balance?api_key={ARKESEL_API_KEY}&response=json", timeout=3)
        return f"{r1.json().get('balance', '0.00')} GHS"
    except: return "Offline"

# --- 4. EXECUTIVE DASHBOARD DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PBE Command Center</title>
    <style>
        :root { --pbe-grey: #414042; --pbe-gold: #f2a900; --bg: #f4f6f9; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); margin: 0; padding-bottom: 80px; }
        .header { background: var(--pbe-grey); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--pbe-gold); }
        .container { max-width: 1300px; margin: auto; padding: 15px; }
        .layer-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .layer-title { font-size: 11px; font-weight: 800; color: #555; text-transform: uppercase; margin-bottom: 15px; border-left: 5px solid var(--pbe-grey); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .matrix-btn { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; text-decoration: none; color: #333; font-size: 10px; font-weight: 700; }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        .registry-table th { background: #f1f1f1; padding: 12px; text-align: left; border-bottom: 2px solid #ddd; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #eee; }
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; }
        .search-input { width: 100%; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; background: #333; color: var(--pbe-gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <div style="font-size: 20px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
    </div>
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
def index(): return redirect(url_for('admin_login'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'] = 'ADMIN'
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:380px; margin: 80px auto; text-align:center;"><form method="POST"><h3>SYSTEM LOCK</h3><input type="password" name="password" placeholder="Master Key" class="search-input" required><button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">UNLOCK</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    bal = get_live_balance()
    conn = get_db(); cur = conn.cursor()
    reg_stats = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        reg_stats[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:15px;">
            <input type="text" id="gSearch" class="search-input" placeholder="Search Personnel Registry..." onkeyup="runSearch()">
            <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; white-space:nowrap; font-size:13px;">SMS: <b style="color:green;">{bal}</b></div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🌍 GHANA REGIONAL DISTRIBUTION (16 REGIONS)</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-btn" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🛠️ TECHNICAL GUILDS (MATRIX)</div>
            <div class="matrix-grid">
                <a href="#" class="matrix-btn" style="background:#333; color:var(--pbe-gold);">ALL SECTORS</a>
                {{% for g in guilds %}}<a href="#" class="matrix-btn">{{{{g}}}}</a>{{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <div class="layer-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <table class="registry-table">
                <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>COMMAND SUITE (6)</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr class="worker-row">
                        <td><b>{{{{ w[5] }}}}</b></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td>{{{{ w[7] }}}}</td>
                        <td>
                            <a href="#" class="btn-6 bg-navy">PRINT</a>
                            <a href="#" class="btn-6 bg-gold">RENEW</a>
                            <a href="#" class="btn-6" style="background:#64748b;">SUSPEND</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            <a href="#" class="btn-6 bg-navy">APPROVE</a>
                            <a href="#" class="btn-6 bg-red">DELETE</a>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
        <a href="/admin/invite" class="fab">+</a>
    """), guilds=PBE_GUILDS, stats=reg_stats, workers=workers)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if not cur.fetchone(): return "INVALID OTP."
        
        photo = cloudinary.uploader.upload(request.files['photo'])
        uid, lic = generate_pbe_id(request.form.get('firstname')), generate_pbe_lic(request.form.get('surname'))
        
        cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, pbe_uid=%s, pbe_license=%s, 
                    rank=%s, department=%s, phone_no=%s, email=%s, ghana_card=%s, photo_url=%s, 
                    region=%s, issuance_date=%s, expiry_date=%s WHERE otp_code=%s""",
                   (request.form.get('surname').upper(), request.form.get('firstname').upper(), uid, lic,
                    request.form.get('rank'), request.form.get('department'), request.form.get('phone'),
                    request.form.get('email'), request.form.get('ghana_card'), photo['secure_url'],
                    request.form.get('region'), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730), otp))
        conn.commit(); cur.close(); conn.close()
        return "SUCCESSFULLY REGISTERED ✅"

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box" style="max-width:500px; margin:auto;">
            <h3>PERSONNEL REGISTRY FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="Enter OTP" class="search-input" required style="margin-bottom:10px;">
                <input name="surname" placeholder="Surname" class="search-input" required style="margin-bottom:10px;">
                <input name="firstname" placeholder="First Name" class="search-input" required style="margin-bottom:10px;">
                <select name="region" class="search-input" style="margin-bottom:10px;">
                    {% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}
                </select>
                <select name="department" class="search-input" style="margin-bottom:10px;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Rank" class="search-input" required style="margin-bottom:10px;">
                <input name="phone" placeholder="Phone (233...)" class="search-input" required style="margin-bottom:10px;">
                <input name="email" type="email" placeholder="Email" class="search-input" required style="margin-bottom:10px;">
                <input name="ghana_card" placeholder="Ghana Card ID" class="search-input" required style="margin-bottom:10px;">
                <p>Passport Photo:</p><input type="file" name="photo" required>
                <button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">SUBMIT FORM</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GH_REGIONS)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (request.form.get('phone'), otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                     json={"sender": "PBE_OTP", "message": f"PBE: Your OTP is {otp}. Register at {request.url_root}register", "recipients": [request.form.get('phone')]}, 
                     headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer-box" style="max-width:400px; margin:auto;"><form method="POST"><h3>SEND INVITE</h3><input name="phone" placeholder="233..." class="search-input" required><button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:10px;">SEND OTP</button></form></div>'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
