from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import math

app = Flask(__name__)
app.secret_key = "farmer-market-demo-secret"

DATABASE = "marketplace.db"

# Demo admin password
ADMIN_PASSWORD = "admin123"


# =========================================================
# DATABASE
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(conn, table, column, definition):
    columns = [row["name"] for row in conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()]

    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def create_database():

    conn = get_db_connection()

    # ---------------- FARMERS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            crops TEXT,
            verified INTEGER DEFAULT 0
        )
    """)

    # ---------------- PRODUCTS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            location TEXT NOT NULL,
            image TEXT DEFAULT ""
        )
    """)

    # Add farmer_id to old products table if it doesn't exist
    add_column_if_missing(conn, "products", "farmer_id", "INTEGER")
    add_column_if_missing(conn, "products", "image", 'TEXT DEFAULT ""')

    # ---------------- ORDERS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            buyer_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            location TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # ---------------- RATINGS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            buyer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review TEXT,
            FOREIGN KEY(farmer_id) REFERENCES farmers(id)
        )
    """)

    # ---------------- REPORTS ----------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            buyer_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()



# =========================================================
# AI MARKET INTELLIGENCE
# =========================================================

# Demo reference prices. For a real deployment, replace these
# with live mandi/eNAM/market data or a trained ML model.
MARKET_PRICES = {
    "tomato": 28, "potato": 24, "onion": 32, "carrot": 40,
    "cabbage": 26, "cauliflower": 38, "brinjal": 35,
    "spinach": 30, "beans": 55, "capsicum": 60, "chilli": 50,
    "banana": 45, "apple": 120, "mango": 80
}

HIGH_DEMAND = {
    "tomato", "onion", "potato", "carrot", "banana", "mango"
}


def get_market_price(product_name):
    name = product_name.lower().strip()
    for key, price in MARKET_PRICES.items():
        if key in name:
            return price
    return 35


def get_market_image(product_name):
    name = product_name.lower().strip()
    image_map = {
        "tomato": "tomato.jpg", "potato": "potato.jpg",
        "onion": "onion.jpg", "carrot": "carrot.jpg",
        "cabbage": "cabbage.jpg", "cauliflower": "cauliflower.jpg",
        "brinjal": "brinjal.jpg", "spinach": "spinach.jpg",
        "beans": "beans.jpg", "capsicum": "capsicum.jpg",
        "chilli": "chilli.jpg", "banana": "banana.jpg",
        "apple": "apple.jpg", "mango": "mango.jpg"
    }
    for key, filename in image_map.items():
        if key in name:
            return filename
    return "vegetable-default.jpg"


def fair_price_recommendation(product_name, quantity, location=""):
    base = get_market_price(product_name)
    demand = "High" if any(x in product_name.lower() for x in HIGH_DEMAND) else "Medium"

    demand_factor = 1.08 if demand == "High" else 1.03
    supply_factor = 0.95 if quantity >= 500 else (0.98 if quantity >= 200 else 1.00)

    recommended = base * demand_factor * supply_factor
    low = round(recommended * 0.95)
    high = round(recommended * 1.05)

    return {
        "base_price": base,
        "recommended": round(recommended),
        "range": f"₹{low}–₹{high}/kg",
        "demand": demand,
        "trend": "Increasing ↗" if demand == "High" else "Stable →",
        "advice": (
            f"Demand for {product_name} is {demand.lower()}. "
            f"A suitable selling price is around ₹{round(recommended)} per kilogram."
        )
    }


def add_ai_data(products):
    result = []
    for product in products:
        item = dict(product)
        item["ai"] = fair_price_recommendation(
            item["name"], item["quantity"], item["location"]
        )
        item["image"] = item.get("image") or get_market_image(item["name"])
        result.append(item)
    return result


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# FARMER PAGE
# =========================================================

@app.route("/farmer")
def farmer():

    conn = get_db_connection()

    farmers = conn.execute("""
        SELECT * FROM farmers
        ORDER BY id DESC
    """).fetchall()

    products = conn.execute("""
        SELECT products.*, farmers.name AS farmer_name,
               farmers.verified
        FROM products
        LEFT JOIN farmers
        ON products.farmer_id = farmers.id
        ORDER BY products.id DESC
    """).fetchall()

    conn.close()
    products = add_ai_data(products)

    return render_template(
        "farmer.html",
        farmers=farmers,
        products=products
    )


# =========================================================
# FARMER REGISTRATION
# =========================================================

@app.route("/register_farmer", methods=["POST"])
def register_farmer():

    name = request.form["name"]
    phone = request.form["phone"]
    location = request.form["location"]
    crops = request.form.get("crops", "")

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO farmers
        (name, phone, location, crops, verified)
        VALUES (?, ?, ?, ?, 0)
    """, (
        name,
        phone,
        location,
        crops
    ))

    farmer_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    session["farmer_id"] = farmer_id

    return """
    <h1>✅ Registration Submitted</h1>

    <p>Your farmer account is waiting for admin verification.</p>

    <p>You can add products after your account is approved.</p>

    <a href="/farmer">Go back to Farmer Page</a>
    """


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route("/add_product", methods=["POST"])
def add_product():

    farmer_id = session.get("farmer_id")
    if not farmer_id:
        return """
        <h1>🔐 Farmer Login Required</h1>
        <p>Please register/login before adding a product.</p>
        <a href="/farmer">Go to Farmer Page</a>
        """

    name = request.form["name"]
    quantity = float(request.form["quantity"])
    price = float(request.form["price"])
    location = request.form["location"]

    conn = get_db_connection()

    # Check whether farmer exists and is verified
    farmer = conn.execute("""
        SELECT * FROM farmers
        WHERE id = ?
    """, (farmer_id,)).fetchone()

    if farmer is None:
        conn.close()

        return """
        <h1>❌ Farmer Not Found</h1>
        <a href="/farmer">Go back</a>
        """

    if farmer["verified"] != 1:
        conn.close()

        return """
        <h1>⏳ Verification Required</h1>

        <p>This farmer has not been verified by the admin.</p>

        <p>You cannot add products until verification is completed.</p>

        <a href="/farmer">Go back</a>
        """

    # Add product
    conn.execute("""
        INSERT INTO products
        (name, quantity, price, location, farmer_id, image)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        quantity,
        price,
        location,
        farmer_id,
        request.form.get("image", "").strip() or get_market_image(name)
    ))

    conn.commit()
    conn.close()

    return redirect("/farmer")


# =========================================================
# ADMIN PAGE
# =========================================================

@app.route("/admin")
def admin():

    password = request.args.get("password", "")

    if password != ADMIN_PASSWORD:
        return """
        <h1>🔐 Admin Login</h1>

        <form method="GET">

            <input
                type="password"
                name="password"
                placeholder="Admin Password"
                required
            >

            <button type="submit">
                Login
            </button>

        </form>

        <p>Demo password: admin123</p>
        """

    conn = get_db_connection()

    farmers = conn.execute("""
        SELECT * FROM farmers
        ORDER BY verified ASC, id DESC
    """).fetchall()

    reports = conn.execute("""
        SELECT
            reports.*,
            products.name AS product_name
        FROM reports
        JOIN products
        ON reports.product_id = products.id
        ORDER BY reports.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        farmers=farmers,
        reports=reports,
        password=password
    )


# =========================================================
# APPROVE FARMER
# =========================================================

@app.route("/approve_farmer/<int:farmer_id>", methods=["POST"])
def approve_farmer(farmer_id):

    password = request.form["password"]

    if password != ADMIN_PASSWORD:
        return "Unauthorized"

    conn = get_db_connection()

    conn.execute("""
        UPDATE farmers
        SET verified = 1
        WHERE id = ?
    """, (farmer_id,))

    conn.commit()
    conn.close()

    return redirect("/admin?password=" + password)


# =========================================================
# REJECT FARMER
# =========================================================

@app.route("/reject_farmer/<int:farmer_id>", methods=["POST"])
def reject_farmer(farmer_id):

    password = request.form["password"]

    if password != ADMIN_PASSWORD:
        return "Unauthorized"

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM farmers
        WHERE id = ?
    """, (farmer_id,))

    conn.commit()
    conn.close()

    return redirect("/admin?password=" + password)


# =========================================================
# BUYER PAGE
# =========================================================

@app.route("/buyer")
def buyer():

    search = request.args.get("search", "")

    conn = get_db_connection()

    if search:

        products = conn.execute("""
            SELECT
                products.*,
                farmers.name AS farmer_name,
                farmers.verified
            FROM products

            JOIN farmers
            ON products.farmer_id = farmers.id

            WHERE products.name LIKE ?
            AND farmers.verified = 1
            AND products.quantity > 0

            ORDER BY products.id DESC
        """, (
            "%" + search + "%",
        )).fetchall()

    else:

        products = conn.execute("""
            SELECT
                products.*,
                farmers.name AS farmer_name,
                farmers.verified
            FROM products

            JOIN farmers
            ON products.farmer_id = farmers.id

            WHERE farmers.verified = 1
            AND products.quantity > 0

            ORDER BY products.id DESC
        """).fetchall()

    conn.close()
    products = add_ai_data(products)

    return render_template(
        "buyer.html",
        products=products,
        search=search
    )


# =========================================================
# PLACE ORDER
# =========================================================

@app.route("/order", methods=["POST"])
def order():

    product_id = request.form["product_id"]
    buyer_name = request.form["buyer_name"]

    requested_quantity = float(
        request.form["quantity"]
    )

    location = request.form["location"]

    latitude = float(
        request.form["latitude"]
    )

    longitude = float(
        request.form["longitude"]
    )

    conn = get_db_connection()

    # Get product + farmer verification
    product = conn.execute("""
        SELECT
            products.*,
            farmers.verified
        FROM products

        JOIN farmers
        ON products.farmer_id = farmers.id

        WHERE products.id = ?
    """, (product_id,)).fetchone()

    if product is None:
        conn.close()

        return """
        <h1>❌ Product Not Found</h1>
        <a href="/buyer">Go back</a>
        """

    # Check farmer verification
    if product["verified"] != 1:
        conn.close()

        return """
        <h1>❌ Farmer Not Verified</h1>

        <p>This product cannot be ordered because the farmer is not verified.</p>

        <a href="/buyer">Go back</a>
        """

    # Check quantity
    if requested_quantity <= 0:
        conn.close()

        return """
        <h1>❌ Invalid Quantity</h1>

        <a href="/buyer">Go back</a>
        """

    if requested_quantity > product["quantity"]:
        available = product["quantity"]

        conn.close()

        return f"""
        <h1>❌ Not Enough Quantity</h1>

        <p>Only {available} kg is available.</p>

        <a href="/buyer">Go back</a>
        """

    # Add order
    conn.execute("""
        INSERT INTO orders
        (
            product_id,
            buyer_name,
            quantity,
            location,
            latitude,
            longitude
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        buyer_name,
        requested_quantity,
        location,
        latitude,
        longitude
    ))

    # Reduce product quantity
    new_quantity = product["quantity"] - requested_quantity

    conn.execute("""
        UPDATE products
        SET quantity = ?
        WHERE id = ?
    """, (
        new_quantity,
        product_id
    ))

    conn.commit()
    conn.close()

    return """
    <h1>✅ Order Placed Successfully!</h1>

    <p>Your order has been recorded.</p>

    <p>The available product quantity has been updated.</p>

    <a href="/buyer">Go back to Buyer Page</a>

    <br><br>

    <a href="/route">View Delivery Route</a>
    """


# =========================================================
# RATE FARMER
# =========================================================

@app.route("/rate_farmer", methods=["POST"])
def rate_farmer():

    farmer_id = request.form["farmer_id"]
    buyer_name = request.form["buyer_name"]
    rating = int(request.form["rating"])
    review = request.form.get("review", "")

    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5."

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO ratings
        (
            farmer_id,
            buyer_name,
            rating,
            review
        )
        VALUES (?, ?, ?, ?)
    """, (
        farmer_id,
        buyer_name,
        rating,
        review
    ))

    conn.commit()
    conn.close()

    return """
    <h1>⭐ Thank You!</h1>

    <p>Your rating has been submitted.</p>

    <a href="/buyer">Go back to Buyer Page</a>
    """


# =========================================================
# REPORT PRODUCT
# =========================================================

@app.route("/report_product", methods=["POST"])
def report_product():

    product_id = request.form["product_id"]
    buyer_name = request.form["buyer_name"]
    reason = request.form["reason"]

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO reports
        (
            product_id,
            buyer_name,
            reason
        )
        VALUES (?, ?, ?)
    """, (
        product_id,
        buyer_name,
        reason
    ))

    conn.commit()
    conn.close()

    return """
    <h1>🚨 Report Submitted</h1>

    <p>Thank you. The admin will review this product.</p>

    <a href="/buyer">Go back to Buyer Page</a>
    """


# =========================================================
# ROUTE OPTIMIZATION
# =========================================================

def calculate_distance(lat1, lon1, lat2, lon2):

    # Convert degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    # Earth radius in km
    radius = 6371

    return radius * c


def optimize_route(start_lat, start_lon, orders):

    remaining = list(orders)

    current_lat = start_lat
    current_lon = start_lon

    route = []
    total_distance = 0

    while remaining:

        nearest_order = None
        nearest_distance = float("inf")

        for order_item in remaining:

            distance = calculate_distance(
                current_lat,
                current_lon,
                order_item["latitude"],
                order_item["longitude"]
            )

            if distance < nearest_distance:

                nearest_distance = distance
                nearest_order = order_item

        route.append({
            "buyer_name": nearest_order["buyer_name"],
            "location": nearest_order["location"],
            "distance": round(nearest_distance, 2)
        })

        total_distance += nearest_distance

        current_lat = nearest_order["latitude"]
        current_lon = nearest_order["longitude"]

        remaining.remove(nearest_order)

    return route, round(total_distance, 2)


# =========================================================
# ROUTE PAGE
# =========================================================

@app.route("/route")
def route():

    conn = get_db_connection()

    orders = conn.execute("""
        SELECT
            orders.id,
            orders.buyer_name,
            orders.quantity,
            orders.location,
            orders.latitude,
            orders.longitude,
            products.name
        FROM orders

        JOIN products
        ON orders.product_id = products.id

        ORDER BY orders.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "route.html",
        orders=orders,
        route=None,
        total_distance=None
    )


# =========================================================
# OPTIMIZE ROUTE
# =========================================================

@app.route("/optimize_route", methods=["POST"])
def optimize_route_page():

    start_lat = float(
        request.form["start_lat"]
    )

    start_lon = float(
        request.form["start_lon"]
    )

    conn = get_db_connection()

    orders = conn.execute("""
        SELECT
            orders.id,
            orders.buyer_name,
            orders.quantity,
            orders.location,
            orders.latitude,
            orders.longitude,
            products.name
        FROM orders

        JOIN products
        ON orders.product_id = products.id
    """).fetchall()

    conn.close()

    route_result, total_distance = optimize_route(
        start_lat,
        start_lon,
        orders
    )

    return render_template(
        "route.html",
        orders=orders,
        route=route_result,
        total_distance=total_distance
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)