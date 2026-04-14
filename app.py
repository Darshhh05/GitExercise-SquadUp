from flask import Flask
app = Flask("SquadUp")

@app.route('/')
def home():
    return "Welcome to SquadUp"

if __name__ == '__main__':
    app.run(debug=True)