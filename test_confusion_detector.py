import unittest
from modules.confusion_detector import detect_confusions_rule_based

class TestConfusionDetector(unittest.TestCase):

    def test_clear_instruction(self):
        clear_text = """
        MEDICATIONS:
        - Lisinopril 10mg: Take 1 tablet daily in the morning for blood pressure.
        - Acetaminophen 500mg: Take 1 tablet every 6 hours as needed for pain.
        FOLLOW-UP:
        - Return to Clinic on Oct 24, 2026.
        """
        issues = detect_confusions_rule_based(clear_text)
        self.assertEqual(len(issues), 0, f"Expected 0 issues for clear instructions, found {len(issues)}")

    def test_unclear_medicine_reference(self):
        unclear_text = "Take 1 pill twice daily after meals (medicine name smudged)."
        issues = detect_confusions_rule_based(unclear_text)
        self.assertGreaterEqual(len(issues), 1)
        self.assertEqual(issues[0]["severity"], "High")
        self.assertEqual(issues[0]["status"], "Needs Confirmation")

    def test_conflicting_dates(self):
        conflicting_text = """
        - Follow-up appointment scheduled for Oct 24, 2026 at 10 AM.
        - Alternate clinic note mentions returning on Oct 21, 2026.
        """
        issues = detect_confusions_rule_based(conflicting_text)
        self.assertGreaterEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue_type"], "Conflicting Follow-up Dates")

    def test_empty_document(self):
        issues = detect_confusions_rule_based("")
        self.assertEqual(len(issues), 0)

if __name__ == "__main__":
    unittest.main()

