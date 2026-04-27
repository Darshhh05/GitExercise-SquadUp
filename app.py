
from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask("SquadUp")

#  DATABASE SETUP
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # EVENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        facility_id INTEGER,
        event_name TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        level TEXT
    )
    """)

    # PARTICIPANTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        user_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

# Run DB setup
init_db()


# 🔹 ROUTES

from flask import Flask, render_template, request, redirect, url_for

app = Flask("SquadUp")

# Temporary storage (no database)
users = {}


@app.route('/')
def home():
    return render_template('index.html')


# LOGIN (updated to handle POST)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password"

    return render_template('login.html')


# REGISTER (NEW)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            return "Username already exists"

        users[username] = password
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/booking')
def booking():
    return render_template('booking.html')



#  FIXED BOOKING

@app.route('/book', methods=['POST'])
def book():
    facility = request.form['facility']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    return f"Booked {facility} on {date} from {start_time} to {end_time}"







#  CREATE EVENT
@app.route('/create_event', methods=['POST'])
def create_event():
    event_name = request.form['event_name']
    facility_id = request.form['facility_id']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    level = request.form['level']

    user_id = 1  # temporary

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO events (user_id, facility_id, event_name, date, start_time, end_time, level)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, facility_id, event_name, date, start_time, end_time, level))

    conn.commit()
    conn.close()

    return redirect('/events')


#  VIEW EVENTS
@app.route('/events')
def events():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM events")
    data = cursor.fetchall()

    conn.close()

    return render_template("booking.html", events=data)


# JOIN EVENT
@app.route('/join_event/<int:event_id>')
def join_event(event_id):
    user_id = 2  # simulate another user

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO event_participants (event_id, user_id)
    VALUES (?, ?)
    """, (event_id, user_id))

    conn.commit()
    conn.close()

    return "Joined Event!"


# RUN APP
if __name__ == '__main__':
    app.run(debug=True)




if __name__ == '__main__':
    app.run(debug=True)

