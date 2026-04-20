from flask import Flask, render_template, request

app = Flask("SquadUp")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

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


    app.run(debug=True)

