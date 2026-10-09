from flask import Flask, render_template, request, redirect, url_for, session, flash
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

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT ID
            FROM SELLER_PRODUCTS
            WHERE PRODUCT_ID = ?
        """, (product_id,))

        seller_product = cursor.fetchone()

        if seller_product is None:
            flash("Товар недоступен для добавления в корзину", "error")
            return redirect(url_for("catalog"))

        seller_product_id = seller_product[0]

        cursor.execute("""
            SELECT
            COALESCE(SUM(QUANTITY),0)
            FROM WAREHOUSE_PRODUCTS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        stock = cursor.fetchone()[0]

        cursor.execute("""
            SELECT ID, QUANTITY
            FROM CART_ITEMS
            WHERE USER_ID = ? AND
            SELLER_PRODUCT_ID = ?
        """, (session["user_id"], seller_product_id))

        cart_item = cursor.fetchone()

        current_quantity = 0

        if cart_item is not None:
            current_quantity = cart_item[1]

        if current_quantity + 1 > stock:
            flash(f"Нельзя добавить товар! Товара осталось только: {stock} шт.", "error")
            return redirect(url_for("product", product_id = product_id))

        if cart_item is None:
            cursor.execute("""
                INSERT INTO CART_ITEMS
                (USER_ID, QUANTITY, SELLER_PRODUCT_ID)
                VALUES (?, ?, ?)
            """, (session["user_id"], 1, seller_product_id))
        else:
            cursor.execute("""
                UPDATE CART_ITEMS
                SET QUANTITY = ?
                WHERE ID = ?
            """, (current_quantity + 1, cart_item[0]))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
    return redirect(url_for("product", product_id=product_id))

@app.route("/cart")
def cart():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            ci.ID,
            p.ID,
            p.NAME,
            p.DESCRIPTION,
            p.IMAGE_URL,
            p.PRICE,
            ci.QUANTITY,
            COALESCE((
            SELECT SUM(wp.QUANTITY)
            FROM WAREHOUSE_PRODUCTS wp
            WHERE wp.SELLER_PRODUCT_ID = sp.ID
            ),0)
            FROM CART_ITEMS ci
            JOIN SELLER_PRODUCTS sp
            ON sp.ID = ci.SELLER_PRODUCT_ID
            JOIN PRODUCTS p
            ON p.ID = sp.PRODUCT_ID
            WHERE ci.USER_ID = ?
            ORDER BY ci.ID
        """, (session["user_id"],))

        items = cursor.fetchall()

    finally:
        connection.close()

    cart_ids = [item[0] for item in items]

    selected_ids = session.get("cart_selected", [])

    selected_ids = [cart_id for cart_id in selected_ids if cart_id in cart_ids]

    session["cart_selected"] = selected_ids

    selected_total = sum(
        item[5] * item[6]
        for item in items
        if item[0] in selected_ids
    )

    selected_count = sum(
        item[6] 
        for item in items
        if item[0] in selected_ids 
    )

    return render_template("cart.html", items=items, selected_ids=selected_ids, selected_total=selected_total, selected_count=selected_count)

@app.route("/cart/select", methods=["POST"])
def cart_select():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.form.get("action") == "clear":
        session["cart_selected"] = []
    elif request.form.get("select_all"):
        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT ID
                FROM CART_ITEMS
                WHERE USER_ID = ?
            """, (session["user_id"],))

            session["cart_selected"] = [ row[0] for row in cursor.fetchall() ]

        finally:
            connection.close()

    else:
        selected_ids = request.form.getlist("selected_items")

        session["cart_selected"] = [ int(cart_id) for cart_id in selected_ids if cart_id.isdigit() ]

    return redirect(url_for("cart"))

@app.route("/cart/update/<int:cart_id>", methods=["POST"])
def cart_update(cart_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    try:
        quantity = int(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    if quantity < 1:
        flash("Количество должно быть не меньше 1", "error")
        return redirect(url_for("cart"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT SELLER_PRODUCT_ID
            FROM CART_ITEMS
            WHERE ID = ? AND USER_ID = ?
        """, (cart_id, session["user_id"]))

        cart_item = cursor.fetchone()

        if cart_item is None:
            flash("Товар не найден в корзине", "error")
            return redirect(url_for("cart"))

        seller_product_id = cart_item[0]

        cursor.execute("""
            SELECT COALESCE(SUM(QUANTITY), 0)
            FROM WAREHOUSE_PRODUCTS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        stock = cursor.fetchone()[0]

        if quantity > stock:
            flash(
                f"Нельзя поставить {quantity} шт. На складе только {stock} шт.",
                "error"
            )
            return redirect(url_for("cart"))

        cursor.execute("""
            UPDATE CART_ITEMS
            SET QUANTITY = ?
            WHERE ID = ? AND USER_ID = ?
        """, (
            quantity,
            cart_id,
            session["user_id"]
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("cart"))

@app.route("/cart/remove/<int:cart_id>", methods=["POST"])
def cart_remove(cart_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM CART_ITEMS
            WHERE ID = ? AND USER_ID = ?
        """, (
            cart_id,
            session["user_id"]
        ))

        connection.commit()

        selected_ids = session.get("cart_selected", [])

        session["cart_selected"] = [
            item_id
            for item_id in selected_ids
            if item_id != cart_id
        ]

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("cart"))


if __name__ == "__main__":
    app.run(debug=1, port=2911)