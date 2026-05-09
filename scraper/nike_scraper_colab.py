# ============================================================
# Nike PH Product Scraper - Relu Consultancy Hiring Challenge
# ============================================================
# Scrapes all products from https://www.nike.com/ph/w using Nike's
# internal API + Playwright for detail pages. Generates filtered CSVs
# and performs analytics.
#
# Author: Kanhaiya Kumar
# ============================================================

# --- Cell 1: Install Dependencies ---
# !pip install playwright pandas
# !playwright install chromium
# !playwright install-deps

# --- Cell 2: Main Scraper Code ---

import csv
import json
import time
import re
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# --- Configuration ---
BASE_URL = "https://www.nike.com/ph/w"
API_BASE = (
    "https://api.nike.com/discover/product_wall/v1/"
    "marketplace/PH/language/en-GB/"
    "consumerChannelId/d9a5bc42-4b9c-4976-858a-f159cf99c647"
)
PRODUCTS_PER_PAGE = 24
REQUEST_DELAY = 1.0
OUTPUT_DIR = "/content"  # Colab default directory
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "nike_products.csv")
TOP20_CSV = os.path.join(OUTPUT_DIR, "top_20_rating_review.csv")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")

CSV_HEADERS = [
    "Product_URL", "Product_Image_URL", "Product_Tagging",
    "Product_Name", "Product_Description", "Original_Price",
    "Discount_Price", "Sizes_Available", "Vouchers",
    "Available_Colors", "Color_Shown", "Style_Code",
    "Rating_Score", "Review_Count"
]


def parse_price(price_str):
    """Extract numeric value from price string like 'PHP 5,495'."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.]', '', str(price_str).replace(',', ''))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def format_price(amount):
    """Format a number as Philippine Peso price string."""
    if not amount or amount == 0:
        return ""
    return f"PHP {amount:,.2f}"


def save_checkpoint(products, index):
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"products": products, "last_index": index}, f, ensure_ascii=False)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   [RESUME] Resuming from checkpoint (index {data['last_index']})")
            return data["products"], data["last_index"]
        except Exception:
            pass
    return [], 0


def extract_product_from_api(prod):
    """Extract product data from Nike API product object."""
    try:
        prices = prod.get("prices", {}) or prod.get("price", {})
        current_price = prices.get("currentPrice", 0)
        initial_price = prices.get("initialPrice", 0) or prices.get("fullPrice", 0)
        discount_pct = prices.get("discountPercentage", 0)
        is_discounted = discount_pct > 0 or (
            current_price and initial_price and current_price < initial_price
        )

        pdp_url_raw = prod.get("pdpUrl", "")
        if isinstance(pdp_url_raw, dict):
            product_url = pdp_url_raw.get("url", "") or pdp_url_raw.get("path", "")
        else:
            product_url = str(pdp_url_raw)
        if product_url and not product_url.startswith("http"):
            product_url = f"https://www.nike.com{product_url}"

        images = prod.get("colorwayImages", {}) or prod.get("images", {})
        image_url = images.get("portraitURL", "") or images.get("squarishURL", "")

        tags = []
        badge_label = prod.get("badgeLabel")
        if badge_label:
            tags.append(str(badge_label))
        badge_attr = prod.get("badgeAttribute")
        if badge_attr:
            tags.append(str(badge_attr))
        label = prod.get("label", "")
        if label and label not in tags:
            tags.append(label)
        tagging = ", ".join(t for t in tags if t)

        copy = prod.get("copy", {})
        if copy and isinstance(copy, dict):
            title = copy.get("title", "")
            subtitle = copy.get("subTitle", "")
        else:
            title = prod.get("title", "")
            subtitle = prod.get("subtitle", "")

        display_colors = prod.get("displayColors", {})
        if display_colors and isinstance(display_colors, dict):
            color_description = display_colors.get("colorDescription", "")
        else:
            color_description = prod.get("colorDescription", "")

        color_count = prod.get("colorCount", 1)
        available_colors = f"{color_count} Colour{'s' if color_count > 1 else ''}"
        style_code = prod.get("productCode", "") or prod.get("styleColor", "")

        promotions = prod.get("promotions")
        voucher_text = ""
        if promotions and isinstance(promotions, list):
            promo_texts = []
            for promo in promotions:
                if isinstance(promo, dict):
                    msg = promo.get("label", "") or promo.get("message", "")
                    if msg:
                        promo_texts.append(msg)
            voucher_text = "; ".join(promo_texts)

        return {
            "Product_URL": product_url,
            "Product_Image_URL": image_url,
            "Product_Tagging": tagging,
            "Product_Name": title,
            "Product_Description": subtitle,
            "Original_Price": format_price(initial_price) if initial_price else "",
            "Discount_Price": format_price(current_price) if is_discounted else "",
            "Sizes_Available": "",
            "Vouchers": voucher_text,
            "Available_Colors": available_colors,
            "Color_Shown": color_description,
            "Style_Code": style_code,
            "Rating_Score": "",
            "Review_Count": "",
        }
    except Exception as e:
        print(f"   [WARN] Error extracting product: {str(e)[:60]}")
        return None


def fetch_all_product_urls(page):
    """Use Nike's internal API to fetch all product listings."""
    print("\n[STEP 2] Fetching all products from Nike PH API...")

    all_products = []
    seen_urls = set()
    anchor = 0

    print("   Loading initial page data...")
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)

    # Dismiss popups
    try:
        for selector in ['button:has-text("Philippines")', 'button:has-text("Accept")',
                         'button:has-text("Close")', 'dialog button']:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(1)
    except Exception:
        pass

    # Get initial data from __NEXT_DATA__
    next_data_str = page.evaluate("""
    () => {
        const el = document.querySelector('#__NEXT_DATA__');
        return el ? el.textContent : null;
    }
    """)

    total_count = 0
    if next_data_str:
        try:
            next_data = json.loads(next_data_str)
            page_props = next_data.get("props", {}).get("pageProps", {})
            initial_state = page_props.get("initialState", {})
            wall = initial_state.get("Wall", {})
            page_data = wall.get("pageData", {})
            total_count = page_data.get("totalResources", 0)
            print(f"   Total products available: {total_count}")

            product_groupings = wall.get("productGroupings", [])
            for group in product_groupings:
                for prod in group.get("products", []):
                    product = extract_product_from_api(prod)
                    if product and product["Product_URL"] not in seen_urls:
                        seen_urls.add(product["Product_URL"])
                        all_products.append(product)
            anchor = len(all_products)
            print(f"   Got {len(all_products)} products from initial page")
        except json.JSONDecodeError as e:
            print(f"   Error parsing __NEXT_DATA__: {e}")

    # Paginate through remaining products
    if total_count > anchor:
        print(f"\n   Fetching remaining products via API...")
        while anchor < total_count:
            api_url = (f"{API_BASE}?path=%2Fph%2Fw&queryType=PRODUCTS"
                       f"&anchor={anchor}&count={PRODUCTS_PER_PAGE}")
            try:
                response_text = page.evaluate(f"""
                async () => {{
                    try {{
                        const resp = await fetch("{api_url}", {{
                            headers: {{'Accept': 'application/json',
                                      'Nike-Api-Caller-Id': 'com.nike.commerce.nikedotcom.web'}}
                        }});
                        if (!resp.ok) return null;
                        return await resp.text();
                    }} catch(e) {{ return null; }}
                }}
                """)
                if not response_text:
                    time.sleep(3)
                    response_text = page.evaluate(f"""
                    async () => {{
                        try {{ const r = await fetch("{api_url}"); return r.ok ? await r.text() : null; }}
                        catch(e) {{ return null; }}
                    }}
                    """)
                    if not response_text:
                        print(f"   [ERROR] Failed at anchor={anchor}")
                        break

                api_data = json.loads(response_text)
                batch_count = 0
                for group in api_data.get("productGroupings", []):
                    for prod in group.get("products", []):
                        product = extract_product_from_api(prod)
                        if product and product["Product_URL"] not in seen_urls:
                            seen_urls.add(product["Product_URL"])
                            all_products.append(product)
                            batch_count += 1

                anchor += PRODUCTS_PER_PAGE
                pct = min(100, (anchor / total_count) * 100)
                print(f"   [{len(all_products)}/{total_count}] ({pct:.1f}%) Fetched {batch_count} new")
                time.sleep(0.5)
            except Exception as e:
                print(f"   [ERROR] anchor={anchor}: {str(e)[:80]}")
                anchor += PRODUCTS_PER_PAGE
                time.sleep(2)

    print(f"\n   [OK] Total unique products collected: {len(all_products)}")
    return all_products


def scrape_product_details(page, products):
    """Visit each product detail page to get sizes, rating, reviews."""
    print(f"\n[DETAIL] Scraping detail pages for {len(products)} products...")

    completed, start_idx = load_checkpoint()
    if start_idx > 0 and len(completed) > 0:
        for i in range(min(start_idx, len(products))):
            if i < len(completed):
                products[i] = completed[i]

    for i in range(start_idx, len(products)):
        product = products[i]
        url = product.get("Product_URL", "")
        if not url:
            continue

        if (i + 1) % 25 == 0 or i == start_idx:
            pct = ((i + 1) / len(products)) * 100
            print(f"   [{i+1}/{len(products)}] ({pct:.1f}%) {product.get('Product_Name', '')[:50]}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            time.sleep(REQUEST_DELAY)

            detail = page.evaluate("""
            () => {
                const d = {};
                const sizeLabels = document.querySelectorAll(
                    'fieldset#size-grid-container label[for^="sku-"], ' +
                    '[data-testid="product-size-grid-container"] label, ' +
                    'fieldset[id*="size"] label'
                );
                const sizes = [];
                sizeLabels.forEach(lbl => {
                    const t = lbl.textContent.trim();
                    if (t && !sizes.includes(t) && t.length < 15) sizes.push(t);
                });
                d.sizes = sizes.join(', ');

                d.rating = ''; d.reviews = '';
                const reviewsAccordion = document.querySelector(
                    '#pdp-info-accordions__reviews-accordion, details[id*="reviews-accordion"]'
                );
                if (reviewsAccordion) {
                    const summary = reviewsAccordion.querySelector('summary');
                    if (summary) {
                        const h4 = summary.querySelector('h4');
                        if (h4) { const m = h4.textContent.match(/\\((\\d+)\\)/); if (m) d.reviews = m[1]; }
                        const rd = summary.querySelector('[aria-label*="Average Rating"]');
                        if (rd) { const m = rd.getAttribute('aria-label').match(/([\\d.]+)/); if (m) d.rating = m[1]; }
                    }
                }
                if (!d.rating) {
                    const s = document.querySelector('[aria-label*="Average Rating"], [aria-label*="Rated"]');
                    if (s) { const m = (s.getAttribute('aria-label')||'').match(/([\\d.]+)/); if (m) d.rating = m[1]; }
                }
                if (!d.reviews) {
                    const m = document.body.innerText.match(/Reviews?\\s*\\((\\d+)\\)/i);
                    if (m) d.reviews = m[1];
                }

                d.vouchers = '';
                const promos = document.querySelectorAll('.promo-message, [data-testid="promo-message"]');
                const ps = []; promos.forEach(e => { const t = e.textContent.trim(); if (t) ps.push(t); });
                d.vouchers = ps.join('; ');

                d.color_shown = ''; d.style_code = '';
                document.querySelectorAll('li').forEach(li => {
                    const text = li.textContent.trim();
                    if (/^colou?r shown/i.test(text)) d.color_shown = text.split(':').slice(1).join(':').trim();
                    if (/^style/i.test(text) && text.includes(':')) d.style_code = text.split(':').slice(1).join(':').trim();
                });

                d.tagging = '';
                const tags = []; document.querySelectorAll('.pill, [data-testid="product-tag"]').forEach(e => {
                    const t = e.textContent.trim(); if (t && t.length < 50) tags.push(t);
                });
                d.tagging = tags.join(', ');
                return d;
            }
            """)

            if detail:
                if detail.get("sizes"): product["Sizes_Available"] = detail["sizes"]
                if detail.get("rating"): product["Rating_Score"] = detail["rating"]
                if detail.get("reviews"): product["Review_Count"] = detail["reviews"]
                if detail.get("vouchers"): product["Vouchers"] = detail["vouchers"]
                if detail.get("color_shown"): product["Color_Shown"] = detail["color_shown"]
                if detail.get("style_code"): product["Style_Code"] = detail["style_code"]
                if detail.get("tagging") and not product.get("Product_Tagging"):
                    product["Product_Tagging"] = detail["tagging"]

        except PWTimeout:
            print(f"   [TIMEOUT] {url[:60]}...")
        except Exception as e:
            print(f"   [ERROR] {str(e)[:60]}")

        if (i + 1) % 50 == 0:
            save_checkpoint(products[:i+1], i + 1)
            print(f"   [SAVE] Checkpoint at #{i+1}")

    return products


def run_scraper():
    """Main scraper execution."""
    print("=" * 70)
    print("  Nike PH Product Scraper - Relu Consultancy Challenge")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Target:  {BASE_URL}")
    print("=" * 70)

    with sync_playwright() as p:
        print("\n[INIT] Launching browser...")
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
        )

        # STEP 1 & 2: Fetch all products
        main_page = context.new_page()
        all_products = fetch_all_product_urls(main_page)

        # STEP 3: Tagging Rule
        print("\n" + "=" * 70)
        print("[STEP 3] Applying Tagging Rule")
        print("=" * 70)
        empty_tag_count = sum(1 for p in all_products if not p.get("Product_Tagging", "").strip())
        print(f"\n   Total products scraped: {len(all_products)}")
        print(f"   Total products with empty tagging: {empty_tag_count}")

        needs_detail = [p for p in all_products
                        if p.get("Product_Tagging", "").strip() and p.get("Discount_Price", "").strip()]
        print(f"   Products with valid tagging AND discount: {len(needs_detail)}")

        # Scrape details for filtered products only
        detail_page = context.new_page()
        needs_detail = scrape_product_details(detail_page, needs_detail)
        detail_page.close()
        main_page.close()
        browser.close()

    filtered = needs_detail

    # STEP 4: Save CSV
    print("\n" + "=" * 70)
    print("[STEP 4] Saving filtered products to CSV")
    print("=" * 70)
    print(f"   Products with valid tagging AND discount price: {len(filtered)}")

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for product in filtered:
            writer.writerow({k: product.get(k, "") for k in CSV_HEADERS})
    print(f"   [OK] Saved to: {OUTPUT_CSV}")

    # STEP 5A: Top 10 Most Expensive
    print("\n" + "=" * 70)
    print("[STEP 5A] Top 10 Most Expensive Products (by Discount Price)")
    print("=" * 70)
    priced = [p for p in filtered if parse_price(p.get("Discount_Price", "")) > 0]
    priced.sort(key=lambda x: parse_price(x.get("Discount_Price", "")), reverse=True)
    top10 = priced[:10]
    print(f"\n{'#':<4} {'Product Name':<50} {'Price':<18}")
    print("-" * 75)
    for idx, p in enumerate(top10, 1):
        print(f"{idx:<4} {p.get('Product_Name', '')[:48]:<50} {p.get('Discount_Price', ''):<18}")

    # STEP 5B: Top 20 Rating & Review Ranking
    print("\n" + "=" * 70)
    print("[STEP 5B] Top 20 Rating & Review Ranking")
    print("=" * 70)
    eligible = []
    for p in filtered:
        try: rev = int(re.sub(r'[^\d]', '', p.get("Review_Count", "") or "0"))
        except ValueError: rev = 0
        try: rating = float(p.get("Rating_Score", "") or "0")
        except ValueError: rating = 0.0
        if rev > 150:
            eligible.append({**p, "_r": rating, "_v": rev})

    print(f"   Products with Review Count > 150: {len(eligible)}")
    eligible.sort(key=lambda x: (-x["_r"], -x["_v"]))

    ranked, cur_rank = [], 1
    for i, p in enumerate(eligible):
        if i > 0:
            prev = eligible[i-1]
            if not (p["_r"] == prev["_r"] and p["_v"] == prev["_v"]):
                cur_rank = i + 1
        ranked.append({**p, "Rank": cur_rank})
    top20 = ranked[:20]

    top20_headers = ["Rank"] + CSV_HEADERS
    with open(TOP20_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=top20_headers, extrasaction='ignore')
        writer.writeheader()
        for p in top20:
            writer.writerow({k: p.get(k, '') for k in top20_headers})
    print(f"   [OK] Saved to: {TOP20_CSV}")
    for p in top20:
        print(f"   Rank {p['Rank']}: {p.get('Product_Name','')[:45]} | Rating: {p.get('Rating_Score','')} | Reviews: {p.get('Review_Count','')}")

    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print("\n" + "=" * 70)
    print("  SCRAPING COMPLETE!")
    print(f"  Total products scraped:    {len(all_products)}")
    print(f"  Empty tagging count:       {empty_tag_count}")
    print(f"  Filtered products (CSV):   {len(filtered)}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


# --- Cell 3: Run the Scraper ---
run_scraper()
