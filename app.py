import streamlit as st
import os
import sys
import io
from gtts import gTTS

# Ensure the root directory of the project is in Python's search path (Crucial for Streamlit Cloud)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
modules_dir = os.path.join(current_dir, "modules")
if os.path.exists(modules_dir) and modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)

# Import our custom modules (resilient to both folder or root placement)
try:
    from modules.document_reader import (
        validate_uploaded_file,
        extract_text_from_pdf,
        extract_text_from_image,
        MAX_FILE_SIZE_MB
    )
    from modules.medical_explainer import (
        get_medical_explanation,
        answer_patient_question
    )
    from modules.confusion_detector import analyze_document_confusion
    from modules.recovery_planner import (
        build_recovery_plan,
        extract_reminders_schedule,
        generate_ics_calendar
    )
except ModuleNotFoundError:
    from document_reader import (
        validate_uploaded_file,
        extract_text_from_pdf,
        extract_text_from_image,
        MAX_FILE_SIZE_MB
    )
    from medical_explainer import (
        get_medical_explanation,
        answer_patient_question
    )
    from confusion_detector import analyze_document_confusion
    from recovery_planner import (
        build_recovery_plan,
        extract_reminders_schedule,
        generate_ics_calendar
    )

# ==============================================================================
# 1. PAGE SETUP & ACCESSIBILITY STYLING
# ==============================================================================
st.set_page_config(
    page_title="CareBridge AI — Your Recovery Companion",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for high readability and accessible design
st.markdown("""
<style>
    /* Clean healthcare typography & spacing */
    .big-font { font-size: 1.15rem !important; line-height: 1.6; }
    /* Soften quotes and callouts */
    blockquote {
        border-left: 4px solid #6366f1 !important;
        padding-left: 12px !important;
        color: inherit !important;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SESSION STATE (Persists state across navigation)
# ==============================================================================
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "checklist_state" not in st.session_state:
    st.session_state.checklist_state = {}

# ==============================================================================
# 3. SIDEBAR NAVIGATION & CONTROLS
# ==============================================================================
st.sidebar.title("🌉 CareBridge AI")
st.sidebar.caption("From hospital instructions to confident recovery.")

nav_pages = [
    "🏠 Home",
    "📄 Upload & Review Document",
    "💡 Understand My Instructions",
    "🔍 Confusion Detector",
    "🗺️ My Recovery Journey",
    "♿ Accessibility & Audio"
]

current_page = st.sidebar.radio("Navigation Menu:", nav_pages)

st.sidebar.divider()

# Privacy & Document Management
st.sidebar.subheader("🔒 Privacy & Safety")
if st.session_state.uploaded_filename:
    st.sidebar.success(f"Active file: `{st.session_state.uploaded_filename}`")
else:
    st.sidebar.info("No document currently loaded.")

if st.sidebar.button("🗑️ Clear Document & Reset", use_container_width=True):
    st.session_state.extracted_text = ""
    st.session_state.uploaded_filename = ""
    st.session_state.checklist_state = {}
    st.rerun()

# Optional Gemini API Key
with st.sidebar.expander("⚙️ Optional AI Settings"):
    custom_key = st.text_input(
        "Gemini API Key (optional):",
        value=st.session_state.api_key if st.session_state.api_key != "your_gemini_api_key_here" else "",
        type="password",
        help="Optional. If left blank, CareBridge AI runs using built-in offline analysis."
    )
    if custom_key != st.session_state.api_key:
        st.session_state.api_key = custom_key

# ==============================================================================
# PAGE 1: HOME
# ==============================================================================
if current_page == "🏠 Home":
    st.title("🌉 CareBridge AI")
    st.subheader("Your Personal Recovery Companion")

    st.write(
        """
        Welcome to **CareBridge AI**! 

        Leaving the hospital after surgery or illness can be overwhelming. Hospital discharge summaries 
        are often packed with complicated medical jargon, confusing medication schedules, and critical warnings. 

        **CareBridge AI** bridges the gap between complicated hospital paperwork and your recovery at home.
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 💡 Understand")
        st.write("Converts complex clinical notes into plain, patient-friendly explanations without altering dosages.")
    with col2:
        st.markdown("### 🔍 Confusion Detector")
        st.write("Identifies unreadable medicines, missing timings, or conflicting dates before mistakes happen.")
    with col3:
        st.markdown("### 🗺️ Recovery Journey")
        st.write("Provides a personalized, interactive daily checklist and follow-up tracker for you and caregivers.")

    st.divider()

    # Mandatory Medical Safety Disclaimer
    st.warning(
        "⚠️ **Important Medical Disclaimer**: CareBridge AI is an educational prototype developed for patient understanding. "
        "It does **not** diagnose medical conditions, prescribe treatments, alter prescriptions, or replace "
        "professional medical advice. Always consult your doctor or pharmacist for any medical decisions."
    )

    st.info("👉 To start, click **📄 Upload & Review Document** in the sidebar on the left.")

# ==============================================================================
# PAGE 2: UPLOAD & REVIEW DOCUMENT
# ==============================================================================
elif current_page == "📄 Upload & Review Document":
    st.title("📄 Upload & Review Discharge Document")
    st.write("Upload your hospital discharge summary or clinic notes to begin.")

    upload_col, sample_col = st.columns([2, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "Select a discharge summary file (PDF, PNG, JPG, JPEG):",
            type=["pdf", "png", "jpg", "jpeg"],
            help=f"Maximum allowed file size is {MAX_FILE_SIZE_MB}MB."
        )

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

    # Process uploaded file
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

    # Editable Text Area for User Review & Correction
    if st.session_state.extracted_text or st.session_state.uploaded_filename:
        st.divider()
        st.subheader("📋 Review Extracted Medical Text")
        st.caption(
            "CareBridge AI extracted this text from your document. "
            "You can review and correct any typos or unclear wording below before analyzing."
        )

        edited_text = st.text_area(
            label="Document Content (Editable):",
            value=st.session_state.extracted_text,
            height=280,
            help="You can manually fix any OCR mistakes or add notes here."
        )

        if edited_text != st.session_state.extracted_text:
            st.session_state.extracted_text = edited_text

        col_left, col_right = st.columns([1, 4])
        with col_left:
            st.metric("Total Characters", len(st.session_state.extracted_text))
        with col_right:
            if len(st.session_state.extracted_text) > 0:
                st.success("✅ Document is ready! Proceed to **💡 Understand My Instructions** or **🔍 Confusion Detector** in the sidebar.")
            else:
                st.info("ℹ️ Text is empty. Please enter or upload text above.")

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
            explanation_data = get_medical_explanation(
                st.session_state.extracted_text,
                api_key=st.session_state.api_key
            )

        st.caption(f"Engine: **{explanation_data.get('mode', 'Standard')}**")

        tab1, tab2, tab3 = st.tabs(["🌟 Patient Explanation", "📖 Medical Glossary", "💬 Ask Questions"])

        with tab1:
            col_exp, col_orig = st.columns([3, 2])
            with col_exp:
                st.markdown(explanation_data.get("summary", "No explanation available."))
            with col_orig:
                st.markdown("#### 📄 Original Source Text")
                st.info(st.session_state.extracted_text)

        with tab2:
            st.subheader("📖 Medical Terms Explained")
            glossary = explanation_data.get("glossary", {})
            if glossary:
                for term, definition in glossary.items():
                    with st.expander(f"🔹 {term}", expanded=True):
                        st.write(definition)
            else:
                st.write("No specialized medical terms detected in this section.")

        with tab3:
            st.subheader("💬 Patient Understanding Assistant")
            st.caption("Ask questions about your uploaded instructions. Answers are grounded strictly in your document.")

            user_q = st.text_input(
                "Enter your question:",
                placeholder="e.g., What follow-up appointment do I have? Or what is furosemide?"
            )
            if st.button("Ask Assistant", type="primary"):
                if user_q.strip():
                    with st.spinner("Searching your document..."):
                        ans = answer_patient_question(
                            st.session_state.extracted_text,
                            user_q,
                            api_key=st.session_state.api_key
                        )
                    st.markdown("#### 🤖 Answer:")
                    st.write(ans)
                else:
                    st.info("Please enter a question.")

# ==============================================================================
# PAGE 4: CONFUSION DETECTOR (THE UNIQUE FEATURE!)
# ==============================================================================
elif current_page == "🔍 Confusion Detector":
    st.title("🔍 Confusion Detector")
    st.subheader("Identifying Ambiguous, Incomplete, or Conflicting Instructions")

    st.write(
        """
        The **Confusion Detector** protects patient safety by flagging instructions that are unclear,
        missing essential drug details, or contain conflicting dates. 
        """
    )

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** to upload your summary.")
    else:
        with st.spinner("Scanning for medical ambiguities..."):
            confusions = analyze_document_confusion(
                st.session_state.extracted_text,
                api_key=st.session_state.api_key
            )

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
                
                if is_high:
                    st.error(content)
                else:
                    st.warning(content)

            st.caption(
                "🛡️ *Note: The Confusion Detector is a safety-support tool. It does not replace clinical judgment or review by your doctor or pharmacist.*"
            )

# ==============================================================================
# PAGE 5: RECOVERY JOURNEY MAP
# ==============================================================================
elif current_page == "🗺️ My Recovery Journey":
    st.title("🗺️ My Recovery Journey")
    st.write("A structured recovery dashboard and daily checklist based only on your document.")

    if not st.session_state.extracted_text.strip():
        st.warning("⚠️ No document uploaded yet. Please go to **📄 Upload & Review Document** first.")
    else:
        plan = build_recovery_plan(
            st.session_state.extracted_text,
            api_key=st.session_state.api_key
        )
        reminders = extract_reminders_schedule(plan)

        tab_checklist, tab_reminders = st.tabs([
            "📋 Daily Recovery Checklist",
            "⏰ Timings, Dates & Reminder Alerts"
        ])

        # ----------------------------------------------------------------------
        # TAB 1: DAILY RECOVERY CHECKLIST
        # ----------------------------------------------------------------------
        with tab_checklist:
            # 1. Critical Red Flags
            if plan.get("warnings"):
                st.markdown("### 🚨 Urgent Warning Signs (Red Flags)")
                for w in plan["warnings"]:
                    st.error(f"**Emergency Sign**: {w['task']} — Contact your doctor or call emergency services if this occurs.")

            # 2. Confirmed Medications
            st.markdown("### 💊 Confirmed Medications")
            if plan.get("medications"):
                for med in plan["medications"]:
                    chk_key = f"med_{med['task']}"
                    st.session_state.checklist_state[chk_key] = st.checkbox(
                        f"**{med['task']}**",
                        value=st.session_state.checklist_state.get(chk_key, False)
                    )
            else:
                st.info("No confirmed medication instructions identified.")

            # 3. Diet, Activity & Wound Care
            col_diet, col_wound = st.columns(2)
            with col_diet:
                st.markdown("### 🥗 Diet & Activity")
                if plan.get("diet_lifestyle"):
                    for diet in plan["diet_lifestyle"]:
                        chk_key = f"diet_{diet['task']}"
                        st.session_state.checklist_state[chk_key] = st.checkbox(
                            diet['task'],
                            value=st.session_state.checklist_state.get(chk_key, False)
                        )
                else:
                    st.write("No specific diet instructions noted.")

            with col_wound:
                st.markdown("### 🩹 Wound Care")
                if plan.get("wound_care"):
                    for w in plan["wound_care"]:
                        chk_key = f"wound_{w['task']}"
                        st.session_state.checklist_state[chk_key] = st.checkbox(
                            w['task'],
                            value=st.session_state.checklist_state.get(chk_key, False)
                        )
                else:
                    st.write("No surgical wound care required.")

            # 4. Follow-Up Appointments
            st.markdown("### 📅 Follow-Up Appointments")
            if plan.get("followups"):
                for appt in plan["followups"]:
                    st.info(f"🗓️ **Scheduled Visit**: {appt['task']}")
            else:
                st.write("No confirmed appointment dates listed.")

            # 5. Items Needing Confirmation
            if plan.get("needs_confirmation"):
                st.markdown("### ⚠️ Instructions Requiring Doctor/Pharmacist Confirmation")
                for conf in plan["needs_confirmation"]:
                    st.warning(f"**Needs Confirmation**: {conf.get('original_text')} — *{conf.get('explanation')}*")

            # 6. Overall Checklist Progress
            st.divider()
            st.subheader("📊 Your Daily Recovery Checklist Progress")
            total_tasks = len(st.session_state.checklist_state)
            completed_tasks = sum(1 for v in st.session_state.checklist_state.values() if v)
            
            if total_tasks > 0:
                progress_val = completed_tasks / total_tasks
                st.progress(progress_val)
                st.write(f"**{completed_tasks} of {total_tasks} tasks completed ({int(progress_val * 100)}%)**")
            else:
                st.caption("Check off items above to track your daily recovery.")

        # ----------------------------------------------------------------------
        # TAB 2: TIMINGS, DATES & REMINDER ALERTS
        # ----------------------------------------------------------------------
        with tab_reminders:
            st.subheader("⏰ Daily Medication Schedule & Appointment Calendar")
            st.caption("Automatically organized from your discharge instructions so you never miss a dose or consultation.")

            # 1. Schedule Cards by Time Slot
            col_morn, col_eve, col_appt = st.columns(3)

            with col_morn:
                st.markdown("#### 🌅 Morning (08:00 AM)")
                morning_items = [r for r in reminders if r["schedule_slot"] == "Morning"]
                if morning_items:
                    for item in morning_items:
                        st.info(f"💊 **{item['title']}**\n\n*Time*: {item['timing']}\n\n*{item['details']}*")
                else:
                    st.write("No morning medications scheduled.")

            with col_eve:
                st.markdown("#### 🌙 Evening / Night (08:00 PM)")
                evening_items = [r for r in reminders if r["schedule_slot"] in ["Evening", "Night"]]
                if evening_items:
                    for item in evening_items:
                        st.info(f"💊 **{item['title']}**\n\n*Time*: {item['timing']}\n\n*{item['details']}*")
                else:
                    st.write("No evening medications scheduled.")

            with col_appt:
                st.markdown("#### 📅 Doctor Consultations")
                appt_items = [r for r in reminders if r["schedule_slot"] == "Appointment"]
                if appt_items:
                    for item in appt_items:
                        st.success(f"🏥 **{item['title']}**\n\n*When*: **{item['timing']}**\n\n*{item['details']}*")
                else:
                    st.write("No specific clinic appointments detected.")

            # Unclear Reminders (Safety Paused)
            paused_items = [r for r in reminders if r["schedule_slot"] == "Action Required"]
            if paused_items:
                st.markdown("#### ⚠️ Paused Reminders (Safety First)")
                for item in paused_items:
                    st.warning(f"**{item['title']}**: {item['details']}\n\n*Reminder is paused until confirmed with your physician or pharmacist.*")

            st.divider()

            # 2. Interactive Reminder Notification Simulator
            st.subheader("📲 Test Reminder & Alert Simulator")
            st.caption("Experience how reminders and text messages notify patients or caregivers in real time.")

            selectable_reminders = [r for r in reminders if r["status"] != "Needs Confirmation"]
            if selectable_reminders:
                options = [f"{r['type']}: {r['title']} ({r['timing']})" for r in selectable_reminders]
                selected_option = st.selectbox("Choose a reminder to test:", options)
                selected_idx = options.index(selected_option)
                chosen_reminder = selectable_reminders[selected_idx]

                test_col1, test_col2 = st.columns([1, 2])
                with test_col1:
                    phone_input = st.text_input("Caregiver/Patient Mobile Number (Simulated):", value="+1 (555) 234-5678")
                    if st.button("🔔 Send Simulated Reminder Alert", type="primary", use_container_width=True):
                        st.toast("📲 Reminder alert sent successfully!", icon="🔔")
                        st.success(
                            f"### 📲 Simulated Phone Notification (Sent to {phone_input})\n\n"
                            f"> **{chosen_reminder['alert_message']}**"
                        )
                with test_col2:
                    st.markdown("**What the Patient / Family Caregiver Sees:**")
                    st.code(
                        f"From: CareBridge AI\n"
                        f"To: {phone_input}\n"
                        f"Time: {chosen_reminder['timing']}\n"
                        f"Message: {chosen_reminder['alert_message']}\n"
                        f"Tip: Keep emergency clinic number saved on speed dial.",
                        language="text"
                    )
            else:
                st.info("No confirmed reminders to test yet.")

            st.divider()

            # 3. Export to Phone Calendar (.ics)
            st.subheader("📅 Export to Phone Calendar")
            st.caption("Download a calendar file to sync your medication and doctor appointments with Google Calendar, Apple Calendar, or Outlook.")
            
            ics_content = generate_ics_calendar(reminders)
            st.download_button(
                label="📥 Download Calendar Reminders (.ics)",
                data=ics_content,
                file_name="carebridge_recovery_schedule.ics",
                mime="text/calendar",
                help="Click to save an .ics calendar file. Open it on your phone or computer to add all reminders instantly."
            )

# ==============================================================================
# PAGE 6: ACCESSIBILITY & AUDIO
# ==============================================================================
elif current_page == "♿ Accessibility & Audio":
    st.title("♿ Accessibility & Audio Instructions")
    st.write("CareBridge AI is designed for universal accessibility, including seniors and caregivers.")

    st.subheader("🔊 Text-to-Speech (Listen Aloud)")
    st.caption("Listen to your recovery instructions spoken aloud clearly.")

    lang_choice = st.selectbox(
        "Choose Speech Language:",
        ["English (en)", "Hindi (hi)", "Telugu (te)"]
    )
    lang_code = lang_choice.split("(")[-1].replace(")", "").strip()

    text_to_speak = st.text_area(
        "Text to Read Aloud:",
        value=st.session_state.extracted_text[:600] if st.session_state.extracted_text else "Welcome to CareBridge AI. Your personal recovery companion.",
        height=180
    )

    if st.button("🎧 Generate Audio", type="primary"):
        if text_to_speak.strip():
            with st.spinner("Generating natural audio..."):
                try:
                    fp = io.BytesIO()
                    tts = gTTS(text=text_to_speak, lang=lang_code)
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    st.audio(fp.read(), format="audio/mp3")
                    st.success("✅ Audio generated successfully! Press play above to listen.")
                except Exception as tts_err:
                    st.error(f"Error generating audio: {tts_err}")
        else:
            st.info("Please enter or load text to generate audio.")

    st.divider()
    st.subheader("👓 Visual & Literacy Accessibility Tips")
    st.markdown(
        """
        - **Zoom In**: Press <kbd>Ctrl</kbd> + <kbd>+</kbd> in your browser to enlarge all text.
        - **High-Contrast Dark Mode**: Click the three dots (⋮) in the top-right corner ➔ **Settings** ➔ **Theme** ➔ choose **Dark** or **Light**.
        - **Screen Reader Support**: All headings and buttons include descriptive labels for assistive devices.
        """
    )
