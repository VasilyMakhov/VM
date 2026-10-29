import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from decimal import Decimal, InvalidOperation
from db import get_connection

catalog_bp = Blueprint("catalog", __name__)

def remove_local_image(image_url):
    if not image_url or not image_url.startswith("/static/images/"):
        return

    filename = os.path.basename(image_url)
    image_path = os.path.join(
        current_app.static_folder,
        "images",
        filename
    )

    try:
        if os.path.isfile(image_path):
            os.remove(image_path)
    except OSError:
        current_app.logger.exception(
            "Не удалось удалить файл изображения: %s",
            image_path
        )

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

    try:
        cursor.execute("""
            SELECT
                p.ID,
                p.NAME,
                p.DESCRIPTION,
                p.IMAGE_URL,
                c.NAME AS CATEGORY,
                p.PRICE,
                COALESCE(SUM(wp.QUANTITY), 0) AS QUANTITY
            FROM PRODUCTS p
            JOIN CATEGORIES c
                ON c.ID = p.CATEGORY_ID
            JOIN SELLER_PRODUCTS sp
                ON sp.PRODUCT_ID = p.ID
            LEFT JOIN WAREHOUSE_PRODUCTS wp
                ON wp.SELLER_PRODUCT_ID = sp.ID
            WHERE p.ID = ?
            GROUP BY
                p.ID,
                p.NAME,
                p.DESCRIPTION,
                p.IMAGE_URL,
                c.NAME,
                p.PRICE
        """, (product_id,))

        product = cursor.fetchone()

        if product is None:
            flash("Товар не найден.", "error")
            return redirect(url_for("catalog.catalog"))

        is_favorite = False

        if session.get("user_id"):
            cursor.execute("""
                SELECT ID
                FROM FAVORITES
                WHERE USER_ID = ?
                AND PRODUCT_ID = ?
            """, (session["user_id"], product_id))

            is_favorite = cursor.fetchone() is not None

        return render_template("product.html", product=product, is_favorite=is_favorite)

    finally:
        connection.close()

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

@catalog_bp.route("/seller-orders")
def seller_orders():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if str(session.get("user_role")) != "2":
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                o.ID,
                o.CREATED_AT,
                os.NAME,
                pm.NAME,
                ps.NAME,
                ds.NAME,
                o.DELIVERY_ADDRESS,
                u.LOGIN,
                ords.PAYMENT_CONFIRMED,
                ords.HANDED_TO_DELIVERY,
                o.PAYMENT_METHOD_ID,
                o.PAYMENT_STATUS_ID,
                o.STATUS_ID,
                o.DELIVERY_STATUS_ID,
                p.NAME,
                oi.QUANTITY,
                oi.PRICE
            FROM ORDER_SELLERS ords
            JOIN ORDERS o
                ON o.ID = ords.ORDER_ID
            JOIN ORDER_STATUSES os
                ON os.ID = o.STATUS_ID
            JOIN PAYMENT_METHODS pm
                ON pm.ID = o.PAYMENT_METHOD_ID
            JOIN PAYMENT_STATUSES ps
                ON ps.ID = o.PAYMENT_STATUS_ID
            JOIN DELIVERY_STATUSES ds
                ON ds.ID = o.DELIVERY_STATUS_ID
            JOIN USERS u
                ON u.ID = o.USER_ID
            JOIN ORDER_ITEMS oi
                ON oi.ORDER_ID = o.ID
            JOIN SELLER_PRODUCTS sp
                ON sp.ID = oi.SELLER_PRODUCT_ID
                AND sp.SELLER_ID = ords.SELLER_ID
            JOIN PRODUCTS p
                ON p.ID = sp.PRODUCT_ID
            WHERE ords.SELLER_ID = ?
            ORDER BY o.CREATED_AT DESC, o.ID DESC, p.NAME
        """, (session["user_id"],))

        rows = cursor.fetchall()

        orders_by_id = {}

        for row in rows:
            order_id = row[0]

            if order_id not in orders_by_id:
                orders_by_id[order_id] = {
                    "id": row[0],
                    "created_at": row[1],
                    "order_status": row[2],
                    "payment_method": row[3],
                    "payment_status": row[4],
                    "delivery_status": row[5],
                    "delivery_address": row[6],
                    "buyer_login": row[7],
                    "payment_confirmed": row[8],
                    "handed_to_delivery": row[9],
                    "payment_method_id": row[10],
                    "payment_status_id": row[11],
                    "status_id": row[12],
                    "delivery_status_id": row[13],
                    "items": [],
                    "seller_total": 0
                }

            orders_by_id[order_id]["items"].append({
                "name": row[14],
                "quantity": row[15],
                "price": row[16]
            })

            orders_by_id[order_id]["seller_total"] += (
                row[15] * row[16]
            )

        orders = list(orders_by_id.values())

        return render_template(
            "seller_orders.html",
            orders=orders
        )

    finally:
        connection.close()

@catalog_bp.route("/seller-orders/<int:order_id>/confirm-payment", methods=["POST"])
def seller_confirm_payment(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if str(session.get("user_role")) != "2":
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        seller_id = session["user_id"]

        cursor.execute("""
            SELECT PAYMENT_METHOD_ID, PAYMENT_STATUS_ID, STATUS_ID
            FROM ORDERS
            WHERE ID = ?
            AND EXISTS (
                SELECT 1
                FROM ORDER_SELLERS
                WHERE ORDER_ID = ORDERS.ID
                AND SELLER_ID = ?
            )
        """, (order_id, seller_id))

        order = cursor.fetchone()

        if order is None:
            flash("Заказ не найден или не относится к вам.", "error")
            return redirect(url_for("catalog.seller_orders"))

        payment_method_id = order[0]
        payment_status_id = order[1]
        status_id = order[2]

        if payment_method_id != 1:
            flash("Для этого способа оплаты подтверждение не требуется.", "error")
            return redirect(url_for("catalog.seller_orders"))

        if payment_status_id != 2:
            flash("Этот платёж уже обработан или не ожидает проверки.", "error")
            return redirect(url_for("catalog.seller_orders"))

        if status_id in (4, 5, 6):
            flash("Для этого заказа подтверждение уже недоступно.", "error")
            return redirect(url_for("catalog.seller_orders"))

        cursor.execute("""
            UPDATE ORDER_SELLERS
            SET PAYMENT_CONFIRMED = 1
            WHERE ORDER_ID = ?
              AND SELLER_ID = ?
              AND PAYMENT_CONFIRMED = 0
        """, (order_id, seller_id))

        if cursor.rowcount == 0:
            flash("Вы уже подтвердили оплату этого заказа.", "info")
            return redirect(url_for("catalog.seller_orders"))

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDER_SELLERS
            WHERE ORDER_ID = ?
              AND PAYMENT_CONFIRMED = 0
        """, (order_id,))

        unconfirmed_sellers = cursor.fetchone()[0]

        if unconfirmed_sellers == 0:
            cursor.execute("""
                UPDATE ORDERS
                SET PAYMENT_STATUS_ID = 3,
                    STATUS_ID = 2
                WHERE ID = ?
                  AND PAYMENT_STATUS_ID = 2
            """, (order_id,))

            flash("Все продавцы подтвердили оплату.", "success")
        else:
            flash("Вы подтвердили оплату своей части заказа.", "success")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("catalog.seller_orders"))


@catalog_bp.route("/seller-orders/<int:order_id>/handover", methods=["POST"])
def seller_handover(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if str(session.get("user_role")) != "2":
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        seller_id = session["user_id"]
        cursor.execute("""
            SELECT PAYMENT_METHOD_ID, PAYMENT_STATUS_ID, STATUS_ID,
                   DELIVERY_STATUS_ID
            FROM ORDERS
            WHERE ID = ?
              AND EXISTS (
                  SELECT 1
                  FROM ORDER_SELLERS
                  WHERE ORDER_ID = ORDERS.ID
                    AND SELLER_ID = ?
              )
        """, (order_id, seller_id))

        order = cursor.fetchone()

        if order is None:
            flash("Заказ не найден или не относится к вам.", "error")
            return redirect(url_for("catalog.seller_orders"))

        payment_method_id = order[0]
        payment_status_id = order[1]
        status_id = order[2]
        delivery_status_id = order[3]

        if status_id in (5, 6) or delivery_status_id in (3, 4):
            flash("Этот заказ уже завершён или отменён.", "error")
            return redirect(url_for("catalog.seller_orders"))

        cursor.execute("""
            UPDATE ORDER_SELLERS
            SET HANDED_TO_DELIVERY = 1
            WHERE ORDER_ID = ?
              AND SELLER_ID = ?
              AND HANDED_TO_DELIVERY = 0
        """, (order_id, seller_id))

        if cursor.rowcount == 0:
            flash("Вы уже отметили передачу своих товаров.", "info")
            return redirect(url_for("catalog.seller_orders"))

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDER_SELLERS
            WHERE ORDER_ID = ?
              AND HANDED_TO_DELIVERY = 0
        """, (order_id,))

        sellers_left = cursor.fetchone()[0]

        if sellers_left == 0:
            cursor.execute("""
                UPDATE ORDERS
                SET STATUS_ID = 4,
                    DELIVERY_STATUS_ID = 2
                WHERE ID = ?
                  AND STATUS_ID NOT IN (5, 6)
                  AND DELIVERY_STATUS_ID NOT IN (3, 4)
            """, (order_id,))

            flash("Все продавцы передали товары. Заказ отправлен в доставку.", "success")
        else:
            flash("Вы отметили передачу своих товаров. Ожидаются остальные продавцы.", "success")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("catalog.seller_orders"))
    
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

@catalog_bp.route("/my-products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != 2:
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()
    new_image_path = None

    try:
        cursor.execute("""
            SELECT
            p.ID,
            p.NAME,
            p.DESCRIPTION,
            p.IMAGE_URL,
            p.CATEGORY_ID,
            p.PRICE,
            sp.ID
            FROM PRODUCTS p
            JOIN SELLER_PRODUCTS sp
            ON sp.PRODUCT_ID = p.ID
            WHERE p.ID = ?
            AND sp.SELLER_ID = ?
        """, (product_id, session["user_id"]))

        product = cursor.fetchone()

        if product is None:
            flash("Товар не найден или не принадлежит вам.", "error")
            return redirect(url_for("catalog.my_products"))

        seller_product_id = product[6]

        cursor.execute("""
            SELECT ID, NAME
            FROM CATEGORIES
            ORDER BY NAME
        """)
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT
            w.ID,
            w.NAME,
            COALESCE(wp.QUANTITY, 0)
            FROM WAREHOUSES w
            LEFT JOIN WAREHOUSE_PRODUCTS wp
            ON wp.WAREHOUSE_ID = w.ID
            AND wp.SELLER_PRODUCT_ID = ?
            ORDER BY w.NAME
        """, (seller_product_id,))

        warehouses = cursor.fetchall()

        if request.method == "GET":
            return render_template("edit_product.html", product=product, categories=categories, warehouses=warehouses)

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category_raw = request.form.get("category_id", "").strip()
        price_raw = request.form.get("price", "").strip()
        image = request.files.get("image")

        if not name or not description or not category_raw or not price_raw:
            flash("Заполните все обязательные поля.", "error")
            return redirect(url_for("catalog.edit_product", product_id=product_id))

        try:
            category_id = int(category_raw)
        except ValueError:
            flash("Некорректная категория.", "error")
            return redirect(url_for("catalog.edit_product", product_id=product_id))

        if not any(category[0] == category_id for category in categories):
            flash("Выбранная категория не существует.", "error")
            return redirect(url_for("catalog.edit_product", product_id=product_id))

        try:
            price = Decimal(price_raw.replace(",", "."))
            if not price.is_finite() or price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Введите корректную неотрицательную цену.", "error")
            return redirect(url_for("catalog.edit_product", product_id=product_id))

        has_new_image = image is not None and bool(image.filename)
        extension = None

        if has_new_image:
            safe_name = secure_filename(image.filename)
            extension = os.path.splitext(safe_name)[1].lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                flash("Разрешены только JPG, PNG и WebP.", "error")
                return redirect(url_for("catalog.edit_product", product_id=product_id))

        warehouse_quantities = []

        for warehouse in warehouses:
            quantity_raw = request.form.get(
                f"quantity_{warehouse[0]}", ""
            ).strip()

            try:
                quantity = int(quantity_raw)
                if quantity < 0:
                    raise ValueError
            except ValueError:
                flash(
                    f"Некорректное количество для склада «{warehouse[1]}».",
                    "error"
                )
                return redirect(url_for("catalog.edit_product",product_id=product_id))

            warehouse_quantities.append((warehouse[0], quantity))

        image_url = product[3]

        if has_new_image:
            filename = f"{uuid.uuid4().hex}{extension}"
            images_dir = os.path.join(
                current_app.static_folder,
                "images"
            )
            os.makedirs(images_dir, exist_ok=True)

            new_image_path = os.path.join(images_dir, filename)
            image.save(new_image_path)
            image_url = f"/static/images/{filename}"

        cursor.execute("""
            UPDATE PRODUCTS
            SET CATEGORY_ID = ?,
            NAME = ?,
            DESCRIPTION = ?,
            IMAGE_URL = ?,
            PRICE = ?
            WHERE ID = ?
        """, (category_id, name, description, image_url, price, product_id))

        for warehouse_id, quantity in warehouse_quantities:
            cursor.execute("""
                SELECT ID
                FROM WAREHOUSE_PRODUCTS
                WHERE WAREHOUSE_ID = ?
                AND SELLER_PRODUCT_ID = ?
            """, (warehouse_id, seller_product_id))

            warehouse_product = cursor.fetchone()

            if warehouse_product is None:
                cursor.execute("""
                    INSERT INTO WAREHOUSE_PRODUCTS
                    (WAREHOUSE_ID, SELLER_PRODUCT_ID, QUANTITY)
                    VALUES (?, ?, ?)
                """, (warehouse_id, seller_product_id, quantity))
            else:
                cursor.execute("""
                    UPDATE WAREHOUSE_PRODUCTS
                    SET QUANTITY = ?
                    WHERE ID = ?
                """, (quantity, warehouse_product[0]))

        connection.commit()

        if has_new_image:
            remove_local_image(product[3])

        flash("Изменения товара сохранены.", "success")
        return redirect(url_for("catalog.my_products"))

    except Exception:
        connection.rollback()

        if new_image_path and os.path.isfile(new_image_path):
            os.remove(new_image_path)

        current_app.logger.exception(
            "Ошибка редактирования товара ID %s",
            product_id
        )
        flash("Не удалось сохранить изменения товара.", "error")
        return redirect(url_for("catalog.edit_product",product_id=product_id))

    finally:
        connection.close()
        
@catalog_bp.route("/my-products/<int:product_id>/delete",methods=["POST"])
def delete_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != 2:
        return redirect(url_for("catalog.catalog"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT p.ID, p.IMAGE_URL, sp.ID
            FROM PRODUCTS p
            JOIN SELLER_PRODUCTS sp
            ON sp.PRODUCT_ID = p.ID
            WHERE p.ID = ?
            AND sp.SELLER_ID = ?
        """, (product_id, session["user_id"]))

        product = cursor.fetchone()

        if product is None:
            flash("Товар не найден или не принадлежит вам.", "error")
            return redirect(url_for("catalog.my_products"))

        image_url = product[1]
        seller_product_id = product[2]

        cursor.execute("""
            DELETE FROM WAREHOUSE_PRODUCTS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        cursor.execute("""
            DELETE FROM SELLER_PRODUCTS
            WHERE ID = ?
              AND SELLER_ID = ?
        """, (seller_product_id, session["user_id"]))

        cursor.execute("""
            DELETE FROM PRODUCTS
            WHERE ID = ?
        """, (product_id,))

        connection.commit()

        remove_local_image(image_url)

        flash("Товар удалён.", "success")
        return redirect(url_for("catalog.my_products"))

    except Exception:
        connection.rollback()

        current_app.logger.exception(
            "Ошибка удаления товара ID %s",
            product_id
        )

        flash("Не удалось удалить товар. Возможно, он используется в заказах.","error")
        return redirect(url_for("catalog.edit_product",product_id=product_id))

    finally:
        connection.close()