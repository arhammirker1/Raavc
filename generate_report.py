import json
import os
from fpdf import FPDF
from ai_model import predict_price
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display


# Economic life by property type (from Taqeem guidelines)
ECONOMIC_LIFE = {
    "traditional_house": 50,
    "villa": 60,
    "residential_building": 70,
    "hotel": 60,
    "warehouse": 50,
    "agricultural": 30
}

# Construction cost estimates for 2025 (SAR per m²)
COST_TABLE = {
    "skeleton": 600,  # Structure only
    "partially_finished_good": 600 + 800,   # structure + good finishing
    "partially_finished_excellent": 600 + 1200,
    "partially_finished_luxury": 600 + 2800,
    "finished_good": 1300,
    "finished_excellent": 1800,
    "finished_luxury": 3500,
}

# Arabic translations dictionary
ARABIC_TRANSLATIONS = {
    "Preliminary Property Valuation Result": "نتيجة التقييم المبدئي للعقار",
    "Estimated Property Value": "القيمة التقديرية للعقار",
    "Based on verified real estate transactions published on the Saudi Real Estate Exchange": "بناءً على المعاملات العقارية المؤكدة المنشورة في منصة التبادل العقاري السعودية",
    "and after analyzing recent data from": "وبعد تحليل البيانات الحديثة من",
    "the estimated market value of the submitted property is": "القيمة السوقية المقدرة للعقار المقدم هي",
    "estimated price per square meter": "السعر التقديري للمتر المربع",
    "Land Value": "قيمة الأرض",
    "Building Value": "قيمة المبنى",
    "Comparable Transactions Used in Analysis": "المعاملات المشابهة المستخدمة في التحليل",
    "Three recent property sales in the same district": "ثلاث عمليات بيع عقارية حديثة في نفس المنطقة",
    "similar in type and size, were used as the basis for comparison": "متشابهة في النوع والحجم، تم استخدامها كأساس للمقارنة",
    "Transaction Date": "تاريخ المعاملة",
    "Area": "المساحة",
    "Total Price": "السعر الإجمالي",
    "Price per": "السعر لكل",
    "Details": "التفاصيل",
    "Market Analysis": "تحليل السوق",
    "Average price per": "متوسط السعر لكل",
    "last 90 days": "آخر 90 يوماً",
    "Market trend": "اتجاه السوق",
    "Demand level for this property type": "مستوى الطلب لهذا النوع من العقارات",
    "Estimated selling time for similar property": "الوقت المقدر لبيع عقار مماثل",
    "Expert Analysis": "التحليل الخبير",
    "Based on comprehensive market analysis and recent transaction data in the": "بناءً على تحليل شامل للسوق وبيانات المعاملات الحديثة في",
    "area, this property valuation reflects current market conditions and comparable sales": "منطقة، يعكس هذا التقييم العقاري ظروف السوق الحالية والمبيعات المشابهة",
    "The property shows good value potential considering location, size, and market trends": "يُظهر العقار إمكانية قيمة جيدة مع الأخذ في الاعتبار الموقع والحجم واتجاهات السوق",
    "Fair market range": "النطاق السوقي العادل",
    "The final valuation of": "التقييم النهائي البالغ",
    "is justified within the current market conditions": "مبرر ضمن ظروف السوق الحالية",
    "RAAVC Recommendation": "توصيات RAAVC",
    "If you are the property owner and wish to sell": "إذا كنت مالك العقار وترغب في البيع",
    "We recommend pricing the property at": "نوصي بتسعير العقار بـ",
    "for a successful sale within 45-60 days": "لبيع ناجح خلال 45-60 يوماً",
    "If you are a buyer or investor": "إذا كنت مشتريًا أو مستثمراً",
    "A purchase price at or below": "سعر الشراء عند أو أقل من",
    "is considered favorable for a good return": "يُعتبر مناسبًا للحصول على عائد جيد",
    "This report is generated based on available market data": "هذا التقرير مُعد بناءً على بيانات السوق المتاحة",
    "and should be used for preliminary assessment only": "ويجب استخدامه للتقييم المبدئي فقط",
    "For formal property appraisal": "للتقييم العقاري الرسمي",
    "please consult with certified real estate professionals": "يُرجى استشارة متخصصين عقاريين معتمدين",
    "Real Estate Valuation Report": "تقرير التقييم العقاري",
    "Increasing": "متزايد",
    "Stable": "مستقر",
    "Decreasing": "متناقص",
    "High": "عالي",
    "Moderate": "متوسط",
    "Low": "منخفض",
    "days": "أيام"
}

def translate_to_arabic(text):
    """Translate text to Arabic using the translations dictionary"""
    if text in ARABIC_TRANSLATIONS:
        return ARABIC_TRANSLATIONS[text]
    return text

def generate_report_and_get_results(data_dict, report_id):
    """
    Generate PDF report and return results for display
    """
    client_name = data_dict.get("client_name", "N/A")
    client_email = data_dict.get("email", "")

    # Get prediction from AI model
    result = predict_price(
        city=data_dict.get("city", ""),
        neighborhood=data_dict.get("neighborhood", ""),
        property_type=data_dict.get("property_type", ""),
        area_sqm=data_dict.get("area_sqm", 0),
        price_per_sqm=data_dict.get("price_per_sqm"),
        street_width=extract_street_width(data_dict.get("street_view", "")),
        evaluation_purpose=data_dict.get("evaluation_purpose", None),
        total_built_up_area=data_dict["total_built_up_area_sqm"],
        building_age=data_dict["building_age"],
        finishing_level=data_dict["finishing_level"],
        structural_condition=data_dict["structural_condition"],
        construction_status=data_dict["construction_status"]
    )

    estimated_price = result["estimated_price"]
    price_per_sqm = result["price_per_sqm"]
    matched_rows = result["matched_rows"]
    land_value = result.get("land_value")
    building_value = result.get("building_value")
    replacement_cost = result.get("replacement_cost")
    depreciation_amount = result.get("depreciation_amount")
    adjusted_depreciation_rate = result.get("adjusted_depreciation_rate")
    economic_life = result.get("economic_life")
    cost_per_m2 = result.get("cost_per_m2")
    depreciation_rate = result.get("depreciation_rate")

    print("DEBUG: predict_price returned:")
    print(f"DEBUG: result type: {type(result)}")
    print(f"DEBUG: result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    print(f"DEBUG: estimated_price: {result.get('estimated_price') if isinstance(result, dict) else 'N/A'}")
    





    # Generate PDF
    pdf_path = generate_custom_pdf_report(data_dict, result, report_id)

    # Return results for API response
    return {
        "client_name": client_name,
        "email": client_email,
        "phone": data_dict.get("phone", ""),
        "area": data_dict.get("area", ""),
        "city": data_dict.get("city", ""),
        "neighborhood": data_dict.get("neighborhood", ""),
        "neighborhood_class": data_dict.get("neighborhood_class", ""),
        "land_area_sqm": data_dict.get("land_area_sqm", 0),
        "building_area_sqm": data_dict.get("building_area_sqm", 0),
        "building_age": data_dict.get("building_age", 0),
        "street_view": data_dict.get("street_view", ""),
        "num_streets": data_dict.get("num_streets", ""),
        "interface": data_dict.get("interface", ""),
        "proximity_services": data_dict.get("proximity_services", ""),
        "property_type": data_dict.get("property_type", ""),
        "evaluation_purpose": data_dict.get("evaluation_purpose", ""),
        "is_owner": data_dict.get("is_owner", ""),
        "area_sqm": data_dict.get("area_sqm", 0),
        "estimated_price": estimated_price,
        "price_per_sqm": price_per_sqm,
        "land_value": land_value,
        "building_value": building_value,
        "matched_transactions": matched_rows,
        "pdf_path": pdf_path,
        "replacement_cost": replacement_cost,
        "depreciation_amount": depreciation_amount,
        "adjusted_depreciation_rate": adjusted_depreciation_rate,
        "economic_life": economic_life,
        "cost_per_m2": cost_per_m2,
        "depreciation_rate": depreciation_rate
    }

def extract_street_width(street_view):
    """Extract numeric street width from street view string"""
    if not street_view:
        return 0
    import re
    numbers = re.findall(r'\d+', street_view)
    return int(numbers[0]) if numbers else 0

def format_arabic_text(text):
    """Properly format Arabic text for display"""
    if not text or text == "N/A":
        return text
    try:
        text_str = str(text)
        has_arabic = any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' for char in text_str)
        if has_arabic:
            reshaped_text = arabic_reshaper.reshape(text_str)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        else:
            return text_str
    except Exception as e:
        
        return str(text)

def format_currency_arabic(amount):
    """Format currency in Arabic"""
    return f"{amount:,.0f} ريال سعودي"



def safe_text_for_pdf(text):
    if not text:
        return "N/A"
    text_str = str(text)
    has_arabic = any('\u0600' <= ch <= '\u06FF' for ch in text_str)
    if has_arabic:
        return format_arabic_text(text_str)
    replacements = {
        '✅': '',
        '💰': 'ريال',
        '📊': '',
        '📈': '',
        '💡': '',
        '🔖': '',
        '✓': '',
        '—': '-',
        '–': '-',
        '[': '',
        ']': '',
    }
    for u, r in replacements.items():
        text_str = text_str.replace(u, r)
    return text_str.strip()

def calculate_market_metrics(matched_rows, estimated_price):
    """Calculate market metrics for analysis"""
    if matched_rows.empty:
        return {
            'avg_ppsqm_90d': 0,
            'trend_label': 'مستقر',
            'demand_level': 'متوسط',
            'expected_days_to_sell': '60-90 أيام'
        }
    avg_ppsqm = matched_rows['total_price'].sum() / matched_rows['area_sqm'].sum() if matched_rows['area_sqm'].sum() > 0 else 0
    return {
        'avg_ppsqm_90d': avg_ppsqm,
        'trend_label': 'متزايد' if avg_ppsqm > estimated_price * 0.9 else 'مستقر',
        'demand_level': 'عالي' if len(matched_rows) > 5 else 'متوسط',
        'expected_days_to_sell': '45-60 أيام' if len(matched_rows) > 3 else '60-90 أيام'
    }

class RAFVCReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.setup_fonts()
        self.set_auto_page_break(auto=True, margin=25)

    def setup_fonts(self):
        try:
            self.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
            self.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
            self.arabic_font = "Amiri"
            
        except Exception as e:
            
            self.arabic_font = "Amiri"

    def header(self):
        self.image("letterhead.png", x=0, y=0, w=210, h=297)

    def footer(self):
        self.set_y(-20)
        self.set_font(self.arabic_font, '', 8)
        self.set_text_color(100, 100, 100)
        footer_text = format_arabic_text(f'RAAVC تقرير التقييم العقاري - {datetime.now().strftime("%Y-%m-%d")}')
        self.cell(0, 5, footer_text, 0, 0, 'C')

    def add_arabic_bullet(self, text, font_size=11, bold=False):
        font_style = 'B' if bold else ''
        self.set_font(self.arabic_font, font_style, font_size)
        self.set_text_color(50, 50, 50)
        formatted_text = format_arabic_text(text)
        self.cell(0, 6, f"• {formatted_text}", 0, 1, 'R')
        self.ln(2)

    def add_section_divider(self):
        self.ln(3)
        self.set_draw_color(150, 150, 150)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)

    def add_comparison_item(self, index, comp_data):
        safe_width = self.w - self.l_margin - self.r_margin
        self.set_font(self.arabic_font, '', 10)
        self.set_text_color(50, 50, 50)
        
        # Right-align Arabic text
        date_text = format_arabic_text(f"{index}. تاريخ المعاملة: {comp_data.get('date', 'غير متوفر')}")
        self.cell(0, 5, date_text, 0, 1, 'R')
        
        area_text = format_arabic_text(f"المساحة: {comp_data.get('area_sqm', 0):,.0f} متر مربع")
        self.cell(0, 5, area_text, 0, 1, 'R')
        
        price_text = format_arabic_text(f"السعر الإجمالي: {format_currency_arabic(comp_data.get('total_price', 0))}")
        self.cell(0, 5, price_text, 0, 1, 'R')
        
        ppsqm = comp_data.get('total_price', 0) / comp_data.get('area_sqm', 1) if comp_data.get('area_sqm', 0) > 0 else 0
        ppsqm_text = format_arabic_text(f"السعر للمتر المربع: {format_currency_arabic(ppsqm)}")
        self.cell(0, 5, ppsqm_text, 0, 1, 'R')
        
        details = f"التفاصيل: {comp_data.get('neighborhood', 'غير متوفر')}, {comp_data.get('property_type', 'غير متوفر')}"
        formatted_details = format_arabic_text(details)
        self.multi_cell(safe_width, 5, formatted_details, 0, 'R')
        self.ln(3)

def generate_custom_pdf_report(data_dict, prediction_result, report_id):
    pdf = RAFVCReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=60, right=20)
    pdf.add_page()
    safe_width = pdf.w - pdf.l_margin - pdf.r_margin

    estimated_price = prediction_result["estimated_price"]
    price_per_sqm = prediction_result["price_per_sqm"]
    matched_rows = prediction_result["matched_rows"]

    market_metrics = calculate_market_metrics(matched_rows, estimated_price)
    owner_reco_price = int(estimated_price * 0.95)
    investor_reco_price = int(estimated_price * 0.85)
    valuation_range_low = int(estimated_price * 0.9)
    valuation_range_high = int(estimated_price * 1.1)

    # Title in Arabic with company name in English
    pdf.set_font(pdf.arabic_font, 'B', 16)
    pdf.set_text_color(50, 50, 50)
    title_text = format_arabic_text('نتيجة التقييم المبدئي للعقار - RAAVC تقييم عقاري')
    pdf.cell(0, 10, title_text, 0, 1, 'C')
    pdf.ln(10)

    # Estimated Property Value
    pdf.add_arabic_bullet('القيمة التقديرية للعقار:', 12, True)
    pdf.set_font(pdf.arabic_font, '', 11)
    pdf.set_text_color(60, 60, 60)
    
    neighborhood = data_dict.get('neighborhood', 'غير متوفر')
    city = data_dict.get('city', 'غير متوفر')
    intro_text = f"بناءً على المعاملات العقارية المؤكدة المنشورة في منصة التبادل العقاري السعودية، وبعد تحليل البيانات الحديثة من {neighborhood} - {city}، القيمة السوقية المقدرة للعقار المقدم هي:"
    formatted_intro = format_arabic_text(intro_text)
    pdf.multi_cell(safe_width, 6, formatted_intro, 0, 'R')
    pdf.ln(5)

    # Price in Arabic
    price_text = format_arabic_text(f"• {format_currency_arabic(estimated_price)}")
    pdf.set_font(pdf.arabic_font, 'B', 14)
    pdf.cell(0, 8, price_text, 0, 1, 'R')
    
    pdf.set_font(pdf.arabic_font, '', 10)
    pdf.set_text_color(80, 80, 80)
    area_sqm = data_dict.get('area_sqm', 0) or data_dict.get('land_area_sqm', 0)
    area_details = format_arabic_text(f"({area_sqm:,.0f} متر مربع × {format_currency_arabic(price_per_sqm)} السعر التقديري للمتر المربع)")
    pdf.cell(0, 5, area_details, 0, 1, 'R')

    # Show Land & Building Value
    land_value = prediction_result.get("land_value", 0)
    building_value = prediction_result.get("building_value", 0)

    if land_value > 0:
        land_text = format_arabic_text(f"قيمة الأرض: {format_currency_arabic(land_value)}")
        pdf.cell(0, 6, land_text, 0, 1, 'R')
    if building_value > 0:
        building_text = format_arabic_text(f"قيمة المبنى: {format_currency_arabic(building_value)}")
        pdf.cell(0, 6, building_text, 0, 1, 'R')

    pdf.add_section_divider()

    # Comparable Transactions
    pdf.add_arabic_bullet('المعاملات المشابهة المستخدمة في التحليل:', 12, True)
    pdf.set_font(pdf.arabic_font, '', 11)
    pdf.set_text_color(60, 60, 60)
    comp_text = format_arabic_text('ثلاث عمليات بيع عقارية حديثة في نفس المنطقة، متشابهة في النوع والحجم، تم استخدامها كأساس للمقارنة:')
    pdf.multi_cell(safe_width, 6, comp_text, 0, 'R')
    pdf.ln(3)

    for comp_count, (_, row) in enumerate(matched_rows.iterrows(), start=1):
        comp_data = {
            'date': str(row['sale_date']),
            'area_sqm': float(row['area_sqm']),
            'total_price': float(row['total_price']),
            'neighborhood': str(row['neighborhood']),
            'property_type': str(row['property_type']),
            'price_per_sqm': float(row['price_per_sqm']) if 'price_per_sqm' in row else 0
        }
        pdf.add_comparison_item(comp_count, comp_data)

    pdf.add_section_divider()

    # Market Analysis
    formatted_neighborhood = format_arabic_text(neighborhood)
    pdf.add_arabic_bullet(f'تحليل السوق - {formatted_neighborhood}:', 12, True)

    pdf.set_font(pdf.arabic_font, '', 10)
    pdf.set_text_color(60, 60, 60)
    
    avg_price_text = format_arabic_text(f"• متوسط السعر للمتر المربع (آخر 90 يوماً): {format_currency_arabic(market_metrics['avg_ppsqm_90d'])}")
    pdf.cell(0, 5, avg_price_text, 0, 1, 'R')
    
    trend_text = format_arabic_text(f"• اتجاه السوق: {market_metrics['trend_label']}")
    pdf.cell(0, 5, trend_text, 0, 1, 'R')
    
    demand_text = format_arabic_text(f"• مستوى الطلب لهذا النوع من العقارات: {market_metrics['demand_level']}")
    pdf.cell(0, 5, demand_text, 0, 1, 'R')
    
    time_text = format_arabic_text(f"• الوقت المقدر لبيع عقار مماثل: {market_metrics['expected_days_to_sell']}")
    pdf.cell(0, 5, time_text, 0, 1, 'R')

    pdf.add_section_divider()

    # Expert Analysis
    pdf.add_arabic_bullet('التحليل الخبير (RAAVC):', 12, True)
    pdf.set_font(pdf.arabic_font, '', 11)
    pdf.set_text_color(60, 60, 60)
    
    expert_analysis = f"بناءً على تحليل شامل للسوق وبيانات المعاملات الحديثة في منطقة {formatted_neighborhood}، يعكس هذا التقييم العقاري ظروف السوق الحالية والمبيعات المشابهة. يُظهر العقار إمكانية قيمة جيدة مع الأخذ في الاعتبار الموقع والحجم واتجاهات السوق."
    formatted_analysis = format_arabic_text(f'"{expert_analysis}"')
    pdf.multi_cell(safe_width, 6, formatted_analysis, 0, 'R')
    pdf.ln(3)
    
    pdf.set_font(pdf.arabic_font, 'B', 11)
    range_text = format_arabic_text(f'النطاق السوقي العادل: {format_currency_arabic(valuation_range_low)} - {format_currency_arabic(valuation_range_high)}.')
    pdf.cell(0, 6, range_text, 0, 1, 'R')
    
    pdf.set_font(pdf.arabic_font, '', 11)
    final_text = format_arabic_text(f'التقييم النهائي البالغ {format_currency_arabic(estimated_price)} مبرر ضمن ظروف السوق الحالية."')
    pdf.cell(0, 6, final_text, 0, 1, 'R')

    pdf.add_section_divider()

    # RAFVC Recommendation
    pdf.add_arabic_bullet('توصيات RAAVC:', 12, True)
    pdf.set_font(pdf.arabic_font, '', 10)
    pdf.set_text_color(60, 60, 60)
    
    owner_rec = format_arabic_text(f"• إذا كنت مالك العقار وترغب في البيع: نوصي بتسعير العقار بـ {format_currency_arabic(owner_reco_price)} لبيع ناجح خلال 45-60 يوماً.")
    pdf.multi_cell(safe_width, 5, owner_rec, 0, 'R')
    pdf.ln(2)
    
    investor_rec = format_arabic_text(f"• إذا كنت مشتريًا أو مستثمراً: سعر الشراء عند أو أقل من {format_currency_arabic(investor_reco_price)} يُعتبر مناسبًا للحصول على عائد جيد.")
    pdf.multi_cell(safe_width, 5, investor_rec, 0, 'R')

    pdf.ln(10)
    pdf.set_font(pdf.arabic_font, '', 9)
    pdf.set_text_color(100, 100, 100)
    
    disclaimer1 = format_arabic_text("هذا التقرير مُعد بناءً على بيانات السوق المتاحة ويجب استخدامه للتقييم المبدئي فقط.")
    pdf.multi_cell(safe_width, 5, disclaimer1, 0, 'C')
    
    disclaimer2 = format_arabic_text("للتقييم العقاري الرسمي، يُرجى استشارة متخصصين عقاريين معتمدين.")
    pdf.multi_cell(safe_width, 5, disclaimer2, 0, 'C')

    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    pdf_file = os.path.join(results_dir, f"RAAVC_Valuation_{report_id}.pdf")
    pdf.output(pdf_file)
    return pdf_file

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def generate_report_from_json():
    with open("sample_input.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    data_dict = {
        "client_name": data.get("client_name", "N/A"),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "city": data.get("city", ""),
        "neighborhood": data.get("neighborhood", ""),
        "property_type": data.get("property_type", ""),
        "area_sqm": data.get("area_sqm", 0),
        "land_area_sqm": data.get("land_area_sqm", 0),
        "building_area_sqm": data.get("building_area_sqm", 0),
        "street_width": data.get("street_width", 0)        
    }
    import uuid
    report_id = str(uuid.uuid4())
    return generate_report_and_get_results(data_dict, report_id)

if __name__ == "__main__":
    result = generate_report_from_json()
    print("Report generated successfully!")
    print(f"Estimated price: SAR {result['estimated_price']:,.0f}") 
    