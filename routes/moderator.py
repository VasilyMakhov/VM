import os
import uuid
from decimal import Decimal, InvalidOperation
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from db import get_connection

moderator_bp = Blueprint("moderator", __name__, url_prefix="/moderator")

def check_moderator_access():
    if "user_id" not in session:
        return False
    if session.get("user_role") != 3:
        return False
    return True

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

@moderator_bp.route("/categories")
def categories_list():
    if not check_moderator_access():
        flash("Доступ запрещен. Требуются права модератора.", "error")
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT 
            ID, 
            NAME,
            DESCRIPTION
            FROM CATEGORIES 
            ORDER BY NAME
        """)
        categories = cursor.fetchall()
        return render_template("moderator/categories.html", categories=categories)
    finally:
        connection.close()

@moderator_bp.route("/categories/add", methods=["GET", "POST"])
def category_add():
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not description:
            return render_template("moderator/category_form.html", error="Название и описание категории обязательны")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO CATEGORIES 
                (NAME, DESCRIPTION) 
                VALUES (?, ?)
            """, (name, description))
            connection.commit()
            flash("Категория успешно добавлена!", "success")
            return redirect(url_for("moderator.categories_list"))
        finally:
            connection.close()

    return render_template("moderator/category_form.html", category=None)

@moderator_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
def category_edit(cat_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()

            if not name or not description:
                cursor.execute("""
                    SELECT 
                    ID, 
                    NAME,
                    DESCRIPTION
                    FROM CATEGORIES 
                    WHERE ID = ?
                """, (cat_id,))
                category = cursor.fetchone()
                return render_template("moderator/category_form.html", category=category, error="Название и описание обязательны")

            cursor.execute("""
                UPDATE CATEGORIES 
                SET NAME = ?,
                DESCRIPTION = ?
                WHERE ID = ?
            """, (name, description, cat_id))
            connection.commit()
            flash("Категория успешно обновлена!", "success")
            return redirect(url_for("moderator.categories_list"))

        cursor.execute("""
            SELECT 
            ID, 
            NAME,
            DESCRIPTION
            FROM CATEGORIES 
            WHERE ID = ?
        """, (cat_id,))
        category = cursor.fetchone()
        
        if not category:
            flash("Категория не найдена", "error")
            return redirect(url_for("moderator.categories_list"))

        return render_template("moderator/category_form.html", category=category)
    finally:
        connection.close()

@moderator_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def category_delete(cat_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM CATEGORIES 
            WHERE ID = ?
        """, (cat_id,))
        connection.commit()
        flash("Категория успешно удалена!", "success")
    except Exception as e:
        connection.rollback()
        flash("Невозможно удалить категорию, так как в ней есть товары.", "error")
    finally:
        connection.close()

    return redirect(url_for("moderator.categories_list"))


@moderator_bp.route("/warehouses")
def warehouses_list():
    if not check_moderator_access():
        flash("Доступ запрещен. Требуются права модератора.", "error")
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT 
            ID, 
            NAME,
            ADDRESS
            FROM WAREHOUSES 
            ORDER BY NAME
        """)
        warehouses = cursor.fetchall()
        return render_template("moderator/warehouses.html", warehouses=warehouses)
    finally:
        connection.close()

@moderator_bp.route("/warehouses/add", methods=["GET", "POST"])
def warehouse_add():
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not address:
            return render_template("moderator/warehouse_form.html", error="Название и адрес склада обязательны")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO WAREHOUSES
                (NAME, ADDRESS)
                VALUES (?, ?)
            """, (name, address))
            connection.commit()
            flash("Склад успешно добавлен!", "success")
            return redirect(url_for("moderator.warehouses_list"))
        finally:
            connection.close()

    return render_template("moderator/warehouse_form.html", warehouse=None)

@moderator_bp.route("/warehouses/<int:wh_id>/edit", methods=["GET", "POST"])
def warehouse_edit(wh_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            address = request.form.get("address", "").strip()

            if not name or not address:
                cursor.execute("""
                    SELECT 
                    ID, 
                    NAME,
                    ADDRESS
                    FROM WAREHOUSES 
                    WHERE ID = ?
                """, (wh_id,))
                warehouse = cursor.fetchone()
                return render_template("moderator/warehouse_form.html", warehouse=warehouse, error="Название и адрес обязательны")

            cursor.execute("""
                UPDATE WAREHOUSES 
                SET NAME = ?,
                ADDRESS = ?
                WHERE ID = ?
            """, (name, address, wh_id))
            connection.commit()
            flash("Склад успешно обновлен!", "success")
            return redirect(url_for("moderator.warehouses_list"))

        cursor.execute("""
            SELECT 
            ID, 
            NAME,
            ADDRESS
            FROM WAREHOUSES 
            WHERE ID = ?
        """, (wh_id,))
        warehouse = cursor.fetchone()
        
        if not warehouse:
            flash("Склад не найден", "error")
            return redirect(url_for("moderator.warehouses_list"))

        return render_template("moderator/warehouse_form.html", warehouse=warehouse)
    finally:
        connection.close()

@moderator_bp.route("/warehouses/<int:wh_id>/delete", methods=["POST"])
def warehouse_delete(wh_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM WAREHOUSES 
            WHERE ID = ?
        """, (wh_id,))
        connection.commit()
        flash("Склад успешно удален!", "success")
    except Exception:
        connection.rollback()
        flash("Невозможно удалить склад, так как с ним связаны товары.", "error")
    finally:
        connection.close()

    return redirect(url_for("moderator.warehouses_list"))

@moderator_bp.route("/products")
def products_list():
    if not check_moderator_access():
        flash("Доступ запрещен. Требуются права модератора.", "error")
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT
                p.ID,
                p.NAME,
                p.IMAGE_URL,
                p.PRICE,
                u.LOGIN,
                sp.ID,
                COALESCE(SUM(wp.QUANTITY), 0)
            FROM PRODUCTS p
            JOIN SELLER_PRODUCTS sp
                ON sp.PRODUCT_ID = p.ID
            JOIN USERS u
                ON u.ID = sp.SELLER_ID
            LEFT JOIN WAREHOUSE_PRODUCTS wp
                ON wp.SELLER_PRODUCT_ID = sp.ID
            GROUP BY
                p.ID,
                p.NAME,
                p.IMAGE_URL,
                p.PRICE,
                u.LOGIN,
                sp.ID
            ORDER BY p.NAME, u.LOGIN
        """)
        products = cursor.fetchall()
        return render_template("moderator/products.html", products=products)
    finally:
        connection.close()


@moderator_bp.route("/products/<int:seller_product_id>/edit", methods=["GET", "POST"])
def product_edit(seller_product_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

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
                sp.ID,
                u.LOGIN
            FROM SELLER_PRODUCTS sp
            JOIN PRODUCTS p
                ON p.ID = sp.PRODUCT_ID
            JOIN USERS u
                ON u.ID = sp.SELLER_ID
            WHERE sp.ID = ?
        """, (seller_product_id,))

        product = cursor.fetchone()

        if product is None:
            flash("Товар не найден.", "error")
            return redirect(url_for("moderator.products_list"))

        product_id = product[0]

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
            return render_template(
                "moderator/product_form.html",
                product=product,
                categories=categories,
                warehouses=warehouses
            )

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category_raw = request.form.get("category_id", "").strip()
        price_raw = request.form.get("price", "").strip()
        image = request.files.get("image")

        if not name or not description or not category_raw or not price_raw:
            flash("Заполните все обязательные поля.", "error")
            return redirect(url_for(
                "moderator.product_edit",
                seller_product_id=seller_product_id
            ))

        try:
            category_id = int(category_raw)
        except ValueError:
            flash("Некорректная категория.", "error")
            return redirect(url_for(
                "moderator.product_edit",
                seller_product_id=seller_product_id
            ))

        if not any(category[0] == category_id for category in categories):
            flash("Выбранная категория не существует.", "error")
            return redirect(url_for(
                "moderator.product_edit",
                seller_product_id=seller_product_id
            ))

        try:
            price = Decimal(price_raw.replace(",", "."))
            if not price.is_finite() or price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Введите корректную неотрицательную цену.", "error")
            return redirect(url_for(
                "moderator.product_edit",
                seller_product_id=seller_product_id
            ))

        has_new_image = image is not None and bool(image.filename)
        extension = None

        if has_new_image:
            safe_name = secure_filename(image.filename)
            extension = os.path.splitext(safe_name)[1].lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                flash("Разрешены только JPG, PNG и WebP.", "error")
                return redirect(url_for(
                    "moderator.product_edit",
                    seller_product_id=seller_product_id
                ))

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
                return redirect(url_for(
                    "moderator.product_edit",
                    seller_product_id=seller_product_id
                ))

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
        return redirect(url_for("moderator.products_list"))

    except Exception:
        connection.rollback()

        if new_image_path and os.path.isfile(new_image_path):
            os.remove(new_image_path)

        current_app.logger.exception(
            "Ошибка редактирования товара модератором, предложение ID %s",
            seller_product_id
        )
        flash("Не удалось сохранить изменения товара.", "error")
        return redirect(url_for(
            "moderator.product_edit",
            seller_product_id=seller_product_id
        ))

    finally:
        connection.close()


@moderator_bp.route("/products/<int:seller_product_id>/delete", methods=["POST"])
def product_delete(seller_product_id):
    if not check_moderator_access():
        return redirect(url_for("main.index"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                p.ID,
                p.IMAGE_URL,
                sp.ID
            FROM SELLER_PRODUCTS sp
            JOIN PRODUCTS p
                ON p.ID = sp.PRODUCT_ID
            WHERE sp.ID = ?
        """, (seller_product_id,))

        product = cursor.fetchone()

        if product is None:
            flash("Товар не найден.", "error")
            return redirect(url_for("moderator.products_list"))

        product_id = product[0]
        image_url = product[1]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDER_ITEMS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        order_items_count = cursor.fetchone()[0]

        if order_items_count > 0:
            flash(
                "Нельзя удалить товар, который уже используется в заказах.",
                "error"
            )
            return redirect(url_for("moderator.products_list"))

        cursor.execute("""
            DELETE FROM CART_ITEMS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        cursor.execute("""
            DELETE FROM WAREHOUSE_PRODUCTS
            WHERE SELLER_PRODUCT_ID = ?
        """, (seller_product_id,))

        cursor.execute("""
            DELETE FROM SELLER_PRODUCTS
            WHERE ID = ?
        """, (seller_product_id,))

        cursor.execute("""
            SELECT COUNT(*)
            FROM SELLER_PRODUCTS
            WHERE PRODUCT_ID = ?
        """, (product_id,))

        other_offers_count = cursor.fetchone()[0]
        product_deleted = other_offers_count == 0

        if product_deleted:
            cursor.execute("""
                DELETE FROM FAVORITES
                WHERE PRODUCT_ID = ?
            """, (product_id,))

            cursor.execute("""
                DELETE FROM PRODUCTS
                WHERE ID = ?
            """, (product_id,))

        connection.commit()

        if product_deleted:
            remove_local_image(image_url)

        flash("Товар удалён.", "success")
        return redirect(url_for("moderator.products_list"))

    except Exception:
        connection.rollback()
        current_app.logger.exception(
            "Ошибка удаления товара модератором, предложение ID %s",
            seller_product_id
        )
        flash(
            "Не удалось удалить товар. Возможно, он используется в заказах.",
            "error"
        )
        return redirect(url_for("moderator.products_list"))

    finally:
        connection.close()
