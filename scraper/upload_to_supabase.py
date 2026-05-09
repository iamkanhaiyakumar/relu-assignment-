"""
Upload scraped Nike PH product data to Supabase.
Reads from nike_products.csv and uploads to a Supabase table.

Usage:
  1. Set environment variables SUPABASE_URL and SUPABASE_KEY
     (or create a .env file in the scraper directory)
  2. Run: python upload_to_supabase.py
"""

import os
import csv
import sys
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
CSV_FILE = os.path.join(os.path.dirname(__file__), "nike_products.csv")
TABLE_NAME = "nike_products"


def create_table_sql():
    """Print SQL to create the table in Supabase."""
    sql = f"""
-- Run this SQL in Supabase SQL Editor to create the table:
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id BIGSERIAL PRIMARY KEY,
    product_url TEXT,
    product_image_url TEXT,
    product_tagging TEXT,
    product_name TEXT,
    product_description TEXT,
    original_price TEXT,
    discount_price TEXT,
    sizes_available TEXT,
    vouchers TEXT,
    available_colors TEXT,
    color_shown TEXT,
    style_code TEXT,
    rating_score TEXT,
    review_count TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
    print(sql)
    return sql


def upload():
    """Upload CSV data to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set.")
        print("   Create a .env file with:")
        print("   SUPABASE_URL=https://your-project.supabase.co")
        print("   SUPABASE_KEY=your-anon-key")
        print("\n   Or set them as environment variables.")
        print("\n📋 Here's the SQL to create the table:")
        create_table_sql()
        sys.exit(1)

    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} not found. Run nike_scraper.py first.")
        sys.exit(1)

    from supabase import create_client

    print(f"🔌 Connecting to Supabase: {SUPABASE_URL}")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Read CSV
    print(f"📖 Reading {CSV_FILE}...")
    rows = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "product_url": row.get("Product_URL", ""),
                "product_image_url": row.get("Product_Image_URL", ""),
                "product_tagging": row.get("Product_Tagging", ""),
                "product_name": row.get("Product_Name", ""),
                "product_description": row.get("Product_Description", ""),
                "original_price": row.get("Original_Price", ""),
                "discount_price": row.get("Discount_Price", ""),
                "sizes_available": row.get("Sizes_Available", ""),
                "vouchers": row.get("Vouchers", ""),
                "available_colors": row.get("Available_Colors", ""),
                "color_shown": row.get("Color_Shown", ""),
                "style_code": row.get("Style_Code", ""),
                "rating_score": row.get("Rating_Score", ""),
                "review_count": row.get("Review_Count", ""),
            })

    print(f"   Found {len(rows)} products to upload")

    # Upload in batches of 500
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            supabase.table(TABLE_NAME).insert(batch).execute()
            print(f"   ✅ Uploaded batch {i // batch_size + 1} "
                  f"({len(batch)} rows)")
        except Exception as e:
            print(f"   ❌ Error uploading batch: {e}")

    print(f"\n✅ Upload complete! {len(rows)} products in Supabase.")


if __name__ == "__main__":
    upload()
