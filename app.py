from flask import Flask, render_template, request, redirect, url_for, session
from db import get_connection 
from routes.cart import cart_bp
from routes.auth import auth_bp
from routes.catalog import catalog_bp
from routes.main import main_bp

app = Flask(__name__)
app.secret_key = "vm-secret-key"

app.register_blueprint(cart_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(catalog_bp)
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=1, port=2911)