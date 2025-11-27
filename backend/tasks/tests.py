from django.test import TestCase
from .scoring import compute_scores, validate_tasks, detect_circular_dependencies
from datetime import date, timedelta

class ScoringTests(TestCase):
    def setUp(self):
        today = date.today()
        self.sample = [
            {"id":"A", "title":"Urgent small", "due_date": (today + timedelta(days=1)).isoformat(), "estimated_hours": 0.5, "importance": 6, "dependencies": []},
            {"id":"B", "title":"Big task", "due_date": (today + timedelta(days=10)).isoformat(), "estimated_hours": 8, "importance": 9, "dependencies": []},
            {"id":"C", "title":"Blocked", "due_date": (today + timedelta(days=5)).isoformat(), "estimated_hours": 2, "importance": 7, "dependencies": ["A"]},
        ]

    def test_compute_scores_returns_sorted(self):
        scored, cycles = compute_scores(self.sample)
        # highest should be either A or C because A is urgent & quick
        self.assertTrue(scored[0]["score"] >= scored[1]["score"])

    def test_fastest_strategy_prioritizes_low_effort(self):
        scored_smart, _ = compute_scores(self.sample, strategy="smart")
        scored_fast, _ = compute_scores(self.sample, strategy="fastest")
        # ensure the fastest strategy prefers "Urgent small" (A)
        ids_fast = [t["id"] for t in scored_fast]
        self.assertTrue(ids_fast[0] == "A")

    def test_detect_circular(self):
        cyc = [
            {"id":"1","title":"1","dependencies":["2"]},
            {"id":"2","title":"2","dependencies":["3"]},
            {"id":"3","title":"3","dependencies":["1"]},
        ]
        cycles = detect_circular_dependencies(cyc)
        self.assertTrue(len(cycles) >= 1)
