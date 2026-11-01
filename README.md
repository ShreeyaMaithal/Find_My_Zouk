# Find My Zouk — v0.1

## Run
1. Install Python 3.10+
2. In this folder run `pip install -r requirements.txt`
3. Run `streamlit run app.py`

## Included
- `app.py`: interactive preference quiz, weighted product matching, personalised explanations and product links
- `zouk_catalogue_snapshot.csv`: starter catalogue snapshot

## Data and model caveats
The catalogue is a starter snapshot based on Zouk official collection pages indexed during research. It is not a full live-site scrape or a product feed. Product-level images, exact dimensions, laptop compatibility, stock, direct product URLs and detailed features need verification on each product page.

The ranking is a transparent weighted rules-based baseline, not a trained ML model and not a purchase-probability score. Confirm stock and price live before any customer-facing launch.
