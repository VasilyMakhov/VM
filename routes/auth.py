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

@auth_bp.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    connection = get_connection()
    cursor = connection.cursor()

    try:
        if request.method == "POST":
            login = request.form.get("login", "").strip()
            email = request.form.get("email", "").strip()
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            password = request.form.get("password", "").strip()

            if not login or not email or not first_name or not last_name:
                return render_template("edit_profile.html", error="Заполните все обязательные поля"), 400

            cursor.execute("""
                SELECT ID
                FROM USERS
                WHERE (LOGIN = ? OR EMAIL = ?) AND ID <> ?
            """, (login, email, user_id))

            if cursor.fetchone() is not None:
                cursor.execute("""
                    SELECT 
                    LOGIN, 
                    EMAIL, 
                    FIRST_NAME, 
                    LAST_NAME
                    FROM USERS
                    WHERE ID = ?
                """, (user_id,))
                user = cursor.fetchone()

                return render_template("edit_profile.html", user=user, error="Такой логин или почта уже заняты"), 400

            if password:
                cursor.execute("""
                    UPDATE USERS
                    SET LOGIN = ?, 
                    EMAIL = ?, 
                    FIRST_NAME = ?,
                    LAST_NAME = ?, 
                    PASSWORD = ?
                    WHERE ID = ?
                """, (login, email, first_name, last_name, password, user_id ))
            else:
                cursor.execute("""
                    UPDATE USERS
                    SET LOGIN = ?, 
                    EMAIL = ?, 
                    FIRST_NAME = ?,
                    LAST_NAME = ?
                    WHERE ID = ?
                """, (login, email, first_name, last_name, user_id))

            connection.commit()
            session["user_login"] = login

            return redirect(url_for("main.index"))

        cursor.execute("""
            SELECT 
            LOGIN, 
            EMAIL, 
            FIRST_NAME, 
            LAST_NAME, 
            ROLE_ID
            FROM USERS
            WHERE ID = ?
        """, (user_id,))

        user = cursor.fetchone()

        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))

        return render_template("edit_profile.html", user=user)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()