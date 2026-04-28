from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date

app = Flask("SquadUp")
app.secret_key = "squadup_secret_key"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        password = request.form['password']
        skill_level = request.form['skill_level']
        avatar = request.form['avatar']

        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing_user:
            conn.close()
            return "Username already exists"

        conn.execute(
            "INSERT INTO users (full_name, username, password, skill_level, avatar) VALUES (?, ?, ?, ?, ?)",
            (full_name, username, password, skill_level, avatar)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password"

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
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
        'dashboard.html',
        user=user,
        due_bookings=due_bookings,
        past_bookings=past_bookings,
        joined_events=joined_events
    )


@app.route('/booking')
def booking():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    events = conn.execute(
        "SELECT * FROM events ORDER BY date ASC, start_time ASC"
    ).fetchall()

    conn.close()

    return render_template('booking.html', events=events)


@app.route('/book', methods=['POST'])
def book():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    facility = request.form['facility']
    date_selected = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    conn = get_db_connection()

    conn.execute(
        "INSERT INTO bookings (username, facility, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
        (username, facility, date_selected, start_time, end_time)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/create_event', methods=['POST'])
def create_event():
    if 'username' not in session:
        return redirect(url_for('login'))

    event_name = request.form['event_name']
    facility_id = request.form['facility_id']
    date_selected = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    level = request.form['level']

    facilities = {
        "1": "Badminton Court",
        "2": "Basketball Court",
        "3": "Swimming Pool",
        "4": "Football Field"
    }

    facility = facilities[facility_id]

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO events 
        (name, facility, date, start_time, end_time, level, created_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_name, facility, date_selected, start_time, end_time, level, session['username'])
    )

    conn.commit()
    conn.close()

    return redirect(url_for('booking'))


@app.route('/join_event', methods=['POST'])
def join_event():
    if 'username' not in session:
        return redirect(url_for('login'))

    event_id = request.form['event_id']

    conn = get_db_connection()

    event = conn.execute(
        "SELECT * FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if not event:
        conn.close()
        return "Event does not exist"

    existing_join = conn.execute(
        "SELECT * FROM joined_events WHERE username = ? AND event_id = ?",
        (session['username'], event_id)
    ).fetchone()

    if existing_join:
        conn.close()
        return "You already joined this event"

    conn.execute(
        "INSERT INTO joined_events (username, event_id) VALUES (?, ?)",
        (session['username'], event_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/delete_booking/<int:booking_id>')
def delete_booking(booking_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM bookings WHERE id = ? AND username = ?",
        (booking_id, session['username'])
    )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)