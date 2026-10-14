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

# Custom CSS for high readability, modern colors, and polished UI
st.markdown("""
<style>
    /* Clean healthcare typography & glowing accents */
    .big-font { font-size: 1.15rem !important; line-height: 1.6; }
    
    /* Modern Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(99, 102, 241, 0.18) 50%, rgba(168, 85, 247, 0.12) 100%);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px !important;
        letter-spacing: -0.5px;
    }
    .hero-tagline {
        font-size: 1.25rem !important;
        font-weight: 500;
        opacity: 0.95;
        margin-bottom: 16px;
    }
    
    /* Vibrant Badges */
    .badge-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .badge-blue { background: rgba(14, 165, 233, 0.18); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.4); }
    .badge-purple { background: rgba(168, 85, 247, 0.18); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }
    .badge-green { background: rgba(34, 197, 94, 0.18); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }

    /* Interactive Feature Cards with smooth hover effect */
    .feature-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 22px;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 28px rgba(99, 102, 241, 0.25);
        border-color: rgba(99, 102, 241, 0.55);
    }
    .feature-icon {
        font-size: 2.2rem;
        margin-bottom: 12px;
    }
    .feature-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .feature-desc {
        font-size: 0.95rem;
        opacity: 0.85;
        line-height: 1.5;
    }
    
    /* Sleek step indicator */
    .step-pill {
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 10px;
        padding: 10px 14px;
        text-align: center;
        font-weight: 600;
        font-size: 0.9rem;
    }

    /* Transform Streamlit sidebar radio into sleek modern navigation pills */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        gap: 6px !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin-bottom: 3px !important;
        transition: all 0.22s ease !important;
        cursor: pointer !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: rgba(99, 102, 241, 0.18) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        transform: translateX(4px) !important;
    }
    /* Active / Checked Navigation Item */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked),
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(14, 165, 233, 0.22), rgba(99, 102, 241, 0.32)) !important;
        border: 1px solid rgba(56, 189, 248, 0.6) !important;
        border-left: 5px solid #38bdf8 !important;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.2) !important;
        font-weight: 700 !important;
    }
    /* Hide the old-fashioned radio dots */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }

    /* Soften quotes and callouts */
    blockquote {
        border-left: 4px solid #818cf8 !important;
        padding-left: 14px !important;
        color: inherit !important;
        opacity: 0.92;
        background: rgba(99, 102, 241, 0.05);
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
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
st.sidebar.markdown(
    """
    <div style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.16) 0%, rgba(99, 102, 241, 0.22) 100%); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 16px; padding: 18px 14px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 18px rgba(0,0,0,0.25);">
        <div style="font-size: 2.2rem; margin-bottom: 4px; filter: drop-shadow(0 2px 8px rgba(56,189,248,0.45));">🌉</div>
        <div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8; letter-spacing: -0.5px;">CareBridge AI</div>
        <div style="font-size: 0.8rem; color: #cbd5e1; opacity: 0.9; margin-top: 2px;">Recovery Companion</div>
        <div style="margin-top: 10px;">
            <span style="background: rgba(56, 189, 248, 0.16); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 20px; font-size: 0.72rem; padding: 3px 10px; font-weight: 600;">v1.0 Ready</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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
    st.sidebar.markdown(
        f"""
        <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.35); border-left: 4px solid #22c55e; border-radius: 12px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 0.75rem; text-transform: uppercase; color: #4ade80; font-weight: 700; letter-spacing: 0.5px;">🟢 Active Document</div>
            <div style="font-size: 0.85rem; font-weight: 600; margin-top: 3px; word-break: break-all;">{st.session_state.uploaded_filename}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        """
        <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7; font-weight: 700; letter-spacing: 0.5px;">⚪ Status</div>
            <div style="font-size: 0.85rem; opacity: 0.85; margin-top: 3px;">No document loaded yet</div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    # Vibrant Hero Section
    st.markdown(
        """
        <div class="hero-container">
            <h1 class="hero-title">🌉 CareBridge AI</h1>
            <p class="hero-tagline">From hospital instructions to confident recovery.</p>
            <div>
                <span class="badge-pill badge-blue">🛡️ Responsible AI Prototype</span>
                <span class="badge-pill badge-purple">⚡ Instant Offline Safety Parser</span>
                <span class="badge-pill badge-green">♿ Universal Accessibility</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write(
        """
        Leaving the hospital after surgery or illness can be confusing and overwhelming. Hospital discharge summaries 
        are often dense with complicated clinical terminology, fragmented medication doses, and vital follow-up dates. 

        **CareBridge AI** bridges the gap between complicated hospital paperwork and your recovery at home.
        """
    )

    # 3 Vibrant Feature Cards with Hover Effects
    st.markdown("### 🌟 What CareBridge AI Does For You")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon">💡</div>
                    <div class="feature-title" style="color: #38bdf8;">Understand</div>
                    <div class="feature-desc">Converts complex medical jargon into clear, patient-friendly explanations while preserving exact dosages and dates.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon">🔍</div>
                    <div class="feature-title" style="color: #fbbf24;">Confusion Detector</div>
                    <div class="feature-desc">Our unique safety engine. Identifies unreadable medicines, missing schedules, or conflicting dates before mistakes happen.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon">🗺️</div>
                    <div class="feature-title" style="color: #4ade80;">Recovery Journey</div>
                    <div class="feature-desc">Interactive daily checklist with progress tracking, reminder alerts, and calendar sync (.ics) for phones.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 4-Step Interactive Visual Flow
    st.markdown("### 🗺️ How Your Recovery Journey Works")
    step1, step2, step3, step4 = st.columns(4)
    with step1:
        st.markdown("<div class='step-pill'>📄 1. Upload Summary<br><small style='opacity:0.7;'>PDF or Photo</small></div>", unsafe_allow_html=True)
    with step2:
        st.markdown("<div class='step-pill'>📋 2. Review Text<br><small style='opacity:0.7;'>Verify Extracted Notes</small></div>", unsafe_allow_html=True)
    with step3:
        st.markdown("<div class='step-pill'>🔍 3. Confusion Scan<br><small style='opacity:0.7;'>Flag Safety Hazards</small></div>", unsafe_allow_html=True)
    with step4:
        st.markdown("<div class='step-pill'>🗺️ 4. Daily Care Plan<br><small style='opacity:0.7;'>Checklist & Reminders</small></div>", unsafe_allow_html=True)

    st.divider()

    # Mandatory Medical Safety Disclaimer
    st.warning(
        "⚠️ **Important Medical Disclaimer**: CareBridge AI is an educational prototype developed for patient understanding. "
        "It does **not** diagnose medical conditions, prescribe treatments, alter prescriptions, or replace "
        "professional medical advice. Always consult your doctor or pharmacist for any medical decisions."
    )

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
                        st.markdown(
                            f"""
                            <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.35); border-left: 5px solid #f59e0b; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;">
                                <div style="font-weight: 700; color: #fbbf24; font-size: 1.05rem;">💊 {item['title']}</div>
                                <div style="font-size: 0.85rem; opacity: 0.8; margin: 4px 0;">⏰ <strong>Time:</strong> {item['timing']}</div>
                                <div style="font-size: 0.9rem; line-height: 1.4;">{item['details']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.write("No morning medications scheduled.")

            with col_eve:
                st.markdown("#### 🌙 Evening / Night (08:00 PM)")
                evening_items = [r for r in reminders if r["schedule_slot"] in ["Evening", "Night"]]
                if evening_items:
                    for item in evening_items:
                        st.markdown(
                            f"""
                            <div style="background: rgba(129, 140, 248, 0.08); border: 1px solid rgba(129, 140, 248, 0.35); border-left: 5px solid #818cf8; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;">
                                <div style="font-weight: 700; color: #a5b4fc; font-size: 1.05rem;">💊 {item['title']}</div>
                                <div style="font-size: 0.85rem; opacity: 0.8; margin: 4px 0;">⏰ <strong>Time:</strong> {item['timing']}</div>
                                <div style="font-size: 0.9rem; line-height: 1.4;">{item['details']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.write("No evening medications scheduled.")

            with col_appt:
                st.markdown("#### 📅 Doctor Consultations")
                appt_items = [r for r in reminders if r["schedule_slot"] == "Appointment"]
                if appt_items:
                    for item in appt_items:
                        st.markdown(
                            f"""
                            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.35); border-left: 5px solid #10b981; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;">
                                <div style="font-weight: 700; color: #34d399; font-size: 1.05rem;">🏥 {item['title']}</div>
                                <div style="font-size: 0.85rem; opacity: 0.8; margin: 4px 0;">🗓️ <strong>When:</strong> {item['timing']}</div>
                                <div style="font-size: 0.9rem; line-height: 1.4;">{item['details']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
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
