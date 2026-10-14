import re
from typing import Dict, List, Any
from datetime import datetime, date
from modules.confusion_detector import analyze_document_confusion

def build_recovery_plan(document_text: str, api_key: str = None) -> Dict[str, Any]:
    """
    Builds a structured Recovery Journey Map from the discharge summary.
    Categorizes facts strictly supported by the text:
    1. Medication instructions
    2. Diet and lifestyle instructions
    3. Follow-up appointments
    4. Wound-care instructions
    5. Warning signs (red flags)
    6. Instructions requiring confirmation (from Confusion Detector)
    """
    if not document_text or not document_text.strip():
        return {
            "medications": [],
            "diet_lifestyle": [],
            "followups": [],
            "wound_care": [],
            "warnings": [],
            "needs_confirmation": []
        }

    # Step 1: Run Confusion Detector to get items requiring confirmation
    confusions = analyze_document_confusion(document_text, api_key=api_key)
    flagged_texts = {c["original_text"].strip().lower() for c in confusions}

    lines = [l.strip() for l in document_text.split("\n") if l.strip()]

    plan = {
        "medications": [],
        "diet_lifestyle": [],
        "followups": [],
        "wound_care": [],
        "warnings": [],
        "needs_confirmation": confusions
    }

    current_cat = "general"

    for line in lines:
        lower = line.lower()
        cleaned = line.lstrip("-*•1234567890. ")
        if not cleaned:
            continue

        # Header detection: Lines that do NOT start with bullet points and act as section titles
        is_bullet = line.startswith(("-", "*", "•"))
        if not is_bullet:
            if any(h in lower for h in ["medication", "medicine", "rx:"]) and len(lower) < 35:
                current_cat = "medications"
                continue
            elif any(h in lower for h in ["diet", "nutrition", "activity", "lifestyle"]) and len(lower) < 35:
                current_cat = "diet_lifestyle"
                continue
            elif any(h in lower for h in ["follow-up", "follow up", "appointment"]) and len(lower) < 35:
                current_cat = "followups"
                continue
            elif any(h in lower for h in ["wound", "incision", "surgical site", "dressing"]) and len(lower) < 35:
                current_cat = "wound_care"
                continue
            elif any(h in lower for h in ["warning", "red flag", "call 911", "emergency", "fever"]) and len(lower) < 35:
                current_cat = "warnings"
                continue

        # Check if this line is already marked as needing confirmation
        is_confused = any(f in lower for f in flagged_texts if len(f) > 5)

        # Categorize item
        if current_cat == "medications":
            if not is_confused:
                plan["medications"].append({
                    "task": cleaned,
                    "category": "Medication",
                    "status": "Confirmed"
                })
        elif current_cat == "diet_lifestyle":
            plan["diet_lifestyle"].append({
                "task": cleaned,
                "category": "Diet & Lifestyle",
                "status": "Confirmed"
            })
        elif current_cat == "followups":
            if not is_confused:
                plan["followups"].append({
                    "task": cleaned,
                    "category": "Follow-Up",
                    "status": "Confirmed"
                })
        elif current_cat == "wound_care":
            plan["wound_care"].append({
                "task": cleaned,
                "category": "Wound Care",
                "status": "Confirmed"
            })
        elif current_cat == "warnings":
            plan["warnings"].append({
                "task": cleaned,
                "category": "Warning Sign",
                "status": "Urgent Alert"
            })
        else:
            # Automatic heuristic detection if no headers present
            if any(w in lower for w in ["mg", "tablet", "capsule", "take "]) and not is_confused:
                plan["medications"].append({"task": cleaned, "category": "Medication", "status": "Confirmed"})
            elif any(w in lower for w in ["appointment", "clinic", "return on"]):
                plan["followups"].append({"task": cleaned, "category": "Follow-Up", "status": "Confirmed"})
            elif any(w in lower for w in ["wound", "dressing", "incision"]):
                plan["wound_care"].append({"task": cleaned, "category": "Wound Care", "status": "Confirmed"})
            elif any(w in lower for w in ["pain", "breath", "fever", "emergency", "swelling"]):
                plan["warnings"].append({"task": cleaned, "category": "Warning Sign", "status": "Urgent Alert"})

    return plan

def extract_reminders_schedule(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses medications and appointments into actionable reminder items with specific
    times, dates, and ready-to-send SMS/push notification messages.
    """
    reminders = []

    # 1. Medication Reminders (Derived strictly from confirmed meds)
    for med in plan.get("medications", []):
        task_text = med["task"]
        lower = task_text.lower()

        # Determine timing slots
        slots = []
        if any(w in lower for w in ["morning", "breakfast", "every morning", "daily in the morning"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
        if any(w in lower for w in ["twice daily", "twice a day", "every 12 hours"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
            slots.append({"slot": "Evening", "time": "08:00 PM"})
        elif any(w in lower for w in ["three times", "every 8 hours"]):
            slots.append({"slot": "Morning", "time": "08:00 AM"})
            slots.append({"slot": "Afternoon", "time": "02:00 PM"})
            slots.append({"slot": "Night", "time": "08:00 PM"})
        elif any(w in lower for w in ["evening", "night", "dinner", "bedtime"]):
            slots.append({"slot": "Night", "time": "08:00 PM"})
        elif any(w in lower for w in ["as needed", "prn"]):
            slots.append({"slot": "As Needed", "time": "When symptoms appear"})
        
        # Default daily if unspecified
        if not slots:
            slots.append({"slot": "Daily", "time": "09:00 AM"})

        # Deduplicate slots by time
        seen_times = set()
        unique_slots = []
        for s in slots:
            if s["time"] not in seen_times:
                seen_times.add(s["time"])
                unique_slots.append(s)

        for s in unique_slots:
            reminders.append({
                "type": "Medication",
                "title": f"Take {task_text.split(':')[0]}",
                "details": task_text,
                "schedule_slot": s["slot"],
                "timing": s["time"],
                "frequency": "Daily",
                "alert_message": f"[Medication Reminder - {s['time']}]: Time to take {task_text}. Please take with water.",
                "status": "Active"
            })

    # 2. Follow-Up Appointments & Doctor Consultation Reminders
    for appt in plan.get("followups", []):
        task_text = appt["task"]
        
        # Extract date and time if available
        date_match = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}", task_text, re.IGNORECASE)
        time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b", task_text)
        
        appt_date = date_match.group(0) if date_match else "Upcoming date"
        appt_time = time_match.group(0) if time_match else "Time specified on clinic card"

        reminders.append({
            "type": "Doctor Consultation",
            "title": "Hospital / Clinic Follow-up",
            "details": task_text,
            "schedule_slot": "Appointment",
            "timing": f"{appt_date} at {appt_time}",
            "frequency": "Scheduled Visit",
            "alert_message": f"[Doctor Appointment Reminder]: Scheduled visit on {appt_date} ({appt_time}). Details: {task_text}. Bring your discharge summary!",
            "status": "Scheduled"
        })

    # 3. Unclear Instructions (Safety Paused Reminders)
    for conf in plan.get("needs_confirmation", []):
        reminders.append({
            "type": "Requires Confirmation",
            "title": f"Needs Confirmation: {conf.get('issue_type', 'Unclear Instruction')}",
            "details": conf.get("original_text", ""),
            "schedule_slot": "Action Required",
            "timing": "Paused for Safety",
            "frequency": "Contact Doctor First",
            "alert_message": f"[Safety Alert - Needs Confirmation]: '{conf.get('original_text')}'. Please contact your doctor or pharmacy to confirm dosage before setting a reminder.",
            "status": "Needs Confirmation"
        })

    return reminders

def generate_ics_calendar(reminders: List[Dict[str, Any]]) -> str:
    """
    Generates an RFC 5545 .ics iCalendar file content string
    that users can import directly into Google Calendar, Apple Calendar, or Outlook.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CareBridge AI//Recovery Companion//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]

    now_str = datetime.now().strftime("%Y%m%dT%H%M%SZ")

    for idx, r in enumerate(reminders):
        if r["status"] == "Needs Confirmation":
            continue  # Do not export ambiguous events to calendar

        summary = f"CareBridge AI: {r['title']}".replace("\n", " ").replace(",", "\\,")
        desc = f"{r['details']}\\n\\nAlert: {r['alert_message']}".replace("\n", " ")
        uid = f"carebridge-{idx}-{now_str}@carebridgeai.local"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "BEGIN:VALARM",
            "TRIGGER:-PT15M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:Reminder: {summary}",
            "END:VALARM",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
