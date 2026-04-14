from flask import Flask
app = Flask("SquadUp")

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/book', methods=[POST])
def book():
    facility = request.form['facility form']
    date = request.form['date']
    time = request.form['time']

    return f"Booked {facility} on {date} at {time}"


if __name__ == '__main__':
    app.run(debug=True)