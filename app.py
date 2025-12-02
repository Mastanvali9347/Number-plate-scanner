import warnings
import os
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from database import get_vehicle_details
from pathlib import Path
import cv2
import numpy as np
import re
from PIL import Image
import easyocr

# --------------------------------------------
# Base directory
# --------------------------------------------
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg"}

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# USE EASY OCR (no Tesseract required)
# ------------------------------------------------------------
reader = easyocr.Reader(['en'], gpu=False)


# --------------------------------------------------------
# Preprocessing
# --------------------------------------------------------
def preprocess_for_ocr(path):
    img = cv2.imread(str(path))
    if img is None:
        return None

    img = cv2.resize(img, None, fx=1.4, fy=1.4)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray


# --------------------------------------------------------
# Regex patterns
# --------------------------------------------------------
PLATE_REGEXES = [
    re.compile(r"[A-Z]{2}\s?[0-9]{2}\s?[A-Z]{1,3}\s?[0-9]{3,4}", re.I),
    re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{3,4}", re.I),
    re.compile(r"[A-Z0-9]{6,10}", re.I),
]

def extract_plate(text):
    if not text:
        return None

    text = text.upper()
    for pattern in PLATE_REGEXES:
        m = pattern.search(text)
        if m:
            return re.sub(r"[^A-Z0-9]", "", m.group(0))

    return None


# --------------------------------------------------------
# EASY OCR TEXT EXTRACTION
# --------------------------------------------------------
def easy_ocr_extract(image_path):
    try:
        results = reader.readtext(str(image_path))
        text = " ".join([res[1] for res in results])
        return text
    except:
        return ""


# --------------------------------------------------------
# Routes
# --------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/scan", methods=["POST"])
def scan():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file name"}), 400

    if not allowed_file(file.filename):
       return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(str(save_path))

    # Preprocess only for clarity (EasyOCR works on raw too)
    processed = preprocess_for_ocr(save_path)

    # EASY OCR extraction
    text = easy_ocr_extract(save_path)

    # Extract number plate
    plate = extract_plate(text)

    if not plate:
        return jsonify({
            "plate_number": None,
            "ocr_text": text,
            "message": "No valid number plate detected"
        }), 200

    # Get vehicle details from database
    details = get_vehicle_details(plate)

    return jsonify({
        "plate_number": plate,
        "vehicle_details": details,
        "ocr_text": text
    }), 200


@app.route("/uploads/<name>")
def uploaded_file(name):
    path = UPLOAD_FOLDER / name
    if path.exists():
        return send_file(str(path))
    return "File not found", 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
