from flask import Blueprint, render_template, session
from db import get_connection

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    user = None;

    if session.get("user_id"):
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
        SELECT
            u.LOGIN,
            u.EMAIL,
            u.FIRST_NAME,
            u.LAST_NAME,
            r.NAME
        FROM USERS u
        JOIN ROLES r
            ON r.ID = u.ROLE_ID
        WHERE u.ID = ?
        """, (session["user_id"],))

        user = cursor.fetchone()
        connection.close()

    return render_template("index.html", user=user)