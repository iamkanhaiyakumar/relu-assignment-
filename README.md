# Nike PH Product Scraper — Relu Consultancy Hiring Challenge

## 📋 Overview
A complete Python-based solution for scraping product data from [Nike Philippines](https://www.nike.com/ph/w), processing it according to specific business rules, performing analytics, and presenting the data through a web dashboard.

## 🏗️ Project Structure
```
relu/
├── scraper/
│   ├── requirements.txt          # Scraper dependencies
│   ├── nike_scraper.py           # Main scraper script
│   ├── upload_to_supabase.py     # Bonus: Upload to Supabase
│   ├── nike_products.csv         # Output: filtered products
│   └── top_20_rating_review.csv  # Output: top 20 ranked
├── webapp/
│   ├── requirements.txt          # Web app dependencies
│   ├── app.py                    # Flask web application
│   ├── templates/
│   │   └── index.html            # Dashboard template
│   └── static/
│       └── style.css             # Premium dark theme
├── Procfile                      # Render deployment
├── render.yaml                   # Render config
└── README.md                     # This file
```

## 🚀 Setup & Usage

### Prerequisites
- Python 3.9+
- pip

### 1. Install Scraper Dependencies
```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the Scraper
```bash
python nike_scraper.py
```
This will:
- Open Nike PH and load all products via infinite scroll
- Visit each product page for detailed extraction
- Print `Total products with empty tagging: X`
- Save `nike_products.csv` (only tagged + discounted products)
- Print Top 10 Most Expensive Products to console
- Generate `top_20_rating_review.csv`

### 3. Run the Web App
```bash
cd webapp
pip install -r requirements.txt
python app.py
```
Visit `http://localhost:5000`

## 📊 Output Files

### nike_products.csv
Contains products with **valid tagging** AND **non-empty discount price** with headers:
`Product_URL, Product_Image_URL, Product_Tagging, Product_Name, Product_Description, Original_Price, Discount_Price, Sizes_Available, Vouchers, Available_Colors, Color_Shown, Style_Code, Rating_Score, Review_Count`

### top_20_rating_review.csv
Top 20 products ranked by Rating Score then Review Count (only products with Review Count > 150).

## 🏆 Bonus Challenge

### Supabase Integration
1. Create a [Supabase](https://supabase.com/) account and project
2. Create a `.env` file in `scraper/`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```
3. Run the SQL from `upload_to_supabase.py` to create the table
4. Upload: `python upload_to_supabase.py`

### Web App Deployment (Render)
1. Push this repo to GitHub
2. Connect to [Render](https://render.com)
3. Create a new Web Service from the repo
4. Set environment variables for Supabase (optional)
5. Deploy!

## 🛠️ Tech Stack
- **Scraping**: Playwright (headless Chromium)
- **Data Processing**: Pandas, CSV
- **Web App**: Flask, Jinja2
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Render
- **Styling**: Custom CSS (Dark theme, responsive)

## 👤 Author
Kanhaiya Kumar — kanhaiyak0104@gmail.com
