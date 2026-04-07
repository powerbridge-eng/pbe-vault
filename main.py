import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY") 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_FINAL_RESTORED_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    for i in range(5):
        try: return psycopg2.connect(DATABASE_URL)
        except: time.sleep(2)
    return None

# --- 2. SYSTEM DOCTOR ---
def init_fresh_system():
    conn = get_db()
    if not conn: return
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_master_registry (id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT, phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, region TEXT, issuance_date DATE, expiry_date DATE);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_soul_audit (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT);")
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_fresh_system()

# --- 3. PBE WORLD MATRIX ---
PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "ETC / GENERAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 4. EXECUTIVE UI ---
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
        .btn-6 { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 9px; font-weight: 800; margin: 2px; display: inline-block; border: none; cursor: pointer; }
        .bg-navy { background: #1e293b; } .bg-wa { background: #22c55e; } .bg-red { background: #ef4444; } .bg-gold { background: var(--pbe-gold); color: #000; } .bg-sus { background: #64748b; }
        .search-bar { width: 100%; padding: 15px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; text-decoration: none; border: 2px solid var(--pbe-gold); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .fab-invite { background: #333; color: var(--pbe-gold); }
        .fab-audit { background: var(--pbe-grey); color: white; }
        .fab-alert { background: #ff4d4d; color: white; }
    </style>
    <script>
        function runSearch() {
            let filter = document.getElementById('gSearch').value.toUpperCase();
            document.querySelectorAll('.worker-row').forEach(row => {
                row.style.display = row.innerText.toUpperCase().includes(filter) ? '' : 'none';
            });
        }
    </script>
</head>
<body>
    <div class="logo-standalone"><img src="{{ url_for('static', filename='logo.png') }}" class="logo-img" onerror="this.src='https://via.placeholder.com/100?text=PBE'"></div>
    <div class="nav-bar">PBE SUPREME COMMAND CENTER</div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/")
def home(): return redirect(url_for('admin_login'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    # Live SMS Pull
    sms_bal = "Offline"
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=2)
        if r.status_code == 200: sms_bal = f"{r.json()['data']['available_balance']} GHS"
    except: pass

    conn = get_db(); cur = conn.cursor()
    stats = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        stats[r] = cur.fetchone()[0]
    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:20px;">
            <input type="text" id="gSearch" class="search-bar" placeholder="Search Personnel Registry..." onkeyup="runSearch()">
            <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; white-space:nowrap; font-weight:bold;">SMS: <span style="color:green;">{sms_bal}</span></div>
        </div>

        <div class="layer-box">
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-item" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>

        <div class="layer-box">
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead><tr style="background:#f1f1f1;"><th style="padding:10px; text-align:left;">PBE-ID</th><th style="text-align:left;">NAME</th><th style="text-align:left;">COMMANDS (6)</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr class="worker-row" style="border-bottom:1px solid #eee;">
                        <td style="padding:12px;"><b>{{{{ w[5] }}}}</b></td>
                        <td>{{{{ w[1] }}}} {{{{ w[2] }}}}</td>
                        <td>
                            <a href="#" class="btn-6 bg-navy">PRINT</a>
                            <a href="#" class="btn-6 bg-red">DELETE</a>
                            <a href="https://wa.me/{{{{ w[9] }}}}" target="_blank" class="btn-6 bg-wa">WA</a>
                            <a href="#" class="btn-6 bg-sus">SUSPEND</a>
                            <a href="mailto:{{{{ w[10] }}}}" class="btn-6 bg-navy">EMAIL</a>
                            <a href="#" class="btn-6 bg-gold">RENEW</a>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>

        <div class="fab-zone">
            <a href="/admin/alerts" class="fab fab-alert">🔔</a>
            <a href="/admin/audit" class="fab fab-audit">📜</a>
            <a href="/admin/invite" class="fab fab-invite">+</a>
        </div>
    """), guilds=PBE_GUILDS, stats=stats, workers=workers))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        first = request.form.get('firstname').upper()
        last = request.form.get('surname').upper()
        full_name = f"{last}_{first}"
        
        # CLOUDINARY SMART NAMING
        photo = cloudinary.uploader.upload(request.files['photo'], public_id=f"PBE_PASSPORT_{full_name}")
        
        now = datetime.datetime.now()
        uid = f"PBE{now.strftime('%y%m')}{first[:3]}{''.join(random.choices(string.digits, k=4))}"
        lic = f"PBELIC{last[:3]}{''.join(random.choices(string.digits, k=6))}"
        
        conn = get_db(); cur = conn.cursor()
        cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, pbe_uid=%s, pbe_license=%s, 
                    rank=%s, department=%s, email=%s, photo_url=%s, region=%s, 
                    issuance_date=%s, expiry_date=%s, status='ACTIVE' WHERE otp_code=%s""",
                   (last, first, uid, lic, request.form.get('rank'), request.form.get('department'),
                    request.form.get('email'), photo['secure_url'], request.form.get('region'), 
                    datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730), otp))
        conn.commit(); cur.close(); conn.close()
        return "REGISTRATION SUCCESSFUL ✅"
    return render_template_string("...[Keep Form HTML here]...")

# [REST OF ROUTES INTACT]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
