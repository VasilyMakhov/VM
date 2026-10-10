from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection 

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not session.get("user_id"):
            return redirect(url_for("auth.login"))

    selected_ids = session.get("cart_selected", [])

    if not selected_ids:
          flash("Сначала выбери товары для заказа", "error")
          return redirect(url_for("cart.cart"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            ID,
            NAME
            FROM PAYMENT_METHODS
            ORDER BY ID
        """)

        payment_methods = cursor.fetchall()

        cursor.execute("""
            SELECT
            ci.ID,
            p.ID,
            p.NAME,
            p.PRICE,
            ci.QUANTITY,
            sp.ID
            FROM CART_ITEMS ci
            JOIN SELLER_PRODUCTS sp
            ON sp.ID = ci.SELLER_PRODUCT_ID
            JOIN PRODUCTS p
            ON p.ID = sp.PRODUCT_ID
            WHERE ci.USER_ID = ?
            ORDER BY ci.ID
        """, (session["user_id"],))

        all_items = cursor.fetchall()

    finally:
        connection.close()

    items = [
        item for item in all_items
        if item[0] in selected_ids
    ]

    if not items:
        session["cart_selected"] = []
        flash("Выбранные товары больше не найдены в корзине :/", "error" )
        return redirect(url_for("cart.cart"))

    total_price = sum(
        item[3] * item[4]
        for item in items
    )

    if request.method == "POST":
        delivery_address = request.form.get("delivery_address", "").strip()

        payment_method_id = request.form.get("payment_method_id", "")

        if not delivery_address:
            flash("Укажите адрес доставки", "error")
            return redirect(url_for("orders.checkout"))

        valid_method_ids = [str(method[0]) for method in payment_methods]

        if payment_method_id not in valid_method_ids:
            flash("Неизвестный способ оплаты", "error")
            return redirect(url_for("orders.checkout"))

        connection = get_connection()
        cursor = connection.cursor()
        try:
                      
            cursor.execute("""
                INSERT INTO ORDERS (
                USER_ID,
                TOTAL_PRICE,
                STATUS_ID,
                DELIVERY_ADDRESS,
                CREATED_AT,
                PAYMENT_METHOD_ID,
                PAYMENT_STATUS_ID,
                DELIVERY_STATUS_ID)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                RETURNING ID
                """, (session["user_id"], total_price, 1, delivery_address, int(payment_method_id), 1, 1,))

            order_id = cursor.fetchone()[0]

            for item in items:
                cursor.execute("""
                    INSERT INTO ORDER_ITEMS (
                    ORDER_ID,
                    QUANTITY,
                    PRICE,
                    SELLER_PRODUCT_ID)
                    VALUES (?, ?, ?, ?)
                """, (order_id, item[4], item[3], item[5]))

                cursor.execute("""
                    DELETE FROM CART_ITEMS
                    WHERE ID = ? AND USER_ID = ?
                """, (item[0], session["user_id"]))

            connection.commit()

            session["cart_selected"] = []
            flash("Заказ успешно оформлен!", "success")
            return redirect(url_for("cart.cart"))
        except Exception as error:
            connection.rollback()
            flash("Не удалось оформить заказ", "error")
            return redirect(url_for("orders.checkout"))
        finally:
            connection.close()

    return render_template("checkout.html", items=items, total_price=total_price, payment_methods=payment_methods)