from flask import Flask, render_template
from firebird.driver import connect

app = Flask(__name__)

def get_connection():
    return connect(
    database="/db/wb_vasa.fdb",
    user="SYSDBA",
    password="masterkey"
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/catalog")
def catalog():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT
        p.ID,
        p.NAME,
        p.IMAGE_URL,
        sp.PRICE
    FROM PRODUCTS p
    JOIN SELLER_PRODUCTS sp
        ON sp.PRODUCT_ID = p.ID
    """)

    products = cursor.fetchall()
    connection.close()

    return render_template("catalog.html", products=products)

@app.route("/product/<int:product_id>")
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
            sp.PRICE,
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

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=1, port=2911)