import warnings
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from pathlib import Path
from io import BytesIO
import cv2
import re
import easyocr

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import get_vehicle_details, get_connection

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

# ================= PATHS =================
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg"}

# ================= OCR =================
reader = easyocr.Reader(['en'], gpu=False)

# ================= IMAGE PREPROCESS =================
def preprocess_image(path):
    img = cv2.imread(str(path))
    if img is None:
        return None
    img = cv2.resize(img, None, fx=1.5, fy=1.5)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

# ================= OCR =================
def easy_ocr_extract(path):
    try:
        res = reader.readtext(str(path))
        return " ".join([r[1] for r in res])
    except:
        return ""

# ================= PLATE EXTRACTION =================
def extract_plate(text):
    if not text:
        return None

    text = text.upper()

    junk_words = ["IND", "INDIA", "FR", "FRNA", "IN"]
    for j in junk_words:
        text = text.replace(j, "")

    cleaned = re.sub(r"[^A-Z0-9]", " ", text)
    tokens = cleaned.split()
    combined = "".join(tokens)

    combined = (
        combined.replace("O", "0")
        .replace("I", "1")
        .replace("Z", "2")
        .replace("S", "5")
    )

    if 8 <= len(combined) <= 10:
        return combined

    return None

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (data["username"],))
    user = cur.fetchone()
    cur.close()
    con.close()

    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user"] = user["username"]
    return jsonify({"success": True, "username": user["username"]})

# ---------- SCAN ----------
@app.route("/scan", methods=["POST"])
def scan():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    filename = secure_filename(file.filename)

    if "." not in filename or filename.rsplit(".", 1)[1].lower() not in ALLOWED_EXT:
        return jsonify({"error": "Invalid file type"}), 400

    path = UPLOAD_FOLDER / filename
    file.save(path)

    processed = preprocess_image(path)
    if processed is not None:
        cv2.imwrite(str(path), processed)

    text = easy_ocr_extract(path)
    plate = extract_plate(text)

    if not plate:
        return jsonify({
            "plate_number": None,
            "ocr_text": text,
            "message": "No valid number plate detected"
        })

    # ✅ SINGLE SOURCE OF TRUTH (history + cache handled inside)
    details = get_vehicle_details(plate, session["user"])

    return jsonify({
        "plate_number": plate,
        "vehicle_details": details,
        "ocr_text": text
    })

# ---------- PROFILE ----------
@app.route("/profile")
def profile():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scan_history
        WHERE username=%s
    """, (session["user"],))
    total = cur.fetchone()["total"]

    cur.execute("""
        SELECT scanned_at
        FROM scan_history
        WHERE username=%s
        ORDER BY scanned_at DESC
        LIMIT 1
    """, (session["user"],))
    last = cur.fetchone()

    cur.close()
    con.close()

    return jsonify({
        "username": session["user"],
        "total_scans": total,
        "last_scan": last["scanned_at"] if last else "N/A"
    })

# ---------- DOWNLOAD PDF ----------
@app.route("/download-report", methods=["POST"])
def download_report():
    data = request.get_json()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Vehicle Scan Report")
    y -= 40

    pdf.setFont("Helvetica", 12)
    for k, v in data["vehicle_details"].items():
        pdf.drawString(50, y, f"{k}: {v}")
        y -= 20

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vehicle_report.pdf",
        mimetype="application/pdf"
    )

# ================= RUN =================
if __name__ == "__main__":
    app.run(port=8000, debug=True)
