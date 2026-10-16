# 🌉 CareBridge AI — Your Personal Recovery Companion

> *"From hospital instructions to confident recovery."*
>
> **Lead Developers & Architects:** **Sree Charan** & **Karthik**

---

## 📌 1. Project Overview
**CareBridge AI** is an accessible, AI-powered healthcare web application built for patients, caregivers, and families navigating post-discharge recovery. 

Hospital discharge summaries are notoriously dense, filled with complex medical jargon, fragmented medication schedules, and vital follow-up dates. CareBridge AI converts these summaries into clear, plain-language explanations, actionable daily recovery checklists, and flags potentially dangerous ambiguities before mistakes happen.

> ⚠️ **Important Disclaimer**: CareBridge AI is an educational prototype developed for a student hackathon. It does **not** diagnose conditions, prescribe or alter medication dosages, or replace professional clinical judgment.

---

## 🌟 2. The Unique Feature: Confusion Detector
While general AI models attempt to guess missing information, **CareBridge AI** introduces the **Confusion Detector** to protect patient safety.

When an uploaded discharge summary contains:
- Instructions to take medication where the medicine name is unreadable or missing
- Missing or ambiguous medication timing or frequency
- Conflicting appointment dates
- Vague or incomplete post-op instructions

The Confusion Detector:
1. **Highlights** the exact source text.
2. **Explains** why the instruction is unclear.
3. **Displays** a high-visibility warning.
4. **Instructs** the patient: *"Do NOT guess. Contact your doctor or pharmacist to confirm."*
5. **Labels** the item as **"Needs Confirmation"** on the Recovery Journey map.

---

## 🛠️ 3. Technology Stack
- **Frontend & App Framework**: [Streamlit](https://streamlit.io/)
- **PDF Extraction**: `pypdf`
- **Image Processing & OCR**: `Pillow` & `pytesseract`
- **Audio & Accessibility**: `gTTS` (Google Text-to-Speech) with multi-language support (English, Telugu, Hindi)
- **AI Engine**: Google Gemini API (`gemini-2.5-flash`) with reliable local fallback parser
- **Testing**: Python `unittest` framework

---

## 📂 4. Project Structure
```text
CareBridgeAI/
│
├── app.py                         # Main Streamlit web application & UI
├── requirements.txt               # Project Python dependencies
├── README.md                      # Documentation & demo script
├── .env.example                   # Template for optional API keys
├── .gitignore                     # Git ignore rules
│
├── modules/
│   ├── document_reader.py         # PDF text extraction & file validation
│   ├── medical_explainer.py       # Plain language translations & grounded Q&A
│   ├── confusion_detector.py      # The Unique Feature: Ambiguity detection
│   ├── recovery_planner.py        # Categorized recovery map & daily checklist
│   └── disease_diet_planner.py    # AI Disease-Specific Clinical Nutrition Planner
│
├── sample_documents/
│   ├── generate_samples.py        # Script to generate fictional test documents
│   ├── sample_discharge_summary.pdf
│   └── sample_discharge_note.png
│
└── tests/
    ├── test_document_reader.py       # Unit tests for upload & extraction
    ├── test_confusion_detector.py    # Unit tests for Confusion Detector
    ├── test_recovery_planner.py      # Unit tests for reminders schedule & calendar export
    └── test_disease_diet_planner.py  # Unit tests for clinical diet planning & metadata filtering
```

---

## 🚀 5. Quick Start Instructions (Windows & VS Code)

### Prerequisites
- Python 3.10+ installed on Windows
- Visual Studio Code

### Step 1: Clone or Open the Project
Open the `CareBridgeAI` directory in VS Code.

### Step 2: Set Up Virtual Environment & Dependencies
In your VS Code terminal (<kbd>Ctrl</kbd> + <kbd>`</kbd>):
```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 3: Run the Application
```powershell
.\venv\Scripts\streamlit.exe run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 6. Running the Automated Tests
Run all unit tests with one command:
```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```
Expected output:
```text
Ran 15 tests in 1.5s
OK
```

---

## 🎙️ 7. Three-Minute Hackathon Demonstration Script

### [0:00 - 0:45] The Problem & Introduction
- *"Every year, millions of patients leave hospitals clutching multi-page discharge summaries filled with clinical terms like 'exacerbation', 'laparoscopic cholecystectomy', and conflicting dates. Over 40% of patients misunderstand their discharge instructions, leading to preventable hospital readmissions."*
- *"Meet CareBridge AI: From hospital instructions to confident recovery."*

### [0:45 - 1:30] Document Upload & Plain Explanation
- Show the **🏠 Home** page and emphasize the **Medical Safety Disclaimer**.
- Switch to **📄 Upload & Review Document**, click **Load Sample Discharge Summary**.
- Highlight that patients can review and correct any extracted text before processing.
- Switch to **💡 Understand My Instructions**:
  - Show the side-by-side view (Original Medical Text vs Plain Language Summary).
  - Show the **Medical Glossary** explaining terms like *Furosemide* and *Congestive Heart Failure*.
  - Show the **Patient Understanding Assistant** by asking: *"What appointment do I have?"*

### [1:30 - 2:20] The Star Feature: Confusion Detector
- Switch to **🔍 Confusion Detector**:
  - *"Here is what makes CareBridge AI unique. Instead of hallucinating answers, our Confusion Detector spots dangerous instructions."*
  - Show **Issue #1**: The document says *"Take one capsule twice daily"* without naming the medicine. CareBridge AI flags this in RED: *"Needs Confirmation. Do not take unknown medication. Call your pharmacy."*
  - Show **Issue #2**: Conflicting follow-up dates (Oct 24 vs Oct 21). CareBridge AI warns the patient to call the clinic to verify.

### [2:20 - 3:00] Recovery Journey & Accessibility
- Switch to **🗺️ My Recovery Journey**:
  - Show the interactive checklist where confirmed medicines are separated from items requiring confirmation.
  - Check off a completed morning task and show the progress bar.
- Switch to **♿ Accessibility & Audio**:
  - Play the Text-to-Speech audio so visually impaired or senior patients can listen aloud.
- Conclude: *"CareBridge AI turns confusing discharge paperwork into a clear, safe bridge to healing."*

