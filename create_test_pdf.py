"""
create_test_pdf.py — Generates a sample MSEDCL-style electricity bill PDF.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

def create_sample_bill(output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Header
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "MAHARASHTRA STATE ELECTRICITY DISTRIBUTION CO. LTD.")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 65, "PUNE URBAN DIVISION, SHIVAJI NAGAR, PUNE - 411005")
    
    # Horizontal line
    c.setStrokeColor(colors.black)
    c.line(50, height - 75, width - 50, height - 75)

    # Bill Info
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(50, height - 100, "CONSUMER DETAILS")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 120, "Name: MR. ADITYA DESHMUKH")
    c.drawString(50, height - 135, "Address: FLAT NO 402, SUNSHINE APARTMENTS, BANER, PUNE")
    c.drawString(50, height - 150, "Consumer No: 610290087432")
    c.drawString(350, height - 120, "Bill Month: MARCH 2026")
    c.drawString(350, height - 135, "Bill Date: 05-APR-2026")
    c.drawString(350, height - 150, "Due Date: 20-APR-2026")

    # Meter Info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 180, "METERING & CONSUMPTION")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 200, "Meter No: MSED778899")
    c.drawString(50, height - 215, "Sanctioned Load: 7.50 KW")
    c.drawString(50, height - 230, "Supply Type: Three Phase")
    
    # Consumption Table
    c.setFillColor(colors.lightgrey)
    c.rect(50, height - 280, width - 100, 20, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 275, "Previous Reading")
    c.drawString(180, height - 275, "Current Reading")
    c.drawString(300, height - 275, "Difference")
    c.drawString(420, height - 275, "Multiplying Factor")
    c.drawString(520, height - 275, "Units (kWh)")

    c.setFont("Helvetica", 10)
    c.drawString(60, height - 300, "15420")
    c.drawString(180, height - 300, "15980")
    c.drawString(300, height - 300, "560")
    c.drawString(420, height - 300, "1.0")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(520, height - 300, "560")

    # Billing Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 350, "BILLING BREAKUP")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 370, "Energy Charges (560 units @ variable slabs)")
    c.drawString(450, height - 370, "Rs. 4,872.00")
    
    c.drawString(50, height - 385, "Fixed Charges")
    c.drawString(450, height - 385, "Rs. 450.00")
    
    c.drawString(50, height - 400, "Wheeling Charges")
    c.drawString(450, height - 400, "Rs. 640.00")
    
    c.drawString(50, height - 415, "Electricity Duty (16%)")
    c.drawString(450, height - 415, "Rs. 954.24")
    
    c.drawString(50, height - 430, "Fuel Adjustment Charges (FAC)")
    c.drawString(450, height - 430, "Rs. 112.00")

    c.line(50, height - 440, width - 50, height - 440)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 460, "TOTAL BILL AMOUNT")
    c.drawString(450, height - 460, "Rs. 7,028.24")
    c.line(50, height - 470, width - 50, height - 470)

    # Note
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(50, 50, "* This is a computer generated sample bill for testing purposes only.")

    c.save()

if __name__ == "__main__":
    output = "sample_msedcl_bill.pdf"
    create_sample_bill(output)
    print(f"Sample bill created: {os.path.abspath(output)}")
