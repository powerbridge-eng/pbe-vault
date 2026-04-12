import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time, json, base64
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, render_template, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ADMIN_PASSWORD = "PBE-Global-2026"
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_ABSOLUTE_SOVEREIGN_BUILD_2026"

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

# --- 2. THE SMART AUTO-RESTART DATABASE DOCTOR ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pbe_registry_2026' AND column_name='gender';")
    is_updated = cur.fetchone()
    
    if not is_updated:
        cur.execute("DROP TABLE IF EXISTS pbe_registry_2026 CASCADE;")
        cur.execute("DROP TABLE IF EXISTS pbe_audit_2026 CASCADE;")
        cur.execute("DROP TABLE IF EXISTS pbe_ip_blacklist CASCADE;")
        print("SYSTEM OVERRIDE: Executed one-time database purge and rebuild.")
        
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_registry_2026 (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT, email TEXT, ghana_card_no TEXT, photo_url TEXT, ghana_card_url TEXT,
            status TEXT DEFAULT 'PENDING', otp_code TEXT, region TEXT, station TEXT,
            issuance_date DATE, expiry_date DATE
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_audit_2026 (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip_address TEXT, device_info TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_ip_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, locked_until TIMESTAMP);")
    
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_db()

# --- THE GEO-IP TRACKING & NAMED AUDIT LOG ENGINE ---
def log_soul_action(action, details):
    role = session.get('role', 'SYSTEM')
    op_name = session.get('op_name', 'Unknown')
    actor = f"{role} ({op_name})"
    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    
    remote = request.remote_addr or '127.0.0.1'
    ip = request.headers.get('X-Forwarded-For', remote).split(',')[0].strip()
    
    location = "Unknown Location"
    if ip and ip != '127.0.0.1':
        try:
            geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
            if geo.get('status') == 'success':
                location = f"{geo.get('city')}, {geo.get('regionName')}, {geo.get('country')}"
        except: pass
        
    ip_with_geo = f"{ip} [{location}]"

    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_2026 (action, actor, details, ip_address, device_info) VALUES (%s, %s, %s, %s, %s)",
                (action, actor, details, ip_with_geo, device))
    conn.commit(); cur.close(); conn.close()

def is_blacklisted(ip):
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT locked_until FROM pbe_ip_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def blacklist_ip(ip):
    lock_time = datetime.datetime.now() + datetime.timedelta(hours=72)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_ip_blacklist (ip_address, locked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET locked_until = %s", (ip, lock_time, lock_time))
    conn.commit(); cur.close(); conn.close()

def generate_pbe_id():
    digits = ''.join(random.choices(string.digits, k=8))
    return f"PBE ID {digits}"

def generate_pbe_lic():
    digits = ''.join(random.choices(string.digits, k=7))
    return f"PBE LIC {digits}"

# --- 3. THE PBE WORLD MATRIX & RANK HIERARCHY ---
PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"]
PBE_RANKS = ["Supreme Commander / CEO", "General Manager", "Chief Engineer", "Project Commander", "Warrant Supervisor", "Senior Master Technician", "Squad Supervisor", "Lead Technician", "Field Technician", "Engineering Recruit"]
GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 4. EXECUTIVE UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Supreme Command Center</title>
    <style>
        :root { --navy: #343a40; --gold: #ffc107; --bg: #f4f6f9; --text: #495057; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; color: var(--text); padding-bottom: 100px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 4px solid var(--gold); }
        .logo { height: 60px; margin-bottom: 10px; border-radius: 50%; }
        .container { max-width: 1300px; margin: auto; padding: 15px; }
        .search-container { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
        .search-bar { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; font-size: 16px; outline: none; background: #fff; min-width: 280px; }
        .sms-balance { background: #fff; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; font-weight: bold; }
        .section-card { background: #fff; border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #e9ecef; }
        .section-title { font-size: 13px; font-weight: 800; color: #6c757d; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
        .matrix-item { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; text-align: center; font-size: 11px; font-weight: bold; color: var(--navy); }
        .guild-btn { text-decoration: none; display: block; }
        .guild-active { background: var(--navy); color: var(--gold); border-color: var(--gold); }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th { text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #f1f3f5; }
        .btn-cmd { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; margin: 2px; display: inline-block; border: none; cursor: pointer; text-align: center;}
        .bg-blue { background: #007bff; } .bg-wa { background: #28a745; } .bg-red { background: #dc3545; } .bg-sus { background: #6c757d; } .bg-gold { background: var(--gold); color: #000; } .bg-navy { background: var(--navy); } .bg-orange { background: #fd7e14; }
        .fab-zone { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 1000; }
        .fab { width: 60px; height: 60px; background: var(--navy); color: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-decoration: none; border: 2px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo" onerror="this.style.display='none'">
        <div style="font-size: 22px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
        <div style="font-size: 12px; margin-top: 5px; color: var(--gold);">OPERATOR: {{ session.get('op_name', 'SYSTEM') }}</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>
        function filterRegistry() {
            let filter = document.getElementById('globalSearch').value.toUpperCase();
            document.querySelectorAll('.worker-row').forEach(row => {
                row.style.display = row.innerText.toUpperCase().includes(filter) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

VERIFY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE ID Verification</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; text-align: center; color: #343a40; }
        .card { max-width: 400px; margin: 20px auto; background: #fff; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; border-top: 5px solid #ffc107; }
        .header { background: #343a40; color: white; padding: 15px; font-weight: bold; font-size: 18px; letter-spacing: 1px; }
        .photo-container { margin: 20px 0; }
        .photo { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid #f4f6f9; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .name { font-size: 22px; font-weight: 900; text-transform: uppercase; margin-bottom: 5px; }
        .rank { font-size: 14px; color: #6c757d; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; }
        .details { text-align: left; padding: 0 20px 20px; font-size: 13px; line-height: 1.8; }
        .details b { color: #343a40; }
        .status-badge { display: inline-block; padding: 10px 20px; border-radius: 30px; color: white; font-weight: 900; font-size: 16px; margin-bottom: 20px; letter-spacing: 1px; }
        .status-active { background: #28a745; box-shadow: 0 0 15px rgba(40,167,69,0.4); }
        .status-suspended { background: #dc3545; box-shadow: 0 0 15px rgba(220,53,69,0.4); }
        .status-expired { background: #ffc107; color: #000; box-shadow: 0 0 15px rgba(255,193,7,0.4); }
        .status-declined { background: #fd7e14; box-shadow: 0 0 15px rgba(253,126,20,0.4); }
        .watermark { font-size: 10px; color: #adb5bd; margin-top: 20px; }
    </style>
</head>
<body>
    <img src="{{ url_for('static', filename='logo.png') }}" style="height: 50px;" onerror="this.style.display='none'">
    {% if not w %}
        <div class="card" style="border-top-color: #dc3545;"><div class="header" style="background: #dc3545;">SECURITY ALERT</div><div style="padding: 40px 20px;"><h1 style="color: #dc3545; margin:0;">❌ INVALID ID</h1><p style="font-weight:bold; margin-top:15px;">This ID does not exist in the PBE Master Registry.</p></div></div>
    {% else %}
        <div class="card">
            <div class="header">OFFICIAL PERSONNEL RECORD</div>
            <div class="photo-container"><img src="{{ w[13] }}" class="photo" onerror="this.src='https://via.placeholder.com/150'"></div>
            <div class="name">{{ w[2] }} {{ w[1] }}</div>
            <div class="rank">{{ w[8] }} - {{ w[9] }}</div>
            <div class="status-badge {% if live_status == 'ACTIVE' %} status-active {% elif live_status == 'EXPIRED' %} status-expired {% elif live_status == 'DECLINED' %} status-declined {% else %} status-suspended {% endif %}">{{ live_status }}</div>
            <div class="details">
                <div><b>PBE ID NUMBER:</b> <span style="float:right;">{{ w[6] }}</span></div>
                <div><b>LICENSE NO:</b> <span style="float:right;">{{ w[7] }}</span></div>
                <div><b>GENDER:</b> <span style="float:right;">{{ w[4] }}</span></div>
                <div><b>STATION/REGION:</b> <span style="float:right; color:#007bff; font-weight:bold;">{{ w[17] | upper }}</span></div>
                <div><b>DATE OF ISSUANCE:</b> <span style="float:right;">{{ w[19] }}</span></div>
                <div><b>DATE OF EXPIRY:</b> <span style="float:right; color: {% if live_status == 'EXPIRED' %}red{% else %}black{% endif %};">{{ w[20] }}</span></div>
            </div>
        </div>
    {% endif %}
</body>
</html>
"""

# --- 5. THE VISUAL EDITOR BRIDGE (FABRIC.JS ENGINE) ---
@app.route("/admin/visual-editor/<uid>")
def visual_editor(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    return render_template('editor.html', uid=uid, w=w)

@app.route("/process-visual-print", methods=['POST'])
def process_visual_print():
    if not session.get('role'): abort(403)
    data = request.json
    img_data = data.get('image').split(',')[1] 
    uid = data.get('uid')
    session[f'print_ready_{uid}'] = img_data
    return jsonify({"status": "success", "redirect": url_for('download_final_pdf', uid=uid)})

@app.route("/download-final-pdf/<uid>")
def download_final_pdf(uid):
    img_data = session.get(f'print_ready_{uid}')
    if not img_data: return "Session Expired", 404
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    img_bytes = BytesIO(base64.b64decode(img_data))
    c.drawImage(ImageReader(img_bytes), 0, 0, width=3.375*inch, height=2.125*inch)
    c.showPage(); c.save(); buffer.seek(0)
    session.pop(f'print_ready_{uid}', None)
    log_soul_action("VISUAL PRINT", f"Generated Final ID for {uid}")
    return send_file(buffer, mimetype='application/pdf', download_name=f"PBE_ID_{uid}.pdf")

# --- 6. DASHBOARD & METRICS ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    role = session.get('role')
    
    sms_live = "..."
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        sms_live = f"{r.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: sms_live = "OFFLINE"

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days' AND surname IS NOT NULL")
    expiry_alerts = cur.fetchone()[0]

    reg_stats = {r: 0 for r in GHANA_REGIONS}
    for r in GHANA_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE region = %s AND surname IS NOT NULL", (r,))
        reg_stats[r] = cur.fetchone()[0]

    guild_stats = {g: 0 for g in PBE_GUILDS}
    for g in PBE_GUILDS:
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE department = %s AND surname IS NOT NULL", (g,))
        guild_stats[g] = cur.fetchone()[0]

    dept = request.args.get('dept')
    if dept: 
        cur.execute("SELECT * FROM pbe_registry_2026 WHERE department = %s AND surname IS NOT NULL ORDER BY id DESC", (dept,))
    else: 
        cur.execute("SELECT * FROM pbe_registry_2026 WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div class="search-container">
            <input type="text" id="globalSearch" class="search-bar" placeholder="Search Master Registry..." onkeyup="filterRegistry()">
            <div class="sms-balance">SMS: <span style="color:green;">{sms_live}</span></div>
        </div>
        <div class="section-card">
            <div class="section-title">🌍 REGIONAL METRIC</div>
            <div class="matrix-grid">
                {{% for reg, count in reg_stats.items() %}}<div class="matrix-item">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>{{% endfor %}}
            </div>
        </div>
        <div class="section-card">
            <div class="section-title">👥 PERSONNEL REGISTRY</div>
            <table class="registry-table">
                <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>STATUS</th><th>COMMAND SUITE</th></tr></thead>
                <tbody>
                    {{% for w in workers %}}
                    <tr class="worker-row">
                        <td><b>{{{{ w[6] }}}}</b></td>
                        <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                        <td><b style="color:red;">{{{{ w[8] }}}}</b></td>
                        <td><b>{{{{ w[15] }}}}</b></td>
                        <td>
                            <a href="{{{{ url_for('visual_editor', uid=w[6]) }}}}" class="btn-cmd bg-blue">PRINT</a>
                            <a href="{{{{ url_for('review_cmd', uid=w[6]) }}}}" class="btn-cmd bg-navy">REVIEW</a>
                            {{% if role == 'ADMIN' %}}
                            <a href="{{{{ url_for('promote_cmd', uid=w[6]) }}}}" class="btn-cmd bg-gold">PROMOTE</a>
                            <a href="{{{{ url_for('delete_cmd', uid=w[6]) }}}}" class="btn-cmd bg-red">DELETE</a>
                            {{% endif %}}
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
    """), reg_stats=reg_stats, workers=workers, role=role, alerts=expiry_alerts)

# --- 7. COMMAND ENDPOINTS ---
@app.route("/admin/review/<uid>")
def review_cmd(uid):
    if not session.get('role'): abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    DOSSIER_HTML = """
    <div class="section-card" style="max-width:800px; margin:auto; text-align:center;">
        <h3>📋 PERSONNEL DOSSIER: {{ w[1] }} {{ w[2] }}</h3>
        <img src="{{ w[13] }}" style="width:200px; border-radius:10px; margin-bottom:20px;">
        <div style="display:flex; gap:10px; justify-content:center;">
            <a href="{{ url_for('approve_cmd', uid=w[6]) }}" class="btn-cmd bg-wa">APPROVE</a>
            <a href="{{ url_for('renew_cmd', uid=w[6]) }}" class="btn-cmd bg-gold">🔄 RENEW ID</a>
            <a href="/admin-dashboard" class="btn-cmd bg-sus">BACK</a>
        </div>
    </div>
    """
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", DOSSIER_HTML), w=w)

@app.route("/admin/promote/<uid>", methods=['GET', 'POST'])
def promote_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    if request.method == 'POST':
        conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET rank = %s WHERE pbe_uid = %s", (request.form.get('new_rank'), uid))
        conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))
    return "Promotion Portal Loading..."

@app.route("/admin/approve/<uid>")
def approve_cmd(uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/admin/renew/<uid>")
def renew_cmd(uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET expiry_date = expiry_date + INTERVAL '2 years' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete/<uid>")
def delete_cmd(uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'] = 'ADMIN'; session['op_name'] = request.form.get('op_name'); return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<form method="POST"><input name="op_name" placeholder="Name"><input type="password" name="password" placeholder="Key"><button>UNLOCK</button></form>'))

@app.route("/")
def index(): return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
