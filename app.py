import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import io
import re
import json
import base64
import urllib.parse
from datetime import datetime
import requests
from pypdf import PdfReader
from PIL import Image, ImageEnhance, ImageOps
from gtts import gTTS

# ==============================================================================
# 1. CONSTANTS & SYSTEM CONFIGURATION
# ==============================================================================
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

MEDICAL_GLOSSARY = {
    "exacerbation": "A sudden worsening of symptoms or flare-up of a condition.",
    "congestive heart failure": "A condition where the heart doesn't pump blood as strongly as it should, often causing fluid buildup.",
    "cholecystectomy": "Surgical removal of the gallbladder.",
    "laparoscopic": "A minimally invasive surgery done through tiny keyhole incisions with a camera.",
    "hypertension": "High blood pressure.",
    "edema": "Swelling caused by fluid trapped in your body's tissues (often in feet or ankles).",
    "furosemide": "A water pill (diuretic) that helps your body get rid of extra salt and water through urine.",
    "lisinopril": "A blood pressure medication that relaxes blood vessels so blood flows more smoothly.",
    "metoprolol": "A beta-blocker medicine that slows down heart rate and lowers blood pressure.",
    "cephalexin": "An antibiotic medicine used to treat or prevent bacterial infections.",
    "acetaminophen": "A common over-the-counter pain reliever and fever reducer (like Tylenol).",
    "atorvastatin": "A cholesterol-lowering medication that protects heart health.",
    "clopidogrel": "A blood thinner that prevents blood clots after heart procedures or stents.",
    "ecosprin": "Low-dose aspirin used to prevent blood clots.",
    "sodium restricted": "Eating less salt to prevent fluid retention and protect your heart and kidneys.",
    "post-op": "Post-operative, meaning the period right after surgery."
}

# Guaranteed Embedded Sample Discharge Summary
SAMPLE_DISCHARGE_TEXT = """ST. JUDE MEMORIAL HOSPITAL
PATIENT DISCHARGE SUMMARY

Patient: John Doe (Fictional) | Age: 68 | Admission Date: Oct 10, 2026 | Discharge Date: Oct 14, 2026
Primary Diagnosis: Mild Congestive Heart Failure Exacerbation
Attending Physician: Dr. Sarah Vance, MD
------------------------------------------------------------------------------------------

1. MEDICATIONS:
- Lisinopril 10mg: Take 1 tablet by mouth every morning for blood pressure.
- Furosemide 20mg: Take 1 tablet daily in the morning.
- Take one capsule twice daily after meals (Medicine name unreadable on prescription).
- Metoprolol Tartrate 25mg: Take 1 tablet twice daily with food.

2. DIET & ACTIVITY:
- Sodium restricted diet: Under 2,000 mg per day.
- Daily morning weight check before breakfast. Report weight gain of >3 lbs in 24 hours.
- Light walking as tolerated. No strenuous heavy lifting over 10 lbs.

3. FOLLOW-UP APPOINTMENT:
- Follow-up with Dr. Vance in Cardiology Clinic on Oct 24, 2026 at 10:30 AM.
- Alternate clinic note mentions returning on Oct 21, 2026.

4. WARNING SIGNS (RED FLAGS):
- Sudden shortness of breath while resting.
- Swelling in lower legs, ankles, or feet.
- Chest pressure or pain: Call 911 immediately."""

# Guaranteed Embedded Sample Handwritten Prescription
SAMPLE_HANDWRITTEN_PRESCRIPTION_TEXT = """CITY HEALTH CLINIC & CARDIOLOGY CARE
Dr. A. K. Sharma, MD, DM (Cardiology) - Reg No: 54921
Date: 14-Oct-2026 | Patient: Rajesh Kumar (Age: 52)
------------------------------------------------------------
Clinical Notes: Post angioplasty follow-up. Blood Pressure: 130/84 mmHg.

Rx (Prescribed Medications):
1. Tab. Ecosprin 75 mg - 1-0-0 (Once daily in morning after breakfast) x 1 month
2. Tab. Clopilet 75 mg - 0-1-0 (Once daily in afternoon after lunch) x 1 month
3. Tab. Atorva 40 mg - 0-0-1 (Once daily at night after dinner) x 1 month
4. Tab. Metolar XR 25 mg - 1-0-0 (Once daily in morning) x 15 days
5. Cap. Pantocid 40 mg - 1-0-0 (Once daily 30 minutes before breakfast) x 15 days
6. Syrup [Illegible / Cursive handwriting - Needs confirmation] - 10ml TDS x 5 days

Diet & Lifestyle Advice:
- Strict low salt (< 2g/day) and low oil diet.
- Light morning walk 20 minutes daily. Avoid heavy lifting (> 5 kg).
- Daily blood pressure and pulse check.

Follow-up & Emergency Instructions:
- Follow-up visit with Dr. Sharma on 29-Oct-2026 at 11:00 AM.
- Alternate note mentions returning on 25-Oct-2026.
- 🚨 Emergency Warning: If severe chest tightness, sweating, or breathlessness occurs, report to emergency room immediately."""

# Country phone codes dictionary
COUNTRY_CODES = {
    "🇮🇳 India (+91)": "+91",
    "🇺🇸 USA / Canada (+1)": "+1",
    "🇬🇧 United Kingdom (+44)": "+44",
    "🇦🇺 Australia (+61)": "+61",
    "🇦🇪 UAE (+971)": "+971",
    "🇸🇦 Saudi Arabia (+966)": "+966",
    "🇸🇬 Singapore (+65)": "+65",
    "🇩🇪 Germany (+49)": "+49",
    "🌐 International (+00)": "+00"
}

# ==============================================================================
# 2. DOCUMENT PROCESSING & HANDWRITING TRANSCRIPTION ENGINE
# ==============================================================================
def validate_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return False, "No file uploaded."
    filename = uploaded_file.name.lower()
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type (.{file_ext}). Please upload a PDF, PNG, JPG, or JPEG."
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File is too large ({file_size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
    return True, f"File valid: {uploaded_file.name} ({file_size_mb:.2f} MB)"

def extract_text_from_pdf(pdf_bytes):
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) == 0:
            return "", False, "The uploaded PDF is empty."
        extracted_pages = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")
        full_text = "\n\n".join(extracted_pages).strip()
        if not full_text:
            return "", False, "No readable digital text found in this PDF. It may be a scanned image."
        return full_text, True, "Successfully extracted text from PDF."
    except Exception as e:
        return "", False, f"Error reading PDF: {str(e)}"

def preprocess_handwritten_image(image_bytes: bytes) -> bytes:
    """
    Enhances contrast and sharpness of handwritten doctor prescriptions
    to make cursive ink legible against paper grain and shadows.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.6)
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.4)
        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG", quality=92)
        return out_buf.getvalue()
    except Exception:
        return image_bytes

def extract_text_from_image(image_bytes):
    """
    Standard OCR extraction using Tesseract.
    """
    try:
        import pytesseract
        
        if os.name == "nt":
            windows_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
            ]
            for wp in windows_paths:
                if os.path.exists(wp):
                    pytesseract.pytesseract.tesseract_cmd = wp
                    break

        image = Image.open(io.BytesIO(image_bytes))
        try:
            text = pytesseract.image_to_string(image).strip()
            if not text:
                return "", False, "OCR completed, but no text could be recognized in this image."
            return text, True, "Successfully extracted text using OCR."
        except Exception:
            return "", False, (
                "Tesseract OCR is not installed on this cloud environment yet. "
                "Use the '✍️ Decipher Doctor Handwriting with AI Vision' button below or paste the text directly into the editor."
            )
    except Exception as img_err:
        return "", False, f"Invalid or unreadable image file: {str(img_err)}"

def extract_handwriting_with_gemini_vision(image_bytes: bytes, api_key: str = None):
    """
    Deciphers doctor handwriting, cursive medical notes, and handwritten prescriptions
    using Gemini Multimodal Vision API with image contrast enhancement.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key.strip() == "your_gemini_api_key_here":
        return "", False, "A Gemini API Key is required for AI Vision handwriting recognition. Enter your key in the sidebar or use the sample handwritten prescription below."
    
    try:
        enhanced_bytes = preprocess_handwritten_image(image_bytes)
        b64_image = base64.b64encode(enhanced_bytes).decode("utf-8")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"
        
        prompt = """You are a senior clinical pharmacist and medical transcription specialist.
Decipher this handwritten doctor's prescription or clinical note image with utmost care.
Doctor handwriting is often hurried, cursive, and difficult for patients to read.

Instructions:
1. Identify and transcribe clinic/hospital name, doctor's name, patient name, and date if visible.
2. Transcribe ALL prescribed medications:
   - Medicine name (trade/brand name and generic equivalent)
   - Strength / dosage (e.g. 500mg, 10mg)
   - Frequency & Timing (e.g., OD/once daily, BD/twice daily, TDS/thrice daily, 1-0-0, before/after meals)
   - Duration of course
3. Transcribe diet, lifestyle, activity, and wound care instructions.
4. Transcribe follow-up appointments and emergency warning red flags.
5. IF ANY WRITING OR MEDICINE NAME IS ILLEGIBLE, BLURRED, OR AMBIGUOUS:
   Explicitly mark it as: "[Illegible / Unclear handwriting - Requires Pharmacist Confirmation]". Never fabricate or guess unreadable drugs.
Format clearly in clean, patient-friendly text with clear sections."""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": b64_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        
        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            return "", False, "AI Vision completed but returned empty text."
        return text, True, "Successfully deciphered doctor handwriting with Gemini AI Vision!"
    except Exception as e:
        return "", False, f"AI Vision error: {str(e)}"

# ==============================================================================
# 3. CONFUSION DETECTOR ENGINE
# ==============================================================================
def detect_confusions_rule_based(document_text: str):
    issues = []
    lines = [line.strip() for line in document_text.split("\n") if line.strip()]
    flagged_med_lines = set()

    for line in lines:
        lower_line = line.lower()
        if any(term in lower_line for term in ["unreadable", "illegible", "blurred", "smudged", "medicine name", "needs confirmation"]):
            if line not in flagged_med_lines:
                flagged_med_lines.add(line)
                issues.append({
                    "issue_type": "Unclear Medication Reference",
                    "severity": "High",
                    "original_text": line,
                    "explanation": "This instruction describes taking medication, but the specific medicine name is missing or marked unreadable/illegible.",
                    "recommendation": "Do NOT take any unknown pill. Contact your doctor or hospital pharmacist immediately to verify the exact drug name.",
                    "status": "Needs Confirmation"
                })
        elif re.search(r"\btake\s+(?:one|two|\d+)?\s*(?:tablet|pill|capsule|dose)", lower_line):
            known_meds = ["lisinopril", "furosemide", "metoprolol", "acetaminophen", "cephalexin", "aspirin", "amoxicillin", "atorvastatin", "ibuprofen", "ecosprin", "clopilet", "pantocid", "metolar", "atorva"]
            if not any(med in lower_line for med in known_meds):
                if line not in flagged_med_lines:
                    flagged_med_lines.add(line)
                    issues.append({
                        "issue_type": "Unclear Medication Reference",
                        "severity": "High",
                        "original_text": line,
                        "explanation": "An instruction specifies taking a pill or dose, but no known medication name is attached to it.",
                        "recommendation": "Contact your prescribing doctor or hospital pharmacy to clarify which medicine this refers to.",
                        "status": "Needs Confirmation"
                    })

    # Conflicting Dates
    followup_lines = [l for l in lines if any(w in l.lower() for w in ["follow-up", "follow up", "appointment", "clinic note", "return to", "review in", "alternate note"])]
    if len(followup_lines) >= 2:
        dates_in_followups = []
        for fl in followup_lines:
            found = re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4}", fl, re.IGNORECASE)
            dates_in_followups.extend(found)
        unique_dates = list(set(dates_in_followups))
        if len(unique_dates) > 1:
            issues.append({
                "issue_type": "Conflicting Follow-up Dates",
                "severity": "Medium",
                "original_text": " ... ".join([f.strip("- ") for f in followup_lines if any(d in f for d in unique_dates)]),
                "explanation": f"The document mentions multiple conflicting dates ({' vs '.join(unique_dates)}) for your follow-up clinic visit.",
                "recommendation": "Call the clinic receptionist or doctor's office to confirm the exact date and time of your scheduled appointment.",
                "status": "Needs Confirmation"
            })

    # Missing Timing
    for line in lines:
        lower_line = line.lower()
        if any(w in lower_line for w in ["diet", "sodium", "salt", "fluid", "lifting", "weight", "lbs", "mg/dl", "bp"]):
            continue
        if re.search(r"\b\d+\s*(?:mg|mcg|ml)\b", lower_line) and any(m in lower_line for m in ["tablet", "capsule", "take", "pill", "tab.", "cap."]):
            has_timing = any(t in lower_line for t in ["daily", "morning", "night", "evening", "hour", "times", "bedtime", "needed", "q8h", "bid", "tid", "qid", "tds", "1-0-0", "0-1-0", "0-0-1"])
            if not has_timing and line not in flagged_med_lines:
                flagged_med_lines.add(line)
                issues.append({
                    "issue_type": "Missing Medication Timing/Frequency",
                    "severity": "Medium",
                    "original_text": line,
                    "explanation": "This medication lists a dosage strength, but does not state the daily schedule or timing.",
                    "recommendation": "Consult with your pharmacist to check the label or call your physician for the exact dosing schedule.",
                    "status": "Needs Confirmation"
                })
    return issues

def analyze_document_confusion(document_text: str, api_key: str = None):
    if not document_text or not document_text.strip():
        return []
    key = api_key or os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"
            prompt = f"""You are the 'Confusion Detector' for CareBridge AI. Identify unclear, incomplete, or contradictory instructions in this hospital discharge summary or prescription:
\"\"\"{document_text}\"\"\"
Return ONLY a valid JSON array of objects with keys: "issue_type", "severity" ("High"/"Medium"), "original_text", "explanation", "recommendation", "status" ("Needs Confirmation"). Return [] if no issues."""
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=12)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception:
            return detect_confusions_rule_based(document_text)
    return detect_confusions_rule_based(document_text)

# ==============================================================================
# 4. MEDICAL EXPLAINER & PATIENT ASSISTANT
# ==============================================================================
def explain_terms_in_text(text: str):
    found = {}
    lower = text.lower()
    for term, definition in MEDICAL_GLOSSARY.items():
        if term in lower:
            found[term.title()] = definition
    return found

def get_medical_explanation(document_text: str, api_key: str = None):
    if not document_text.strip():
        return {"summary": "No document text available.", "glossary": {}, "mode": "None"}
    
    key = api_key or os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"
            prompt = f"""You are the Medical Explainer for CareBridge AI. Convert this discharge summary or prescription into simple, patient-friendly language.
Strict Rules: Preserve all medication names, dosages, and dates exactly without alterations.
Text:
\"\"\"{document_text}\"\"\"
Return a JSON object with:
- "summary": Clear markdown with bullet points explaining what the patient needs to do.
- "glossary": A dictionary of {{"Medical Term": "Simple Definition"}}."""
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            res = json.loads(raw)
            res["mode"] = "Gemini 2.5 Flash AI"
            return res
        except Exception:
            pass

    # Local Reliable Engine
    lines = [l.strip() for l in document_text.split("\n") if l.strip()]
    sections = {"Medications": [], "Diet & Daily Care": [], "Follow-Up Appointments": [], "Warning Signs (Red Flags)": []}
    curr = "Diet & Daily Care"
    for l in lines:
        low = l.lower()
        if any(w in low for w in ["medication", "medicine", "rx", "tab.", "cap."]): curr = "Medications"; continue
        elif any(w in low for w in ["diet", "activity", "wound", "lifestyle"]): curr = "Diet & Daily Care"; continue
        elif any(w in low for w in ["follow-up", "appointment", "clinic", "review in"]): curr = "Follow-Up Appointments"; continue
        elif any(w in low for w in ["warning", "red flag", "emergency"]): curr = "Warning Signs (Red Flags)"; continue
        cleaned = l.lstrip("-*•1234567890. ")
        if cleaned: sections[curr].append(cleaned)
    
    parts = ["### 🌟 Plain Language Summary\nHere is your discharge summary explained in simple everyday words:\n"]
    for s_name, items in sections.items():
        if items:
            parts.append(f"#### 📌 {s_name}")
            for it in items:
                if s_name == "Medications": parts.append(f"- **{it}** *(Take exactly as prescribed; do not skip or change dose)*")
                elif s_name == "Warning Signs (Red Flags)": parts.append(f"- 🚨 **{it}** *(Seek immediate emergency care if this occurs)*")
                else: parts.append(f"- {it}")
            parts.append("")
    return {"summary": "\n".join(parts), "glossary": explain_terms_in_text(document_text), "mode": "Built-in Safety Parser"}

def answer_patient_question(document_text: str, question: str, api_key: str = None):
    if not document_text.strip(): return "Please upload a document first."
    if not question.strip(): return "Please enter a question."
    key = api_key or os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"
            prompt = f"Answer strictly using this medical document only. If not mentioned, state so clearly. Never diagnose or change medicines.\nDoc:\n{document_text}\nQuestion: {question}"
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=12)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    low_q = question.lower()
    for term, definition in MEDICAL_GLOSSARY.items():
        if term in low_q: return f"**{term.title()}**: {definition} (Source: CareBridge Medical Reference)"
    if any(w in low_q for w in ["appointment", "follow up", "clinic", "when"]):
        follow_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["follow-up", "appointment", "clinic", "review in"])]
        if follow_lines: return "Based on your document, here are the follow-up instructions:\n" + "\n".join(follow_lines)
    if any(w in low_q for w in ["medicine", "medication", "pill", "tablet", "tab"]):
        med_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["mg", "tablet", "capsule", "take", "tab.", "cap."])]
        if med_lines: return "Medication instructions found in your document:\n" + "\n".join(med_lines)
    return "This detail is not specifically mentioned in your discharge summary. Please consult your physician or clinic."

# ==============================================================================
# 5. RECOVERY PLANNER & REMINDERS ENGINE
# ==============================================================================
def build_recovery_plan(document_text: str, api_key: str = None):
    if not document_text or not document_text.strip():
        return {"medications": [], "diet_lifestyle": [], "followups": [], "wound_care": [], "warnings": [], "needs_confirmation": []}
    confusions = analyze_document_confusion(document_text, api_key=api_key)
    flagged = {c["original_text"].strip().lower() for c in confusions}
    lines = [l.strip() for l in document_text.split("\n") if l.strip()]
    plan = {"medications": [], "diet_lifestyle": [], "followups": [], "wound_care": [], "warnings": [], "needs_confirmation": confusions}
    curr = "general"

    for line in lines:
        lower = line.lower()
        cleaned = line.lstrip("-*•1234567890. ")
        if not cleaned: continue
        is_bullet = line.startswith(("-", "*", "•"))
        if not is_bullet:
            if any(h in lower for h in ["medication", "medicine", "rx", "prescribed"]) and len(lower) < 35: curr = "medications"; continue
            elif any(h in lower for h in ["diet", "nutrition", "activity", "lifestyle"]) and len(lower) < 35: curr = "diet_lifestyle"; continue
            elif any(h in lower for h in ["follow-up", "appointment", "review in"]) and len(lower) < 35: curr = "followups"; continue
            elif any(h in lower for h in ["wound", "dressing"]) and len(lower) < 35: curr = "wound_care"; continue
            elif any(h in lower for h in ["warning", "red flag", "emergency"]) and len(lower) < 35: curr = "warnings"; continue

        is_confused = any(f in lower for f in flagged if len(f) > 5)
        if curr == "medications" and not is_confused:
            plan["medications"].append({"task": cleaned, "category": "Medication", "status": "Confirmed"})
        elif curr == "diet_lifestyle":
            plan["diet_lifestyle"].append({"task": cleaned, "category": "Diet & Lifestyle", "status": "Confirmed"})
        elif curr == "followups" and not is_confused:
            plan["followups"].append({"task": cleaned, "category": "Follow-Up", "status": "Confirmed"})
        elif curr == "wound_care":
            plan["wound_care"].append({"task": cleaned, "category": "Wound Care", "status": "Confirmed"})
        elif curr == "warnings":
            plan["warnings"].append({"task": cleaned, "category": "Warning Sign", "status": "Urgent Alert"})
        else:
            if any(w in lower for w in ["mg", "tablet", "take ", "tab.", "cap.", "1-0-0", "0-1-0", "0-0-1"]) and not is_confused:
                plan["medications"].append({"task": cleaned, "category": "Medication", "status": "Confirmed"})
            elif any(w in lower for w in ["appointment", "clinic", "return on", "review in"]):
                plan["followups"].append({"task": cleaned, "category": "Follow-Up", "status": "Confirmed"})
            elif any(w in lower for w in ["pain", "breath", "emergency"]):
                plan["warnings"].append({"task": cleaned, "category": "Warning Sign", "status": "Urgent Alert"})
    return plan

def extract_reminders_schedule(plan):
    reminders = []
    for med in plan.get("medications", []):
        task = med["task"]
        low = task.lower()
        slots = []
        if any(w in low for w in ["morning", "breakfast", "every morning", "1-0-0", "od"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
        if any(w in low for w in ["afternoon", "lunch", "0-1-0"]):
            slots.append({"slot": "Afternoon", "time": "01:00 PM"})
        if any(w in low for w in ["twice daily", "twice a day", "bid"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
            slots.append({"slot": "Evening", "time": "08:00 PM"})
        elif any(w in low for w in ["night", "evening", "bedtime", "0-0-1", "dinner"]):
            slots.append({"slot": "Night", "time": "08:00 PM"})
        if not slots: slots.append({"slot": "Daily", "time": "09:00 AM"})

        seen = set()
        for s in slots:
            if s["time"] not in seen:
                seen.add(s["time"])
                reminders.append({
                    "type": "Medication",
                    "title": f"Take {task.split(':')[0]}",
                    "details": task,
                    "schedule_slot": s["slot"],
                    "timing": s["time"],
                    "alert_message": f"[CareBridge Medication Alert - {s['time']}]: Time to take {task}. Take with water as prescribed.",
                    "status": "Active"
                })

    for appt in plan.get("followups", []):
        task = appt["task"]
        date_m = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4}", task, re.IGNORECASE)
        time_m = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b", task)
        a_date = date_m.group(0) if date_m else "Upcoming date"
        a_time = time_m.group(0) if time_m else "Clinic hours"
        reminders.append({
            "type": "Doctor Consultation",
            "title": "Hospital / Clinic Follow-up",
            "details": task,
            "schedule_slot": "Appointment",
            "timing": f"{a_date} at {a_time}",
            "alert_message": f"[CareBridge Appointment Alert]: Scheduled clinic visit on {a_date} ({a_time}). Details: {task}.",
            "status": "Scheduled"
        })

    for conf in plan.get("needs_confirmation", []):
        reminders.append({
            "type": "Requires Confirmation",
            "title": f"Needs Confirmation: {conf.get('issue_type', 'Unclear Instruction')}",
            "details": conf.get("original_text", ""),
            "schedule_slot": "Action Required",
            "timing": "Paused for Safety",
            "alert_message": f"[Safety Alert - Needs Confirmation]: '{conf.get('original_text')}'. Please verify with your doctor.",
            "status": "Needs Confirmation"
        })
    return reminders

def generate_ics_calendar(reminders):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CareBridge AI//Recovery Companion//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    now_str = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    for idx, r in enumerate(reminders):
        if r["status"] == "Needs Confirmation": continue
        summary = f"CareBridge AI: {r['title']}".replace("\n", " ").replace(",", "\\,")
        desc = f"{r['details']}\\n\\nAlert: {r['alert_message']}".replace("\n", " ")
        lines.extend([
            "BEGIN:VEVENT", f"UID:carebridge-{idx}-{now_str}@carebridge.local", f"DTSTAMP:{now_str}",
            f"SUMMARY:{summary}", f"DESCRIPTION:{desc}",
            "BEGIN:VALARM", "TRIGGER:-PT15M", "ACTION:DISPLAY", f"DESCRIPTION:Reminder: {summary}", "END:VALARM",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

def send_browser_notification_js(title: str, message: str):
    """
    Injects JavaScript to request Web Notification permissions, trigger a real
    browser desktop/mobile push notification, and play an alert chime sound.
    """
    safe_title = json.dumps(title)
    safe_msg = json.dumps(message)
    js_code = f"""
    <script>
    (function() {{
        function triggerNotif() {{
            try {{
                var audio = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
                audio.play().catch(function(e){{}});
            }} catch(e) {{}}
            
            if (!("Notification" in window)) {{
                alert("Browser notifications are not supported in this browser window.");
                return;
            }}
            if (Notification.permission === "granted") {{
                new Notification({safe_title}, {{
                    body: {safe_msg},
                    icon: "https://cdn-icons-png.flaticon.com/512/2966/2966327.png"
                }});
            }} else if (Notification.permission !== "denied") {{
                Notification.requestPermission().then(function(perm) {{
                    if (perm === "granted") {{
                        new Notification({safe_title}, {{
                            body: {safe_msg},
                            icon: "https://cdn-icons-png.flaticon.com/512/2966/2966327.png"
                        }});
                    }}
                }});
            }} else {{
                alert("Browser notification permission is blocked. Please enable notifications in your browser address bar.");
            }}
        }}
        triggerNotif();
    }})();
    </script>
    <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; border-radius: 8px; padding: 10px; font-size: 0.85rem; color: #34d399; margin-top: 6px;">
        🔔 <b>Real Browser Push Notification Dispatched!</b> If prompted, click <i>'Allow Notifications'</i> to receive desktop alerts.
    </div>
    """
    components.html(js_code, height=65)

# ==============================================================================
# 6. STREAMLIT UI CONFIGURATION & THEMING
# ==============================================================================
st.set_page_config(page_title="CareBridge AI — Recovery Companion", page_icon="🌉", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .big-font { font-size: 1.15rem !important; line-height: 1.6; }
    .hero-container {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.14) 0%, rgba(99, 102, 241, 0.20) 50%, rgba(168, 85, 247, 0.14) 100%);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
    }
    .hero-title {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px !important;
    }
    .badge-pill {
        display: inline-block; padding: 5px 14px; border-radius: 9999px;
        font-size: 0.82rem; font-weight: 600; margin-right: 8px; margin-bottom: 8px;
    }
    .badge-blue { background: rgba(14, 165, 233, 0.18); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.4); }
    .badge-purple { background: rgba(168, 85, 247, 0.18); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }
    .badge-green { background: rgba(34, 197, 94, 0.18); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
    
    .feature-card {
        background: rgba(30, 41, 59, 0.55); border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px; padding: 22px; transition: transform 0.25s ease; height: 100%;
    }
    .feature-card:hover { transform: translateY(-4px); border-color: rgba(99, 102, 241, 0.55); }
    
    .activity-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75), rgba(15, 23, 42, 0.85));
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 16px; padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .activity-log-item {
        background: rgba(255, 255, 255, 0.04);
        border-left: 3px solid #10b981;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 0.85rem;
    }
    .step-pill {
        background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 10px; padding: 10px 14px; text-align: center; font-weight: 600; font-size: 0.9rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div { gap: 6px !important; }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.04) !important; border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important; padding: 10px 14px !important; margin-bottom: 3px !important;
        transition: all 0.22s ease !important; cursor: pointer !important; width: 100% !important; display: flex !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: rgba(99, 102, 241, 0.18) !important; border-color: rgba(99, 102, 241, 0.5) !important; transform: translateX(4px) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked),
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(14, 165, 233, 0.22), rgba(99, 102, 241, 0.32)) !important;
        border: 1px solid rgba(56, 189, 248, 0.6) !important; border-left: 5px solid #38bdf8 !important; font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child { display: none !important; }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] input[type="radio"] { display: none !important; }
    blockquote {
        border-left: 4px solid #818cf8 !important; padding-left: 14px !important;
        background: rgba(99, 102, 241, 0.05); border-radius: 0 8px 8px 0; margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "extracted_text" not in st.session_state: st.session_state.extracted_text = ""
if "uploaded_filename" not in st.session_state: st.session_state.uploaded_filename = ""
if "api_key" not in st.session_state: st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "checklist_state" not in st.session_state: st.session_state.checklist_state = {}
if "activity_log" not in st.session_state: st.session_state.activity_log = []
if "user_name" not in st.session_state: st.session_state.user_name = "Rajesh Kumar"
if "user_country" not in st.session_state: st.session_state.user_country = "🇮🇳 India (+91)"
if "user_phone" not in st.session_state: st.session_state.user_phone = "9876543210"
if "is_signed_in" not in st.session_state: st.session_state.is_signed_in = True
if "show_browser_notif" not in st.session_state: st.session_state.show_browser_notif = None

# ==============================================================================
# SIDEBAR: BRANDING & PATIENT SIGN-IN / PROFILE
# ==============================================================================
st.sidebar.markdown("""
<div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.16) 0%, rgba(99, 102, 241, 0.22) 100%); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 16px; padding: 18px 14px; margin-bottom: 15px; text-align: center;">
    <div style="font-size: 2.2rem; margin-bottom: 4px;">🌉</div>
    <div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8;">CareBridge AI</div>
    <div style="font-size: 0.8rem; color: #cbd5e1; opacity: 0.9;">Your Personal Recovery Companion</div>
    <div style="margin-top: 8px;"><span style="background: rgba(56, 189, 248, 0.16); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 20px; font-size: 0.72rem; padding: 3px 10px; font-weight: 600;">v2.0 Enhanced</span></div>
</div>
""", unsafe_allow_html=True)

# Patient Phone Sign-in Card
with st.sidebar.expander("👤 Patient Sign-In & Mobile Profile", expanded=not st.session_state.is_signed_in):
    user_name_input = st.text_input("Patient / Caregiver Name:", value=st.session_state.user_name)
    country_choice = st.selectbox("Country Code:", list(COUNTRY_CODES.keys()), index=list(COUNTRY_CODES.keys()).index(st.session_state.user_country) if st.session_state.user_country in COUNTRY_CODES else 0)
    raw_phone_input = st.text_input("Mobile Number (10 digits):", value=st.session_state.user_phone, placeholder="e.g. 9876543210")
    
    clean_phone_digits = re.sub(r"[^\d]", "", raw_phone_input)
    if st.button("💾 Save Profile & Connect Device", use_container_width=True, type="primary"):
        if not user_name_input.strip():
            st.error("Please enter a patient or caregiver name.")
        elif len(clean_phone_digits) < 7:
            st.error("Please enter a valid phone number (at least 7 to 10 digits).")
        else:
            st.session_state.user_name = user_name_input.strip()
            st.session_state.user_country = country_choice
            st.session_state.user_phone = clean_phone_digits
            st.session_state.is_signed_in = True
            st.toast("Profile saved successfully!", icon="✅")
            st.rerun()

curr_prefix = COUNTRY_CODES.get(st.session_state.user_country, "+91")
st.sidebar.markdown(f"""
<div style="background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 10px 14px; margin-bottom: 14px;">
    <div style="font-size: 0.78rem; color: #4ade80; font-weight: 700;">🟢 CONNECTED PATIENT</div>
    <div style="font-size: 0.95rem; font-weight: 700; color: #f8fafc;">{st.session_state.user_name}</div>
    <div style="font-size: 0.8rem; color: #94a3b8;">📱 {curr_prefix} {st.session_state.user_phone}</div>
</div>
""", unsafe_allow_html=True)

nav_pages = ["🏠 Home", "📄 Upload & Review Document", "💡 Understand My Instructions", "🔍 Confusion Detector", "🗺️ My Recovery Journey", "♿ Accessibility & Audio"]
current_page = st.sidebar.radio("Navigation Menu:", nav_pages)
st.sidebar.divider()

if st.session_state.uploaded_filename:
    st.sidebar.markdown(f"<div style='background: rgba(34, 197, 94, 0.12); border-left: 4px solid #22c55e; border-radius: 10px; padding: 10px; margin-bottom: 10px;'><b style='color:#4ade80;'>🟢 Active Document:</b><br><small>{st.session_state.uploaded_filename}</small></div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div style='background: rgba(255, 255, 255, 0.04); border-radius: 10px; padding: 10px; margin-bottom: 10px;'><small style='opacity:0.7;'>⚪ No document loaded</small></div>", unsafe_allow_html=True)

if st.sidebar.button("🗑️ Clear Document & Reset", use_container_width=True):
    st.session_state.extracted_text = ""
    st.session_state.uploaded_filename = ""
    st.session_state.checklist_state = {}
    st.session_state.activity_log = []
    st.rerun()

with st.sidebar.expander("⚙️ Optional AI Settings"):
    custom_key = st.text_input("Gemini API Key (optional):", value=st.session_state.api_key if st.session_state.api_key != "your_gemini_api_key_here" else "", type="password")
    if custom_key != st.session_state.api_key: st.session_state.api_key = custom_key

# ==============================================================================
# PAGE 1: HOME
# ==============================================================================
if current_page == "🏠 Home":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">🌉 CareBridge AI</h1>
        <p style="font-size: 1.25rem; font-weight: 500; opacity: 0.95; margin-bottom: 14px;">From complex hospital instructions and cursive prescriptions to confident recovery at home.</p>
        <div>
            <span class="badge-pill badge-blue">✍️ Doctor Handwriting AI Vision</span>
            <span class="badge-pill badge-purple">🔔 Real Push & WhatsApp Alerts</span>
            <span class="badge-pill badge-green">📊 Side-by-Side Activity Tracker</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("Leaving the hospital or clinic can be overwhelming. Prescriptions are frequently written in hurried doctor cursive, while discharge summaries contain confusing medical abbreviations. **CareBridge AI** bridges this critical gap, converting clinical paperwork into clear instructions, daily checklists, and real reminders.")

    st.markdown("### 🌟 What CareBridge AI Does For You")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>✍️</div><h4 style='color:#38bdf8;'>Handwriting Deciphering</h4><p style='font-size:0.9rem; opacity:0.85;'>Specialized Multimodal AI Vision reads doctor cursive, abbreviation shorthands (1-0-0, OD, BD), and handwritten prescriptions.</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>🔍</div><h4 style='color:#fbbf24;'>Confusion Detector</h4><p style='font-size:0.9rem; opacity:0.85;'>Our proactive safety engine. Detects unreadable pills, conflicting follow-up dates, or missing schedules before mistakes occur.</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>📊</div><h4 style='color:#4ade80;'>Side-by-Side Tracker & Alerts</h4><p style='font-size:0.9rem; opacity:0.85;'>Track your daily checklist alongside a live activity log, with real desktop push notifications and direct WhatsApp reminder links.</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🗺️ How Your Recovery Journey Works")
    s1, s2, s3, s4 = st.columns(4)
    with s1: st.markdown("<div class='step-pill'>📄 1. Upload Document<br><small style='opacity:0.7;'>PDF, Scan, or Prescription</small></div>", unsafe_allow_html=True)
    with s2: st.markdown("<div class='step-pill'>✍️ 2. AI Deciphering<br><small style='opacity:0.7;'>Extract Handwriting & Text</small></div>", unsafe_allow_html=True)
    with s3: st.markdown("<div class='step-pill'>🔍 3. Confusion Scan<br><small style='opacity:0.7;'>Flag Safety Hazards</small></div>", unsafe_allow_html=True)
    with s4: st.markdown("<div class='step-pill'>📊 4. Daily Care & Alerts<br><small style='opacity:0.7;'>Side-by-Side Activity Tracker</small></div>", unsafe_allow_html=True)

    st.divider()
    st.warning("⚠️ **Important Medical Disclaimer**: CareBridge AI is an educational recovery assistant prototype. It does **not** diagnose medical conditions, alter physician prescriptions, or replace professional medical advice. Always consult your doctor or hospital pharmacist for clinical decisions.")

# ==============================================================================
# PAGE 2: UPLOAD & REVIEW DOCUMENT (WITH HANDWRITING VISION)
# ==============================================================================
elif current_page == "📄 Upload & Review Document":
    st.title("📄 Upload & Review Medical Document")
    st.write("Upload a hospital discharge summary, clinical note, or doctor's handwritten prescription.")

    upload_col, sample_col = st.columns([2, 1.2])
    with upload_col:
        doc_type_mode = st.radio(
            "Document Type:",
            ["📄 Standard Printed Document (PDF/Typed)", "✍️ Doctor Handwritten Prescription / Cursive Notes"],
            horizontal=True
        )
        uploaded_file = st.file_uploader("Upload your document (PDF, PNG, JPG, JPEG):", type=["pdf", "png", "jpg", "jpeg"], help=f"Max size: {MAX_FILE_SIZE_MB}MB.")
    
    with sample_col:
        st.markdown("**Or test with instant pre-loaded data:**")
        if st.button("📁 Load Standard Discharge Summary (PDF)", use_container_width=True, type="primary"):
            st.session_state.extracted_text = SAMPLE_DISCHARGE_TEXT
            st.session_state.uploaded_filename = "sample_discharge_summary.pdf"
            st.toast("Standard sample loaded successfully!", icon="✅")
            st.rerun()
            
        if st.button("✍️ Load Handwritten Prescription Sample", use_container_width=True):
            st.session_state.extracted_text = SAMPLE_HANDWRITTEN_PRESCRIPTION_TEXT
            st.session_state.uploaded_filename = "sample_handwritten_prescription.jpg"
            st.toast("Handwritten prescription sample loaded!", icon="✍️")
            st.rerun()

    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.uploaded_filename:
            is_valid, validation_msg = validate_uploaded_file(uploaded_file)
            if not is_valid:
                st.error(f"❌ {validation_msg}")
            else:
                file_bytes = uploaded_file.read()
                file_ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
                
                if file_ext == "pdf":
                    with st.spinner("Extracting text from PDF document..."):
                        extracted_text, success, msg = extract_text_from_pdf(file_bytes)
                else:
                    st.image(file_bytes, caption=f"Uploaded: {uploaded_file.name}", width=420)
                    
                    if "Handwritten" in doc_type_mode:
                        with st.spinner("🧠 Enhancing image contrast & deciphering doctor handwriting with AI Vision..."):
                            extracted_text, success, msg = extract_handwriting_with_gemini_vision(file_bytes, api_key=st.session_state.api_key)
                            if not success and not st.session_state.api_key:
                                # Graceful fallback to Tesseract with clear instructions
                                extracted_text, success, msg = extract_text_from_image(file_bytes)
                                msg += " (Tip: Enter a Gemini API Key in the sidebar for AI Vision cursive handwriting deciphering)."
                    else:
                        with st.spinner("Extracting printed text using OCR..."):
                            extracted_text, success, msg = extract_text_from_image(file_bytes)
                
                st.session_state.extracted_text = extracted_text
                st.session_state.uploaded_filename = uploaded_file.name
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.warning(f"⚠️ {msg}")

    if st.session_state.extracted_text or st.session_state.uploaded_filename:
        st.divider()
        st.subheader("📋 Review & Verify Extracted Medical Text")
        st.caption("CareBridge AI converted your document into digital text. Verify or adjust any specific dosage details below before proceeding:")
        edited_text = st.text_area(label="Document Text Content (Editable):", value=st.session_state.extracted_text, height=280)
        if edited_text != st.session_state.extracted_text:
            st.session_state.extracted_text = edited_text
        
        m1, m2 = st.columns(2)
        m1.metric("Character Count", len(st.session_state.extracted_text))
        m2.metric("Word Count", len(st.session_state.extracted_text.split()))

# ==============================================================================
# PAGE 3: UNDERSTAND MY INSTRUCTIONS
# ==============================================================================
elif current_page == "💡 Understand My Instructions":
    st.title("💡 Understand My Instructions")
    st.write("Clear, patient-friendly explanations of your discharge instructions and prescription.")
    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** to load your summary.")
    else:
        with st.spinner("Generating patient explanation..."):
            explanation_data = get_medical_explanation(st.session_state.extracted_text, api_key=st.session_state.api_key)
        st.caption(f"Analysis Engine: **{explanation_data.get('mode', 'Standard')}**")
        tab1, tab2, tab3 = st.tabs(["🌟 Patient Explanation", "📖 Medical Glossary", "💬 Ask Questions"])
        with tab1:
            col_exp, col_orig = st.columns([3, 2])
            with col_exp: st.markdown(explanation_data.get("summary", "No explanation available."))
            with col_orig:
                st.markdown("#### 📄 Original Source Text")
                st.info(st.session_state.extracted_text)
        with tab2:
            st.subheader("📖 Medical Terms Explained")
            glossary = explanation_data.get("glossary", {})
            if glossary:
                for term, definition in glossary.items():
                    with st.expander(f"🔹 {term}", expanded=True): st.write(definition)
            else: st.write("No specialized medical terms detected.")
        with tab3:
            st.subheader("💬 Patient Understanding Assistant")
            user_q = st.text_input("Enter your question:", placeholder="e.g., What follow-up appointment do I have? Or what is furosemide?")
            if st.button("Ask Assistant", type="primary"):
                if user_q.strip():
                    with st.spinner("Searching document..."):
                        ans = answer_patient_question(st.session_state.extracted_text, user_q, api_key=st.session_state.api_key)
                    st.markdown("#### 🤖 Answer:")
                    st.write(ans)

# ==============================================================================
# PAGE 4: CONFUSION DETECTOR
# ==============================================================================
elif current_page == "🔍 Confusion Detector":
    st.title("🔍 Confusion Detector")
    st.subheader("Identifying Ambiguous, Incomplete, or Conflicting Instructions")
    st.write("The **Confusion Detector** protects patient safety by flagging instructions that are unreadable, missing essential drug schedules, or contain conflicting dates.")

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** first.")
    else:
        with st.spinner("Scanning for medical ambiguities and cursive illegibility..."):
            confusions = analyze_document_confusion(st.session_state.extracted_text, api_key=st.session_state.api_key)

        if not confusions:
            st.success("✅ **No Ambiguities Detected!** All medication instructions and dates in this document appear clear and consistent.")
        else:
            st.warning(f"⚠️ **{len(confusions)} Item(s) Need Professional Confirmation** before taking action.")
            for idx, issue in enumerate(confusions):
                is_high = (issue.get("severity") == "High")
                icon = "🚨" if is_high else "⚠️"
                content = (
                    f"### {icon} Issue #{idx + 1}: {issue.get('issue_type')}\n\n"
                    f"**Original Text from Document:**\n> *\"{issue.get('original_text')}\"*\n\n"
                    f"**What is Unclear:**\n{issue.get('explanation')}\n\n"
                    f"**Recommended Safe Action:**\n{issue.get('recommendation')}\n\n"
                    f"**Status:** `{issue.get('status')}` ({issue.get('severity')} Severity)"
                )
                if is_high: st.error(content)
                else: st.warning(content)
            st.caption("🛡️ *Note: The Confusion Detector is a safety-support tool. It does not replace clinical judgment or review by your doctor or pharmacist.*")

# ==============================================================================
# PAGE 5: RECOVERY JOURNEY MAP (SIDE-BY-SIDE CHECKLIST & ACTIVITY TRACKER)
# ==============================================================================
elif current_page == "🗺️ My Recovery Journey":
    st.title("🗺️ My Recovery Journey")
    st.write("A structured recovery dashboard with side-by-side daily checklist, activity completion log, and real device alerts.")

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** first.")
    else:
        plan = build_recovery_plan(st.session_state.extracted_text, api_key=st.session_state.api_key)
        reminders = extract_reminders_schedule(plan)
        
        tab_checklist, tab_reminders = st.tabs(["📋 Daily Recovery Checklist & Activity Tracker", "⏰ Timings, Dates & Real Reminders"])

        # ----------------------------------------------------------------------
        # TAB 1: SIDE-BY-SIDE CHECKLIST & LIVE ACTIVITY TRACKER
        # ----------------------------------------------------------------------
        with tab_checklist:
            col_check, col_activity = st.columns([1.15, 0.85], gap="large")
            
            with col_check:
                st.markdown("### 📋 Daily Recovery Checklist")
                st.caption("Check off items as you complete them throughout your day.")

                if plan.get("warnings"):
                    st.markdown("#### 🚨 Urgent Warning Signs (Red Flags)")
                    for w in plan["warnings"]: 
                        st.error(f"**Emergency Alert**: {w['task']} — Seek immediate emergency care if this occurs.")

                st.markdown("#### 💊 Confirmed Medications")
                if plan.get("medications"):
                    for med in plan["medications"]:
                        chk_key = f"med_{med['task']}"
                        prev_state = st.session_state.checklist_state.get(chk_key, False)
                        val = st.checkbox(f"**{med['task']}**", value=prev_state, key=f"chk_{chk_key}")
                        if val != prev_state:
                            st.session_state.checklist_state[chk_key] = val
                            timestamp = datetime.now().strftime("%I:%M %p")
                            status_label = "Completed" if val else "Unchecked"
                            st.session_state.activity_log.insert(0, {"task": med['task'], "time": timestamp, "status": status_label, "cat": "Medication"})
                            st.rerun()
                else: 
                    st.info("No confirmed medication instructions identified.")

                st.markdown("#### 🥗 Diet & Lifestyle Instructions")
                if plan.get("diet_lifestyle"):
                    for diet in plan["diet_lifestyle"]:
                        chk_key = f"diet_{diet['task']}"
                        prev_state = st.session_state.checklist_state.get(chk_key, False)
                        val = st.checkbox(diet['task'], value=prev_state, key=f"chk_{chk_key}")
                        if val != prev_state:
                            st.session_state.checklist_state[chk_key] = val
                            timestamp = datetime.now().strftime("%I:%M %p")
                            status_label = "Completed" if val else "Unchecked"
                            st.session_state.activity_log.insert(0, {"task": diet['task'], "time": timestamp, "status": status_label, "cat": "Diet"})
                            st.rerun()
                else: 
                    st.write("No specific diet instructions noted.")

                if plan.get("wound_care"):
                    st.markdown("#### 🩹 Surgical Wound Care")
                    for w in plan["wound_care"]:
                        chk_key = f"wound_{w['task']}"
                        prev_state = st.session_state.checklist_state.get(chk_key, False)
                        val = st.checkbox(w['task'], value=prev_state, key=f"chk_{chk_key}")
                        if val != prev_state:
                            st.session_state.checklist_state[chk_key] = val
                            timestamp = datetime.now().strftime("%I:%M %p")
                            status_label = "Completed" if val else "Unchecked"
                            st.session_state.activity_log.insert(0, {"task": w['task'], "time": timestamp, "status": status_label, "cat": "Wound Care"})
                            st.rerun()

                st.markdown("#### 📅 Clinic Appointments")
                if plan.get("followups"):
                    for appt in plan["followups"]: st.info(f"🗓️ **Scheduled Visit**: {appt['task']}")
                else: 
                    st.write("No confirmed appointment dates listed.")

                if plan.get("needs_confirmation"):
                    st.markdown("#### ⚠️ Instructions Requiring Confirmation")
                    for conf in plan["needs_confirmation"]: 
                        st.warning(f"**Needs Confirmation**: {conf.get('original_text')} — *{conf.get('explanation')}*")

            # Beside the checklist: Live Activity Tracker!
            with col_activity:
                st.markdown("""
                <div class="activity-card">
                    <h3 style="margin-top:0; color:#38bdf8; font-size:1.25rem;">📈 Live Activity Tracker</h3>
                    <p style="font-size:0.85rem; color:#94a3b8; margin-bottom:12px;">Real-time adherence log beside your checklist.</p>
                """, unsafe_allow_html=True)
                
                # Metrics Calculation
                total_tasks = len(st.session_state.checklist_state)
                completed_tasks = sum(1 for v in st.session_state.checklist_state.values() if v)
                pct = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
                
                m_c1, m_c2 = st.columns(2)
                m_c1.metric("Tasks Completed", f"{completed_tasks} / {total_tasks}")
                m_c2.metric("Adherence Rate", f"{pct}%")
                
                st.progress(pct / 100.0)
                
                # Streak & Adherence Badge
                if pct == 100 and total_tasks > 0:
                    st.markdown("<div style='background: rgba(34, 197, 94, 0.2); border:1px solid #22c55e; border-radius:10px; padding:8px 12px; text-align:center; color:#4ade80; font-weight:700; margin:10px 0;'>🏆 All Tasks Completed Today! Excellent adherence!</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='background: rgba(99, 102, 241, 0.15); border:1px solid rgba(99, 102, 241, 0.35); border-radius:10px; padding:8px 12px; text-align:center; color:#a5b4fc; font-weight:600; margin:10px 0;'>🔥 3-Day Adherence Streak</div>", unsafe_allow_html=True)
                
                st.markdown("#### 🕒 Recent Activity Log")
                if st.session_state.activity_log:
                    # Show last 6 activity items
                    for item in st.session_state.activity_log[:6]:
                        icon = "✅" if item["status"] == "Completed" else "↩️"
                        color = "#10b981" if item["status"] == "Completed" else "#94a3b8"
                        st.markdown(f"""
                        <div class="activity-log-item" style="border-left-color: {color};">
                            <b>{icon} [{item['time']}]</b>: {item['task'][:45]}... <span style="float:right; opacity:0.75; font-size:0.75rem;">{item['status']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("⚪ No activity recorded yet today. Check off your first task on the left to start tracking!")
                
                st.markdown("<br>", unsafe_allow_html=True)
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("✅ Mark All Done", use_container_width=True):
                        for k in st.session_state.checklist_state.keys():
                            st.session_state.checklist_state[k] = True
                        timestamp = datetime.now().strftime("%I:%M %p")
                        st.session_state.activity_log.insert(0, {"task": "All daily tasks", "time": timestamp, "status": "Completed", "cat": "General"})
                        st.rerun()
                with btn_c2:
                    if st.button("🔄 Reset Checklist", use_container_width=True):
                        for k in st.session_state.checklist_state.keys():
                            st.session_state.checklist_state[k] = False
                        st.session_state.activity_log = []
                        st.rerun()
                        
                st.markdown("</div>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # TAB 2: REMINDERS & REAL NOTIFICATIONS (WEB PUSH + WHATSAPP + SMS)
        # ----------------------------------------------------------------------
        with tab_reminders:
            st.subheader("⏰ Daily Schedule & Multi-Channel Reminder Dispatcher")
            st.caption(f"Connected Device: **{st.session_state.user_name}** ({curr_prefix} {st.session_state.user_phone})")
            
            col_morn, col_eve, col_appt = st.columns(3)
            with col_morn:
                st.markdown("#### 🌅 Morning (08:00 AM)")
                morning_items = [r for r in reminders if r["schedule_slot"] == "Morning"]
                if morning_items:
                    for item in morning_items:
                        st.markdown(f"<div style='background: rgba(245, 158, 11, 0.08); border-left: 5px solid #f59e0b; border-radius: 12px; padding: 12px; margin-bottom: 10px;'><b style='color:#fbbf24;'>💊 {item['title']}</b><br><small>⏰ {item['timing']}</small><br><small>{item['details']}</small></div>", unsafe_allow_html=True)
                else: st.write("No morning medications scheduled.")

            with col_eve:
                st.markdown("#### 🌙 Evening / Night (08:00 PM)")
                evening_items = [r for r in reminders if r["schedule_slot"] in ["Evening", "Night"]]
                if evening_items:
                    for item in evening_items:
                        st.markdown(f"<div style='background: rgba(129, 140, 248, 0.08); border-left: 5px solid #818cf8; border-radius: 12px; padding: 12px; margin-bottom: 10px;'><b style='color:#a5b4fc;'>💊 {item['title']}</b><br><small>⏰ {item['timing']}</small><br><small>{item['details']}</small></div>", unsafe_allow_html=True)
                else: st.write("No evening medications scheduled.")

            with col_appt:
                st.markdown("#### 📅 Doctor Consultations")
                appt_items = [r for r in reminders if r["schedule_slot"] == "Appointment"]
                if appt_items:
                    for item in appt_items:
                        st.markdown(f"<div style='background: rgba(16, 185, 129, 0.08); border-left: 5px solid #10b981; border-radius: 12px; padding: 12px; margin-bottom: 10px;'><b style='color:#34d399;'>🏥 {item['title']}</b><br><small>🗓️ {item['timing']}</small><br><small>{item['details']}</small></div>", unsafe_allow_html=True)
                else: st.write("No clinic appointments detected.")

            st.divider()
            st.markdown("### 📲 Send Real Notification to Patient or Caregiver")
            st.write("Trigger an actual alert directly to your phone, desktop, WhatsApp, or SMS messaging app.")

            selectable_reminders = [r for r in reminders if r["status"] != "Needs Confirmation"]
            if selectable_reminders:
                options = [f"{r['type']}: {r['title']} ({r['timing']})" for r in selectable_reminders]
                selected_option = st.selectbox("Select which reminder alert to send:", options)
                selected_idx = options.index(selected_option)
                chosen = selectable_reminders[selected_idx]

                clean_user_phone = re.sub(r"[^\d]", "", f"{curr_prefix}{st.session_state.user_phone}")
                encoded_message = urllib.parse.quote(chosen["alert_message"])
                whatsapp_url = f"https://wa.me/{clean_user_phone}?text={encoded_message}"
                sms_url = f"sms:{clean_user_phone}?body={encoded_message}"

                alert_col1, alert_col2 = st.columns([1.1, 0.9])
                with alert_col1:
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 16px; margin-bottom: 14px;">
                        <div style="font-size:0.8rem; color:#94a3b8;">ALERT MESSAGE PREVIEW:</div>
                        <div style="font-weight:600; color:#f1f5f9; margin-top:4px;">{chosen['alert_message']}</div>
                        <div style="font-size:0.8rem; color:#38bdf8; margin-top:8px;">Target: {st.session_state.user_name} ({curr_prefix} {st.session_state.user_phone})</div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("🔔 Send Real Browser Push Notification", type="primary", use_container_width=True):
                            st.session_state.show_browser_notif = chosen
                    
                    with btn_c2:
                        st.link_button(
                            "📲 Send via WhatsApp",
                            url=whatsapp_url,
                            use_container_width=True,
                            type="secondary"
                        )
                    
                    sms_c1, sms_c2 = st.columns(2)
                    with sms_c1:
                        st.link_button(
                            "💬 Send via SMS / Messages",
                            url=sms_url,
                            use_container_width=True
                        )
                    with sms_c2:
                        ics_data = generate_ics_calendar(reminders)
                        st.download_button(
                            label="📥 Download Calendar (.ics)",
                            data=ics_data,
                            file_name="carebridge_schedule.ics",
                            mime="text/calendar",
                            use_container_width=True
                        )

                    if st.session_state.show_browser_notif:
                        send_browser_notification_js(
                            title=f"CareBridge AI: {st.session_state.show_browser_notif['title']}",
                            message=st.session_state.show_browser_notif['alert_message']
                        )

                with alert_col2:
                    st.markdown("""
                    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 12px; padding: 16px;">
                        <h4 style="color:#a5b4fc; margin-top:0;">🛡️ Multi-Channel Alert Delivery</h4>
                        <ul style="font-size:0.85rem; color:#cbd5e1; padding-left:18px;">
                            <li><b>Real Browser Notifications</b>: Uses the HTML5 Desktop Notification API with audible alarm chime directly on your computer or Android screen.</li>
                            <li><b>WhatsApp Direct Link</b>: Opens your WhatsApp with the medication time and instructions pre-formatted for 1-tap delivery.</li>
                            <li><b>Native SMS</b>: Prepares a mobile SMS directly addressed to the patient's saved phone number.</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

# ==============================================================================
# PAGE 6: ACCESSIBILITY & AUDIO
# ==============================================================================
elif current_page == "♿ Accessibility & Audio":
    st.title("♿ Accessibility & Audio Instructions")
    st.write("CareBridge AI is designed for universal accessibility, including seniors and caregivers.")
    st.subheader("🔊 Text-to-Speech (Listen Aloud)")

    lang_choice = st.selectbox("Choose Speech Language:", ["English (en)", "Hindi (hi)", "Telugu (te)"])
    lang_code = lang_choice.split("(")[-1].replace(")", "").strip()
    text_to_speak = st.text_area("Text to Read Aloud:", value=st.session_state.extracted_text[:600] if st.session_state.extracted_text else "Welcome to CareBridge AI. Your personal recovery companion.", height=160)

    if st.button("🎧 Generate Audio", type="primary"):
        if text_to_speak.strip():
            with st.spinner("Generating audio..."):
                try:
                    fp = io.BytesIO()
                    tts = gTTS(text=text_to_speak, lang=lang_code)
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    st.audio(fp.read(), format="audio/mp3")
                    st.success("✅ Audio ready! Click play above to listen.")
                except Exception as tts_err:
                    st.error(f"Error generating audio: {tts_err}")
