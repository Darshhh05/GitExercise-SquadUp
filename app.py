from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import date, datetime, timedelta
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "squadup_secret_key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

EMAIL_ADDRESS = "squaduphere@gmail.com"
EMAIL_APP_PASSWORD = "ixudbfygyxgvlwgb"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def send_email(to_email, subject, body):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully to", to_email)

    except Exception as e:
        print("Email sending failed:", e)

def get_user_email(username):
    conn = get_db_connection()

    user = conn.execute(
        "SELECT email FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if user and user["email"]:
        return user["email"]

    return None        


def fix_database():
    conn = get_db_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        skill_level TEXT,
        avatar TEXT,
        email TEXT
        last_activity TEXT
                 
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
        status TEXT DEFAULT 'Pending',
        max_players INTEGER DEFAULT 8
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


def update_database():
    conn = get_db_connection()

    # Add email column to old users table if it does not exist yet
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # Add last_activity column to old users table if it does not exist yet
    try:
        conn.execute("ALTER TABLE users ADD COLUMN last_activity TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # Give existing users a current activity date first
    conn.execute(
        """
        UPDATE users
        SET last_activity = ?
        WHERE last_activity IS NULL OR last_activity = ''
        """,
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
    )

    # Add max_players column to old events table if it does not exist yet
    try:
        conn.execute("ALTER TABLE events ADD COLUMN max_players INTEGER DEFAULT 8")
    except sqlite3.OperationalError:
        pass



    # Add default facilities if your facilities table is empty
    default_facilities = [
        "Badminton Court",
        "Basketball Court",
        "Futsal Court",
        "Pickleball Court",
        "Ping Pong ",
        "Swimming Pool",
        "Tennis Court"
    ]

    for facility in default_facilities:
        conn.execute(
            "INSERT OR IGNORE INTO facilities (name) VALUES (?)",
            (facility,)
        )

    conn.commit()
    conn.close()


# =========================
# FACILITY AVAILABILITY HELPERS
# =========================

def time_to_minutes(time_value):
    hour, minute = map(int, time_value.split(":"))
    return hour * 60 + minute


def is_time_overlap(start1, end1, start2, end2):
    return time_to_minutes(start1) < time_to_minutes(end2) and time_to_minutes(end1) > time_to_minutes(start2)


def is_facility_available(facility, booking_date, start_time, end_time):
    conn = get_db_connection()

    bookings = conn.execute(
        """
        SELECT start_time, end_time
        FROM bookings
        WHERE facility = ?
        AND date = ?
        AND status IN ('Pending', 'Approved')
        """,
        (facility, booking_date)
    ).fetchall()

    events = conn.execute(
        """
        SELECT start_time, end_time
        FROM events
        WHERE facility = ?
        AND date = ?
        AND status IN ('Pending', 'Approved')
        """,
        (facility, booking_date)
    ).fetchall()

    conn.close()

    for booking in bookings:
        if is_time_overlap(start_time, end_time, booking["start_time"], booking["end_time"]):
            return False

    for event in events:
        if is_time_overlap(start_time, end_time, event["start_time"], event["end_time"]):
            return False

    return True


@app.route("/")
def home():
    conn = get_db_connection()

    booking_count = conn.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0]

    event_count = conn.execute(
        "SELECT COUNT(*) FROM events"
    ).fetchone()[0]

    player_count = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    facility_count = 7

    conn.close()

    return render_template(
        "index.html",
        booking_count=booking_count,
        event_count=event_count,
        player_count=player_count,
        facility_count=facility_count
    )


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form["username"]
        password = request.form["password"]
        skill_level = request.form.get("skill_level")
        avatar = request.form["avatar"]
        email = request.form.get("email", "").strip()

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()
            return "Username already exists!"

        last_activity = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            INSERT INTO users (full_name, username, password, skill_level, avatar, email, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (full_name, username, password, skill_level, avatar, email, last_activity))

        conn.commit()
        conn.close()

        # Send welcome email after successful registration
        if email:
            send_email(
                email,
                "Welcome to SquadUp!",
                f"""Hi {full_name},

Welcome to SquadUp!

Your account has been created successfully.

You can now book facilities, join sports events, create your own matches, and unlock achievement badges.

See you on the court!

Regards,
SquadUp Team"""
            )

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

        if user:
            session["username"] = user["username"]

            conn.execute(
                "UPDATE users SET last_activity = ? WHERE username = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("dashboard"))

        conn.close()
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
        "SELECT * FROM bookings WHERE username = ? AND date >= ? ORDER BY date ASC, start_time ASC",
        (username, today)
    ).fetchall()

    past_bookings = conn.execute(
        "SELECT * FROM bookings WHERE username = ? AND date < ? ORDER BY date DESC, start_time DESC",
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

    conn.close()

    badges = []

    # Active Player unlocks only after 20 bookings
    if booking_count >= 20:
        badges.append("Active Player")

    # Team Player unlocks only after 20 joined events
    if joined_count >= 20:
        badges.append("Team Player")

    # Team Organizer unlocks only after 10 created events
    if created_count >= 10:
        badges.append("Team Organizer")

    # Champion unlocks only after completing all achievements
    if booking_count >= 20 and joined_count >= 20 and created_count >= 10:
        badges.append("SquadUp Champion")

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

    username = session["username"]

    conn = get_db_connection()

    facilities = conn.execute("SELECT * FROM facilities").fetchall()
    events = conn.execute("SELECT * FROM events WHERE status = 'Approved'").fetchall()

    events_with_members = []

    for event in events:
        members = conn.execute(
            "SELECT username FROM joined_events WHERE event_id = ?",
            (event["id"],)
        ).fetchall()

        joined_count = len(members)
        max_players = event["max_players"] if event["max_players"] else 8

        already_joined = conn.execute(
            """
            SELECT * FROM joined_events
            WHERE event_id = ?
            AND username = ?
            """,
            (event["id"], username)
        ).fetchone()

        events_with_members.append({
            "id": event["id"],
            "name": event["name"],
            "organizer": event["organizer"],
            "created_by": event["created_by"],
            "facility": event["facility"],
            "date": event["date"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "level": event["level"],
            "max_players": max_players,
            "joined_count": joined_count,
            "is_full": joined_count >= max_players,
            "already_joined": True if already_joined else False,
            "members": [m["username"] for m in members]
        })

    conn.close()

    return render_template(
        "booking.html",
        facilities=facilities,
        events=events_with_members
    )


@app.route("/approved_events")
def approved_events():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    conn = get_db_connection()

    events = conn.execute(
        "SELECT * FROM events WHERE status='Approved'"
    ).fetchall()

    events_with_members = []

    for event in events:
        members = conn.execute(
            "SELECT username FROM joined_events WHERE event_id = ?",
            (event["id"],)
        ).fetchall()

        joined_count = len(members)
        max_players = event["max_players"] if event["max_players"] else 8

        already_joined = conn.execute(
            """
            SELECT * FROM joined_events
            WHERE event_id = ?
            AND username = ?
            """,
            (event["id"], username)
        ).fetchone()

        events_with_members.append({
            "id": event["id"],
            "name": event["name"],
            "organizer": event["organizer"],
            "created_by": event["created_by"],
            "facility": event["facility"],
            "date": event["date"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "level": event["level"],
            "max_players": max_players,
            "joined_count": joined_count,
            "is_full": joined_count >= max_players,
            "already_joined": True if already_joined else False,
            "members": [m["username"] for m in members]
        })

    conn.close()

    return render_template(
        "approved_events.html",
        events=events_with_members
    )


@app.route("/availability_slots")
def availability_slots():
    facility = request.args.get("facility")
    booking_date = request.args.get("date")

    if not facility or not booking_date:
        return jsonify([])

    slots = [
        ("08:00", "09:00"),
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
        ("12:00", "13:00"),
        ("13:00", "14:00"),
        ("14:00", "15:00"),
        ("15:00", "16:00"),
        ("16:00", "17:00"),
        ("17:00", "18:00"),
        ("18:00", "19:00"),
        ("19:00", "20:00"),
        ("20:00", "21:00"),
        ("21:00", "22:00")
    ]

    slot_data = []

    for start, end in slots:
        available = is_facility_available(facility, booking_date, start, end)

        slot_data.append({
            "start": start,
            "end": end,
            "available": available
        })

    return jsonify(slot_data)


@app.route("/book", methods=["POST"])
def book():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    facility = request.form["facility"]
    booking_date = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]

    if not is_facility_available(facility, booking_date, start_time, end_time):
        return """
        <script>
            alert("This facility is already booked for the selected time. Please choose another slot.");
            window.history.back();
        </script>
        """

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO bookings (username, facility, date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        facility,
        booking_date,
        start_time,
        end_time,
        "Pending"
    ))

    conn.commit()
    conn.close()

    user_email = get_user_email(username)

    if user_email:
        send_email(
            user_email,
            "SquadUp Booking Request Submitted",
            f"""Hi {username},

Your booking request has been submitted successfully.

Facility: {facility}
Date: {booking_date}
Time: {start_time} - {end_time}
Status: Pending Admin Approval

You will be notified once the admin approves or rejects your booking.

Regards,
SquadUp Team"""
        )

    return redirect(url_for("dashboard"))


@app.route("/delete_booking/<int:booking_id>")
def delete_booking(booking_id):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    conn = get_db_connection()

    booking = conn.execute(
        """
        SELECT * FROM bookings
        WHERE id = ?
        AND username = ?
        """,
        (booking_id, username)
    ).fetchone()

    if booking:
        conn.execute(
            "DELETE FROM bookings WHERE id = ? AND username = ?",
            (booking_id, username)
        )

    conn.commit()
    conn.close()

    if booking:
        user_email = get_user_email(username)

        if user_email:
            send_email(
                user_email,
                "SquadUp Booking Cancelled",
                f"""Hi {username},

Your booking has been cancelled successfully.

Cancelled Booking Details:

Facility: {booking["facility"]}
Date: {booking["date"]}
Time: {booking["start_time"]} - {booking["end_time"]}

You may create a new booking anytime through SquadUp.

Regards,
SquadUp Team"""
            )

    return redirect(url_for("dashboard"))

@app.route("/create_event", methods=["POST"])
def create_event():
    if "username" not in session:
        return redirect(url_for("login"))

    organizer = session["username"]
    event_name = request.form["event_name"]
    facility = request.form["facility"]
    event_date = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    level = request.form["level"]
    max_players = request.form.get("max_players", 8)

    if not is_facility_available(facility, event_date, start_time, end_time):
        return """
        <script>
            alert("This facility is already booked for the selected time. Please choose another slot.");
            window.history.back();
        </script>
        """

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO events
        (name, organizer, created_by, facility, date, start_time, end_time, level, status, max_players)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_name,
        organizer,
        organizer,
        facility,
        event_date,
        start_time,
        end_time,
        level,
        "Pending",
        max_players
    ))

    conn.commit()
    conn.close()

    user_email = get_user_email(organizer)

    if user_email:
        send_email(
            user_email,
            "SquadUp Event Created",
            f"""Hi {organizer},

Your event has been created successfully.

Event Name: {event_name}
Facility: {facility}
Date: {event_date}
Time: {start_time} - {end_time}
Level: {level}
Max Players: {max_players}
Status: Pending Admin Approval

Once approved, other players will be able to view and join your event.

Regards,
SquadUp Team"""
        )

    return redirect(url_for("booking"))


@app.route("/join_event", methods=["POST"])
def join_event():
    if "username" not in session:
        return redirect(url_for("login"))

    event_id = request.form["event_id"]
    username = session["username"]

    conn = get_db_connection()

    event = conn.execute(
        "SELECT * FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if not event:
        conn.close()
        return redirect(url_for("booking"))

    existing = conn.execute(
        "SELECT * FROM joined_events WHERE username = ? AND event_id = ?",
        (username, event_id)
    ).fetchone()

    if existing:
        conn.close()
        return redirect(url_for("booking"))

    joined_count = conn.execute(
        "SELECT COUNT(*) FROM joined_events WHERE event_id = ?",
        (event_id,)
    ).fetchone()[0]

    max_players = event["max_players"] if event["max_players"] else 8

    if joined_count >= max_players:
        conn.close()
        return """
        <script>
            alert("This event is already full.");
            window.history.back();
        </script>
        """

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

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    conn = get_db_connection()

    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        skill_level = request.form["skill_level"]
        avatar = request.form["avatar"]

        conn.execute(
            """
            UPDATE users
            SET full_name = ?, email = ?, skill_level = ?, avatar = ?
            WHERE username = ?
            """,
            (full_name, email, skill_level, avatar, username)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    return render_template("edit_profile.html", user=user)

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    return render_template("edit_profile.html", user=user)


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
    two_months_ago = datetime.now() - timedelta(days=60)

    inactive_users = conn.execute("""
    SELECT *
    FROM users
    WHERE last_activity IS NOT NULL
    AND last_activity != ''
    AND datetime(last_activity) <= datetime(?)
    """, (two_months_ago.strftime("%Y-%m-%d %H:%M:%S"),)).fetchall()



    total_users = len(users)
    total_bookings = len(bookings)
    total_events = len(events)
    total_facilities = len(facilities)

    overview_max = max(
        total_users,
        total_bookings,
        total_events,
        total_facilities,
        1
    )

    conn.close()

    return render_template(
        "admin_dashboard.html",
        facilities=facilities,
        announcements=announcements,
        users=users,
        bookings=bookings,
        events=events,
        inactive_users=inactive_users,
        total_users=total_users,
        total_bookings=total_bookings,
        total_events=total_events,
        total_facilities=total_facilities,
        overview_max=overview_max
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
    conn.execute("UPDATE bookings SET status = 'Approved' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/reject_booking/<int:booking_id>")
def reject_booking(booking_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("UPDATE bookings SET status = 'Rejected' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

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

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user:
        username = user["username"]

        conn.execute(
            "DELETE FROM bookings WHERE username = ?",
            (username,)
        )

        conn.execute(
            "DELETE FROM joined_events WHERE username = ?",
            (username,)
        )

        created_events = conn.execute(
            "SELECT id FROM events WHERE created_by = ? OR organizer = ?",
            (username, username)
        ).fetchall()

        for event in created_events:
            conn.execute(
                "DELETE FROM joined_events WHERE event_id = ?",
                (event["id"],)
            )

        conn.execute(
            "DELETE FROM events WHERE created_by = ? OR organizer = ?",
            (username, username)
        )

        try:
            conn.execute(
                "DELETE FROM notifications WHERE username = ?",
                (username,)
            )
        except:
            pass

        conn.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))
@app.route("/make_inactive/<username>")
def make_inactive(username):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    inactive_date = (datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()

    conn.execute(
        "UPDATE users SET last_activity = ? WHERE username = ?",
        (inactive_date, username)
    )

    conn.commit()
    conn.close()

    return f"{username} has been marked as inactive for demo."

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
    update_database()
    app.run(debug=True)
