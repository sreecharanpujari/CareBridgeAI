from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs("sample_documents", exist_ok=True)

# 1. Generate Sample 1: Standard Discharge Summary (PDF)
pdf1 = FPDF()
pdf1.add_page()
pdf1.set_font("Helvetica", "B", 16)
pdf1.cell(0, 10, "ST. JUDE MEMORIAL HOSPITAL", new_x="LMARGIN", new_y="NEXT", align="C")
pdf1.set_font("Helvetica", "B", 12)
pdf1.cell(0, 8, "PATIENT DISCHARGE SUMMARY", new_x="LMARGIN", new_y="NEXT", align="C")
pdf1.ln(4)

pdf1.set_font("Helvetica", size=10)
pdf1.multi_cell(0, 6, "Patient: John Doe (Fictional) | Age: 68 | Admission Date: Oct 10, 2026 | Discharge Date: Oct 14, 2026\n"
                      "Primary Diagnosis: Mild Congestive Heart Failure Exacerbation\n"
                      "Attending Physician: Dr. Sarah Vance, MD\n"
                      "------------------------------------------------------------------------------------------\n\n"
                      "1. MEDICATIONS:\n"
                      "- Lisinopril 10mg: Take 1 tablet by mouth every morning for blood pressure.\n"
                      "- Furosemide 20mg: Take 1 tablet daily in the morning.\n"
                      "- Take one capsule twice daily after meals (Medicine name unreadable on prescription).\n"
                      "- Metoprolol Tartrate 25mg: Take 1 tablet twice daily with food.\n\n"
                      "2. DIET & ACTIVITY:\n"
                      "- Sodium restricted diet: Under 2,000 mg per day.\n"
                      "- Daily morning weight check before breakfast. Report weight gain of >3 lbs in 24 hours.\n"
                      "- Light walking as tolerated. No strenuous heavy lifting over 10 lbs.\n\n"
                      "3. FOLLOW-UP APPOINTMENT:\n"
                      "- Follow-up with Dr. Vance in Cardiology Clinic on Oct 24, 2026 at 10:30 AM.\n"
                      "- Alternate clinic note mentions returning on Oct 21, 2026.\n\n"
                      "4. WARNING SIGNS (RED FLAGS):\n"
                      "- Sudden shortness of breath while resting.\n"
                      "- Swelling in lower legs, ankles, or feet.\n"
                      "- Chest pressure or pain: Call 911 immediately.")

pdf1.output("sample_documents/sample_discharge_summary.pdf")
print("Created sample_discharge_summary.pdf")

# 2. Generate Sample 2: Image version of a short discharge note
img = Image.new("RGB", (800, 600), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

text_content = """CITY GENERAL HOSPITAL - DISCHARGE NOTE
Patient: Jane Smith (Fictional)
Discharge Date: October 14, 2026

DIAGNOSIS: Post-Laparoscopic Cholecystectomy (Gallbladder removal)

INSTRUCTIONS:
1. Medications:
   - Acetaminophen 500mg: 1-2 tablets every 6 hours as needed for pain.
   - Cephalexin 500mg: 1 capsule every 8 hours for 5 days. Finish all pills.

2. Wound Care:
   - Keep surgical incision sites clean and dry.
   - Gauze dressing may be removed after 48 hours.

3. Follow-up:
   - Post-op check with Surgical Clinic in 10 days (October 24, 2026).

WARNING: If temperature exceeds 101 F or redness spreads, call hospital."""

draw.text((30, 30), text_content, fill=(20, 20, 20))
img.save("sample_documents/sample_discharge_note.png")
print("Created sample_discharge_note.png")

