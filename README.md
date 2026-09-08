# SmartCart

A self-checkout web app. Customers scan products as they shop, pay from
their phone, and get a QR code receipt to show at the exit instead of
waiting in a line. Store owners get their own login to manage what's for
sale in their store.

## Features

- Customer signup/login
- Browse stores, scan products (camera or manual code entry), cart with
  quantity +/- buttons
- Checkout with a choice of payment method (UPI / Card / Wallet)
- Digital receipt with a QR code
- Exit verification page for staff — scanning the same receipt twice is
  correctly flagged as "already used"
- Separate store owner login — add or remove products from their own store

## Tech stack

- **Backend:** Python (Flask)
- **Database:** SQLite
- **Frontend:** HTML + Jinja2 templates, CSS, a bit of JavaScript for the
  camera scanner (`html5-qrcode`, loaded from a CDN)

## Running it locally

```
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The database file (`smartcart.db`) and a
few demo stores/products are created automatically the first time you
run it.

**Demo product codes** (type these into the scan page instead of using a
camera, if you're testing without a real barcode):

| Code    | Store          | Item        | Price |
|---------|----------------|-------------|-------|
| SC1001  | Big Bazaar     | Milk Packet | ₹25   |
| SC1002  | Big Bazaar     | Bread       | ₹30   |
| SC1003  | Reliance Fresh | Rice 1kg    | ₹65   |
| SC1004  | Reliance Fresh | Eggs (6pc)  | ₹42   |
| SC1005  | Spencer's      | Chips       | ₹50   |
| SC1006  | Phoenix Mall   | Toothpaste  | ₹60   |

To try the store owner side, go to `/owner/signup` and create a new
store — it'll show up in the customer store list right away.

## Project structure

```
smartcart/
├── app.py               # all routes
├── db.py                 # database setup and queries
├── qr_utils.py             # generates the QR code for receipts
├── requirements.txt
├── Procfile                # tells a host like Render how to run this
├── templates/               # one HTML file per page
└── static/style.css          # all the styling
```

