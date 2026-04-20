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


@app.route('/book', methods=['POST'])
def book():
    facility = request.form['facility']
    date = request.form['date']
    time = request.form['time']

    return f"Booked {facility} on {date} at {time}"


if __name__ == '__main__':
    app.run(debug=True)