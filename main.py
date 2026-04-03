import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = os.environ.get("ARKESEL_SENDER_ID", "PBE_AUTH")

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY,
            surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT,
            insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT,
            photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING'
        );
    """)
    # Self-healing columns to ensure database is always up to date
    cols = ["dob", "insurance_date", "expiry_date", "ghana_card", "otp_code", "photo_url"]
    for col in cols:
        cur.execute(f"ALTER TABLE pbe_master_registry ADD COLUMN IF NOT EXISTS {col} TEXT;")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 2. ENCRYPTION ENGINE (The 15-Char Rule) ---
def generate_pbe_code(name):
    # Rule: Name + Random characters = Exactly 15 characters
    clean_name = re.sub(r'[^a-zA-Z]', '', name).upper()
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=15))
    return f"{clean_name}{random_part}"[:15]

# --- 3. UI TEMPLATE (Permanent Design) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; margin: 0; text-align: center; }
        .header { background: #1a3a5a; color: white; padding: 20px; border-bottom: 5px solid #0056b3; }
        .container { max-width: 1100px; margin: 20px auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f8f9fa; color: #1a3a5a; }
        .btn { padding: 8px 12px; border-radius: 4px; text-decoration: none; font-size: 13px; display: inline-block; border: none; color: white; cursor: pointer; font-weight: bold; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input, select { padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; width: 100%; max-width: 450px; box-sizing: border-box; font-size: 16px; }
        .label-text { font-weight: bold; color: #333; display: block; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header"><h1>POWER BRIDGE ENGINEERING</h1></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 4. ROUTES ---

@app.route("/")
def home():
    return redirect(url_for('admin_dashboard'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        surname = request.form.get('surname').upper()
        firstname = request.form.get('firstname').upper()
        
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        user = cur.fetchone()
        
        if user:
            # Generate the 15-character Smart IDs as requested
            pbe_id = generate_pbe_code(firstname) 
            pbe_license = generate_pbe_code(surname) 
            
            # Process Photo Upload
            photo = request.files['photo']
            upload_result = cloudinary.uploader.upload(photo)
            photo_url = upload_result['secure_url']

            cur.execute("""
                UPDATE pbe_master_registry SET 
                surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s,
                insurance_date=%s, expiry_date=%s
                WHERE otp_code=%s
            """, (surname, firstname, request.form.get('dob'), pbe_id, pbe_license, 
                  request.form.get('ghana_card'), photo_url, request.form.get('rank'),
                  request.form.get('insurance'), request.form.get('expiry'), otp))
            conn.commit(); cur.close(); conn.close()
            return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", "<h2>REGISTRATION COMPLETE ✅</h2><p>Your details have been secured. The CEO will issue your ID card shortly.</p>"))
        return "<h1>INVALID OTP ❌</h1>"

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Employee Identity Enrollment</h2>
        <p>Enter your OTP and details to generate your PBE Identity.</p>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="otp" placeholder="Enter 6-Digit SMS OTP" required>
            <input type="text" name="surname" placeholder="Surname (As on Ghana Card)" required>
            <input type="text" name="firstname" placeholder="First Name" required>
            <span class="label-text">Date of Birth</span>
            <input type="date" name="dob" required>
            <input type="text" name="ghana_card" placeholder="Ghana Card Number (GHA-XXXXXXXXX-X)" required>
            <input type="text" name="rank" placeholder="Current Rank / Role" required>
            <input type="text" name="insurance" placeholder="Insurance Date (DD/MM/YYYY)" required>
            <input type="text" name="expiry" placeholder="Expiry Date (DD/MM/YYYY)" required>
            <span class="label-text">Passport Photo</span>
            <input type="file" name="photo" accept="image/*" required>
            <br><button class="btn btn-blue" type="submit">Submit Enrollment</button>
        </form>
    """))

@app.route("/admin")
def admin_dashboard():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Worker Registry</h2>
        <a href="/admin/invite" class="btn btn-green" style="margin-bottom: 15px;">+ Invite New Employee</a>
        <table>
            <tr>
                <th>PBE-ID (15ch)</th>
                <th>Full Name</th>
                <th>License (15ch)</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] or 'PENDING' }}</b></td>
                <td>{{ w[1] or '---' }}, {{ w[2] or '---' }}</td>
                <td>{{ w[5] or '---' }}</td>
                <td><span style="color: {{ 'green' if w[13]=='ACTIVE' else 'orange' }}; font-weight:bold;">{{ w[13] }}</span></td>
                <td>
                    {% if w[4] %}
                    <a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print Card</a>
                    {% endif %}
                    <a href="/admin/delete/{{ w[0] }}" class="btn btn-red" onclick="return confirm('Suspend/Delete this worker?')">Del</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    """), workers=workers)

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        
        # ARKESEL SMS Logic
        sms_url = "https://sms.arkesel.com/api/v2/sms/send"
        payload = {
            "sender": ARKESEL_SENDER_ID, 
            "message": f"PBE: Your code is {otp}. Register your ID at: {request.url_root}register", 
            "recipients": [phone]
        }
        headers = {"api-key": ARKESEL_API_KEY}
        r = requests.post(sms_url, json=payload, headers=headers)
        
        return f"Invite Sent to {phone}. <br>Arkesel Status: {r.text} <br><a href='/admin'>Back to Dashboard</a>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h3>Invite Employee</h3>
        <form method='POST'>
            <input name='phone' placeholder='Phone Number (e.g. 233XXXXXXXXX)' required>
            <br><button class='btn btn-blue'>Send Enrollment SMS</button>
        </form>
    """))

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: return "Record Not Found", 404
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    template = "POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    if os.path.exists(template): c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)
    
    # Draw Passport Photo
    if w[10]: 
        try: c.drawImage(w[10], 0.2*inch, 0.65*inch, width=0.9*inch, height=1.1*inch)
        except: pass

    # Set Font for Data
    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black)
    x_col = 1.35*inch
    c.drawString(x_col, 1.6*inch, f"SURNAME: {w[1]}".upper())
    c.drawString(x_col, 1.45*inch, f"FIRSTNAME: {w[2]}".upper())
    c.drawString(x_col, 1.25*inch, f"ID NO: {w[4]}")
    c.drawString(x_col, 1.1*inch, f"LICENSE: {w[5]}")
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}")
    c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}")
    c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}")
    c.drawString(x_col, 0.5*inch, f"DOB: {w[3]}")

    # Draw QR Code
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); width, height = bounds[2]-bounds[0], bounds[3]-bounds[1]
    d = Drawing(45, 45, transform=[45./width,0,0,45./height,0,0]); d.add(qr_code)
    d.drawOn(c, 2.8*inch, 0.15*inch)
    
    c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT firstname, surname, rank, pbe_license, status FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if w: return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>✅ VERIFIED PBE EMPLOYEE</h1><p>Name: {w[0]} {w[1]}</p><p>Rank: {w[2]}</p><h3>STATUS: {w[4]}</h3></div>"
    return "<h1>❌ INVALID ID</h1>"

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
