from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection

moderator_bp = Blueprint("moderator", __name__, url_prefix="/moderator")

def check_moderator_access():
    if "user_id" not in session:
        return False
    if session.get("user_role") != 3:
        return False
    return True
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