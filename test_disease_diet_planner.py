import unittest
from modules.disease_diet_planner import (
    is_document_metadata_line,
    detect_conditions_from_text,
    generate_disease_diet_plan,
    format_diet_plan_markdown
)

class TestDiseaseDietPlanner(unittest.TestCase):

    def test_metadata_filtering(self):
        # Header, address, DEA, and license lines should be flagged as metadata
        self.assertTrue(is_document_metadata_line("MEDICAL CENTRE"))
        self.assertTrue(is_document_metadata_line("824 14th Street, New York, NY 10001"))
        self.assertTrue(is_document_metadata_line("DEA# GB 05455616 | LIC # 976269"))
        self.assertTrue(is_document_metadata_line("Patient: John Smith, Age: 54"))
        self.assertTrue(is_document_metadata_line("Attending Physician: Dr. Steve Johnson"))
        self.assertTrue(is_document_metadata_line("Dr. Steve Johnson, MD"))

        # Real clinical instructions and appointments should NOT be flagged as metadata
        self.assertFalse(is_document_metadata_line("Low sodium DASH diet under 2,000 mg/day"))
        self.assertFalse(is_document_metadata_line("Avoid grapefruit and high caffeine drinks"))
        self.assertFalse(is_document_metadata_line("Clinic Follow-up with Dr. Vance on Oct 24, 2026 at 10:30 AM."))
        self.assertFalse(is_document_metadata_line("MEDICATIONS:"))
        self.assertFalse(is_document_metadata_line("DIET & NUTRITION:"))

    def test_condition_detection(self):
        sample_text = """
        Prescribed Medications:
        - Betaloc 50mg daily (Metoprolol)
        - Cimetidine 400mg twice daily
        - Dorzolamidum eye drops
        """
        conditions = detect_conditions_from_text(sample_text)
        self.assertIn("Cardiovascular & Hypertension (Blood Pressure Support)", conditions)
        self.assertIn("Acid Reflux (GERD) & Gastric Mucosal Protection", conditions)
        self.assertIn("Glaucoma & Elevated Eye Pressure Management", conditions)

    def test_diet_plan_generation_and_formatting(self):
        sample_text = """
        MEDICAL CENTRE
        824 14th Street, NY
        Rx: Betaloc 50mg, Cimetidine 400mg
        """
        diet = generate_disease_diet_plan(sample_text)
        self.assertIn("conditions", diet)
        self.assertGreater(len(diet["recommended_foods"]), 0)
        self.assertGreater(len(diet["foods_to_avoid"]), 0)
        self.assertIsNotNone(diet.get("hydration_plan"))

        # Check markdown formatting
        md = format_diet_plan_markdown(diet)
        self.assertIn("AI Disease-Specific Diet & Nutrition Plan", md)
        self.assertIn("Recommended Therapeutic Foods", md)
        self.assertIn("Foods & Drinks to Avoid", md)
        # Ensure address or DEA numbers never appear in the diet markdown
        self.assertNotIn("824 14th Street", md)
        self.assertNotIn("05455616", md)

if __name__ == "__main__":
    unittest.main()

