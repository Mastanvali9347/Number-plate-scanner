import mysql.connector
from mysql.connector import Error
from difflib import get_close_matches
import re

def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="Mastan@12345",
            database="vehicles_db",
            port=3306
        )
    except Error as e:
        print("MySQL Error:", e)
        return None


def init_db():
    con = get_connection()
    if con is None:
        return

    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            reg_number VARCHAR(20) PRIMARY KEY,
            owner VARCHAR(100),
            model VARCHAR(100),
            fuel VARCHAR(20),
            reg_date VARCHAR(50),
            vehicle_class VARCHAR(50),
            color VARCHAR(50)
        )
    """)

    sample_data = [
        ("RJ14DT3249", "Amit Patel", "Maruti Swift Dzire", "Diesel", "10 Aug 2019", "Motor Car", "White"),
        ("KA41ER4547", "Rahul Mehta", "Royal Enfield Classic 350", "Petrol", "15 Feb 2021", "Two Wheeler", "Black"),
        ("DL82AF5032", "Sunita Sharma", "Hyundai Creta", "Petrol", "22 May 2020", "Motor Car", "Silver"),
        ("MH12AB1234", "Vikram Singh", "Honda City", "Petrol", "30 Mar 2018", "Motor Car", "Blue"),
        ("TN09CD5678", "Priya Reddy", "Bajaj Pulsar 150", "Petrol", "12 Dec 2019", "Two Wheeler", "Red")
    ]

    for record in sample_data:
        cur.execute("""
            INSERT IGNORE INTO vehicles
            (reg_number, owner, model, fuel, reg_date, vehicle_class, color)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, record)

    con.commit()
    cur.close()
    con.close()

# Fuzzy Match
def find_closest_plate(plate, all_plates):
    matches = get_close_matches(plate, all_plates, n=1, cutoff=0.6)
    return matches[0] if matches else None

# GET VEHICLE DETAILS (FINAL WORKING)
def get_vehicle_details(plate):
    """
    Works for:
    - Exact match
    - OCR mistakes
    - Missing characters
    - Extra spaces, dashes
    """

    # 1) Normalize plate
    normalized = re.sub(r"[^A-Z0-9]", "", plate.upper())
    print("NORMALIZED:", normalized)

    con = get_connection()
    if con is None:
        return None

    cur = con.cursor()

    # 2) Get all plates from DB
    cur.execute("SELECT reg_number FROM vehicles")
    rows = cur.fetchall()

    all_plates = [r[0].replace(" ", "").upper() for r in rows]

    # 3) Exact match
    if normalized in all_plates:
        matched = normalized
    else:
        # 4) Fuzzy match
        matched = find_closest_plate(normalized, all_plates)

    print("MATCHED PLATE:", matched)

    if not matched:
        print("No match found.")
        cur.close()
        con.close()
        return None

    # 5) Fetch record
    cur.execute("""
        SELECT reg_number, owner, model, fuel, reg_date, vehicle_class, color
        FROM vehicles
        WHERE UPPER(REPLACE(reg_number, ' ', '')) = %s
    """, (matched,))

    row = cur.fetchone()
    cur.close()
    con.close()

    if not row:
        return None

    return {
        "Registration Number": row[0],
        "Owner Name": row[1],
        "Vehicle Model": row[2],
        "Fuel Type": row[3],
        "Registration Date": row[4],
        "Vehicle Class": row[5],
        "Color": row[6]
    }


# Run database initializer
init_db()
