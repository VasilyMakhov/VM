import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from decimal import Decimal, InvalidOperation
from db import get_connection

catalog_bp = Blueprint("catalog", __name__)

@catalog_bp.route("/catalog")
def catalog():
    connection = get_connection()
    cursor = connection.cursor()
   
    cursor.execute("""
        SELECT
        ID,
        NAME
        FROM CATEGORIES
        ORDER BY NAME
    """)

    categories = cursor.fetchall()

    search = request.args.get("search", "")

    selected_categoty = request.args.get("category", "")

    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")

    sort = request.args.get("sort", "")

    query = """
        SELECT
        p.ID,
        p.NAME,
        p.IMAGE_URL,
        p.PRICE
        FROM PRODUCTS p
        JOIN SELLER_PRODUCTS sp
        ON sp.PRODUCT_ID = p.ID
        WHERE 1 = 1
    """

    params = []

    if selected_categoty:
        query += " AND p.CATEGORY_ID = ?"
        params.append(int(selected_categoty))

    if search:
        query += " AND p.NAME CONTAINING ?"
        params.append(search)

    if min_price:
        query += " AND p.PRICE >= ?"
        params.append(float(min_price))

    if max_price:
        query += " AND p.PRICE <= ?"
        params.append(float(max_price))

    if sort == "price_asc":
        query += " ORDER BY p.PRICE ASC"
    elif sort == "price_desc":
        query += " ORDER BY p.PRICE DESC"
    elif sort == "name":
        query += " ORDER BY p.NAME"
    
    cursor.execute(query, params)

    products = cursor.fetchall()
    connection.close()

    return render_template("catalog.html", products=products, categories=categories, 
                           selected_categoty=selected_categoty, search=search,
                           min_price=min_price, max_price=max_price,
                           sort=sort)

@catalog_bp.route("/product/<int:product_id>")
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

@catalog_bp.route("/my-products")
def my_products():
    if not session.get("user_id"):
            return redirect(url_for("auth.login"))

    if session.get("user_role")!=2:
        return redirect(url_for("catalog.catalog"))

    user_id = session["user_id"]

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            p.ID,
            p.NAME,
            p.IMAGE_URL,
            p.PRICE
            FROM PRODUCTS P
            JOIN SELLER_PRODUCTS sp
            ON sp.PRODUCT_ID = p.ID
            WHERE sp.SELLER_ID = ?
            ORDER BY p.NAME
        """, (user_id,))

        products = cursor.fetchall()

        return render_template("my_products.html", products=products)

    finally:
        connection.close()
    
@catalog_bp.route("/my-products/create", methods=["GET", "POST"])
def create_product():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if str(session.get("user_role")) != "2":
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()
    image_path = None

    try:
        cursor.execute("""
            SELECT
                ID,
                NAME
            FROM CATEGORIES
            ORDER BY NAME
        """)
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT
                ID,
                NAME
            FROM WAREHOUSES
            ORDER BY NAME
        """)
        warehouses = cursor.fetchall()

        if request.method == "GET":
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses
            )

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category_raw = request.form.get("category_id", "").strip()
        price_raw = request.form.get("price", "").strip()
        image = request.files.get("image")

        if (
            not name
            or not description
            or not category_raw
            or not price_raw
            or not image
            or not image.filename
        ):
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses,
                error="Заполните все поля товара"
            ), 400

        try:
            category_id = int(category_raw)
        except ValueError:
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses,
                error="Выбрана несуществующая категория"
            ), 400

        if not any(category[0] == category_id for category in categories):
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses,
                error="Выбрана несуществующая категория"
            ), 400

        try:
            price = Decimal(price_raw.replace(",", "."))
            if not price.is_finite() or price < 0:
                raise InvalidOperation
        except InvalidOperation:
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses,
                error="Укажите корректную неотрицательную цену"
            ), 400

        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        safe_name = secure_filename(image.filename)
        extension = os.path.splitext(safe_name)[1].lower()

        if extension not in allowed_extensions:
            return render_template(
                "create_product.html",
                categories=categories,
                warehouses=warehouses,
                error="Разрешены только JPG, PNG и WebP"
            ), 400

        warehouse_quantities = []

        for warehouse in warehouses:
            quantity_raw = request.form.get(
                f"quantity_{warehouse[0]}", "0"
            ).strip()

            try:
                quantity = int(quantity_raw)
                if quantity < 0:
                    raise ValueError
            except ValueError:
                return render_template(
                    "create_product.html",
                    categories=categories,
                    warehouses=warehouses,
                    error=f"Некорректное количество для склада «{warehouse[1]}»"
                ), 400

            warehouse_quantities.append((warehouse[0], quantity))

        filename = f"{uuid.uuid4().hex}{extension}"
        images_dir = os.path.join(current_app.static_folder, "images")
        os.makedirs(images_dir, exist_ok=True)
        image_path = os.path.join(images_dir, filename)
        image.save(image_path)

        image_url = f"/static/images/{filename}"

        cursor.execute("""
            INSERT INTO PRODUCTS
                (CATEGORY_ID, NAME, DESCRIPTION, IMAGE_URL, PRICE)
            VALUES (?, ?, ?, ?, ?)
            RETURNING ID
        """, (category_id, name, description, image_url, price))

        product_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO SELLER_PRODUCTS
                (SELLER_ID, PRODUCT_ID)
            VALUES (?, ?)
            RETURNING ID
        """, (session["user_id"], product_id))

        seller_product_id = cursor.fetchone()[0]

        for warehouse_id, quantity in warehouse_quantities:
            cursor.execute("""
                INSERT INTO WAREHOUSE_PRODUCTS
                    (WAREHOUSE_ID, SELLER_PRODUCT_ID, QUANTITY)
                VALUES (?, ?, ?)
            """, (warehouse_id, seller_product_id, quantity))

        connection.commit()
        flash("Товар успешно создан", "success")

        return redirect(url_for("catalog.my_products"))

    except Exception:
        connection.rollback()

        if image_path and os.path.isfile(image_path):
            os.remove(image_path)

        raise

    finally:
        connection.close()