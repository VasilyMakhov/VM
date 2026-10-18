from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection 

favorites_bp = Blueprint("favorites", __name__)

@favorites_bp.route("/favorites/add/<int:product_id>", methods=["POST"])
def favorites_add(product_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT ID
            FROM FAVORITES
            WHERE USER_ID = ?
            AND PRODUCT_ID = ?
        """, (session["user_id"], product_id))

        favorites_item = cursor.fetchone()

        if favorites_item is None:
            cursor.execute("""
                INSERT INTO FAVORITES
                (USER_ID, PRODUCT_ID)
                VALUES (?, ?)
            """, (session["user_id"], product_id))

            connection.commit()
        else:
            flash("Товар уже в избранном", "error")
            return redirect(url_for("catalog.product", product_id=product_id))

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
    flash("Успешно добавлено! Товар в избранном", "success")
    return redirect(url_for("catalog.product", product_id=product_id))


@favorites_bp.route("/favorites/remove/<int:product_id>", methods=["POST"])
def favorites_remove(product_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT ID
            FROM FAVORITES
            WHERE USER_ID = ?
            AND PRODUCT_ID = ?
        """, (session["user_id"], product_id))

        favorites_item = cursor.fetchone()

        if favorites_item is not None:
            cursor.execute("""
                DELETE FROM FAVORITES
                WHERE USER_ID = ?
                AND PRODUCT_ID = ?
            """, (session["user_id"], product_id))
        else:
            flash("Товара нет в избранном", "error")
            return redirect(url_for("catalog.product", product_id=product_id))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
    flash("Успешно удалено из избранного!", "success")
    return redirect(url_for("catalog.product", product_id=product_id))

@favorites_bp.route("/favorites")
def favorites():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
            p.ID,
            p.NAME,
            p.IMAGE_URL,
            p.PRICE
            FROM PRODUCTS p
            JOIN FAVORITES F
            ON f.PRODUCT_ID = p.ID
            WHERE f.USER_ID = ?
        """, (session["user_id"],))

        products = cursor.fetchall()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return render_template("favorites.html", products=products)

