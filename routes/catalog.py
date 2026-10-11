from flask import Blueprint, render_template, request
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
