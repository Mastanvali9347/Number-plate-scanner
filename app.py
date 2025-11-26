import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")

import os
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from database import get_vehicle_details
from pathlib import Path
import cv2
import numpy as np
import easyocr
import re
from PIL import Image

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

# EasyOCR (English)
reader = easyocr.Reader(['en'], gpu=False, verbose=False)


# ====================
# Image Preprocessing
# ====================
def preprocess_for_ocr(image_path):
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError("Could not read image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    th = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morph = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
    return morph


# ====================
# Plate Extraction
# ====================
PLATE_REGEXES = [
    re.compile(r'\b([A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{1,4})\b', re.I),
    re.compile(r'\b([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4})\b', re.I),
    re.compile(r'\b([A-Z]{2}\d{2}\d{4})\b', re.I),
    re.compile(r'\b([A-Z0-9]{6,10})\b', re.I)
]

def normalize_plate(text):
    s = re.sub(r'[^A-Z0-9]', '', text.upper())
    return s


def extract_plate_from_texts(texts):
    joined = " ".join(texts).upper()
    print("OCR TEXTS:", texts)

    for rx in PLATE_REGEXES:
        m = rx.search(joined)
        if m:
            raw_plate = m.group(1)
            return normalize_plate(raw_plate)

    return None


def run_easyocr_on_image(preprocessed_img):
    pil = Image.fromarray(preprocessed_img).convert("RGB")
    results = reader.readtext(np.array(pil))
    return [t[1].strip() for t in results if t[1].strip()]


# ====================
# Routes
# ====================
@app.route("/")
def index():
    return render_template("index.html")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@app.route("/scan", methods=["POST"])
def scan():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_FOLDER / filename
    file.save(str(save_path))

    try:
        # OCR Process
        pre = preprocess_for_ocr(save_path)
        easy_texts = run_easyocr_on_image(pre)
        plate = extract_plate_from_texts(easy_texts)

        if not plate:
            return jsonify({
                "plate_number": None,
                "ocr_texts": easy_texts,
                "message": "No plate-like text found"
            }), 200

        # Fetch MySQL details
        details = get_vehicle_details(plate)

        return jsonify({
            "plate_number": plate,
            "vehicle_details": details,
            "ocr_texts": easy_texts
        }), 200

    except Exception as e:
        print("ERROR IN /scan:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/uploads/<name>")
def uploaded_file(name):
    filepath = UPLOAD_FOLDER / name
    if filepath.exists():
        return send_file(str(filepath))
    return ("File not found", 404)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)
