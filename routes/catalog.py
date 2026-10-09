from flask import Blueprint, render_template
from db import get_connection

catalog_bp = Blueprint("catalog", __name__)

@catalog_bp.route("/catalog")
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
