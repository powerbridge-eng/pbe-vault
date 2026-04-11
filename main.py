import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
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
PBE_GUILDS = [
    "ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", 
    "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", 
    "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"
]

PBE_RANKS = [
    "Supreme Commander / CEO", "General Manager", "Chief Engineer", 
    "Project Commander", "Warrant Supervisor", "Senior Master Technician", 
    "Squad Supervisor", "Lead Technician", "Field Technician", "Engineering Recruit"
]

GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 4A. EXECUTIVE UI DESIGN ---
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

# --- 4B. PUBLIC VERIFICATION UI DESIGN ---
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
        <div class="card" style="border-top-color: #dc3545;">
            <div class="header" style="background: #dc3545;">SECURITY ALERT</div>
            <div style="padding: 40px 20px;">
                <h1 style="color: #dc3545; margin:0;">❌ INVALID ID</h1>
                <p style="font-weight:bold; margin-top:15px;">This ID does not exist in the PBE Master Registry.</p>
                <p>Card may be counterfeit.</p>
            </div>
        </div>
    {% else %}
        <div class="card">
            <div class="header">OFFICIAL PERSONNEL RECORD</div>
            
            <div class="photo-container">
                <img src="{{ w[13] }}" class="photo" alt="Personnel Photo" onerror="this.src='https://via.placeholder.com/150'">
            </div>
            
            <div class="name">{{ w[2] }} {{ w[1] }}</div>
            <div class="rank">{{ w[8] }} - {{ w[9] }}</div>
            
            <div class="status-badge 
                {% if live_status == 'ACTIVE' %} status-active 
                {% elif live_status == 'EXPIRED' %} status-expired 
                {% elif live_status == 'DECLINED' %} status-declined
                {% else %} status-suspended {% endif %}">
                {{ live_status }}
            </div>
            
            <div class="details">
                <hr style="border: 0; border-top: 1px solid #eee; margin-bottom:15px;">
                <div><b>PBE ID NUMBER:</b> <span style="float:right;">{{ w[6] }}</span></div>
                <div><b>LICENSE NO:</b> <span style="float:right;">{{ w[7] }}</span></div>
                <div><b>GENDER:</b> <span style="float:right;">{{ w[4] }}</span></div>
                <div><b>STATION/REGION:</b> <span style="float:right; color:#007bff; font-weight:bold;">{{ w[17] | upper }}</span></div>
                <hr style="border: 0; border-top: 1px solid #eee; margin:top:15px; margin-bottom:15px;">
                <div><b>DATE OF ISSUANCE:</b> <span style="float:right;">{{ w[19] }}</span></div>
                <div><b>DATE OF EXPIRY:</b> <span style="float:right; color: {% if live_status == 'EXPIRED' %}red{% else %}black{% endif %};">{{ w[20] }}</span></div>
            </div>
        </div>
        <div class="watermark">POWER BRIDGE ENGINEERING © 2026<br>VERIFICATION PORTAL</div>
    {% endif %}
</body>
</html>
"""

# --- 5. DASHBOARD & METRICS ---
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

    reg_stats = {}
    for r in GHANA_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE region = %s AND surname IS NOT NULL", (r,))
        reg_stats[r] = cur.fetchone()[0]

    guild_stats = {}
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
            {{% if role == 'ADMIN' %}}
            <a href="https://cloudinary.com/console" target="_blank" class="btn-cmd bg-navy" style="padding:15px; font-size:14px;">☁️ CLOUDINARY</a>
            {{% endif %}}
            <div class="sms-balance">SMS: <span style="color:green;">{sms_live}</span></div>
        </div>
        
        <div class="section-card">
            <div class="section-title">🌍 16-REGION GLOBAL METRIC</div>
            <div class="matrix-grid">
                {{% for reg, count in reg_stats.items() %}}
                <div class="matrix-item" style="text-align:left;">
                    {{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b>
                </div>
                {{% endfor %}}
            </div>
        </div>

        <div class="section-card">
            <div class="section-title">🛠️ TECHNICAL GUILDS WORKFORCE METRIC</div>
            <div class="matrix-grid">
                {{% for guild, count in guild_stats.items() %}}
                <div class="matrix-item" style="text-align:left;">
                    <a href="?dept={{{{guild}}}}" class="guild-btn {{{{ 'guild-active' if current_dept == guild else '' }}}}">
                        {{{{guild}}}} <b style="color:{{{{ 'var(--gold)' if current_dept == guild else 'red' }}}}; float:right;">{{{{count}}}}</b>
                    </a>
                </div>
                {{% endfor %}}
            </div>
            {{% if current_dept %}}
            <a href="/admin-dashboard" class="btn-cmd bg-navy" style="margin-top:10px;">SHOW ALL GUILDS</a>
            {{% endif %}}
        </div>

        <div class="section-card">
            <div class="section-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID / LICENSE</th><th>NAME</th><th>RANK & DEPT</th><th>STATUS</th><th>COMMAND SUITE</th></tr></thead>
                    <tbody>
                        {{% for w in workers %}}
                        <tr class="worker-row">
                            <td>ID: <b>{{{{ w[6] }}}}</b><br>LIC: <small>{{{{ w[7] }}}}</small></td>
                            <td>{{{{ w[1] }}}}, {{{{ w[2] }}}}</td>
                            <td><b style="color:red;">{{{{ w[8] }}}}</b><br><small>{{{{ w[9] }}}}</small></td>
                            <td><b style="color:{{{{ '#28a745' if w[15]=='ACTIVE' else '#fd7e14' if w[15]=='DECLINED' else '#dc3545' }}}};">{{{{ w[15] }}}}</b></td>
                            <td>
                                <a href="{{{{ url_for('print_id', pbe_uid=w[6]) }}}}" class="btn-cmd bg-blue">PRINT</a>
                                <a href="{{{{ url_for('review_cmd', uid=w[6]) }}}}" class="btn-cmd bg-navy">REVIEW DOSSIER</a>
                                <a href="mailto:{{{{ w[11] }}}}" class="btn-cmd bg-navy">EMAIL</a>
                                <a href="https://wa.me/{{{{ w[10]|replace('+', '')|replace(' ', '') }}}}" class="btn-cmd bg-wa" target="_blank">WA</a>
                                {{% if role == 'ADMIN' %}}
                                <a href="{{{{ url_for('promote_cmd', uid=w[6]) }}}}" class="btn-cmd bg-gold">PROMOTE</a>
                                <a href="{{{{ url_for('suspend_cmd', uid=w[6]) }}}}" class="btn-cmd bg-sus">SUSPEND</a>
                                <a href="{{{{ url_for('unsuspend_cmd', uid=w[6]) }}}}" class="btn-cmd bg-blue">UNSUSPEND</a>
                                <a href="{{{{ url_for('renew_cmd', uid=w[6]) }}}}" class="btn-cmd bg-gold">RENEW</a>
                                <a href="{{{{ url_for('delete_cmd', uid=w[6]) }}}}" class="btn-cmd bg-red" onclick="return confirm('Erase Soul Record Permanently?')">DELETE</a>
                                {{% endif %}}
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="fab-zone">
            <a href="/admin/alerts" class="fab" title="Alerts">🔔 {{{{alerts}}}}</a>
            {{% if role == 'ADMIN' %}}<a href="/admin/audit" class="fab" title="Audit">📜</a>{{% endif %}}
            <a href="/admin/invite" class="fab" title="Invite">＋</a>
        </div>
    """), guilds=PBE_GUILDS, workers=workers, current_dept=dept, role=role, alerts=expiry_alerts, reg_stats=reg_stats, guild_stats=guild_stats)

# --- 6. COMMAND ENDPOINTS (THE MATRIX BUTTONS) ---
@app.route("/admin/review/<uid>")
def review_cmd(uid):
    if not session.get('role'): abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    
    # Pre-warm Cloudinary Cache to prevent Print timeouts
    photo_url = w[13]
    if photo_url and "cloudinary" in photo_url and "/upload/" in photo_url:
        parts = photo_url.split('/upload/')
        photo_url = f"{parts[0]}/upload/e_background_removal/f_png/{parts[1]}"
        
    DOSSIER_HTML = """
    <div class="section-card" style="max-width:800px; margin:auto;">
        <h3>📋 PERSONNEL REVIEW DOSSIER</h3>
        <div style="display:flex; gap:20px; flex-wrap:wrap; margin-bottom:20px;">
            <div style="flex:1; min-width:250px;">
                <p style="font-size:12px; font-weight:bold;">PASSPORT PHOTO (Pre-processing AI Cache...):</p>
                <img src="{{ photo_url }}" style="width:100%; max-width:250px; border:2px solid #dee2e6; border-radius:8px;">
            </div>
            <div style="flex:1; min-width:250px;">
                <p style="font-size:12px; font-weight:bold;">GHANA CARD VERIFICATION:</p>
                <img src="{{ w[14] }}" style="width:100%; max-width:350px; border:2px solid #dee2e6; border-radius:8px;">
            </div>
        </div>
        <table class="registry-table" style="margin-bottom:20px; border:1px solid #dee2e6; border-radius:8px; overflow:hidden;">
            <tr style="background:#f8f9fa;"><th>PBE ID</th><td><b>{{ w[6] }}</b></td><th>LICENSE</th><td><b>{{ w[7] }}</b></td></tr>
            <tr><th>FULL NAME</th><td>{{ w[1] }} {{ w[2] }}</td><th>DOB</th><td>{{ w[3] }}</td></tr>
            <tr style="background:#f8f9fa;"><th>GENDER</th><td>{{ w[4] }}</td><th>NATIONALITY</th><td>{{ w[5] }}</td></tr>
            <tr><th>PHONE</th><td>{{ w[10] }}</td><th>EMAIL</th><td>{{ w[11] }}</td></tr>
            <tr style="background:#f8f9fa;"><th>GHANA CARD NO</th><td>{{ w[12] }}</td><th>REGION / STATION</th><td>{{ w[17] }} / {{ w[18] }}</td></tr>
            <tr><th>GUILD / DEPT</th><td>{{ w[9] }}</td><th>RANK</th><td><b style="color:red;">{{ w[8] }}</b></td></tr>
        </table>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <a href="{{ url_for('approve_cmd', uid=w[6]) }}" class="btn-cmd bg-wa" style="flex:1; padding:15px; font-size:14px;">✅ APPROVE </a>
            <a href="{{ url_for('decline_cmd', uid=w[6]) }}" class="btn-cmd bg-orange" style="flex:1; padding:15px; font-size:14px;">❌ DECLINE & SMS</a>
            <a href="/admin-dashboard" class="btn-cmd bg-sus" style="padding:15px; font-size:14px;">BACK TO HQ</a>
        </div>
    </div>
    """
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", DOSSIER_HTML), w=w, photo_url=photo_url)

@app.route("/admin/promote/<uid>", methods=['GET', 'POST'])
def promote_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor()
    if request.method == 'POST':
        new_rank = request.form.get('new_rank')
        cur.execute("UPDATE pbe_registry_2026 SET rank = %s WHERE pbe_uid = %s", (new_rank, uid))
        conn.commit(); cur.close(); conn.close()
        log_soul_action("PROMOTE", f"Elevated {uid} to {new_rank}")
        return redirect(url_for('admin_dashboard'))
        
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    PROMOTE_HTML = """
    <div class="section-card" style="max-width:500px; margin:auto; text-align:center;">
        <h3 style="color:red;">🎖️ SUPREME COMMAND PROMOTION</h3>
        <div style="margin:20px 0; padding:15px; background:#f8f9fa; border-radius:8px;">
            <p style="margin:5px 0;"><b>Personnel:</b> {{ w[1] }} {{ w[2] }}</p>
            <p style="margin:5px 0;"><b>Current Rank:</b> <span style="color:red; font-weight:bold;">{{ w[8] }}</span></p>
        </div>
        <form method="POST">
            <select name="new_rank" style="width:100%; padding:15px; margin-bottom:15px; border-radius:8px; border:1px solid #dee2e6;" required>
                {% for r in ranks %}
                <option value="{{ r }}" {% if r == w[8] %}selected{% endif %}>{{ r }}</option>
                {% endfor %}
            </select>
            <button class="btn-cmd bg-navy" style="width:100%; padding:15px; font-size:14px;">CONFIRM RANK ELEVATION</button>
        </form>
        <a href="/admin-dashboard" class="btn-cmd bg-sus" style="display:block; padding:10px; margin-top:10px;">CANCEL</a>
    </div>
    """
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", PROMOTE_HTML), w=w, ranks=PBE_RANKS)

@app.route("/admin/approve/<uid>")
def approve_cmd(uid):
    if not session.get('role'): abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("APPROVE", f"Activated PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/decline/<uid>")
def decline_cmd(uid):
    if not session.get('role'): abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT phone_no FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    res = cur.fetchone()
    if res:
        phone = res[0]
        msg = "PBE ALERT: Your registration was declined due to errors. Please contact HQ to reset your profile and re-register."
        try:
            requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_ALERT", "message": msg, "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY}, timeout=5)
        except Exception as e:
            print(f"SMS Error: {e}")
    
    cur.execute("UPDATE pbe_registry_2026 SET status = 'DECLINED' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("DECLINE", f"Declined Registration: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/suspend/<uid>")
def suspend_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'SUSPENDED' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("SUSPEND", f"Suspended PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/unsuspend/<uid>")
def unsuspend_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("UNSUSPEND", f"Restored PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/renew/<uid>")
def renew_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET expiry_date = expiry_date + INTERVAL '2 years' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("RENEW", f"Extended license for {uid}")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete/<uid>")
def delete_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); log_soul_action("DELETE", f"Purged PBE-ID: {uid}")
    return redirect(url_for('admin_dashboard'))

# --- 7. ROBOT MAPPING LOGIC (FLAWLESS CALIBRATION) ---
@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    
    log_soul_action("PRINT", f"Printed ID for {pbe_uid}")
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    
    # EXACT FILENAME FIX FOR GITHUB DEPLOYMENT
    tpl_path = os.path.join(app.root_path, 'static', 'POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png') 
    if os.path.exists(tpl_path): 
        c.drawImage(tpl_path, 0, 0, width=3.375*inch, height=2.125*inch)
    else:
        print(f"CRITICAL WARNING: Template not found at {tpl_path}. Check GitHub!")
    
    # EXACT BACKGROUND REMOVAL LOGIC RESTORED 
    photo_url = w[13]
    if photo_url: 
        if "cloudinary" in photo_url and "/upload/" in photo_url:
            parts = photo_url.split('/upload/')
            photo_url = f"{parts[0]}/upload/e_background_removal/f_png/{parts[1]}"

        try: 
            profile_img = ImageReader(photo_url) 
            c.saveState()
            c.setFillAlpha(0.2)
            c.drawImage(profile_img, 0.15*inch, 0.2*inch, width=0.6*inch, height=0.75*inch)
            c.restoreState()
            c.drawImage(profile_img, 2.45*inch, 0.45*inch, width=0.75*inch, height=1.0*inch)
        except Exception as e: 
            print(f"Image Mapping Error: {e}")

    try:
        font_path = os.path.join(app.root_path, 'static', 'MyriadPro-Bold.ttf')
        pdfmetrics.registerFont(TTFont('MyriadPro', font_path))
        font_name = 'MyriadPro'
    except:
        font_name = 'Helvetica-Bold' 

    c.setFont(font_name, 6)
    c.setFillColor(colors.black)

    val_x = 0.85 * inch
    c.drawString(val_x, 1.70*inch, f"{w[2]}")  
    c.drawString(val_x, 1.55*inch, f"{w[1]}")  
    c.drawString(val_x, 1.40*inch, f"{w[4]}")  
    c.drawString(val_x, 1.25*inch, f"{w[5]}")  
    c.drawString(val_x, 1.10*inch, f"{w[6]}")  
    c.drawString(val_x, 0.95*inch, f"{w[7]}")  
    c.drawString(val_x, 0.80*inch, f"{w[8]}")  
    c.drawString(val_x, 0.65*inch, f"{w[19]}") 
    c.drawCentredString(1.68*inch, 0.45*inch, f"{w[20]}") 
    
    safe_uid = quote(w[6])
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{safe_uid}")
    bounds = qr_code.getBounds()
    d = Drawing(35, 35, transform=[35./(bounds[2]-bounds[0]),0,0,35./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code)
    d.drawOn(c, 1.45*inch, 0.08*inch)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    
    return send_file(buffer, mimetype='application/pdf', as_attachment=False, download_name=f"{w[6]}_ID.pdf")

# --- 8. PUBLIC VERIFICATION PORTAL ---
@app.route("/verify/<pbe_uid>")
def verify_id(pbe_uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    
    if not w:
        return render_template_string(VERIFY_HTML, w=None)
    
    live_status = w[15] 
    today = datetime.date.today()
    
    if w[20] and w[20] < today and live_status == 'ACTIVE':
        live_status = 'EXPIRED'
        
    return render_template_string(VERIFY_HTML, w=w, live_status=live_status)

# --- 9. ISOLATED ENROLLMENT ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT id FROM pbe_registry_2026 WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            fname = request.form.get('firstname', '').upper().replace(" ", "_")
            sname = request.form.get('surname', '').upper().replace(" ", "_")
            
            photo = cloudinary.uploader.upload(
                request.files['photo'], 
                public_id=f"PBE_PP_{fname}_{sname}"
            )
            
            ghana_card = cloudinary.uploader.upload(request.files['ghana_card_img'], public_id=f"PBE_GHANACARD_{fname}_{sname}")
            
            uid = generate_pbe_id()
            lic = generate_pbe_lic()
            
            assigned_rank = "Engineering Recruit"
            
            cur.execute("""UPDATE pbe_registry_2026 SET surname=%s, firstname=%s, dob=%s, gender=%s, nationality=%s, pbe_uid=%s, pbe_license=%s,
                        issuance_date=%s, expiry_date=%s, rank=%s, department=%s, photo_url=%s, ghana_card_url=%s, 
                        email=%s, ghana_card_no=%s, status='PENDING', region=%s, station=%s WHERE otp_code=%s""",
                        (request.form.get('surname').upper(), fname, request.form.get('dob'), request.form.get('gender'), request.form.get('nationality').upper(), uid, lic,
                        datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730),
                        assigned_rank, request.form.get('department'), photo['secure_url'], ghana_card['secure_url'],
                        request.form.get('email'), request.form.get('ghana_card_no'), request.form.get('region'), request.form.get('station'), otp))
            conn.commit(); cur.close(); conn.close()
            return "<div style='text-align:center; padding:100px; font-family:sans-serif;'><h1 style='color:#28a745;'>Submit successful ✅</h1><p style='font-size:20px; font-weight:bold; color:#495057;'>The office will respond within 3 working days.</p></div>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:500px; margin: auto;">
            <h3>ENROLLMENT FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="OTP from SMS" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="surname" placeholder="Surname" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="firstname" placeholder="First Name" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="dob" placeholder="Date of Birth (e.g. 01/Jan/1990)" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <select name="gender" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                    <option value="">Select Gender</option>
                    <option value="MALE">MALE</option>
                    <option value="FEMALE">FEMALE</option>
                </select>
                <input name="nationality" placeholder="Nationality" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="email" type="email" placeholder="Email Address" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <input name="ghana_card_no" placeholder="Ghana Card ID Number" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;" required>
                <select name="region" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;">
                    {% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}
                </select>
                <select name="department" style="width:100%; padding:12px; margin:5px 0; box-sizing:border-box;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <p style="font-size:12px; margin-bottom:2px; font-weight:bold;">Passport Photo:</p>
                <input type="file" name="photo" style="margin-bottom:10px;" required>
                <p style="font-size:12px; margin-bottom:2px; font-weight:bold;">Ghana Card Image:</p>
                <input type="file" name="ghana_card_img" style="margin-bottom:10px;" required>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px; margin-top:10px;">SUBMIT REGISTRY</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GHANA_REGIONS)

# --- 10. SECURITY, INVITE & AUDIT ---
@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    ip = request.remote_addr
    if is_blacklisted(ip): return "<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>403: SYSTEM ACCESS REVOKED</h1><p>IP locked due to unauthorized attempts.</p></div>"

    if request.method == 'POST':
        pwd = request.form.get('password')
        op_name = request.form.get('op_name', 'UNKNOWN').upper()
        
        if pwd == ADMIN_PASSWORD: 
            session['role'] = 'ADMIN'
            session['op_name'] = op_name
            log_soul_action("LOGIN", "Supreme Admin Access Granted")
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD: 
            session['role'] = 'SUPERVISOR'
            session['op_name'] = op_name
            log_soul_action("LOGIN", "Supervisor Access Granted")
            return redirect(url_for('admin_dashboard'))
        else:
            blacklist_ip(ip)
            session['op_name'] = op_name
            log_soul_action("SECURITY ALERT", f"Intruder Blocked from IP: {ip}")
            session.clear()
            return redirect(url_for('admin_login'))

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:400px; margin:auto; text-align:center;">
            <h3>HQ SYSTEM LOCK</h3>
            <form method="POST">
                <input type="text" name="op_name" placeholder="Operator Name (e.g. General Imperial)" style="width:100%; padding:12px; margin-bottom:10px; box-sizing:border-box;" required>
                <input type="password" name="password" placeholder="Master Access Key" style="width:100%; padding:12px; margin-bottom:15px; box-sizing:border-box;" required>
                <button class="btn-cmd bg-navy" style="width:100%; padding:15px;">UNLOCK COMMAND CENTER</button>
            </form>
        </div>
    """))

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('role'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        otp = str(random.randint(111111, 999999))
        phone = request.form.get('phone')
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM pbe_registry_2026 WHERE phone_no = %s AND status = 'PENDING'", (phone,))
        cur.execute("INSERT INTO pbe_registry_2026 (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        try:
            requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": "PBE_OTP", "message": f"PBE: Use OTP {otp} to register: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY}, timeout=5)
        except Exception as e:
            print(f"SMS Error: {e}")
        log_soul_action("INVITE", f"OTP {otp} sent to {phone}")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card" style="max-width:400px; margin:auto;">
            <h3>+ SEND INVITE</h3>
            <form method="POST">
                <input name="phone" placeholder="+233..." style="width:100%; padding:12px; margin-bottom:15px; box-sizing:border-box;" required>
                <button class="btn-cmd bg-blue" style="width:100%; padding:15px;">SEND OTP LINK</button>
            </form>
        </div>
    """))

@app.route("/admin/audit")
def view_audit():
    if session.get('role') != 'ADMIN': abort(403) # THE IRON DOOR
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT timestamp, action, actor, details, ip_address FROM pbe_audit_2026 ORDER BY id DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card">
            <div class="section-title">📜 SOUL AUDIT LOGS (CLASSIFIED)</div>
            <div style="font-family:monospace; font-size:12px; max-height:500px; overflow-y:auto; background:#1e1e1e; color:#00ff00; padding:15px; border-radius:8px;">
                {% for l in logs %}
                <div style="margin-bottom:8px; border-bottom:1px solid #333; padding-bottom:5px;">
                    <span style="color:#888;">[{{ l[0].strftime('%Y-%m-%d %H:%M') }}]</span> 
                    <span style="color:#ffc107;">[{{ l[2] }}]</span> 
                    <b>{{ l[1] }}</b>: {{ l[3] }} <br>
                    <span style="color:#00ccff; font-size: 10px;">Geo-IP Tracker: {{ l[4] }}</span>
                </div>
                {% endfor %}
            </div>
            <a href="/admin-dashboard" class="btn-cmd bg-navy" style="margin-top:20px; padding:10px;">BACK TO DASHBOARD</a>
        </div>
    """), logs=logs)

@app.route("/admin/alerts")
def view_alerts():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days' AND surname IS NOT NULL")
    alerts = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card">
            <div class="section-title">🔔 RENEWAL ALERTS</div>
            {% for a in alerts %}
            <div style="padding:10px; border-bottom:1px solid #eee; font-size:13px;">
                <b>{{ a[1] }} {{ a[2] }}</b> (ID: {{ a[6] }}) - <span style="color:red;">Expires: {{ a[20] }}</span>
            </div>
            {% endfor %}
            {% if not alerts %}<p>No upcoming renewals.</p>{% endif %}
            <a href="/admin-dashboard" class="btn-cmd bg-navy" style="margin-top:20px; padding:10px;">BACK</a>
        </div>
    """), alerts=alerts)

@app.route("/")
def index(): return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
