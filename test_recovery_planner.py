import unittest
from modules.recovery_planner import build_recovery_plan, extract_reminders_schedule, generate_ics_calendar

class TestRecoveryPlanner(unittest.TestCase):

    def setUp(self):
        self.sample_text = """
        MEDICATIONS:
        - Lisinopril 10mg: Take 1 tablet daily in the morning for blood pressure.
        - Metoprolol Tartrate 25mg: Take 1 tablet twice daily with food.
        - Take 1 capsule twice daily (Medicine name unreadable).
        FOLLOW-UP:
        - Clinic Follow-up with Dr. Vance on Oct 24, 2026 at 10:30 AM.
        """

    def test_reminders_extraction(self):
        plan = build_recovery_plan(self.sample_text)
        reminders = extract_reminders_schedule(plan)
        
        # Check that we have reminders
        self.assertGreater(len(reminders), 0)

        # Check morning timing
        morning_rems = [r for r in reminders if r["schedule_slot"] == "Morning"]
        self.assertGreaterEqual(len(morning_rems), 2)  # Lisinopril and Metoprolol morning

        # Check evening timing
        evening_rems = [r for r in reminders if r["schedule_slot"] == "Evening"]
        self.assertGreaterEqual(len(evening_rems), 1)  # Metoprolol evening

        # Check appointment
        appts = [r for r in reminders if r["schedule_slot"] == "Appointment"]
        self.assertEqual(len(appts), 1)
        self.assertIn("Oct 24, 2026", appts[0]["timing"])

        # Check that the unreadable medicine reminder is safety paused
        paused = [r for r in reminders if r["status"] == "Needs Confirmation"]
        self.assertGreaterEqual(len(paused), 1)

    def test_calendar_ics_generation(self):
        plan = build_recovery_plan(self.sample_text)
        reminders = extract_reminders_schedule(plan)
        ics_text = generate_ics_calendar(reminders)
        
        self.assertTrue(ics_text.startswith("BEGIN:VCALENDAR"))
        self.assertTrue(ics_text.strip().endswith("END:VCALENDAR"))
        self.assertIn("CareBridge AI:", ics_text)

if __name__ == "__main__":
    unittest.main()

