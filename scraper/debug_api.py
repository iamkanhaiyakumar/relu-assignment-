"""Quick check of CSV output quality."""
import csv, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('scraper/nike_products.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")
print(f"Headers: {list(rows[0].keys())}")

# Check field fill rates
fields = list(rows[0].keys())
for field in fields:
    filled = sum(1 for r in rows if r.get(field, '').strip())
    pct = (filled / len(rows)) * 100
    print(f"  {field:25s}: {filled:4d}/{len(rows)} ({pct:.0f}%)")

print("\n--- Sample Product ---")
sample = rows[0]
for k, v in sample.items():
    print(f"  {k}: {v[:80] if v else '(empty)'}")
