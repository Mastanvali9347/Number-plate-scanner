FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean

# Create working directory
WORKDIR /app

# Copy dependency list
COPY requirements.txt /app/

# Install Python dependencies (including Gunicorn)
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . /app/

# Expose port
EXPOSE 10000

# Run app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
