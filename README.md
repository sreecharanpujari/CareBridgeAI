# 📁 Sample Documents for Testing CareBridge AI

All medical documents in this folder are **100% fictional** and created strictly for educational testing, safety verification, and hackathon demonstrations.

> **Privacy Notice**: No real patient health information (PHI) or personal data is stored in these files or anywhere in this repository.

---

### Included Sample Files:

1. **`sample_discharge_summary.pdf`**
   - **Scenario**: Post-hospitalization instructions for mild heart failure management.
   - **Contains**:
     - Confirmed medications (*Lisinopril*, *Furosemide*, *Metoprolol*)
     - **Ambiguity Test 1**: An unreadable/missing medicine name (*"Take one capsule twice daily after meals (Medicine name unreadable)"*) to verify the **Confusion Detector**.
     - **Ambiguity Test 2**: Conflicting follow-up appointment dates (*Oct 24 vs Oct 21*).
     - Diet & sodium restriction instructions.
     - Red flag warning signs (sudden shortness of breath, leg swelling).

2. **`sample_discharge_note.png`**
   - **Scenario**: Image scan of a post-laparoscopic surgery discharge note.
   - **Contains**: Pain medication (*Acetaminophen*), antibiotics (*Cephalexin*), wound care steps, and fever warnings.

---

### Generating New Samples
You can regenerate or extend the sample documents at any time by running:
```powershell
.\venv\Scripts\python.exe sample_documents\generate_samples.py
```

