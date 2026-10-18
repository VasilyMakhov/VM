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
                seller_product_id = item[5]
                order_quantity = item[4]

                cursor.execute("""
                    SELECT
                        ID,
                        QUANTITY
                    FROM WAREHOUSE_PRODUCTS
                    WHERE SELLER_PRODUCT_ID = ?
                    AND QUANTITY > 0
                    ORDER BY WAREHOUSE_ID
                """, (seller_product_id,))

                warehouse_stock = cursor.fetchall()

                total_stock = sum(
                    warehouse[1]
                    for warehouse in warehouse_stock
                )

                if total_stock < order_quantity:
                    connection.rollback()
                    flash(
                        f"Недостаточно товара «{item[2]}» на складах",
                        "error"
                    )
                    return redirect(url_for("cart.cart"))

                remaining_quantity = order_quantity

                for warehouse in warehouse_stock:
                    if remaining_quantity == 0:
                        break

                    warehouse_id = warehouse[0]
                    warehouse_quantity = warehouse[1]

                    quantity_to_remove = min(
                        warehouse_quantity,
                        remaining_quantity
                    )

                    cursor.execute("""
                        UPDATE WAREHOUSE_PRODUCTS
                        SET QUANTITY = QUANTITY - ?
                        WHERE ID = ?
                        AND QUANTITY >= ?
                    """, (
                        quantity_to_remove,
                        warehouse_id,
                        quantity_to_remove
                    ))

                    if cursor.rowcount != 1:
                        raise Exception("Не удалось обновить остаток товара")

                    remaining_quantity -= quantity_to_remove

                    cursor.execute("""
                        INSERT INTO ORDER_ITEMS (
                            ORDER_ID,
                            QUANTITY,
                            PRICE,
                            SELLER_PRODUCT_ID
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        order_id,
                        order_quantity,
                        item[3],
                        seller_product_id
                    ))

                    cursor.execute("""
                        DELETE FROM CART_ITEMS
                        WHERE ID = ? AND USER_ID = ?
                    """, (item[0], session["user_id"]))

            connection.commit()

            session["cart_selected"] = []
            if payment_method_id == "1":
                return redirect(url_for("orders.sbp_payment", order_id=order_id))
            flash("Заказ успешно оформлен!", "success")
            return redirect(url_for("orders.my_orders"))
        except Exception as error:
            connection.rollback()
            flash("Не удалось оформить заказ", "error")
            return redirect(url_for("orders.checkout"))
        finally:
            connection.close()

    return render_template("checkout.html", items=items, total_price=total_price, payment_methods=payment_methods)

@orders_bp.route("/payment/sbp/<int:order_id>")
def sbp_payment(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            ID,
            TOTAL_PRICE
            FROM ORDERS
            WHERE ID = ? AND USER_ID = ?
        """, (order_id, session["user_id"]))

        order = cursor.fetchone()

    finally:
        connection.close()

    if not order[0]:
        flash("Заказ не найден", "error")
        return redirect(url_for("catalog.catalog"))
    total_price = order[1]
    return render_template("sbp_payment.html", order_id=order_id, total_price=total_price)

@orders_bp.route("/payment/sbp/<int:order_id>/confirm", methods=["POST"])
def confirm_payment(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE ORDERS
            SET PAYMENT_STATUS_ID = 2
            WHERE ID = ?
            AND USER_ID = ?
            AND PAYMENT_METHOD_ID = 1
        """, (order_id, session["user_id"]))

        if cursor.rowcount == 0:
            connection.rollback()
            flash("Заказ не найден или оплата недоступна", "error")
            return redirect(url_for("catalog.catalog"))

        connection.commit()
        flash("Заявка на оплату отправлена на проверку", "success")

    except Exception as error:
        connection.rollback()
        print("Ошибка обновления оплаты:", error)
        flash("Не удалось обновить статус оплаты", "error")
        return redirect(url_for("catalog.catalog"))

    finally:
        connection.close()

    return redirect(url_for("orders.my_orders"))

@orders_bp.route("/my-orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            o.ID,
            o.CREATED_AT,
            o.TOTAL_PRICE,
            os.NAME,
            pm.NAME,
            ps.NAME,
            ds.NAME
            FROM ORDERS o
            JOIN ORDER_STATUSES os
            ON os.ID = o.STATUS_ID
            JOIN PAYMENT_METHODS pm
            ON pm.ID = o.PAYMENT_METHOD_ID
            JOIN PAYMENT_STATUSES ps
            ON ps.ID = o.PAYMENT_STATUS_ID
            JOIN DELIVERY_STATUSES ds
            ON ds.ID = o.DELIVERY_STATUS_ID
            WHERE o.USER_ID = ?
            ORDER BY o.CREATED_AT DESC
        """, (session["user_id"],))

        orders = cursor.fetchall()

    finally:
        connection.close()

    return render_template("my_orders.html", orders=orders)