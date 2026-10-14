import streamlit as st
import os
import sys
import io
import re
import json
from datetime import datetime
import requests
from pypdf import PdfReader
from PIL import Image
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
    "sodium restricted": "Eating less salt to prevent fluid retention and protect your heart and kidneys.",
    "post-op": "Post-operative, meaning the period right after surgery."
}

# ==============================================================================
# 2. DOCUMENT PROCESSING FUNCTIONS
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

def extract_text_from_image(image_bytes):
    try:
        import pytesseract
        image = Image.open(io.BytesIO(image_bytes))
        try:
            text = pytesseract.image_to_string(image).strip()
            if not text:
                return "", False, "OCR completed, but no text could be recognized in this image."
            return text, True, "Successfully extracted text using OCR."
        except Exception:
            return "", False, (
                "Tesseract OCR is not installed on this cloud environment. "
                "You can still view the image and type or paste the text directly into the editor below."
            )
    except Exception as img_err:
        return "", False, f"Invalid or unreadable image file: {str(img_err)}"

# ==============================================================================
# 3. CONFUSION DETECTOR ENGINE
# ==============================================================================
def detect_confusions_rule_based(document_text: str):
    issues = []
    lines = [line.strip() for line in document_text.split("\n") if line.strip()]
    flagged_med_lines = set()

    for line in lines:
        lower_line = line.lower()
        if any(term in lower_line for term in ["unreadable", "illegible", "blurred", "smudged", "medicine name"]):
            if line not in flagged_med_lines:
                flagged_med_lines.add(line)
                issues.append({
                    "issue_type": "Unclear Medication Reference",
                    "severity": "High",
                    "original_text": line,
                    "explanation": "This instruction describes taking medication, but the specific medicine name is missing or marked unreadable.",
                    "recommendation": "Do NOT take any unknown pill. Contact your doctor or hospital pharmacist immediately to verify the exact drug name.",
                    "status": "Needs Confirmation"
                })
        elif re.search(r"\btake\s+(?:one|two|\d+)?\s*(?:tablet|pill|capsule|dose)", lower_line):
            known_meds = ["lisinopril", "furosemide", "metoprolol", "acetaminophen", "cephalexin", "aspirin", "amoxicillin", "atorvastatin", "ibuprofen"]
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
    followup_lines = [l for l in lines if any(w in l.lower() for w in ["follow-up", "follow up", "appointment", "clinic note", "return to"])]
    if len(followup_lines) >= 2:
        dates_in_followups = []
        for fl in followup_lines:
            found = re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?", fl, re.IGNORECASE)
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
        if any(w in lower_line for w in ["diet", "sodium", "salt", "fluid", "lifting", "weight", "lbs", "mg/dl"]):
            continue
        if re.search(r"\b\d+\s*(?:mg|mcg|ml)\b", lower_line) and any(m in lower_line for m in ["tablet", "capsule", "take", "pill"]):
            has_timing = any(t in lower_line for t in ["daily", "morning", "night", "evening", "hour", "times", "bedtime", "needed", "q8h", "bid", "tid", "qid"])
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
            prompt = f"""You are the 'Confusion Detector' for CareBridge AI. Identify unclear, incomplete, or contradictory instructions in this hospital discharge summary:
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
            prompt = f"""You are the Medical Explainer for CareBridge AI. Convert this discharge summary into simple, patient-friendly language.
Strict Rules: Preserve all medication names, dosages, and dates exactly without alterations.
Text:
\"\"\"{document_text}\"\"\"
Return a JSON object with:
- "summary": Clear markdown with bullet points.
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
        if any(w in low for w in ["medication", "medicine", "rx"]): curr = "Medications"; continue
        elif any(w in low for w in ["diet", "activity", "wound"]): curr = "Diet & Daily Care"; continue
        elif any(w in low for w in ["follow-up", "appointment", "clinic"]): curr = "Follow-Up Appointments"; continue
        elif any(w in low for w in ["warning", "red flag", "emergency"]): curr = "Warning Signs (Red Flags)"; continue
        cleaned = l.lstrip("-*•1234567890. ")
        if cleaned: sections[curr].append(cleaned)
    
    parts = ["### 🌟 Plain Language Summary\nHere is your discharge summary explained in simple everyday words:\n"]
    for s_name, items in sections.items():
        if items:
            parts.append(f"#### 📌 {s_name}")
            for it in items:
                if s_name == "Medications": parts.append(f"- **{it}** *(Take exactly as written; do not alter dose)*")
                elif s_name == "Warning Signs (Red Flags)": parts.append(f"- 🚨 **{it}** *(Seek immediate care if this occurs)*")
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
            prompt = f"Answer strictly using this discharge summary only. If not mentioned, state so clearly. Never diagnose or change medicines.\nDoc:\n{document_text}\nQuestion: {question}"
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=12)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    low_q = question.lower()
    for term, definition in MEDICAL_GLOSSARY.items():
        if term in low_q: return f"**{term.title()}**: {definition} (Source: CareBridge Medical Reference)"
    if any(w in low_q for w in ["appointment", "follow up", "clinic", "when"]):
        follow_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["follow-up", "appointment", "clinic"])]
        if follow_lines: return "Based on your document, here are the follow-up instructions:\n" + "\n".join(follow_lines)
    if any(w in low_q for w in ["medicine", "medication", "pill", "tablet"]):
        med_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["mg", "tablet", "capsule", "take"])]
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
            if any(h in lower for h in ["medication", "medicine", "rx"]) and len(lower) < 35: curr = "medications"; continue
            elif any(h in lower for h in ["diet", "nutrition", "activity"]) and len(lower) < 35: curr = "diet_lifestyle"; continue
            elif any(h in lower for h in ["follow-up", "appointment"]) and len(lower) < 35: curr = "followups"; continue
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
            if any(w in lower for w in ["mg", "tablet", "take "]) and not is_confused:
                plan["medications"].append({"task": cleaned, "category": "Medication", "status": "Confirmed"})
            elif any(w in lower for w in ["appointment", "clinic", "return on"]):
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
        if any(w in low for w in ["morning", "breakfast", "every morning", "daily"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
        if any(w in low for w in ["twice daily", "twice a day", "bid"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
            slots.append({"slot": "Evening", "time": "08:00 PM"})
        elif any(w in low for w in ["night", "evening", "bedtime"]):
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
                    "alert_message": f"[Medication Reminder - {s['time']}]: Time to take {task}. Take with water.",
                    "status": "Active"
                })

    for appt in plan.get("followups", []):
        task = appt["task"]
        date_m = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}", task, re.IGNORECASE)
        time_m = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b", task)
        a_date = date_m.group(0) if date_m else "Upcoming date"
        a_time = time_m.group(0) if time_m else "Clinic hours"
        reminders.append({
            "type": "Doctor Consultation",
            "title": "Hospital / Clinic Follow-up",
            "details": task,
            "schedule_slot": "Appointment",
            "timing": f"{a_date} at {a_time}",
            "alert_message": f"[Doctor Appointment Reminder]: Scheduled visit on {a_date} ({a_time}). Details: {task}.",
            "status": "Scheduled"
        })

    for conf in plan.get("needs_confirmation", []):
        reminders.append({
            "type": "Requires Confirmation",
            "title": f"Needs Confirmation: {conf.get('issue_type', 'Unclear Instruction')}",
            "details": conf.get("original_text", ""),
            "schedule_slot": "Action Required",
            "timing": "Paused for Safety",
            "alert_message": f"[Safety Alert - Needs Confirmation]: '{conf.get('original_text')}'. Please confirm with your doctor.",
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

# ==============================================================================
# 6. STREAMLIT UI CONFIGURATION & THEMING
# ==============================================================================
st.set_page_config(page_title="CareBridge AI — Recovery Companion", page_icon="🌉", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .big-font { font-size: 1.15rem !important; line-height: 1.6; }
    .hero-container {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(99, 102, 241, 0.18) 50%, rgba(168, 85, 247, 0.12) 100%);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
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
        background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 22px; transition: transform 0.25s ease; height: 100%;
    }
    .feature-card:hover { transform: translateY(-4px); border-color: rgba(99, 102, 241, 0.55); }
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

# State
if "extracted_text" not in st.session_state: st.session_state.extracted_text = ""
if "uploaded_filename" not in st.session_state: st.session_state.uploaded_filename = ""
if "api_key" not in st.session_state: st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "checklist_state" not in st.session_state: st.session_state.checklist_state = {}

# Sidebar Navigation
st.sidebar.markdown("""
<div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.16) 0%, rgba(99, 102, 241, 0.22) 100%); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 16px; padding: 18px 14px; margin-bottom: 20px; text-align: center;">
    <div style="font-size: 2.2rem; margin-bottom: 4px;">🌉</div>
    <div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8;">CareBridge AI</div>
    <div style="font-size: 0.8rem; color: #cbd5e1; opacity: 0.9;">Recovery Companion</div>
    <div style="margin-top: 8px;"><span style="background: rgba(56, 189, 248, 0.16); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 20px; font-size: 0.72rem; padding: 3px 10px; font-weight: 600;">v1.0 Live</span></div>
</div>
""", unsafe_allow_html=True)

nav_pages = ["🏠 Home", "📄 Upload & Review Document", "💡 Understand My Instructions", "🔍 Confusion Detector", "🗺️ My Recovery Journey", "♿ Accessibility & Audio"]
current_page = st.sidebar.radio("Navigation Menu:", nav_pages)
st.sidebar.divider()
st.sidebar.subheader("🔒 Privacy & Safety")

if st.session_state.uploaded_filename:
    st.sidebar.markdown(f"<div style='background: rgba(34, 197, 94, 0.12); border-left: 4px solid #22c55e; border-radius: 10px; padding: 10px; margin-bottom: 10px;'><b style='color:#4ade80;'>🟢 Active File:</b><br><small>{st.session_state.uploaded_filename}</small></div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div style='background: rgba(255, 255, 255, 0.04); border-radius: 10px; padding: 10px; margin-bottom: 10px;'><small style='opacity:0.7;'>⚪ No document loaded</small></div>", unsafe_allow_html=True)

if st.sidebar.button("🗑️ Clear Document & Reset", use_container_width=True):
    st.session_state.extracted_text = ""
    st.session_state.uploaded_filename = ""
    st.session_state.checklist_state = {}
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
        <p style="font-size: 1.25rem; font-weight: 500; opacity: 0.95; margin-bottom: 14px;">From hospital instructions to confident recovery.</p>
        <div>
            <span class="badge-pill badge-blue">🛡️ Responsible AI Prototype</span>
            <span class="badge-pill badge-purple">⚡ Instant Offline Safety Parser</span>
            <span class="badge-pill badge-green">♿ Universal Accessibility</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("Leaving the hospital after surgery or illness can be overwhelming. Hospital discharge summaries are often dense with complicated clinical terminology, fragmented medication doses, and vital follow-up dates. **CareBridge AI** bridges the gap between complicated hospital paperwork and your recovery at home.")

    st.markdown("### 🌟 What CareBridge AI Does For You")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>💡</div><h4 style='color:#38bdf8;'>Understand</h4><p style='font-size:0.9rem; opacity:0.85;'>Converts medical jargon into clear explanations while strictly preserving exact dosages and dates.</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>🔍</div><h4 style='color:#fbbf24;'>Confusion Detector</h4><p style='font-size:0.9rem; opacity:0.85;'>Our unique safety engine. Identifies unreadable medicines, missing schedules, or conflicting dates before mistakes happen.</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='feature-card'><div style='font-size:2rem; margin-bottom:8px;'>🗺️</div><h4 style='color:#4ade80;'>Recovery Journey</h4><p style='font-size:0.9rem; opacity:0.85;'>Interactive daily checklist with progress tracking, reminder alerts, and phone calendar sync (.ics).</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🗺️ How Your Recovery Journey Works")
    s1, s2, s3, s4 = st.columns(4)
    with s1: st.markdown("<div class='step-pill'>📄 1. Upload Summary<br><small style='opacity:0.7;'>PDF or Photo</small></div>", unsafe_allow_html=True)
    with s2: st.markdown("<div class='step-pill'>📋 2. Review Text<br><small style='opacity:0.7;'>Verify Extracted Notes</small></div>", unsafe_allow_html=True)
    with s3: st.markdown("<div class='step-pill'>🔍 3. Confusion Scan<br><small style='opacity:0.7;'>Flag Safety Hazards</small></div>", unsafe_allow_html=True)
    with s4: st.markdown("<div class='step-pill'>🗺️ 4. Daily Care Plan<br><small style='opacity:0.7;'>Checklist & Reminders</small></div>", unsafe_allow_html=True)

    st.divider()
    st.warning("⚠️ **Important Medical Disclaimer**: CareBridge AI is an educational prototype developed for patient understanding. It does **not** diagnose medical conditions, prescribe treatments, alter prescriptions, or replace professional medical advice. Always consult your doctor or pharmacist for any medical decisions.")

# ==============================================================================
# PAGE 2: UPLOAD & REVIEW DOCUMENT
# ==============================================================================
elif current_page == "📄 Upload & Review Document":
    st.title("📄 Upload & Review Discharge Document")
    st.write("Upload your hospital discharge summary or clinic notes to begin.")

    upload_col, sample_col = st.columns([2, 1])
    with upload_col:
        uploaded_file = st.file_uploader("Select a discharge summary file (PDF, PNG, JPG, JPEG):", type=["pdf", "png", "jpg", "jpeg"], help=f"Max size: {MAX_FILE_SIZE_MB}MB.")
    with sample_col:
        st.write("**Or try with a sample document:**")
        sample_path = os.path.join("sample_documents", "sample_discharge_summary.pdf")
        if os.path.exists(sample_path):
            if st.button("📁 Load Sample Discharge Summary", use_container_width=True):
                with open(sample_path, "rb") as f:
                    pdf_bytes = f.read()
                text, success, msg = extract_text_from_pdf(pdf_bytes)
                if success:
                    st.session_state.extracted_text = text
                    st.session_state.uploaded_filename = "sample_discharge_summary.pdf"
                    st.toast("Sample loaded successfully!", icon="✅")
                    st.rerun()

    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.uploaded_filename:
            is_valid, validation_msg = validate_uploaded_file(uploaded_file)
            if not is_valid:
                st.error(f"❌ {validation_msg}")
            else:
                file_bytes = uploaded_file.read()
                file_ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
                with st.spinner("Extracting text from your document..."):
                    if file_ext == "pdf":
                        extracted_text, success, msg = extract_text_from_pdf(file_bytes)
                    else:
                        st.image(file_bytes, caption=f"Uploaded: {uploaded_file.name}", width=400)
                        extracted_text, success, msg = extract_text_from_image(file_bytes)
                if success:
                    st.session_state.extracted_text = extracted_text
                    st.session_state.uploaded_filename = uploaded_file.name
                    st.success(f"✅ {msg}")
                else:
                    st.warning(f"⚠️ {msg}")
                    st.session_state.uploaded_filename = uploaded_file.name

    if st.session_state.extracted_text or st.session_state.uploaded_filename:
        st.divider()
        st.subheader("📋 Review Extracted Medical Text")
        st.caption("CareBridge AI extracted this text from your document. You can review and correct any typos below before analyzing.")
        edited_text = st.text_area(label="Document Content (Editable):", value=st.session_state.extracted_text, height=260)
        if edited_text != st.session_state.extracted_text:
            st.session_state.extracted_text = edited_text
        st.metric("Total Characters", len(st.session_state.extracted_text))

# ==============================================================================
# PAGE 3: UNDERSTAND MY INSTRUCTIONS
# ==============================================================================
elif current_page == "💡 Understand My Instructions":
    st.title("💡 Understand My Instructions")
    st.write("Clear, patient-friendly explanations of your discharge instructions.")
    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** to upload your summary.")
    else:
        with st.spinner("Analyzing document..."):
            explanation_data = get_medical_explanation(st.session_state.extracted_text, api_key=st.session_state.api_key)
        st.caption(f"Engine: **{explanation_data.get('mode', 'Standard')}**")
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
# PAGE 4: CONFUSION DETECTOR (THE UNIQUE FEATURE!)
# ==============================================================================
elif current_page == "🔍 Confusion Detector":
    st.title("🔍 Confusion Detector")
    st.subheader("Identifying Ambiguous, Incomplete, or Conflicting Instructions")
    st.write("The **Confusion Detector** protects patient safety by flagging instructions that are unclear, missing essential drug details, or contain conflicting dates.")

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** first.")
    else:
        with st.spinner("Scanning for medical ambiguities..."):
            confusions = analyze_document_confusion(st.session_state.extracted_text, api_key=st.session_state.api_key)

        if not confusions:
            st.success("✅ **No Ambiguities Detected!** All medication instructions and dates in this document appear clear and consistent.")
        else:
            st.warning(f"⚠️ **{len(confusions)} Item(s) Need Professional Confirmation** before you act on them.")
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
# PAGE 5: RECOVERY JOURNEY MAP
# ==============================================================================
elif current_page == "🗺️ My Recovery Journey":
    st.title("🗺️ My Recovery Journey")
    st.write("A structured recovery dashboard and daily checklist based only on your document.")

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** first.")
    else:
        plan = build_recovery_plan(st.session_state.extracted_text, api_key=st.session_state.api_key)
        reminders = extract_reminders_schedule(plan)
        tab_checklist, tab_reminders = st.tabs(["📋 Daily Recovery Checklist", "⏰ Timings, Dates & Reminder Alerts"])

        with tab_checklist:
            if plan.get("warnings"):
                st.markdown("### 🚨 Urgent Warning Signs (Red Flags)")
                for w in plan["warnings"]: st.error(f"**Emergency Sign**: {w['task']} — Contact your doctor immediately if this occurs.")
            
            st.markdown("### 💊 Confirmed Medications")
            if plan.get("medications"):
                for med in plan["medications"]:
                    chk_key = f"med_{med['task']}"
                    st.session_state.checklist_state[chk_key] = st.checkbox(f"**{med['task']}**", value=st.session_state.checklist_state.get(chk_key, False))
            else: st.info("No confirmed medication instructions identified.")

            col_diet, col_wound = st.columns(2)
            with col_diet:
                st.markdown("### 🥗 Diet & Activity")
                if plan.get("diet_lifestyle"):
                    for diet in plan["diet_lifestyle"]:
                        chk_key = f"diet_{diet['task']}"
                        st.session_state.checklist_state[chk_key] = st.checkbox(diet['task'], value=st.session_state.checklist_state.get(chk_key, False))
                else: st.write("No specific diet instructions noted.")
            with col_wound:
                st.markdown("### 🩹 Wound Care")
                if plan.get("wound_care"):
                    for w in plan["wound_care"]:
                        chk_key = f"wound_{w['task']}"
                        st.session_state.checklist_state[chk_key] = st.checkbox(w['task'], value=st.session_state.checklist_state.get(chk_key, False))
                else: st.write("No surgical wound care required.")

            st.markdown("### 📅 Follow-Up Appointments")
            if plan.get("followups"):
                for appt in plan["followups"]: st.info(f"🗓️ **Scheduled Visit**: {appt['task']}")
            else: st.write("No confirmed appointment dates listed.")

            if plan.get("needs_confirmation"):
                st.markdown("### ⚠️ Instructions Requiring Confirmation")
                for conf in plan["needs_confirmation"]: st.warning(f"**Needs Confirmation**: {conf.get('original_text')} — *{conf.get('explanation')}*")

            st.divider()
            st.subheader("📊 Your Daily Recovery Checklist Progress")
            total_tasks = len(st.session_state.checklist_state)
            completed_tasks = sum(1 for v in st.session_state.checklist_state.values() if v)
            if total_tasks > 0:
                progress_val = completed_tasks / total_tasks
                st.progress(progress_val)
                st.write(f"**{completed_tasks} of {total_tasks} tasks completed ({int(progress_val * 100)}%)**")

        with tab_reminders:
            st.subheader("⏰ Daily Medication Schedule & Appointment Calendar")
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
            st.subheader("📲 Test Reminder & Alert Simulator")
            selectable_reminders = [r for r in reminders if r["status"] != "Needs Confirmation"]
            if selectable_reminders:
                options = [f"{r['type']}: {r['title']} ({r['timing']})" for r in selectable_reminders]
                selected_option = st.selectbox("Choose a reminder to test:", options)
                selected_idx = options.index(selected_option)
                chosen = selectable_reminders[selected_idx]
                test_c1, test_c2 = st.columns([1, 2])
                with test_c1:
                    phone_input = st.text_input("Mobile Number (Simulated):", value="+1 (555) 234-5678")
                    if st.button("🔔 Send Simulated Reminder Alert", type="primary", use_container_width=True):
                        st.toast("📲 Alert sent!", icon="🔔")
                        st.success(f"**Simulated Phone Alert sent to {phone_input}:**\n\n> {chosen['alert_message']}")
                with test_c2:
                    st.code(f"From: CareBridge AI\nTo: {phone_input}\nTime: {chosen['timing']}\nMessage: {chosen['alert_message']}", language="text")

            st.divider()
            st.subheader("📅 Export to Phone Calendar")
            ics_content = generate_ics_calendar(reminders)
            st.download_button(label="📥 Download Calendar Reminders (.ics)", data=ics_content, file_name="carebridge_schedule.ics", mime="text/calendar")

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
