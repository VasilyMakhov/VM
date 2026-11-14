from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection 

orders_bp = Blueprint("orders", __name__)


def restore_order_stock(cursor, order_id):
    cursor.execute("""
        SELECT
            SELLER_PRODUCT_ID,
            QUANTITY
        FROM ORDER_ITEMS
        WHERE ORDER_ID = ?
        ORDER BY ID
    """, (order_id,))

    items = cursor.fetchall()

    for seller_product_id, quantity in items:
        cursor.execute("""
            SELECT FIRST 1 ID
            FROM WAREHOUSE_PRODUCTS
            WHERE SELLER_PRODUCT_ID = ?
            ORDER BY WAREHOUSE_ID
        """, (seller_product_id,))

        warehouse_product = cursor.fetchone()

        if warehouse_product is not None:
            cursor.execute("""
                UPDATE WAREHOUSE_PRODUCTS
                SET QUANTITY = QUANTITY + ?
                WHERE ID = ?
            """, (quantity, warehouse_product[0]))
            continue

        cursor.execute("""
            SELECT FIRST 1 ID
            FROM WAREHOUSES
            ORDER BY ID
        """)
        warehouse = cursor.fetchone()

        if warehouse is not None:
            cursor.execute("""
                INSERT INTO WAREHOUSE_PRODUCTS
                    (WAREHOUSE_ID, SELLER_PRODUCT_ID, QUANTITY)
                VALUES (?, ?, ?)
            """, (warehouse[0], seller_product_id, quantity))

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

            seller_ids = set()

            for item in items:
                cursor.execute("""
                    SELECT SELLER_ID
                    FROM SELLER_PRODUCTS
                    WHERE ID = ?
                """, (item[5],))

                seller = cursor.fetchone()

                if seller is not None:
                    seller_ids.add(seller[0])

            for seller_id in seller_ids:
                cursor.execute("""
                    INSERT INTO ORDER_SELLERS (
                        ORDER_ID,
                        SELLER_ID
                    )
                    VALUES (?, ?)
                """, (order_id, seller_id))


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

                if remaining_quantity != 0:
                    raise Exception("Не удалось полностью зарезервировать товар")

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

    if order is None:
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
        flash("Не удалось обновить статус оплаты", "error")
        return redirect(url_for("catalog.catalog"))

    finally:
        connection.close()

    return redirect(url_for("orders.my_orders"))

@orders_bp.route("/my-orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    selected_status = request.args.get("status", "")
    sort = request.args.get("sort", "date_desc")

    selected_status_id = None

    if selected_status:
        try:
            selected_status_id = int(selected_status)
        except ValueError:
            selected_status = ""

    order_by = "ORDER BY o.CREATED_AT DESC"

    if sort == "date_asc":
        order_by = "ORDER BY o.CREATED_AT ASC"
    elif sort == "status":
        order_by = "ORDER BY o.STATUS_ID, o.CREATED_AT DESC"
    elif sort == "status_desc":
        order_by = "ORDER BY o.STATUS_ID DESC, o.CREATED_AT DESC"
    else:
        sort = "date_desc"

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            ID,
            NAME
            FROM ORDER_STATUSES
            ORDER BY ID
        """)

        statuses = cursor.fetchall()

        query = """
            SELECT
            o.ID,
            o.CREATED_AT,
            o.TOTAL_PRICE,
            os.NAME,
            pm.NAME,
            ps.NAME,
            ds.NAME,
            o.STATUS_ID,
            o.DELIVERY_STATUS_ID,
            (
                SELECT COUNT(*)
                FROM ORDER_SELLERS ords
                WHERE ords.ORDER_ID = o.ID
                  AND ords.HANDED_TO_DELIVERY = 1
            )
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
        """

        params = [session["user_id"]]

        if selected_status_id is not None:
            query += " AND o.STATUS_ID = ?"
            params.append(selected_status_id)

        query += " " + order_by

        cursor.execute(query, params)

        orders = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "my_orders.html",
        orders=orders,
        statuses=statuses,
        selected_status=selected_status,
        sort=sort
    )

@orders_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                STATUS_ID,
                DELIVERY_STATUS_ID
            FROM ORDERS
            WHERE ID = ?
              AND USER_ID = ?
        """, (order_id, session["user_id"]))

        order = cursor.fetchone()

        if order is None:
            flash("Заказ не найден.", "error")
            return redirect(url_for("orders.my_orders"))

        status_id = order[0]
        delivery_status_id = order[1]

        if status_id in (5, 6) or delivery_status_id in (3, 4):
            flash("Этот заказ уже нельзя отменить.", "error")
            return redirect(url_for("orders.my_orders"))

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDER_SELLERS
            WHERE ORDER_ID = ?
              AND HANDED_TO_DELIVERY = 1
        """, (order_id,))

        handed_count = cursor.fetchone()[0]

        if handed_count > 0:
            flash(
                "Продавец уже передал товар в доставку. Отмена невозможна.",
                "error"
            )
            return redirect(url_for("orders.my_orders"))

        cursor.execute("""
            UPDATE ORDERS
            SET STATUS_ID = 6,
                DELIVERY_STATUS_ID = 4
            WHERE ID = ?
              AND USER_ID = ?
              AND STATUS_ID NOT IN (5, 6)
              AND DELIVERY_STATUS_ID NOT IN (3, 4)
        """, (order_id, session["user_id"]))

        if cursor.rowcount != 1:
            connection.rollback()
            flash("Не удалось отменить заказ.", "error")
            return redirect(url_for("orders.my_orders"))

        restore_order_stock(cursor, order_id)

        connection.commit()

        flash("Заказ отменён, товары возвращены на склад.", "success")

    except Exception:
        connection.rollback()
        flash("Не удалось отменить заказ.", "error")

    finally:
        connection.close()

    return redirect(url_for("orders.my_orders"))

@orders_bp.route("/orders/<int:order_id>/confirm-receipt", methods=["POST"])
def confirm_receipt(order_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                PAYMENT_METHOD_ID,
                STATUS_ID,
                DELIVERY_STATUS_ID
            FROM ORDERS
            WHERE ID = ?
              AND USER_ID = ?
        """, (order_id, session["user_id"]))

        order = cursor.fetchone()

        if order is None:
            flash("Заказ не найден.", "error")
            return redirect(url_for("orders.my_orders"))

        payment_method_id = order[0]
        status_id = order[1]
        delivery_status_id = order[2]

        if status_id != 4 or delivery_status_id != 2:
            flash("Этот заказ ещё не передан в доставку.", "error")
            return redirect(url_for("orders.my_orders"))

        cursor.execute("""
            UPDATE ORDERS
            SET
                STATUS_ID = 5,
                DELIVERY_STATUS_ID = 3,
                PAYMENT_STATUS_ID = CASE
                    WHEN PAYMENT_METHOD_ID = 2 THEN 3
                    ELSE PAYMENT_STATUS_ID
                END
            WHERE ID = ?
              AND USER_ID = ?
              AND STATUS_ID = 4
              AND DELIVERY_STATUS_ID = 2
        """, (order_id, session["user_id"]))

        if cursor.rowcount != 1:
            connection.rollback()
            flash("Не удалось подтвердить получение заказа.", "error")
            return redirect(url_for("orders.my_orders"))

        connection.commit()

        flash("Получение заказа подтверждено!", "success")

    except Exception as error:
        connection.rollback()
        flash("Не удалось подтвердить получение заказа.", "error")

    finally:
        connection.close()

    return redirect(url_for("orders.my_orders"))