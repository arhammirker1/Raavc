import pandas as pd
from sqlalchemy import create_engine
from googletrans import Translator
import numpy as np
from rapidfuzz import process, fuzz

# ------------------------
# Database connection
# ------------------------
DB_USER = "arham"
DB_PASSWORD = "xxx"  # your PostgreSQL password
DB_HOST = "localhost"
DB_PORT = xxx
DB_NAME = "xxxx"

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

translator = Translator()

land_type1 = None
land_type2 = None
land_type3 = None
land_type4 = None


LAND_PROPERTY_TYPES = {
    "أرض سكنية",
    "أرض صناعية", 
    "أرض تجارية",
    "أرض زراعية"
}

# ----------------------------
# Residential Factors
# ----------------------------
frontage_res = {
    "شارع واحد": 1.00,
    "شارعين - زاوية": 1.15,   # average 1.10–1.20
    "شارعين - متظاهرة": 1.15,
    "ثلاث واجهات أو أكثر": 1.20
}

street_width_res = {
    30: 1.06,
    20: 1.03,
    15: 1.00,
    12: 0.98,
    10: 0.96
}

orientation_res = {
    "north": 1.01,
    "east": 1.005,
    "south": 1.005,
    "west": 0.99
}

services_res = {
    "عالي": 1.03,
    "متوسط": 1.00,
    "منخفض": 0.97
}


# ----------------------------
# Commercial Factors
# ----------------------------
frontage_com = {
    "شارع واحد": 1.00,
    "شارعين - زاوية": 1.20,
    "شارعين - متظاهرة": 1.25,
    "ثلاث واجهات أو أكثر": 1.30
}

street_width_com = {
    30: 1.10,
    20: 1.05,
    15: 1.00,
    12: 0.97,
    10: 0.95
}

orientation_com = {
    "north": 1.02,
    "east": 1.01,
    "south": 1.01,
    "west": 0.98
}

services_com = {
    "عالي": 1.05,
    "متوسط": 1.00,
    "منخفض": 0.95
}


# ----------------------------
# Industrial Factors
# ----------------------------
frontage_ind = {
    "شارع واحد": 1.00,
    "شارعين - زاوية": 1.10,
    "شارعين - متظاهرة": 1.15,
    "ثلاث واجهات أو أكثر": 1.20
}

street_width_ind = {
    30: 1.08,
    20: 1.04,
    15: 1.00,
    12: 0.97,
    10: 0.95
}

orientation_ind = {
    "north": 1.00,
    "east": 1.00,
    "south": 1.00,
    "west": 1.00
}

services_ind = {
    "عالي": 1.02,
    "متوسط": 1.00,
    "منخفض": 0.98
}


# ----------------------------
# Agricultural Factors
# ----------------------------
frontage_agr = {
    "شارع واحد": 1.00,
    "شارعين - زاوية": 1.05,
    "شارعين - متظاهرة": 1.07,
    "ثلاث واجهات أو أكثر": 1.10
}

street_width_agr = {
    30: 1.05,
    20: 1.02,
    15: 1.00,
    12: 0.99,
    10: 0.97
}

orientation_agr = {
    "north": 1.00,
    "east": 1.00,
    "south": 1.00,
    "west": 1.00
}

services_agr = {
    "عالي": 1.04,
    "متوسط": 1.00,
    "منخفض": 0.96
}



# ------------------------
# Helper function: translate English input to Arabic
# ------------------------
def translate_to_arabic(text):
    if not text:
        return ""
    try:
        detected = translator.detect(str(text))
        if detected.lang != 'ar':
            translated = translator.translate(str(text), src='en', dest='ar').text
            return translated
        return text
    except Exception:
        return text  # return original text if translation fails


# ------------------------
# Core filter helper
# ------------------------
def filter_transactions(df_base, city_ar, city, neighborhood_ar, neighborhood, property_type_ar, property_type):
    """Filter dataframe by city, neighborhood, property_type with fuzzy fallback"""

    # City filter
    df_city = df_base[df_base["city"] == city_ar]

    if df_city.empty:
        df_city = df_base[df_base["city"] == city]
    if df_city.empty and city:
        df_city = df_base[df_base["city"].str.contains(city, case=False, na=False)]
    if df_city.empty:
        df_city = df_base

    # Neighborhood filter
    if neighborhood_ar:
        df_neigh = df_city[df_city["neighborhood"] == neighborhood_ar]

        if df_neigh.empty:
            df_neigh = df_city[df_city["neighborhood"] == neighborhood]

        if df_neigh.empty:
            all_neighs = df_city["neighborhood"].dropna().unique().tolist()
            if all_neighs:
                best_match = process.extractOne(neighborhood_ar, all_neighs, scorer=fuzz.token_sort_ratio)
                if best_match and best_match[1] >= 70:  # threshold
                    df_neigh = df_city[df_city["neighborhood"] == best_match[0]]

        if not df_neigh.empty:
            df_city = df_neigh

    # Property type filter
    if property_type_ar:
        df_type = df_city[df_city["property_type"] == property_type_ar]

        if df_type.empty:
            df_type = df_city[df_city["property_type"] == property_type]

        if df_type.empty:
            all_types = df_city["property_type"].dropna().unique().tolist()
            if all_types:
                best_match = process.extractOne(property_type_ar, all_types, scorer=fuzz.token_sort_ratio)
                if best_match and best_match[1] >= 70:
                    df_type = df_city[df_city["property_type"] == best_match[0]]

        if not df_type.empty:
            df_city = df_type

    return df_city

def calculate_building_value(total_built_up_area, building_age, finishing_level, structural_condition, property_type=None, construction_status=None, base_construction_cost=None):

    """
    Estimate building value using the Cost Approach:
    - Uses 2025 SAR/m² valuation costs
    - Depreciation by economic life
    - Adjustment by condition
    """

    if not total_built_up_area or total_built_up_area <= 0:
        print("⚠️ No built-up area, returning 0")
        return 0
    
    



    # --- Step 1: Select cost per m² based on construction + finishing ---
    CONSTRUCTION_COST = {
    "skeleton": 600,          # عظم
    "partial": 600,           # تشطيب جزئي
    "finished": 1300,         # مشطب
}

    FINISHING_COST = {
    "normal": 0,      # عادي
    "good": 0,        # جيد
    "excellent": 500, # ممتاز
    "luxury": 2200,   # فاخر
}

    STRUCTURAL_CONDITION_FACTOR = {
    "poor": 0.6,       # ضعيف
    "fair": 0.8,    # متوسط
    "good": 1.0,       # جيد
    "excellent": 1.1,  # ممتاز
}
    print(construction_status,finishing_level,structural_condition)

# Directly use English values
    status = (construction_status or "").strip().lower()
    finish = (finishing_level or "").strip().lower()
    condition = (structural_condition or "").strip().lower()

# Get costs
    base_cost = CONSTRUCTION_COST.get(status, 1200)
    if status in ("finished", "partial"):
        extra_cost = FINISHING_COST.get(finish, 0)
    else:
     extra_cost = 0


    
    cost_per_m2 = base_cost + extra_cost
    replacement_cost = total_built_up_area * cost_per_m2
    cond_factor = STRUCTURAL_CONDITION_FACTOR.get(condition, 1.0)


    # --- Step 2: Economic life by property type ---
    ECONOMIC_LIFE = {
    # 🏠 العقارات السكنية
    "فيلا سكنية": 60,
    "عمارة سكنية": 70,
    "شقة": 60,
    "دور منفصل": 60,
    "بيت شعبي": 50,
    "استراحة سكنية": 30,

    # 🏢 العقارات التجارية
    "مبنى تجاري": 60,
    "عمارة تجارية": 70,
    "برج إداري": 80,
    "محل تجاري": 40,
    "فندق": 60,
    "ورشة": 50,

    # 🏭 الصناعي / المستودعات
    "مستودع": 50,
    "صناعي": 50,

    # 🌱 الزراعي / الخفيف
    "زراعي": 30,

    # 🌍 الأراضي (ليس لها عمر اقتصادي، نعطي None أو 0)
    "أرض سكنية": None,
    "أرض تجارية": None,
    "أرض صناعية": None,
    "أرض زراعية": None
}


    economic_life = ECONOMIC_LIFE.get(property_type, 60)
    # Step 1: Calculate theoretical depreciation rate (Age ÷ Economic Life)
    depreciation_rate = building_age / economic_life if economic_life > 0 else 0
    depreciation_rate = min(depreciation_rate, 1.0)  # Cap at 100%

# --- Step 3: Adjust depreciation by condition ---
    condition_factor = {
        "excellent": 0.8,  # Better condition = less depreciation
        "good": 1.0,       # Standard condition
        "fair": 1.2,       # Fair condition = more depreciation
        "poor": 1.5        # Poor condition = much more depreciation
    }.get((structural_condition or "good").lower(), 1.0)

    # Apply condition factor to the theoretical rate, then cap at 100%
    adjusted_depreciation_rate = min(depreciation_rate * condition_factor, 1.0)
    depreciation_amount = replacement_cost * adjusted_depreciation_rate

    

    

    # --- Step 4: Net building value ---
    building_value = max(replacement_cost - depreciation_amount, 0)

     # 🔎 Debug prints
    print(f"🏗️ Building Value Debug → area={total_built_up_area}, cost_per_m2={cost_per_m2}, "
      f"replacement_cost={replacement_cost}, age={building_age}, life={economic_life}, "
      f"depr_rate={depreciation_rate:.3f}, cond_factor={condition_factor}, "
      f"adj_depr_rate={adjusted_depreciation_rate:.3f}, dep_amount={depreciation_amount}, net_value={building_value}")
      
    return {
    'building_value': building_value,
    'replacement_cost': replacement_cost,
    'depreciation_amount': depreciation_amount,
    'adjusted_depreciation_rate': adjusted_depreciation_rate,
    'economic_life': economic_life,
    'cost_per_m2': cost_per_m2,
    'condition_factor': condition_factor,
    'depreciation_rate': depreciation_rate
    
}


# ------------------------
# Predict function
# ------------------------
def predict_price(city, neighborhood, property_type, area_sqm, price_per_sqm=None, street_width=0, evaluation_purpose=None, num_streets=None, interface=None, proximity_services=None, total_built_up_area=0, building_age=0, finishing_level=None, structural_condition=None, construction_status=None, building_value= None):   
    
    

    # Validate area_sqm
    if not area_sqm or area_sqm <= 0:
        return {
            "estimated_price": 0,
            "price_per_sqm": 0,
            "matched_rows": pd.DataFrame()
        }

    # Translate inputs to Arabic with error handling
    try:
        city_ar = translate_to_arabic(city)
        neighborhood_ar = translate_to_arabic(neighborhood)
        property_type_ar = translate_to_arabic(property_type)
    except Exception:
        city_ar, neighborhood_ar, property_type_ar = city, neighborhood, property_type

    # Load historical transactions
    try:
        query = "SELECT * FROM property_transactions WHERE total_price > 0"
        df = pd.read_sql(query, engine)

        if df.empty:
            return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": pd.DataFrame()}

        # Focus on recent years first
        df_recent = df.copy()
        if "sale_date" in df_recent.columns:
            try:
                df_recent["sale_date"] = pd.to_datetime(df_recent["sale_date"], errors="coerce")
                df_recent = df_recent[df_recent["sale_date"].dt.year.isin([2023, 2024, 2025])]
            except Exception:
                df_recent = df.copy()

    except Exception:
        return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": pd.DataFrame()}

    # Step 1: Try filtering with recent years
    df_city = filter_transactions(df_recent, city_ar, city, neighborhood_ar, neighborhood, property_type_ar, property_type)

    # Step 2: If empty, fall back to all years
    if df_city.empty:
        df_city = filter_transactions(df, city_ar, city, neighborhood_ar, neighborhood, property_type_ar, property_type)

    if df_city.empty:
        return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": pd.DataFrame()}

    # Step 3: Compute similarity based on numeric fields
    def similarity(row):
        score = 0
        area_diff = abs(row.get("area_sqm", 0) - area_sqm) / max(area_sqm, 1)
        score += area_diff

        if price_per_sqm:
            price_diff = abs(row.get("price_per_sqm", 0) - price_per_sqm) / max(price_per_sqm, 1)
            score += price_diff

        if street_width > 0:
            street_diff = abs(row.get("street_width", 0) - street_width) / max(street_width, 1)
            score += street_diff

        return score

    df_city = df_city.copy()
    df_city["similarity"] = df_city.apply(similarity, axis=1)

    # Step 4: Take top 5 closest matches
    top_matches = df_city.sort_values("similarity").head(5)

    if top_matches.empty:
        return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": pd.DataFrame()}
    

    # Step 5: Compute predicted total price scaling with input area
    try:
        valid_matches = top_matches[
            (top_matches["total_price"] > 0) &
            (top_matches["area_sqm"] > 0)
        ]

         # 🚫 Exclude abnormal property types like "فك رهن"
        valid_matches = valid_matches[~valid_matches["property_type"].str.contains("فك رهن", na=False)]

         # 🚫 Exclude extreme outliers (e.g., >100k SAR per sqm)
        valid_matches = valid_matches[
             (valid_matches["total_price"] / valid_matches["area_sqm"]) < 100000
        ]

        if valid_matches.empty:
           return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": top_matches}

       
        

        


        price_per_sqm_values = valid_matches["total_price"] / valid_matches["area_sqm"]
        avg_price_per_sqm = price_per_sqm_values.mean()

        predicted_total = avg_price_per_sqm * area_sqm
        predicted_price_per_sqm = avg_price_per_sqm

    except Exception:
        return {"estimated_price": 0, "price_per_sqm": 0, "matched_rows": top_matches}
    

    

            # ✅ Apply adjustment based on evaluation_purpose (keep same return variable names)
    purpose_discounts = {
        "البيع": 0.00,
        "الشراء": 0.03,        # avg of 3–5%
        "التمويل": 0.08,       # avg of 8–10%
        "الرهن": 0.08,         # avg of 8–12%
        "التأمين": 0.20,       # avg of 20–30%
        "المحاسبة": 0.15,      # avg of 15–25%
        "النزاعات القانونية": 0.00,
        "الميراث": 0.00,
        "الزكاة والضرائب": 0.02,   # avg of 2–5%
        "التصفية": 0.20,       # avg of 20–30%
        "الإفلاس": 0.25,       # avg of 25–35%
        "إثبات الملكية": 0.00,
        "التسعير الحكومي": 0.10,   # avg of 10–20%
        "الاستثمار": -0.10     # negative discount = +20% increase
    }

    try:
        discount = purpose_discounts.get(evaluation_purpose, 0.0)
    except NameError:
        discount = 0.0  # fallback if evaluation_purpose not passed

    adjusted_price = predicted_total * (1 - discount)

    

    # overwrite predicted_total with adjusted value
    predicted_total = adjusted_price



        # ✅ Apply property-specific adjustment factors (AFTER prediction)
    try:
        if "سكنية" in property_type:  # Residential
            frontage_factor = frontage_res.get(num_streets, 1.0)
            street_factor   = street_width_res.get(street_width, 1.0)
            orient_factor   = orientation_res.get(interface, 1.0)
            service_factor  = services_res.get(proximity_services, 1.0)

        elif "تجاري" in property_type:  # Commercial
            frontage_factor = frontage_com.get(num_streets, 1.0)
            street_factor   = street_width_com.get(street_width, 1.0)
            orient_factor   = orientation_com.get(interface, 1.0)
            service_factor  = services_com.get(proximity_services, 1.0)

        elif "صناعي" in property_type:  # Industrial
            frontage_factor = frontage_ind.get(num_streets, 1.0)
            street_factor   = street_width_ind.get(street_width, 1.0)
            orient_factor   = orientation_ind.get(interface, 1.0)
            service_factor  = services_ind.get(proximity_services, 1.0)

        elif "زراعي" in property_type:  # Agricultural
            frontage_factor = frontage_agr.get(num_streets, 1.0)
            street_factor   = street_width_agr.get(street_width, 1.0)
            orient_factor   = orientation_agr.get(interface, 1.0)
            service_factor  = services_agr.get(proximity_services, 1.0)

        else:  # fallback (no adjustment)
            frontage_factor = street_factor = orient_factor = service_factor = 1.0

        total_factor = frontage_factor * street_factor * orient_factor * service_factor
        predicted_total *= total_factor  # ✅ overwrite final price with factor adjustments

        

    except Exception as e:
        print(f"⚠️ Factor adjustment skipped: {e}")

        #recalcualate price per sqm #
    predicted_price_per_sqm = predicted_total / area_sqm


    # ✅ Building value integration    
    print(property_type)
    print(total_built_up_area)
    print(building_age)
    print(finishing_level)
    print(structural_condition)
    print(property_type)
    print(construction_status)
    


    

    if property_type not in LAND_PROPERTY_TYPES and (total_built_up_area and total_built_up_area > 0):
            result = calculate_building_value(
        total_built_up_area=total_built_up_area or 0,
        building_age=building_age or 0,
        finishing_level=finishing_level,
        structural_condition=structural_condition,
        property_type=property_type,
        construction_status=construction_status,
        base_construction_cost=2000
    )            
        
    
            # Extract all values from the returned dictionary
            building_value = result.get('building_value', 0)
            replacement_cost = result.get('replacement_cost', 0)
            depreciation_amount = result.get('depreciation_amount', 0)
            adjusted_depreciation_rate = result.get('adjusted_depreciation_rate', 0)
            economic_life = result.get('economic_life', 0)
            cost_per_m2 = result.get('cost_per_m2', 0)
            depreciation_rate = result.get('depreciation_rate', 0)

            print(building_value)
            print(replacement_cost)
            
            print(depreciation_amount)
            print(adjusted_depreciation_rate) 
            print(economic_life)
            print(cost_per_m2)
            print(depreciation_rate)


            predicted_total += building_value
    else:
        # For land properties, set all building-related values to 0
        building_value = 0
        replacement_cost = 0
        depreciation_amount = 0
        adjusted_depreciation_rate = 0
        economic_life = 0
        cost_per_m2 = 0
        depreciation_rate = 0
        print("🏞️ Land property detected - no building value calculation applied")
       
            
    
    return {
    "estimated_price": predicted_total,
    "price_per_sqm": predicted_price_per_sqm,
    # ✅ Use only the filtered rows for report/PDF
    "matched_rows": valid_matches,
    "land_value": predicted_total - building_value if building_value > 0 else predicted_total,
    "building_value": building_value,
    # new returns:
    "replacement_cost": replacement_cost,  # from calculate_building_value
    "depreciation_amount": depreciation_amount,  # from calculate_building_value  
    "adjusted_depreciation_rate": adjusted_depreciation_rate,  # from calculate_building_value
    "economic_life": economic_life,  # from calculate_building_value
    "cost_per_m2": cost_per_m2,  # from calculate_building_value
    "depreciation_rate": depreciation_rate
}

