🚀 Number Plate Scanner – Flask + OCR (Tesseract)

A web application that scans bike number plates from images using Tesseract OCR, extracts the plate number, and fetches vehicle details from a MySQL database.
The app includes preprocessing (OpenCV), regex-based number detection, and a clean API response.

Fully optimized for Render.com Deployment using Docker + Python 3.13 + Tesseract OCR.

📌 Features

📸 Upload an image & extract number plate text

🔍 Tesseract OCR (lightweight & fast)

🧠 Custom preprocessing (OpenCV)

🔤 True Indian plate detection (regex-based)

🚘 Fetch details from MySQL database

🌐 Fully deployable on Render using Docker

🗂 Clean API JSON response

🧾 Ready-to-use render.yaml + Dockerfile

🛠 Tech Stack
Component	Technology
Backend	Flask (Python)
OCR	Tesseract OCR
Image Processing	OpenCV
Database	MySQL
Deployment	Render (Docker)
Regex	Custom Indian plate matcher
📁 Project Structure
NUMBER-PLATE-SCANNER/
│── app.py
│── database.py
│── requirements.txt
│── render.yaml
│── static/
│    ├── style.css
│    ├── script.js
│── templates/
│    └── index.html
│── uploads/              (auto-created)
│── docker/
│    └── Dockerfile

⚙️ Installation (Local Machine)
1️⃣ Clone the repo
git clone https://github.com/your-username/number-plate-scanner.git
cd number-plate-scanner

2️⃣ Create a virtual environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Install Tesseract OCR locally

Windows:
Download → https://github.com/UB-Mannheim/tesseract/wiki

Set path in code if needed.

Linux:

sudo apt install tesseract-ocr

5️⃣ Run the app
python app.py


The app runs on:

http://127.0.0.1:8000
