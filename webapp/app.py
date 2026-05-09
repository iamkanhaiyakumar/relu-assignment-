"""
Nike PH Products Web App — Flask Application
Displays scraped product data in a premium, searchable table.
Connects to Supabase if configured, otherwise reads from CSV.
"""

import os
import csv
import re
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── Configuration ───────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "scraper", "nike_products.csv")
TOP20_CSV = os.path.join(os.path.dirname(__file__), "..", "scraper", "top_20_rating_review.csv")


def parse_price(price_str):
    """Extract numeric value from price string."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.]', '', str(price_str).replace(',', ''))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_products_csv():
    """Load products from CSV file."""
    products = []
    if not os.path.exists(CSV_PATH):
        return products
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(dict(row))
    return products


def load_products_supabase():
    """Load products from Supabase."""
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table("nike_products").select("*").execute()
        return result.data or []
    except Exception as e:
        print(f"Supabase error: {e}, falling back to CSV")
        return load_products_csv()


def get_products():
    """Load products from Supabase or CSV."""
    if SUPABASE_URL and SUPABASE_KEY:
        return load_products_supabase()
    return load_products_csv()


def load_top20():
    """Load top 20 from CSV."""
    products = []
    if not os.path.exists(TOP20_CSV):
        return products
    with open(TOP20_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(dict(row))
    return products


@app.route("/")
def index():
    """Main page — display all products."""
    products = get_products()
    top20 = load_top20()

    # Calculate top 10 most expensive
    priced = [p for p in products if parse_price(p.get("Discount_Price", "")) > 0]
    priced.sort(key=lambda x: parse_price(x.get("Discount_Price", "")), reverse=True)
    top10 = priced[:10]

    # Stats
    stats = {
        "total": len(products),
        "avg_price": 0,
        "max_price": 0,
        "with_rating": sum(1 for p in products if p.get("Rating_Score")),
    }
    if priced:
        prices = [parse_price(p.get("Discount_Price", "")) for p in priced]
        stats["avg_price"] = f"₱{sum(prices) / len(prices):,.0f}"
        stats["max_price"] = f"₱{max(prices):,.0f}"

    return render_template("index.html",
                           products=products,
                           top10=top10,
                           top20=top20,
                           stats=stats)


@app.route("/api/products")
def api_products():
    """API endpoint for AJAX loading."""
    products = get_products()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search = request.args.get("search", "").lower()

    if search:
        products = [
            p for p in products
            if search in p.get("Product_Name", "").lower() or
               search in p.get("Product_Tagging", "").lower() or
               search in p.get("Product_Description", "").lower()
        ]

    total = len(products)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = products[start:end]

    return jsonify({
        "products": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
