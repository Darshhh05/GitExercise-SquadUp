from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "squadup_secret_key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]
        skill_level = request.form["skill_level"]
        avatar = request.form["avatar"]

        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing_user:
            conn.close()
            return "Username already exists"

        conn.execute(
            """
            INSERT INTO users (full_name, username, password, skill_level, avatar)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name, username, password, skill_level, avatar)
        )

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
        """
        SELECT * FROM bookings
        WHERE username = ? AND date >= ?
        ORDER BY date ASC, start_time ASC
        """,
        (username, today)
    ).fetchall()

    past_bookings = conn.execute(
        """
        SELECT * FROM bookings
        WHERE username = ? AND date < ?
        ORDER BY date DESC, start_time DESC
        """,
        (username, today)
    ).fetchall()

    joined_events = conn.execute(
        """
        SELECT events.*
        FROM joined_events
        JOIN events ON joined_events.event_id = events.id
        WHERE joined_events.username = ?
        ORDER BY events.date ASC, events.start_time ASC
        """,
        (username,)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        due_bookings=due_bookings,
        past_bookings=past_bookings,
        joined_events=joined_events
    )


@app.route("/booking")
def booking():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    facilities = conn.execute(
        "SELECT * FROM facilities ORDER BY name ASC"
    ).fetchall()

    events = conn.execute(
        "SELECT * FROM events ORDER BY date ASC, start_time ASC"
    ).fetchall()

    conn.close()

    return render_template(
        "booking.html",
        facilities=facilities,
        events=events
    )


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

    conn.execute(
        """
        INSERT INTO bookings (username, facility, date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, facility, date_selected, start_time, end_time, "Pending")
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/create_event", methods=["POST"])
def create_event():
    if "username" not in session:
        return redirect(url_for("login"))

    event_name = request.form["event_name"]
    facility = request.form["facility"]
    date_selected = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    level = request.form["level"]

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO events
        (name, facility, date, start_time, end_time, level, created_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_name,
            facility,
            date_selected,
            start_time,
            end_time,
            level,
            session["username"],
            "Pending"
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("booking"))



@app.route("/join_event", methods=["POST"])
def join_event():
    if "username" not in session:
        return redirect(url_for("login"))

    event_id = request.form["event_id"]

    conn = get_db_connection()

    event = conn.execute(
        "SELECT * FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if not event:
        conn.close()
        return "Event does not exist"

    existing_join = conn.execute(
        """
        SELECT * FROM joined_events
        WHERE username = ? AND event_id = ?
        """,
        (session["username"], event_id)
    ).fetchone()

    if existing_join:
        conn.close()
        return "You already joined this event"

    conn.execute(
        "INSERT INTO joined_events (username, event_id) VALUES (?, ?)",
        (session["username"], event_id)
    )

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


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))

        return "Invalid admin username or password"

    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    facilities = conn.execute(
        "SELECT * FROM facilities ORDER BY id DESC"
    ).fetchall()

    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY id DESC"
    ).fetchall()

    users = conn.execute(
        "SELECT * FROM users ORDER BY id DESC"
    ).fetchall()

    bookings = conn.execute(
        "SELECT * FROM bookings ORDER BY date DESC, start_time DESC"
    ).fetchall()

    events = conn.execute(
        "SELECT * FROM events ORDER BY date DESC, start_time DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        facilities=facilities,
        announcements=announcements,
        users=users,
        bookings=bookings,
        events=events
    )


@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))



@app.route("/add_facility", methods=["POST"])
def add_facility():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    facility_name = request.form["facility_name"]

    conn = get_db_connection()

    conn.execute(
        "INSERT INTO facilities (name) VALUES (?)",
        (facility_name,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_facility/<int:facility_id>")
def delete_facility(facility_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM facilities WHERE id = ?",
        (facility_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))



@app.route("/post_announcement", methods=["POST"])
def post_announcement():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    message = request.form["message"]

    conn = get_db_connection()

    conn.execute(
        "INSERT INTO announcements (message) VALUES (?)",
        (message,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/delete_announcement/<int:announcement_id>")
def delete_announcement(announcement_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM announcements WHERE id = ?",
        (announcement_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))



@app.route("/approve_booking/<int:booking_id>")
def approve_booking(booking_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "UPDATE bookings SET status = 'Approved' WHERE id = ?",
        (booking_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/reject_booking/<int:booking_id>")
def reject_booking(booking_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "UPDATE bookings SET status = 'Rejected' WHERE id = ?",
        (booking_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))



@app.route("/approve_event/<int:event_id>")
def approve_event(event_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "UPDATE events SET status = 'Approved' WHERE id = ?",
        (event_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/reject_event/<int:event_id>")
def reject_event(event_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    conn.execute(
        "UPDATE events SET status = 'Rejected' WHERE id = ?",
        (event_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)