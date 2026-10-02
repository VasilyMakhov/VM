from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


products = [
    {
        "name": "Беспроводные наушники",
        "description": "Удобные беспроводные наушники для музыки и звонков.",
        "price": 2999
    },
    {
        "name": "Механическая клавиатура",
        "description": "Клавиатура с механическими переключателями.",
        "price": 4999
    },
    {
        "name": "Игровая мышь",
        "description": "Компьютерная мышь для игр и повседневной работы.",
        "price": 1999
    }
]


@app.route("/catalog")
def catalog():
    return render_template("catalog.html", products=products)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=1, port=2911)