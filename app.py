from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "squadup_secret_key"


# ---------- DATABASE ----------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def fix_database():
    conn = sqlite3.connect("database.db")

    # USERS (WITH AVATAR)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        avatar TEXT
    )
    """)

    # BOOKINGS
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        facility TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT
    )
    """)

    # EVENTS
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        organizer TEXT,
        created_by TEXT NOT NULL,
        facility TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        level TEXT
    )
    """)

    # JOINED EVENTS
    conn.execute("""
    CREATE TABLE IF NOT EXISTS joined_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        event_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


# ---------- HOME ----------
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        avatar = request.form["avatar"]  # 👈 IMPORTANT

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()
            return "Username already exists!"

        conn.execute(
            "INSERT INTO users (username, password, avatar) VALUES (?, ?, ?)",
            (username, password, avatar)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        return "Invalid username or password"

    return render_template("login.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    today = date.today().isoformat()

    conn = get_db_connection()

    # GET USER (FOR AVATAR)
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    due_bookings = conn.execute(
        "SELECT * FROM bookings WHERE username = ? AND date >= ?",
        (username, today)
    ).fetchall()

    past_bookings = conn.execute(
        "SELECT * FROM bookings WHERE username = ? AND date < ?",
        (username, today)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        user=user,
        due_bookings=due_bookings,
        past_bookings=past_bookings
    )


# ---------- DELETE BOOKING ----------
@app.route("/delete_booking/<int:booking_id>")
def delete_booking(booking_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ---------- BOOKING PAGE ----------
@app.route("/booking")
def booking():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    events = conn.execute("SELECT * FROM events").fetchall()

    events_with_members = []

    for event in events:
        members = conn.execute(
            "SELECT username FROM joined_events WHERE event_id = ?",
            (event["id"],)
        ).fetchall()

        events_with_members.append({
            "id": event["id"],
            "name": event["name"],
            "organizer": event["organizer"],
            "facility": event["facility"],
            "date": event["date"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "members": [m["username"] for m in members]
        })

    conn.close()

    return render_template("booking.html", events=events_with_members)


# ---------- BOOK ----------
@app.route("/book", methods=["POST"])
def book():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    facility = request.form["facility"]
    date_selected = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO bookings (username, facility, date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, facility, date_selected, start_time, end_time, "Pending"))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ---------- CREATE EVENT ----------
@app.route("/create_event", methods=["POST"])
def create_event():
    if "username" not in session:
        return redirect(url_for("login"))

    organizer = session["username"]

    event_name = request.form["event_name"]
    facility = request.form["facility"]
    date_selected = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    level = request.form["level"]

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO events
        (name, organizer, created_by, facility, date, start_time, end_time, level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_name,
        organizer,
        organizer,  # 👈 FIX
        facility,
        date_selected,
        start_time,
        end_time,
        level
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("booking"))


# ---------- JOIN EVENT ----------
@app.route("/join_event", methods=["POST"])
def join_event():
    if "username" not in session:
        return redirect(url_for("login"))

    event_id = request.form["event_id"]
    username = session["username"]

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM joined_events WHERE username = ? AND event_id = ?",
        (username, event_id)
    ).fetchone()

    if not existing:
        conn.execute(
            "INSERT INTO joined_events (username, event_id) VALUES (?, ?)",
            (username, event_id)
        )
        conn.commit()

    conn.close()

    return redirect(url_for("booking"))


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- RUN ----------
if __name__ == "__main__":
    fix_database()
    app.run(debug=True)