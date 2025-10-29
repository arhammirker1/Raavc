# server.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import os
from datetime import datetime
from generate_report import generate_report_and_get_results
import traceback
import sys 

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://raavc.com", "https://www.raavc.com", "http://localhost:3000"],  # Add both variants    
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Server is running"}

@app.get("/")
def root():
    return {"message": "Property Valuation API is running"}

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Serve static HTML/CSS/JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

class AssessmentRequest(BaseModel):
    # Form fields
    area: str
    city: str
    neighborhood: str
    neighborhood_class: str
    land_area: float
    total_built_up_area: Optional[float] = None  
    construction_status: Optional[str] = None    
    finishing_level: Optional[str] = None     
    structural_condition: Optional[str] = None     
    building_area: float
    building_age: int
    street_view: str
    num_streets: str
    interface: str
    proximity_services: str
    property_type: str
    evaluation_purpose: str
    # Popup fields
    name: str
    email: str
    phone: str

# Store results temporarily--- awaiting production to update to database
results_store = {}

@app.post("/calculate")
def calculate_assessment(data: AssessmentRequest):
    print("="*50)
    print("DEBUG: Starting calculate_assessment")
    print(f"DEBUG: Received data type: {type(data)}")
    # Create unique ID for this report
    report_id = str(uuid.uuid4())
    print(f"DEBUG: Generated report_id: {report_id}")
    
    try:
        print("DEBUG: Step 1 - Validating basic fields")
        if not data.city or not data.neighborhood:
            raise ValueError("City and neighborhood are required")
        
        print("DEBUG: Step 2 - Extracting street width")
        
        
        # Extract street width from street_view
        def extract_street_width(street_view_str):
            if not street_view_str:
                return 0
            import re
            numbers = re.findall(r'\d+', str(street_view_str))
            return int(numbers[0]) if numbers else 0
        
        # Convert pydantic model to dict with proper data types
        street_width = extract_street_width(data.street_view)
        print(f"DEBUG: Extracted street_width: {street_width}")
        
        print("DEBUG: Step 3 - Calculating effective area")

        
        
        # Handle the case where building_area is 0 but land_area has value
        # For land properties, use land_area as the main area
        effective_area = float(data.building_area) if data.building_area > 0 else float(data.land_area)
        print(f"DEBUG: Calculated effective_area: {effective_area}")
        if effective_area <= 0:
            error_msg = f"Invalid area: building_area={data.building_area}, land_area={data.land_area}"
            print(f"DEBUG: ERROR - {error_msg}")
            raise ValueError(error_msg)
        
        print("DEBUG: Step 4 - Building data dictionary")           
        data_dict = {
            "client_name": data.name,
            "email": data.email,
            "phone": data.phone,
            "area": data.area,
            "city": data.city,
            "neighborhood": data.neighborhood,
            "neighborhood_class": data.neighborhood_class,
    "land_area_sqm": float(data.land_area),
    "total_built_up_area_sqm": float(data.total_built_up_area) if data.total_built_up_area else 0,
    "building_area_sqm": float(data.building_area),
    "area_sqm": float(data.land_area),  # Always use land_area as primary
    "building_age": int(data.building_age),
    "construction_status": data.construction_status,
    "finishing_level": data.finishing_level,
    "structural_condition": data.structural_condition,
    "street_view": data.street_view,
    "street_width": street_width,
    "num_streets": data.num_streets,
    "interface": data.interface,
    "proximity_services": data.proximity_services,
    "property_type": data.property_type,
    "evaluation_purpose": data.evaluation_purpose
        }
        print(f"DEBUG: Built data_dict with keys: {list(data_dict.keys())}")
        print("DEBUG: Full data_dict content")
        for key, value in data_dict.items():
            print(f"  {key}: {value}")



        print("DEBUG: Step 5 - Calling generate_report_and_get_results")
               
        # Validate critical fields
        if data_dict['area_sqm'] <= 0:
            error_msg = f"Invalid area: building_area={data.building_area}, land_area={data.land_area}. At least one must be greater than 0."
            
            raise ValueError(error_msg)
        
        if not data_dict['city'] or not data_dict['neighborhood']:
            error_msg = "City and neighborhood are required"
            
            raise ValueError(error_msg)
        
        
        
        # Generate report and get results
        results = generate_report_and_get_results(data_dict, report_id)
        
        
        
        # Store results temporarily
        results_store[report_id] = results
        

        # Send compant notification email
        try:
            from email_sender import send_company_notification
            send_company_notification(data_dict, results)
            
        except Exception as e:
            print(f"DEBUG: Failed to send company notification: {str(e)}")
            # dont fail the whole request if email fails
        
    except ValueError as ve:
        
        raise HTTPException(status_code=400, detail=f"Validation error: {str(ve)}")
    except Exception as e:
        
        import traceback
        
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

    # Redirect user to result page
    
    return RedirectResponse(url=f"/result/{report_id}", status_code=303)

def get_facade_text(facade):
    """Convert English facade to Arabic"""
    facade_map = {
        'north': 'شمالية',
        'south': 'جنوبية',
        'east': 'شرقية',
        'west': 'غربية'
    }
    return facade_map.get(facade, facade)

@app.get("/result/{report_id}", response_class=HTMLResponse)
def result_page(report_id: str):
    if report_id not in results_store:
        raise HTTPException(status_code=404, detail="Report not found")
    
    results = results_store[report_id]
    print(f"DEBUG: Processing report_id: {report_id}")
    print(f"DEBUG: Available keys in results: {list(results.keys())}")

    try:
        # Extract data for display with error handling
        client_name = results.get('client_name', 'عميل RAAVC')
        email = results.get('email', '')
        phone = results.get('phone', '')
        city = results.get('city', 'غير محدد')
        area = results.get('area', 'غير محدد')
        neighborhood = results.get('neighborhood', '')
        neighborhood_class = results.get('neighborhood_class', '')
        property_type = results.get('property_type', '')
        land_area = results.get('land_area_sqm', 0)
        building_area = results.get('building_area_sqm', 0)
        building_age = results.get('building_age', 0)
        street_view = results.get('street_view', '')
        num_streets = results.get('num_streets', '')
        interface = results.get('interface', '')
        proximity_services = results.get('proximity_services', '')
        evaluation_purpose = results.get('evaluation_purpose', '')
        
        # Calculate values with validation
        estimated_price = results.get('estimated_price', 0)
        price_per_sqm = results.get('price_per_sqm', 0)
        effective_area = building_area if building_area > 0 else land_area
        building_value = results.get('building_value', 0)
        replacement_cost = results.get('replacement_cost', 0)
        depreciation_amount = results.get('depreciation_amount', 0)
        adjusted_depreciation_rate = results.get('adjusted_depreciation_rate', 0)
        economic_life = results.get('economic_life', 50)  # Default value
        cost_per_m2 = results.get('cost_per_m2', 0)
        depreciation_rate = results.get('depreciation_rate', 0)
        
        # Validate critical values
        if estimated_price <= 0:
            print(f"DEBUG: Invalid estimated_price: {estimated_price}")
            raise ValueError(f"Invalid estimated price: {estimated_price}")
        if effective_area <= 0:
            print(f"DEBUG: Invalid effective_area: {effective_area}")
            raise ValueError(f"Invalid effective area: {effective_area}")
        if price_per_sqm <= 0:
            print(f"DEBUG: Invalid price_per_sqm: {price_per_sqm}")
            raise ValueError(f"Invalid price per sqm: {price_per_sqm}")
            
    except Exception as e:
        print(f"DEBUG: Error in result_page calculations: {str(e)}")
        print(f"DEBUG: Results data: {results}")
        raise HTTPException(status_code=500, detail=f"Error processing results: {str(e)}")

    show_building_methodology = building_value > 0
    
    # Get current date
    current_date = datetime.now().strftime('%Y/%m/%d')
    
    # URLs for PDF download and email
    pdf_url = f"/download-pdf/{report_id}"
    email_url = f"/email-pdf/{report_id}"
     
    # Professional Result Page HTML
    html_content = f'''<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تقرير التقييم العقاري - RAAVC</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
        body {{
            font-family: 'Cairo', sans-serif;
            background: #f4f7fa;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        .result-container {{
            max-width: 100%;
            margin: 0;
            background: transparent;
            box-shadow: none;
            border-radius: 0;
            overflow: visible;
            min-height: 100vh;
        }}
        .report-header {{
    background: linear-gradient(135deg, #1e3c72, #2a5298);
    color: white;
    padding: 20px;
    text-align: center;
    border-radius: 15px; /* Rounded corners for header */
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}}
        .report-header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .report-header .subtitle {{
            font-size: 18px;
            margin-top: 5px;
            opacity: 0.9;
        }}
        .report-section {{
            background: #fff; /* White background for each section */
            padding: 25px;
            border-bottom: none; /* Remove the border line */
            margin-bottom: 20px; /* Space between sections */
            border-radius: 15px; /* Rounded corners */
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); /* Nice shadow */
            border: 1px solid #e9ecef; /* Subtle border */
        }}
        .report-section h2 {{
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 22px;
        }}
        .property-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }}
        .property-detail {{
            background: #f9f9f9;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .property-detail .label {{
            font-weight: bold;
            font-size: 14px;
            color: #555;
        }}
        .property-detail .value {{
            font-size: 16px;
            margin-top: 5px;
        }}
        .value-display {{
            text-align: center;
            font-size: 26px;
            font-weight: bold;
            color: #28a745;
        }}
        .calculation-breakdown {{
            margin-top: 15px;
        }}
        .calculation-breakdown .breakdown-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px dashed #ddd;
        }}
        
        



        .recommendations {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .recommendation {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 5px solid #1e3c72;
        }}
        .recommendation h3 {{
            margin: 0 0 10px 0;
            font-size: 18px;
            color: #1e3c72;
        }}
        .recommendation .price {{
            font-size: 20px;
            font-weight: bold;
            color: #28a745;
        }}
        .action-buttons {{
            text-align: center;
            margin: 25px 0;
            background: #fff;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            margin: 10px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            background: #1e3c72;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
        }}
        .btn:hover {{
            background: #0f2347;
            transform: translateY(-2px);
        }}
        .btn.secondary {{
            background: #6c757d;
        }}
        .btn.secondary:hover {{
            background: #545b62;
        }}
        .report-header-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .logo-section {{
            text-align: left;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
        }}
        .company-info h1 {{
            font-size: 32px;
            margin: 10px 0 5px 0;
        }}
        .description {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .contact-info {{
            text-align: right;
            font-size: 14px;
            line-height: 1.6;
        }}
        .contact-info div {{
            margin: 3px 0;
        }}
        .report-content {{
            padding: 0;
            width: 100%;
        }}
        .report-title {{
    text-align: center;
    padding: 30px 25px 20px;
    background: #fff; /* White background */
    border-bottom: none;
    border-radius: 15px; /* Rounded corners */
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}
/* Special styling for the value display section */
.report-section.primary {{
    background: linear-gradient(135deg, #28a745, #20c997);
    color: white;
    border-radius: 15px;
    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.3);
}}

.report-section.primary h2,
.report-section.primary p {{
    color: white;
}}



        .report-title h1 {{
            margin: 0;
            font-size: 28px;
            color: #1e3c72;
        }}
        .date {{
            margin-top: 10px;
            font-size: 16px;
            color: #666;
        }}
        .value-display .amount {{
            font-size: 32px;
            font-weight: 700;
            color: white;
        }}
        .value-display .details {{
            font-size: 16px;
            margin-top: 8px;
            opacity: 0.9;
            color: white;
        }}
        @media (max-width: 768px) {{
            .report-header-content {{
                flex-direction: column;
                text-align: center;
            }}
            .contact-info {{
                text-align: center;
                direction: rtl;
                margin-top: 15px;
            }}
            .property-details {{
                grid-template-columns: 1fr;
            }}
            .report-content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="result-container">
        <!-- Professional Report Header -->
        <div class="report-header">
            <div class="report-header-content">
                <div class="logo-section">
                    <div class="logo">RAAVC</div>
                    <div class="company-info">
                        <h1>رافك</h1>
                        <div class="subtitle">RAAVC</div>
                        <div class="description">الخبراء الرواد في تقييم وإدارة رأس المال</div>
                    </div>
                </div>
                <div class="contact-info">
                    <div>📧 Info@raavc.com</div>
                    <div>📞 +966 580 069 350</div>
                    <div>🌐 www.Raavc.com</div>
                    <div>📱 raavc_sa</div>
                </div>
            </div>
        </div>

        <!-- Report Content -->
        <div class="report-content">
            <div class="report-title">
                <h1>تقرير التقييم العقاري</h1>
                <div class="date">Property Valuation Report - {current_date}</div>
            </div>

            <!-- Client Information Section -->
            <div class="report-section">
                <h2>👤 معلومات العميل</h2>
                <div class="property-details">
                    <div class="property-detail">
                        <div class="label">اسم العميل</div>
                        <div class="value">{client_name}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">البريد الإلكتروني</div>
                        <div class="value">{email}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">رقم الهاتف</div>
                        <div class="value">{phone}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">الغرض من التقييم</div>
                        <div class="value">{evaluation_purpose}</div>
                    </div>
                </div>
            </div>

            <!-- Property Information Section -->
            <div class="report-section">
                <h2>🏠 معلومات العقار</h2>
                <div class="property-details">
                    <div class="property-detail">
                        <div class="label">المنطقة</div>
                        <div class="value">{area}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">المدينة</div>
                        <div class="value">{city}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">الحي</div>
                        <div class="value">{neighborhood}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">تصنيف الحي</div>
                        <div class="value">{neighborhood_class}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">نوع العقار</div>
                        <div class="value">{property_type}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">مساحة الأرض</div>
                        <div class="value">{land_area:,.0f} م²</div>
                    </div>'''

    # Add building area conditionally
    if building_value > 0:
        html_content += f'''
                    <div class="property-detail">
                        <div class="label">مساحة البناء</div>
                        <div class="value">{building_area:,.0f} م²</div>                       
                    </div>
                    <div class="property-detail">
                        <div class="label">عمر المبنى</div>
                        <div class="value">{building_age} سنة</div>
                    </div>'''

    # REPLACE the entire section from line 440 onwards with this corrected version:

    html_content += f'''
                    <div class="property-detail">
                        <div class="label">عرض الشارع</div>
                        <div class="value">{street_view}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">عدد الشوارع</div>
                        <div class="value">{num_streets}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">الواجهة</div>
                        <div class="value">{get_facade_text(interface)}</div>
                    </div>
                    <div class="property-detail">
                        <div class="label">قرب الخدمات</div>
                        <div class="value">{proximity_services}</div>
                    </div>
                </div>
            </div>'''

    # Handle land value section conditionally before the main section
    land_value_section = ""
    if building_value > 0:
        land_value_section = f'''                        <!-- Left: Land Value -->
                        <div style="flex:1; background:#28a745; padding:15px; border-radius:8px;">
                            <div style="font-size:18px; font-weight:600; color:white;">قيمة الأرض</div>
                            <div style="font-size:22px; font-weight:700; color:white;">{estimated_price - building_value:,.0f} ريال</div> 
                        </div>'''
        

    html_content += f'''
            <!-- Primary Value Section -->
            <div class="report-section primary">
                <h2>✅ القيمة التقديرية للعقار</h2>
                <p>بناءً على تحليل البيانات العقارية المتاحة والمعاملات المشابهة في المنطقة، القيمة التقديرية للعقار هي:</p>
                <div class="value-display">
                    <div style="display:flex; justify-content:space-between; align-items:center; text-align:center; gap:20px; flex-wrap:wrap;">
                        {land_value_section}
                        <!-- Center: Total -->
                        <div style="flex:{1.5 if building_value > 0 else 1}; background:#28a745; padding:20px; border-radius:8px;">
                            <div class="amount">{estimated_price:,.0f} ريال سعودي</div>
                            <div class="details">({effective_area:,.0f} م² × {price_per_sqm:,.0f} ريال)</div>
                        </div>'''

    # Add building value section conditionally  
    if building_value > 0:
        html_content += f'''
                        <!-- Right: Building Value -->
                        <div style="flex:1; background:#28a745; padding:15px; border-radius:8px;">
                            <div style="font-size:18px; font-weight:600; color:white;">قيمة المبنى</div>
                            <div style="font-size:22px; font-weight:700; color:white;">{building_value:,.0f} ريال</div>
                        </div>'''

    html_content += '''
                    </div>
                </div>
                <div class="calculation-breakdown">'''

    # Add building area breakdown conditionally
    if building_value > 0:
        html_content += f'''
                    <div class="breakdown-item">
                        <span class="label">مساحة البناء</span>
                        <span class="value">{building_area:,.0f} م²</span>
                    </div>'''

    html_content += f'''
                    <div class="breakdown-item">
                        <span class="label">متوسط سعر المتر المربع</span>
                        <span class="value">{price_per_sqm:,.0f} ريال</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="label">إجمالي القيمة التقديرية</span>
                        <span class="value">{estimated_price:,.0f} ريال</span>
                    </div>
                </div>
            </div>

            <!-- Market Analysis Section -->
            <div class="report-section">
                <h2>📈 تحليل السوق</h2>
                <p>بناءً على تحليل السوق العقاري في منطقة {neighborhood} بمدينة {city}، يُظهر السوق استقراراً نسبياً مع نمو طفيف في الأسعار. 
                متوسط سعر المتر المربع للعقارات المشابهة يتراوح بين {price_per_sqm * 0.9:,.0f} و {price_per_sqm * 1.1:,.0f} ريال. 
                الطلب على هذا النوع من العقارات يعتبر {"عالي" if neighborhood_class == "راقي" else "متوسط" if neighborhood_class == "متوسط" else "معتدل"}، 
                والوقت المتوقع للبيع يتراوح بين 60 إلى 90 يوماً في ظل الظروف الطبيعية للسوق.</p>
            </div>'''

    # Add building methodology as separate section first
    if building_value > 0:
      html_content += f'''
        <!-- Building Value Methodology Section -->
        <div class="report-section">
            <h2>🏗️ تحليل النتيجة - رافق</h2>
            
            <p>بناءً على المنهجية المطبقة في أسلوب التكلفة، قام فريق التقييم العقاري برافق بحساب قيمة المبنى من خلال تحديد تكلفة الاستبدال لكل متر مربع، ثم تطبيق معادلة إهلاك ديناميكية تأخذ في الاعتبار العمر الفعلي للمبنى مقارنة بعمره الاقتصادي، مع تعديلات بناءً على الحالة الإنشائية للمبنى.</p>

            <ul>
                <li>🕐 <strong>العمر الفعلي للمبنى:</strong> {building_age} سنة</li>
                <li>⏳ <strong>العمر الاقتصادي (حسب نوع العقار):</strong> {economic_life} سنة</li>
                <li>📊 <strong>نسبة الإهلاك النظرية:</strong> {depreciation_rate:.1f}%</li>
                <li>⚖️ <strong>النسبة المعدلة وفقاً للحالة:</strong> {adjusted_depreciation_rate:.1f}%</li>
                <li>🏗️ <strong>تكلفة الاستبدال (RCN):</strong> {replacement_cost:,.0f} ريال سعودي</li>
                <li>📉 <strong>قيمة الإهلاك:</strong> {depreciation_amount:,.0f} ريال سعودي</li>
                <li>✅ <strong>قيمة المبنى النهائية بعد الإهلاك:</strong> {building_value:,.0f} ريال سعودي</li>
            </ul>

            <p><strong>🎯 ماذا تعني هذه النتيجة بالنسبة لك كعميل رافق؟</strong></p>
            <ul>
                <li>هذا التقييم يعكس العمر الحقيقي لعقارك بدلاً من الاعتماد على نسب ثابتة ومعممة قد لا تعكس الواقع.</li>
                <li>النسبة النهائية تمثل الاستهلاك الفعلي الذي مرّ به المبنى عبر سنوات الاستخدام، مع الأخذ في الاعتبار جودته وحالته الإنشائية.</li>
                <li>المنهجية المطبقة تضمن أن التقييم أكثر عدالة وموضوعية، حيث يعتمد على بيانات فعلية مرتبطة بالعمر والحالة وليس على تقديرات عامة.</li>
                <li>بدمج قيمة الأرض مع قيمة المبنى بعد الإهلاك، يتم تحديد القيمة السوقية النهائية للعقار وفق معايير الهيئة السعودية للمقيمين المعتمدين (تقييم).</li>
            </ul>

            <p><strong>⸻ خلاصة خبير رافق</strong></p>
            <p><strong>قيمة المبنى المحسوبة بعد الإهلاك هي: {building_value:,.0f} ريال سعودي</strong></p>
            <p>وهي تعكس:</p>
            <ul>
                <li>العمر الفعلي للعقار.</li>
                <li>الحالة الإنشائية الحالية.</li>
                <li>التكلفة الحقيقية للإحلال في السوق.</li>
            </ul>
            <p>وبالتالي، فإن هذا التقييم يمنحك صورة شاملة عن القيمة الحالية لعقارك.</p>
            <p><strong>رافق.. قرار واعي</strong></p>
        </div>'''

            

    # Main valuation methodology section
    html_content += f'''
            <!-- Valuation Method Section -->
            <div class="report-section">
                <h2>🔬 منهجية التقييم</h2>
                <p>تم استخدام منهجية <strong>السوق المقارن (Sales Comparison Approach)</strong> في هذا التقييم، والتي تعتبر من أكثر المناهج دقة للعقارات السكنية والتجارية.</p>
                <h3>المعايير المستخدمة في التقييم:</h3>
                <ul>
                    <li><strong>الموقع الجغرافي:</strong> منطقة {area} - مدينة {city}</li>
                    <li><strong>تصنيف الحي:</strong> {neighborhood_class}</li>
                    <li><strong>نوع العقار:</strong> {property_type}</li>
                    <li><strong>المساحة والأبعاد:</strong> مساحة {land_area:,.0f} م²</li>
                    <li><strong>خصائص الشارع:</strong> {street_view}، {num_streets}</li>
                    <li><strong>مستوى الخدمات:</strong> {proximity_services}</li>
                    <li><strong>الغرض من التقييم:</strong> {evaluation_purpose}</li>
                </ul>
                <p>تم تطبيق معاملات تصحيح مناسبة لكل عامل من العوامل المؤثرة على القيمة، مع مراعاة الظروف الحالية للسوق العقاري السعودي.</p>
            </div>

            <!-- Recommendations Section -->
            <div class="report-section">
                <h2>📖 توصيات RAAVC</h2>
                <div class="recommendations">
                    <div class="recommendation seller">
                        <h3>🏠 إذا كنت مالك العقار وترغب في البيع:</h3>
                        <p>نوصي بتسعير العقار عند</p>
                        <div class="price">{estimated_price * 1.05:,.0f} ريال</div>
                        <p>للحصول على بيع ناجح خلال 60-90 يوم.</p>
                    </div>
                    <div class="recommendation buyer">
                        <h3>💰 إذا كنت مشتري أو مستثمر:</h3>
                        <p>سعر الشراء عند أو أقل من</p>
                        <div class="price">{estimated_price * 0.95:,.0f} ريال</div>
                        <p>يعتبر مناسباً للحصول على عائد جيد.</p>
                    </div>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="action-buttons">
                <a href="{pdf_url}" class="btn">📄 تحميل التقرير PDF</a>
                <button onclick="sendEmail('{report_id}')" class="btn" id="emailBtn">📧 إرسال التقرير بالبريد</button>
                <a href="/" class="btn secondary">🔄 حساب تقييم جديد</a>
            </div>

            <script>
            function sendEmail(reportId) {{
                var emailBtn = document.getElementById('emailBtn');
                var originalText = emailBtn.innerHTML;
                emailBtn.innerHTML = '⏳ جاري الإرسال...';
                emailBtn.disabled = true;
                emailBtn.style.cursor = 'not-allowed';
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/email-pdf/' + reportId, true);
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{
                        try {{
                            if (xhr.status === 200) {{
                                var result = JSON.parse(xhr.responseText);
                                if (result.status === "Email sent successfully") {{
                                    emailBtn.innerHTML = '✅ تم إرسال البريد بنجاح';
                                    emailBtn.style.backgroundColor = '#28a745';
                                    setTimeout(function() {{
                                        emailBtn.innerHTML = originalText;
                                        emailBtn.style.backgroundColor = '#1e3c72';
                                        emailBtn.style.cursor = 'pointer';
                                        emailBtn.disabled = false;
                                    }}, 5000);
                                }} else {{
                                    emailBtn.innerHTML = '❌ فشل في الإرسال';
                                    emailBtn.style.backgroundColor = '#dc3545';
                                    setTimeout(function() {{
                                        emailBtn.innerHTML = originalText;
                                        emailBtn.style.backgroundColor = '#1e3c72';
                                        emailBtn.style.cursor = 'pointer';
                                        emailBtn.disabled = false;
                                    }}, 5000);
                                }}
                            }} else {{
                                emailBtn.innerHTML = '❌ خطأ في الشبكة';
                                emailBtn.style.backgroundColor = '#dc3545';
                                setTimeout(function() {{
                                    emailBtn.innerHTML = originalText;
                                    emailBtn.style.backgroundColor = '#1e3c72';
                                    emailBtn.style.cursor = 'pointer';
                                    emailBtn.disabled = false;
                                }}, 5000);
                            }}
                        }} catch (error) {{
                            emailBtn.innerHTML = '⚠️ خطأ غير متوقع';
                            emailBtn.style.backgroundColor = '#dc3545';
                            setTimeout(function() {{
                                emailBtn.innerHTML = originalText;
                                emailBtn.style.backgroundColor = '#1e3c72';
                                emailBtn.style.cursor = 'pointer';
                                emailBtn.disabled = false;
                            }}, 5000);
                        }}
                    }}
                }};
                xhr.send();
            }}
            </script>
        </div>
    </div>
</body>
</html>'''
    
    return html_content


@app.get("/download-pdf/{report_id}")
async def download_pdf(report_id: str):
    pdf_file = f"results/RAAVC_Valuation_{report_id}.pdf"
    
    if os.path.exists(pdf_file):
        return FileResponse(
            path=pdf_file,
            filename=f"RAAVC_Property_Report.pdf",
            media_type='application/pdf'
        )
    else:
        raise HTTPException(status_code=404, detail="PDF file not found")

@app.get("/email-pdf/{report_id}")
def email_pdf(report_id: str):
    if report_id not in results_store:
        raise HTTPException(status_code=404, detail="Report not found")
    
    results = results_store[report_id]
    
    # Use the correct PDF filename format that matches generate_report.py
    pdf_path = os.path.join(RESULTS_DIR, f"RAAVC_Valuation_{report_id}.pdf")
    
    
    
    if not os.path.exists(pdf_path):
        # Also try the pdf_path from results if available
        if 'pdf_path' in results:
            pdf_path = results['pdf_path']
            
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"PDF not found at {pdf_path}")
    
    try:
        from email_sender import send_email_with_pdf
        client_email = results.get('email', '')
        client_name = results.get('client_name', 'Client')
        
        if not client_email:
            return {"status": "Error: No email address found for client"}
        
        send_email_with_pdf(client_email, client_name, pdf_path)
        
        return {"status": "Email sent successfully"}
    except Exception as e:
        
        return {"status": f"Email failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
