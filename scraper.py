import os, json, time, calendar, requests
from datetime import datetime

SAVE_FILE = "save.json"

def get_max_days_in_month(year, month):
    return calendar.monthrange(year, month)[1]

def zero_pad_number(num):
    return f"{int(num):02d}"

def load_save_file():
    """Load save.json without overwriting existing data."""
    if not os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "w") as f:
            json.dump({"SAVE": {"data": {}}}, f, indent=4)
    with open(SAVE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("⚠ save.json is corrupted. Creating a new one.")
            return {"SAVE": {"data": {}}}

def save_progress(data):
    """Save progress safely."""
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_last_saved_point(data):
    """Return last saved (year, month, iter) from save.json."""
    if not data["SAVE"]["data"]:
        return 2006, 1, 0  # start from scratch

    all_months = sorted(data["SAVE"]["data"].keys())
    last_month_key = all_months[-1]
    y, m = map(int, last_month_key.split("-"))

    iters_done = sorted(map(int, data["SAVE"]["data"][last_month_key].keys()))
    last_iter = iters_done[-1] if iters_done else 0

    return y, m, last_iter

def Scraper():
    headers = {
        "Host": "prod-inquiryservice-srem.moj.gov.sa",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": "undefined undefined",  # Replace with token if needed
        "Origin": "https://srem.moj.gov.sa",
        "Referer": "https://srem.moj.gov.sa/"
    }

    data = load_save_file()
    last_y, last_m, last_iter = get_last_saved_point(data)
    current_y, current_m = datetime.now().year, datetime.now().month

    print(f"▶ Resuming from {last_y}-{zero_pad_number(last_m)} iter {last_iter}")

    for y in range(last_y, current_y + 1):
        for m in range(last_m if y == last_y else 1, 13):
            if y == current_y and m > current_m:
                break

            days_in_month = get_max_days_in_month(y, m)
            date_ranges = [
                (f"{y}-{zero_pad_number(m)}-01", f"{y}-{zero_pad_number(m)}-{days_in_month//2}"),
                (f"{y}-{zero_pad_number(m)}-{days_in_month//2 + 1}", f"{y}-{zero_pad_number(m)}-{days_in_month}")
            ]

            month_key = f"{y}-{zero_pad_number(m)}"
            if month_key not in data["SAVE"]["data"]:
                data["SAVE"]["data"][month_key] = {}

            for iter_idx, (date_from, date_to) in enumerate(date_ranges, start=1):
                if (y == last_y and m == last_m and iter_idx <= last_iter) or \
                   (str(iter_idx) in data["SAVE"]["data"][month_key]):
                    print(f"⏩ Skipping {month_key} iter {iter_idx} — already done")
                    continue

                all_pages = []
                print(f"📅 Fetching {month_key} Iter {iter_idx} ({date_from} → {date_to})")
                for p in range(1, 11):
                    payload = {
                        "page": p,
                        "pageSize": 50,
                        "sortType": 1,
                        "sortField": 0,
                        "cityId": None,
                        "districtId": None,
                        "areaFrom": None,
                        "areaTo": None,
                        "priceFrom": None,
                        "priceTo": None,
                        "meterPriceFrom": None,
                        "meterPriceTo": None,
                        "planId": None,
                        "landNumber": None,
                        "isAgricalture": False,
                        "dateFrom": date_from,
                        "dateTo": date_to,
                        "regionid": None,
                        "transactionFormatFilter": [2, 3, 6, 4, 5]
                    }
                    try:
                        res = requests.post(
                            "https://prod-inquiryservice-srem.moj.gov.sa/api/v1/SremRealEstates/ShamilTransactions",
                            json=payload, headers=headers, timeout=15
                        ).json()
                        transactions = res.get("Data", {}).get("Transactions", [])
                        all_pages.extend(transactions)
                        print(f"  📄 Page {p}: {len(transactions)} records")
                    except Exception as e:
                        print(f"  ❌ Error on page {p}: {e}")
                        time.sleep(5)
                        continue
                    time.sleep(0.5)

                # Save new data without overwriting other months
                data["SAVE"]["data"][month_key][str(iter_idx)] = all_pages
                save_progress(data)

                print(f"✅ Saved {month_key} iter {iter_idx} ({len(all_pages)} total)")

if __name__ == "__main__":
    Scraper()
