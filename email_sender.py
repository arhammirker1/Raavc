import smtplib
from email.message import EmailMessage
import os
from datetime import datetime

def send_company_notification(form_data, results):
    """Send notification email to company with form data and results"""
    
    # Company email configuration
    COMPANY_EMAIL = "info@raavc.com"  # CHANGE THIS TO YOUR COMPANY EMAIL
    
    # Email configuration (same as existing)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    EMAIL_ADDRESS = "arhammirkerc8a@gmail.com"
    EMAIL_PASSWORD = "xxxxx"
    
    # Create email message
    msg = EmailMessage()
    msg["Subject"] = "New Property Valuation Request - RAFVC"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = COMPANY_EMAIL
    
    # Format the email body with all form data and results
    email_body = f"""
New Property Valuation Request Received

CLIENT INFORMATION:
==================
Name: {form_data.get('client_name', 'N/A')}
Email: {form_data.get('email', 'N/A')}
Phone: {form_data.get('phone', 'N/A')}

PROPERTY DETAILS:
================
Area/Region: {form_data.get('area', 'N/A')}
City: {form_data.get('city', 'N/A')}
Neighborhood: {form_data.get('neighborhood', 'N/A')}
Neighborhood Class: {form_data.get('neighborhood_class', 'N/A')}
Property Type: {form_data.get('property_type', 'N/A')}
Evaluation Purpose: {form_data.get('evaluation_purpose', 'N/A')}

PROPERTY SPECIFICATIONS:
=======================
Land Area: {form_data.get('land_area_sqm', 0):,.0f} m²
Building Area: {form_data.get('building_area_sqm', 0):,.0f} m²
Building Age: {form_data.get('building_age', 0)} years
Street View: {form_data.get('street_view', 'N/A')}
Number of Streets: {form_data.get('num_streets', 'N/A')}
Interface/Facade: {form_data.get('interface', 'N/A')}
Proximity to Services: {form_data.get('proximity_services', 'N/A')}

VALUATION RESULTS:
=================
Estimated Price: SAR {results.get('estimated_price', 0):,.0f}
Price per m²: SAR {results.get('price_per_sqm', 0):,.0f}
Total Area Used: {form_data.get('area_sqm', 0):,.0f} m²

CALCULATION:
============
{form_data.get('area_sqm', 0):,.0f} m² × SAR {results.get('price_per_sqm', 0):,.0f} = SAR {results.get('estimated_price', 0):,.0f}

Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---
This is an automated notification from RAFVC Property Valuation System.
"""
    
    msg.set_content(email_body)
    
    # Send email
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        print(f"📧 Company notification sent successfully to {COMPANY_EMAIL}")
        return True
        
    except Exception as e:
        print(f"❌ Company notification failed: {str(e)}")
        return False

def send_email_with_pdf(client_email, client_name, pdf_path):
    """Send email with PDF attachment"""
    
    if not client_email or not os.path.exists(pdf_path):
        raise Exception("Email address missing or PDF file not found")
    
    # Email configuration (update these with your settings)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    EMAIL_ADDRESS = "info@raavc.com"  # Your email
    EMAIL_PASSWORD = "dfex bset tikf mylk"      # Your app password
    
    # Create email message
    msg = EmailMessage()
    msg["Subject"] = "Property Valuation Report"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = client_email
    
    # Email body
    email_body = f"""
Dear {client_name},

Thank you for using our property valuation service. Please find your detailed property assessment report attached to this email.

The report includes:
- Property valuation estimate
- Price per square meter analysis
- Comparable market transactions
- Detailed property information

If you have any questions about the report or need further assistance, please don't hesitate to contact us.

Best regards,
Property Valuation Team
"""
    
    msg.set_content(email_body)
    
    # Attach PDF file
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
            msg.add_attachment(
                pdf_data, 
                maintype="application", 
                subtype="pdf", 
                filename="property_valuation_report.pdf"
            )
    except Exception as e:
        raise Exception(f"Failed to attach PDF: {str(e)}")
    
    # Send email
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        print(f"📧 Email sent successfully to {client_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        raise Exception(f"Failed to send email: {str(e)}")

if __name__ == "__main__":
    # Test email sending
    test_email = "test@example.com"
    test_name = "Test User"
    test_pdf = "test_report.pdf"
    
    # Create a dummy PDF for testing
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(40, 10, 'Test Report')
    pdf.output(test_pdf)
    
    try:
        send_email_with_pdf(test_email, test_name, test_pdf)
        print("Test email sent successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Clean up test file
        if os.path.exists(test_pdf):
            os.remove(test_pdf)
