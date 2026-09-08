import uuid
import json
from datetime import datetime

from flask import Flask, request, redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

import db
import qr_utils

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deploying"

# runs once when the app starts, whether that's "python app.py" locally
# or gunicorn on a real server
db.init_db()


def cart_total(cart):
    return sum(item["price"] * item["qty"] for item in cart.values())


@app.route("/")
def home():
    return render_template("home.html")


# ---------------- customer auth ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Please fill in both fields."
        elif db.get_customer(username):
            error = "That username is already taken."
        else:
            db.create_customer(username, generate_password_hash(password))
            session["user"] = username
            return redirect(url_for("stores"))

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        row = db.get_customer(username)
        if row and check_password_hash(row["password_hash"], password):
            session["user"] = username
            return redirect(url_for("stores"))
        error = "Wrong username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("cart", None)
    return redirect(url_for("home"))


# ---------------- store owner auth ----------------

@app.route("/owner/signup", methods=["GET", "POST"])
def owner_signup():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        store_name = request.form.get("store_name", "").strip()

        if not username or not password or not store_name:
            error = "Please fill in all fields."
        elif db.get_owner(username):
            error = "That owner username is already taken."
        elif db.store_exists(store_name):
            error = "A store with that name already exists."
        else:
            db.create_owner(username, generate_password_hash(password), store_name)
            db.create_store(store_name)
            session["owner"] = username
            return redirect(url_for("owner_dashboard"))

    return render_template("owner_signup.html", error=error)


@app.route("/owner/login", methods=["GET", "POST"])
def owner_login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        row = db.get_owner(username)
        if row and check_password_hash(row["password_hash"], password):
            session["owner"] = username
            return redirect(url_for("owner_dashboard"))
        error = "Wrong owner username or password."

    return render_template("owner_login.html", error=error)


@app.route("/owner/logout")
def owner_logout():
    session.pop("owner", None)
    return redirect(url_for("home"))


@app.route("/owner/dashboard", methods=["GET", "POST"])
def owner_dashboard():
    if "owner" not in session:
        return redirect(url_for("owner_login"))

    owner_row = db.get_owner(session["owner"])
    store_name = owner_row["store_name"]

    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "")
        code = request.form.get("code", "").strip()

        if name and price and code:
            try:
                db.add_product(store_name, name, float(price), code)
                message = f"Added {name} to {store_name}."
            except Exception:
                # most likely the UNIQUE(store_name, code) constraint in db.py
                message = "That product code is already used in your store."
        else:
            message = "Please fill in all fields."

    products = db.get_products_for_store(store_name)
    return render_template(
        "owner_dashboard.html", store_name=store_name, products=products, message=message
    )


@app.route("/owner/dashboard/delete/<int:product_id>", methods=["POST"])
def owner_delete_product(product_id):
    if "owner" not in session:
        return redirect(url_for("owner_login"))
    db.delete_product(product_id)
    return redirect(url_for("owner_dashboard"))


# ---------------- shopping flow ----------------

@app.route("/stores")
def stores():
    if "user" not in session:
        return redirect(url_for("login"))
    store_list = db.get_all_stores()
    return render_template("stores.html", store_list=store_list)


@app.route("/store/<store_name>")
def store_page(store_name):
    if "user" not in session:
        return redirect(url_for("login"))
    products = db.get_products_for_store(store_name)
    return render_template("store.html", store_name=store_name, products=products)


@app.route("/store/<store_name>/scan", methods=["GET", "POST"])
def scan_page(store_name):
    if "user" not in session:
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        typed_code = request.form.get("code", "").strip()
        found = db.find_product(store_name, typed_code)

        if found:
            cart = session.get("cart", {})
            if typed_code in cart:
                cart[typed_code]["qty"] += 1
            else:
                cart[typed_code] = {
                    "name": found["name"],
                    "price": found["price"],
                    "code": typed_code,
                    "qty": 1,
                }
            session["cart"] = cart
            message = f"Added: {found['name']} — ₹{found['price']}"
        else:
            message = f"No product found for code '{typed_code}'"

    return render_template("scan.html", store_name=store_name, message=message)


@app.route("/store/<store_name>/cart")
def cart_page(store_name):
    if "user" not in session:
        return redirect(url_for("login"))
    cart = session.get("cart", {})
    return render_template(
        "cart.html", store_name=store_name, cart=cart, total=cart_total(cart)
    )


@app.route("/store/<store_name>/cart/increase", methods=["POST"])
def cart_increase(store_name):
    code = request.form.get("code")
    cart = session.get("cart", {})
    if code in cart:
        cart[code]["qty"] += 1
    session["cart"] = cart
    return redirect(url_for("cart_page", store_name=store_name))


@app.route("/store/<store_name>/cart/decrease", methods=["POST"])
def cart_decrease(store_name):
    code = request.form.get("code")
    cart = session.get("cart", {})
    if code in cart:
        cart[code]["qty"] -= 1
        if cart[code]["qty"] <= 0:
            del cart[code]
    session["cart"] = cart
    return redirect(url_for("cart_page", store_name=store_name))


@app.route("/store/<store_name>/checkout")
def checkout_page(store_name):
    if "user" not in session:
        return redirect(url_for("login"))
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("cart_page", store_name=store_name))
    return render_template(
        "checkout.html", store_name=store_name, cart=cart, total=cart_total(cart)
    )


@app.route("/store/<store_name>/pay", methods=["POST"])
def pay(store_name):
    if "user" not in session:
        return redirect(url_for("login"))

    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("cart_page", store_name=store_name))

    payment_method = request.form.get("payment_method", "UPI")
    total = cart_total(cart)
    receipt_id = uuid.uuid4().hex[:8].upper()

    db.save_receipt(
        receipt_id,
        store_name,
        session["user"],
        json.dumps(list(cart.values())),
        total,
        payment_method,
        datetime.now().isoformat(),
    )

    session["cart"] = {}
    return redirect(url_for("receipt_page", receipt_id=receipt_id))


@app.route("/receipt/<receipt_id>")
def receipt_page(receipt_id):
    row = db.get_receipt(receipt_id)
    if not row:
        return "Receipt not found", 404

    items = json.loads(row["items_json"])
    qr_b64 = qr_utils.make_qr_base64(receipt_id)

    return render_template(
        "receipt.html",
        receipt_id=row["receipt_id"],
        store_name=row["store_name"],
        items=items,
        total=row["total"],
        payment_method=row["payment_method"],
        qr_b64=qr_b64,
    )


# ---------------- exit verification (store staff) ----------------

@app.route("/verify", methods=["GET", "POST"])
def verify():
    result = None
    if request.method == "POST":
        receipt_id = request.form.get("receipt_id", "").strip().upper()
        row = db.get_receipt(receipt_id)

        if row:
            already_used = row["status"] == "verified"
            if not already_used:
                db.mark_receipt_verified(receipt_id)
            result = {
                "found": True,
                "already_used": already_used,
                "receipt_id": row["receipt_id"],
                "total": row["total"],
            }
        else:
            result = {"found": False}

    return render_template("verify.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)
