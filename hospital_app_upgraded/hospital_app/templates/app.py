from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BOOKINGS_FILE = DATA_DIR / "bookings.json"
USERS_FILE = DATA_DIR / "users.json"


def read_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")



def seed_users_if_empty():
    users = read_json(USERS_FILE, [])
    if users:
        return

    demo_users = [
        {
            "role": "staff",
            "phone": "9999990001",
            "countryCode": "+91",
            "password": "staff123",   # demo only
            "approved": True
        },
        {
            "role": "patient",
            "phone": "9999991001",
            "approved": True
        },
        {
            "role": "patient",
            "phone": "9999991002",
            "approved": False
        }
    ]
    write_json(USERS_FILE, demo_users)


seed_users_if_empty()




def load_bookings():
    return read_json(BOOKINGS_FILE, [])


def save_bookings(bookings):
    write_json(BOOKINGS_FILE, bookings)


def generate_token(bookings):
    """
    Turn last token like 'OP-021' into 'OP-022'.
    If anything goes wrong, just count length.
    """
    if not bookings:
        return "OP-001"
    last = bookings[-1].get("token", "OP-000")
    try:
        num = int(last.split("-")[1]) + 1
    except Exception:
        num = len(bookings) + 1
    return "OP-" + str(num).zfill(3)




def load_users():
    return read_json(USERS_FILE, [])


def find_user_by_phone(phone, role=None, country_code=None):
    users = load_users()
    for u in users:
        if u.get("phone") != phone:
            continue
        if role and u.get("role") != role:
            continue
        if country_code and u.get("countryCode") != country_code:
            continue
        return u
    return None


# ---------- Page routes (multi-page app) ----------

@app.route("/")
def welcome_page():
    # First screen with "I am staff / I am patient" buttons
    return render_template("welcome.html")  # [web:205][web:241]


@app.route("/login/staff-page")
def staff_login_page():
    # Staff login with phone + password
    return render_template("login_staff.html")  # [web:236][web:243]


@app.route("/login/patient-page")
def patient_login_page():
    # Patient login with phone only
    return render_template("login_patient.html")  # [web:236][web:243]


@app.route("/dashboard")
def dashboard_page():
    # Main CityCare dashboard (your modified paste.txt)
    return render_template("dashboard.html")  # [web:205][web:247]


# ---------- Booking API ----------

@app.route("/api/book", methods=["POST"])
def api_book():
    """
    Handles booking form from dashboard booking widget.
    Expects: pname, page, dept, doc, date, slot (form-data).
    """
    form = request.form  # [web:205][web:149]

    name = (form.get("pname") or "").strip()
    age = (form.get("page") or "").strip()
    dept = (form.get("dept") or "").strip()
    doc = (form.get("doc") or "").strip()
    date = (form.get("date") or "").strip()
    slot = (form.get("slot") or "").strip()

    if not name or not age or not date:
        return jsonify({"ok": False, "message": "Please fill name, age and date."}), 400

    bookings = load_bookings()
    token = generate_token(bookings)

    bookings.append(
        {
            "token": token,
            "name": name,
            "age": age,
            "dept": dept,
            "doc": doc,
            "date": date,
            "slot": slot,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    save_bookings(bookings)

    return jsonify({"ok": True, "token": token})


@app.route("/api/bookings", methods=["GET"])
def api_bookings():
    """
    Returns all bookings as JSON for dashboard booking list.
    """
    return jsonify(load_bookings())


# ---------- Staff login API (phone + password) ----------

@app.route("/login/staff", methods=["POST"])
def api_login_staff():
    """
    JSON POST:
    {
      "countryCode": "+91",
      "phone": "9999990001",
      "password": "staff123"
    }
    """
    data = request.get_json(silent=True) or {}  # [web:248]
    phone = (data.get("phone") or "").strip()
    country_code = (data.get("countryCode") or "").strip()
    password = data.get("password") or ""

    if not phone or not password:
        return jsonify({"ok": False, "message": "Phone and password are required."}), 400

    user = find_user_by_phone(phone, role="staff", country_code=country_code)
    if not user:
        return jsonify({"ok": False, "message": "Staff user not found."}), 401

    if not user.get("approved", False):
        return jsonify({"ok": False, "message": "Staff account not approved."}), 403

    if user.get("password") != password:
        return jsonify({"ok": False, "message": "Invalid password."}), 401

    # For demo: no real session, just respond OK
    return jsonify(
        {
            "ok": True,
            "role": "staff",
            "phone": phone,
            "displayName": "CityCare staff",
            "sessionToken": "demo-staff-session-token",
            "redirect": url_for("dashboard_page"),
        }
    )


# ---------- Patient login API (phone only) ----------

@app.route("/login/patient", methods=["POST"])
def api_login_patient():
    """
    JSON POST:
    {
      "phone": "9999991001"
    }
    """
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()

    if not phone:
        return jsonify({"ok": False, "message": "Phone is required."}), 400

    user = find_user_by_phone(phone, role="patient")
    if not user:
        return jsonify(
            {
                "ok": False,
                "message": "Phone number not found. Please register at hospital.",
            }
        ), 401

    if not user.get("approved", False):
        return jsonify(
            {
                "ok": False,
                "message": "This phone number is not yet approved by staff.",
            }
        ), 403

    # In a real app you would send OTP; here we just say ok
    return jsonify(
        {
            "ok": True,
            "role": "patient",
            "phone": phone,
            "displayName": "CityCare patient",
            "sessionToken": "demo-patient-session-token",
            "redirect": url_for("dashboard_page"),
        }
    )


# ---------- Simple 404 handler (optional) ----------

@app.errorhandler(404)
def page_not_found(e):
    return (
        "<h1>404</h1><p>Page not found. Try /, /login/staff-page, /login/patient-page or /dashboard.</p>",
        404,
    )


if __name__ == "__main__":
    # Debug=True auto-reloads templates when you change HTML files. [web:205]
    app.run(debug=True)
