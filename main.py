import os
import random
import requests
import urllib.parse
import re
import psycopg2
import cloudinary
import cloudinary.uploader
from datetime import datetime, date
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.units import inch

# --- 1. SECURE CONFIG ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = os.environ.get("ARKESEL_SENDER_ID", "PBE_OTP")

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY,
            surname VARCHAR(100), firstname VARCHAR(100),
            gender VARCHAR(10), nationality VARCHAR(50),
            pbe_uid VARCHAR(20) UNIQUE, pbe_license VARCHAR(50) UNIQUE,
            rank VARCHAR(50), phone_no VARCHAR(20) UNIQUE,
            photo_url TEXT, otp_code VARCHAR(6), 
            status VARCHAR(20) DEFAULT 'ACTIVE', is_verified BOOLEAN DEFAULT FALSE,
            joined_date DATE DEFAULT CURRENT_DATE
        );
    """)
    conn.commit(); cursor.close(); conn.close()
    yield

app = FastAPI(title="PBE Master IIV System", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 2. CORE UTILITIES ---
def send_arkesel_sms(phone: str, message: str):
    url = "https://sms.arkesel.com/api/v2/sms/send"
    headers = {"api-key": ARKESEL_API_KEY, "Content-Type": "application/json"}
    payload = {"sender": ARKESEL_SENDER_ID, "message": message, "recipients": [phone]}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except: return {"status": "error"}

# --- 3. ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><body style="font-family:sans-serif; text-align:center; padding-top:50px;">
        <img src="/static/logo.png" width="150">
        <h1>POWER BRIDGE ENGINEERING</h1>
        <p>Identity Vault is Online & Secure.</p>
    </body></html>
    """

@app.get("/admin/print-id/{pbe_uid}")
async def print_card(pbe_uid: str):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    emp = cursor.fetchone()
    
    pdf_file = f"PBE_{pbe_uid}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=(3.375*inch, 2.125*inch))
    
    # MATCHING YOUR EXACT FILE NAME
    template = "static/POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    
    if os.path.exists(template):
        c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)

    c.setFont("Helvetica-Bold", 6.5); c.setFillColor(colors.black)
    x_data = 1.35 * inch
    c.drawString(x_data, 1.83*inch, str(emp[1])) # Surname
    c.drawString(x_data, 1.63*inch, str(emp[2])) # Firstname
    c.drawString(x_data, 1.43*inch, str(emp[3])) # Gender
    c.drawString(x_data, 1.23*inch, str(emp[4])) # Nationality
    c.drawString(x_data, 1.03*inch, str(emp[5])) # UID
    c.drawString(x_data, 0.83*inch, str(emp[6])) # License
    c.drawString(x_data, 0.63*inch, str(emp[7])) # Rank

    # Barcode
    barcode = code128.Code128(emp[5], barHeight=0.2*inch, barWidth=0.8)
    barcode.drawOn(c, 1.1*inch, 0.18*inch)
    
    # Worker Photo
    resp = requests.get(emp[9])
    with open("temp.jpg", "wb") as f: f.write(resp.content)
    c.drawImage("temp.jpg", 0.15*inch, 0.65*inch, width=0.85*inch, height=1.05*inch)
    
    c.save(); cursor.close(); conn.close()
    return FileResponse(pdf_file, media_type='application/pdf')