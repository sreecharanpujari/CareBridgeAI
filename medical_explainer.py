import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Common Medical Glossary for offline / local explanations
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

def explain_terms_in_text(text: str):
    """Identifies and explains medical terms present in the text."""
    found_terms = {}
    lower = text.lower()
    for term, definition in MEDICAL_GLOSSARY.items():
        if term in lower:
            found_terms[term.title()] = definition
    return found_terms

def generate_local_explanation(document_text: str):
    """
    Offline patient-friendly explanation generator.
    Parses document text, groups instructions into clean sections,
    and extracts medical terminology without modifying dosages or dates.
    """
    lines = [l.strip() for l in document_text.split("\n") if l.strip()]
    
    sections = {
        "Medications": [],
        "Diet & Daily Care": [],
        "Follow-Up Appointments": [],
        "Warning Signs (Red Flags)": [],
        "General Instructions": []
    }
    
    current_sec = "General Instructions"
    for line in lines:
        lower = line.lower()
        if "medication" in lower or "medicine" in lower or "rx" in lower:
            current_sec = "Medications"
            continue
        elif "diet" in lower or "activity" in lower or "wound" in lower or "care" in lower:
            current_sec = "Diet & Daily Care"
            continue
        elif "follow-up" in lower or "follow up" in lower or "appointment" in lower or "clinic" in lower:
            current_sec = "Follow-Up Appointments"
            continue
        elif "warning" in lower or "red flag" in lower or "emergency" in lower or "call 911" in lower:
            current_sec = "Warning Signs (Red Flags)"
            continue
        
        # Clean line and categorize
        cleaned = line.lstrip("-*•1234567890. ")
        if cleaned:
            sections[current_sec].append(cleaned)
    
    # Identify glossary terms
    terms = explain_terms_in_text(document_text)

    # Build patient-friendly summary
    summary_parts = [
        "### 🌟 Plain Language Summary\n",
        "Here is what your discharge summary means in everyday words, keeping all original medicine names, dosages, and dates exactly as written:\n"
    ]

    for sec_name, items in sections.items():
        if items:
            summary_parts.append(f"#### 📌 {sec_name}")
            for item in items:
                # Add simple safety note if medicine
                if sec_name == "Medications":
                    summary_parts.append(f"- **{item}** *(Take exactly as instructed; do not change dose)*")
                elif sec_name == "Warning Signs (Red Flags)":
                    summary_parts.append(f"- 🚨 **{item}** *(Seek immediate medical help if this happens)*")
                else:
                    summary_parts.append(f"- {item}")
            summary_parts.append("")

    return {
        "summary": "\n".join(summary_parts),
        "glossary": terms,
        "mode": "Local Reliable Parser"
    }

def generate_ai_explanation(document_text: str, api_key: str):
    """
    Calls Gemini API to generate patient-friendly explanation,
    strictly preserving medication names, dosages, and dates.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""You are the Medical Explainer module for CareBridge AI.
Your job is to convert this hospital discharge summary into clear, simple, patient-friendly language for an elderly patient or family caregiver.

Strict Safety Rules:
1. Preserve ALL medication names, exact dosages, frequencies, and follow-up dates WITHOUT ANY ALTERATION.
2. Never invent missing prescriptions or assume unmentioned instructions.
3. Use short, easily readable sentences.
4. Explain any medical terminology in simple, everyday language.
5. Emphasize urgent warning signs (red flags) clearly.

Discharge summary text:
\"\"\"
{document_text}
\"\"\"

Respond with a JSON object with two keys:
- "summary": A clear markdown string formatted with headers, short bullet points, and plain-English explanations.
- "glossary": A dictionary of {{"Medical Term": "Simple Definition"}} for any complex terms appearing in the document.
"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)
    
    result = json.loads(raw_text)
    result["mode"] = "Gemini 2.5 Flash AI"
    return result

def get_medical_explanation(document_text: str, api_key: str = None):
    """
    Main entry point for generating patient explanations.
    Uses Gemini if key available; falls back to local parser.
    """
    if not document_text.strip():
        return {"summary": "No document text available. Please upload a document first.", "glossary": {}, "mode": "None"}

    key = api_key or os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        try:
            return generate_ai_explanation(document_text, key.strip())
        except Exception:
            return generate_local_explanation(document_text)

    return generate_local_explanation(document_text)

def answer_patient_question(document_text: str, question: str, api_key: str = None):
    """
    Patient Understanding Assistant (Q&A).
    Prioritizes the document as the sole source of truth.
    Refuses to diagnose or alter medication.
    """
    if not document_text.strip():
        return "Please upload a discharge summary first before asking questions."

    if not question.strip():
        return "Please enter a question about your document."

    key = api_key or os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"
            prompt = f"""You are the Patient Understanding Assistant for CareBridge AI.
Answer the patient's question based STRICTLY and ONLY on the provided discharge summary.

CRITICAL RULES:
1. If the information is NOT mentioned in the document, explicitly say: "This information is not mentioned in your discharge summary. Please consult your doctor or nurse."
2. NEVER diagnose new symptoms or suggest changing medicine dosages.
3. Keep answers concise, empathetic, and simple to understand.

Discharge Summary:
\"\"\"
{document_text}
\"\"\"

Patient Question: {question}
"""
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # Offline / Fallback Q&A
    lower_q = question.lower()
    lower_doc = document_text.lower()
    
    # Check for glossary lookup
    for term, definition in MEDICAL_GLOSSARY.items():
        if term in lower_q:
            return f"**{term.title()}**: {definition} (Source: CareBridge Medical Reference)"

    # Check for follow-up question
    if any(w in lower_q for w in ["appointment", "follow up", "follow-up", "when", "date", "clinic"]):
        follow_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["follow-up", "appointment", "clinic", "return"])]
        if follow_lines:
            return "Based on your document, here are the follow-up instructions found:\n" + "\n".join(follow_lines)

    # Check for medication question
    if any(w in lower_q for w in ["medicine", "medication", "pill", "drug", "tablet"]):
        med_lines = [l for l in document_text.split("\n") if any(k in l.lower() for k in ["mg", "tablet", "capsule", "take", "daily"])]
        if med_lines:
            return "Here are the medication instructions found in your document:\n" + "\n".join(med_lines)

    return (
        "I looked through your document, but could not find a direct answer to that specific question. "
        "Because this application does not diagnose or make unsupported assumptions, please contact your doctor or hospital clinic for guidance."
    )

