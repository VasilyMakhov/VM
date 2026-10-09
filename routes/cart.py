from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection 

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    
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
            return redirect(url_for("catalog.catalog"))

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
            return redirect(url_for("catalog.product", product_id = product_id))

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
    return redirect(url_for("catalog.product", product_id=product_id))

@cart_bp.route("/cart")
def cart():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    
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

@cart_bp.route("/cart/select", methods=["POST"])
def cart_select():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

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

    return redirect(url_for("cart.cart"))

@cart_bp.route("/cart/update/<int:cart_id>", methods=["POST"])
def cart_update(cart_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    try:
        quantity = int(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    if quantity < 1:
        flash("Количество должно быть не меньше 1", "error")
        return redirect(url_for("cart.cart"))

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
            return redirect(url_for("cart.cart"))

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
            return redirect(url_for("cart.cart"))

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

    return redirect(url_for("cart.cart"))

@cart_bp.route("/cart/remove/<int:cart_id>", methods=["POST"])
def cart_remove(cart_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

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

    return redirect(url_for("cart.cart"))
