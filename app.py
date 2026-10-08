from flask import Flask, render_template, request, redirect, url_for, session
from firebird.driver import connect

app = Flask(__name__)
app.secret_key = "vm-secret-key"

def get_connection():
    return connect(
    database="/db/wb_vasa.fdb",
    user="SYSDBA",
    password="masterkey"
    )

@app.route("/")
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

@app.route("/catalog")
def catalog():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT
        p.ID,
        p.NAME,
        p.IMAGE_URL,
        p.PRICE
    FROM PRODUCTS p
    JOIN SELLER_PRODUCTS sp
        ON sp.PRODUCT_ID = p.ID
    """)

    products = cursor.fetchall()
    connection.close()

    return render_template("catalog.html", products=products)

@app.route("/product/<int:product_id>")
def product(product_id):
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT
            p.ID,
            p.NAME,
            p.DESCRIPTION,
            p.IMAGE_URL,
            c.NAME AS CATEGORY,
            p.PRICE,
            wp.QUANTITY
        FROM PRODUCTS p
        JOIN CATEGORIES c
            ON c.ID = p.CATEGORY_ID
        JOIN SELLER_PRODUCTS sp
            ON sp.PRODUCT_ID = p.ID
        JOIN WAREHOUSE_PRODUCTS wp
            ON wp.SELLER_PRODUCT_ID = sp.ID
        WHERE p.ID = ?
    """, (product_id,))

    product = cursor.fetchone()
    connection.close()
    
    return render_template("product.html", product=product)

@app.route("/login", methods=["GET", "POST"])
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

            return redirect(url_for("catalog"))
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
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

        return redirect(url_for("login"))
     
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=1, port=2911)