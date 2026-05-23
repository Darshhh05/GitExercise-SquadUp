from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "squadup_secret_key"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "squadupheregmail@gmail.com"
app.config["MAIL_PASSWORD"] = "squadup123"
mail = Mail(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def fix_database():
    conn = get_db_connection()

    conn.execute("""
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    username TEXT UNIQUE,
    email TEXT,
    password TEXT,
    skill_level TEXT,
    avatar TEXT
)
""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        facility TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        organizer TEXT,
        created_by TEXT,
        facility TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        level TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS joined_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        event_id INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        skill_level = request.form.get("skill_level")
        avatar = request.form["avatar"]

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()
            return "Username already exists!"

        conn.execute("""
    INSERT INTO users (full_name, username, email, password, skill_level, avatar)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (full_name, username, email, password, skill_level, avatar)) 
        
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


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


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    today = date.today().isoformat()

    conn = get_db_connection()

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

    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY id DESC"
    ).fetchall()

    joined_events = conn.execute("""
        SELECT events.*
        FROM joined_events
        JOIN events ON joined_events.event_id = events.id
        WHERE joined_events.username = ?
    """, (username,)).fetchall()

    booking_count = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE username = ?",
        (username,)
    ).fetchone()[0]

    joined_count = conn.execute(
        "SELECT COUNT(*) FROM joined_events WHERE username = ?",
        (username,)
    ).fetchone()[0]

    created_count = conn.execute(
        "SELECT COUNT(*) FROM events WHERE created_by = ?",
        (username,)
    ).fetchone()[0]

    badges = []

    if booking_count >= 3:
        badges.append("Active Player")

    if joined_count >= 3:
        badges.append("Team Player")

    if created_count >= 2:
        badges.append("Team Organizer")

    if booking_count >= 5 and joined_count >= 5:
        badges.append("SquadUp Champion")

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        user=user,
        due_bookings=due_bookings,
        past_bookings=past_bookings,
        announcements=announcements,
        joined_events=joined_events,
        badges=badges,
        booking_count=booking_count,
        joined_count=joined_count,
        created_count=created_count
    )


@app.route("/booking")
def booking():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    facilities = conn.execute("SELECT * FROM facilities").fetchall()
    events = conn.execute("SELECT * FROM events WHERE status = 'Approved'").fetchall()

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
            "level": event["level"],
            "members": [m["username"] for m in members]
        })

    conn.close()

    return render_template(
        "booking.html",
        facilities=facilities,
        events=events_with_members
    )


@app.route("/book", methods=["POST"])
def book():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO bookings (username, facility, date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session["username"],
        request.form["facility"],
        request.form["date"],
        request.form["start_time"],
        request.form["end_time"],
        "Pending"
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/delete_booking/<int:booking_id>")
def delete_booking(booking_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM bookings WHERE id = ? AND username = ?",
        (booking_id, session["username"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/create_event", methods=["POST"])
def create_event():
    if "username" not in session:
        return redirect(url_for("login"))

    organizer = session["username"]

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO events
        (name, organizer, created_by, facility, date, start_time, end_time, level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request.form["event_name"],
        organizer,
        organizer,
        request.form["facility"],
        request.form["date"],
        request.form["start_time"],
        request.form["end_time"],
        request.form["level"],
        "Pending"
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("booking"))


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

@app.route("/unjoin_event", methods=["POST"])
def unjoin_event():

    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    event_id = request.form["event_id"]

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM joined_events WHERE username = ? AND event_id = ?",
        (username, event_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("booking"))


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = username
            return redirect(url_for("admin_dashboard"))

        return "Invalid admin username or password"

    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    facilities = conn.execute("SELECT * FROM facilities").fetchall()
    announcements = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    users = conn.execute("SELECT * FROM users").fetchall()
    bookings = conn.execute("SELECT * FROM bookings").fetchall()
    events = conn.execute("SELECT * FROM events").fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        facilities=facilities,
        announcements=announcements,
        users=users,
        bookings=bookings,
        events=events
    )


@app.route("/add_facility", methods=["POST"])
def add_facility():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    facility_name = request.form["facility_name"]

    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO facilities (name) VALUES (?)", (facility_name,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_facility/<int:facility_id>")
def delete_facility(facility_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM facilities WHERE id = ?", (facility_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/post_announcement", methods=["POST"])
def post_announcement():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    message = request.form["message"]

    conn = get_db_connection()
    conn.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_announcement/<int:announcement_id>")
def delete_announcement(announcement_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/approve_booking/<int:booking_id>")
def approve_booking(booking_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ?",
        (booking_id,)
    ).fetchone()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (booking["username"],)
    ).fetchone()

    conn.execute(
        "UPDATE bookings SET status = 'Approved' WHERE id = ?",
        (booking_id,)
    )

    conn.commit()
    conn.close()

    if user and user["email"]:
        msg = Message(
            "Booking Approved - SquadUp",
            sender=app.config["MAIL_USERNAME"],
            recipients=[user["email"]]
        )

        msg.body = f"""
Hello {user['username']},

Your booking for {booking['facility']} on {booking['date']}
from {booking['start_time']} to {booking['end_time']} has been approved.

Thank you for using SquadUp.
"""

        mail.send(msg)

    return redirect(url_for("admin_dashboard"))

@app.route("/reject_booking/<int:booking_id>")
def reject_booking(booking_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ?",
        (booking_id,)
    ).fetchone()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (booking["username"],)
    ).fetchone()

    conn.execute(
        "UPDATE bookings SET status = 'Rejected' WHERE id = ?",
        (booking_id,)
    )

    conn.commit()
    conn.close()

    if user and user["email"]:
        msg = Message(
            "Booking Rejected - SquadUp",
            sender=app.config["MAIL_USERNAME"],
            recipients=[user["email"]]
        )

        msg.body = f"""
Hello {user['username']},

Your booking for {booking['facility']} on {booking['date']}
from {booking['start_time']} to {booking['end_time']} has been rejected.

Thank you for using SquadUp.
"""

        mail.send(msg)

    return redirect(url_for("admin_dashboard")) 


@app.route("/approve_event/<int:event_id>")
def approve_event(event_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("UPDATE events SET status = 'Approved' WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/reject_event/<int:event_id>")
def reject_event(event_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("UPDATE events SET status = 'Rejected' WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    fix_database()
    app.run(debug=True)