from flask import Blueprint, render_template, request, redirect, url_for, session

from db import get_connection 

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
            login = request.form.get("login", "").strip()
            password = request.form.get("password", "").strip()

            if not login or not password:
                return render_template("login.html", error="Заполните все поля"), 400

            connection = get_connection()
            cursor = connection.cursor()
            
            try:
                cursor.execute(""" 
                    SELECT ID, LOGIN, PASSWORD, ROLE_ID
                    FROM USERS
                    WHERE LOGIN = ?
                """, (login,))

                user = cursor.fetchone()
                
                if (user is None) or (user[2] != password):
                    return render_template("login.html", error="Неверный логин или пароль"), 400

                session["user_id"] = user[0]
                session["user_login"] = user[1]
                session["user_role"] = user[3]
            finally:
                connection.close()

            return redirect(url_for("catalog.catalog"))
    
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login = request.form.get("login", "").strip() 
        email = request.form.get("email", "").strip() 
        password = request.form.get("password", "").strip() 
        first_name = request.form.get("first_name", "").strip() 
        last_name = request.form.get("last_name", "").strip()     

        if not login or not email or not password or not first_name or not last_name:
            return render_template("register.html", error="Заполните все поля"), 400

        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT ID
                FROM USERS
                WHERE LOGIN = ? OR EMAIL = ?
            """, (login, email))

            user = cursor.fetchone()

            if user is not None:
                return render_template("register.html", error="Пользователь с таким логином или почтой уже существует =("), 400
            
            cursor.execute("""
                INSERT INTO USERS 
                (LOGIN, EMAIL, PASSWORD, FIRST_NAME, LAST_NAME, ROLE_ID)
                VALUES 
                (?, ?, ?, ?, ?, ?)
            """, (login, email, password, first_name, last_name, 1))

            connection.commit()
        
        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

        return redirect(url_for("auth.login"))
     
    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
