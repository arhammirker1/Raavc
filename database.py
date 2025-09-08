import json
import psycopg2
from psycopg2.extras import execute_batch

# --- Update these with your TimescaleDB credentials ---
DB_HOST = "localhost"    # SSH tunnel forwards to server
DB_PORT = 5432
DB_NAME = "property_transaction_db"
DB_USER = "arham"
DB_PASS = "N12345123-nn"

def connect_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def load_json(filepath="save.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_num(value):
    try:
        if value is None:
            return 0
        return float(value)
    except (TypeError, ValueError):
        return 0

def parse_transaction(transaction):
    """Convert a raw transaction JSON into DB-ready dict using JSON's UniqueKey."""
    city = transaction.get("City")
    neighborhood = transaction.get("District")
    property_type = transaction.get("RequestTypeName")
    area_sqm = safe_num(transaction.get("TransactionArea") or transaction.get("Area"))
    total_price = safe_num(transaction.get("Amount"))
    price_per_sqm = safe_num(transaction.get("PricePerMeter", 0))
    if price_per_sqm == 0 and area_sqm > 0 and total_price > 0:
        price_per_sqm = total_price / area_sqm

    sale_date = transaction.get("CreatedOn")
    if sale_date:
        sale_date = sale_date.split("T")[0]

    street_width = sum([
        safe_num(transaction.get("NorthLimitLength")),
        safe_num(transaction.get("SouthLimitLength")),
        safe_num(transaction.get("EastLimitLength")),
        safe_num(transaction.get("WestLimitLength"))
    ])

    number_of_streets = transaction.get("StreetLimitsCount")
    if number_of_streets is not None:
        try:
            number_of_streets = int(number_of_streets)
        except:
            number_of_streets = None

    unique_key = transaction.get("UniqueKey")  # directly use the JSON value

    return {
        "sale_date": sale_date,
        "unique_key": unique_key,
        "city": city,
        "neighborhood": neighborhood,
        "property_type": property_type,
        "area_sqm": area_sqm,
        "price_per_sqm": price_per_sqm,
        "street_width": street_width,
        "number_of_streets": number_of_streets,
        "orientation": None,
        "proximity_services": None,
        "total_price": total_price
    }

def sync_transactions(conn, transactions):
    insert_sql = """
    INSERT INTO property_transactions
    (sale_date, unique_key, city, neighborhood, property_type, area_sqm, price_per_sqm,
     street_width, number_of_streets, orientation, proximity_services, total_price)
    VALUES (%(sale_date)s, %(unique_key)s, %(city)s, %(neighborhood)s, %(property_type)s,
            %(area_sqm)s, %(price_per_sqm)s, %(street_width)s, %(number_of_streets)s,
            %(orientation)s, %(proximity_services)s, %(total_price)s)
    ON CONFLICT (sale_date, unique_key) DO UPDATE
    SET city = EXCLUDED.city,
        neighborhood = EXCLUDED.neighborhood,
        property_type = EXCLUDED.property_type,
        area_sqm = EXCLUDED.area_sqm,
        price_per_sqm = EXCLUDED.price_per_sqm,
        street_width = EXCLUDED.street_width,
        number_of_streets = EXCLUDED.number_of_streets,
        orientation = EXCLUDED.orientation,
        proximity_services = EXCLUDED.proximity_services,
        total_price = EXCLUDED.total_price;
    """
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, transactions)
    conn.commit()

def main():
    conn = connect_db()
    data = load_json()

    transactions = []
    # Iterate over all months and half-months in JSON
    for month_data in data.get("SAVE", {}).get("data", {}).values():
        for half_month_key in month_data:
            for transaction in month_data[half_month_key]:
                parsed = parse_transaction(transaction)
                transactions.append(parsed)

    print(f"Syncing {len(transactions)} transactions...")
    sync_transactions(conn, transactions)
    print("✅ Sync complete.")
    conn.close()

if __name__ == "__main__":
    main()
