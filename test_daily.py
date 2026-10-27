import unittest
from datetime import date

import daily

CFG = {"start_date": "2026-10-01", "end_date": "2026-10-31"}
OPEN = {"start_date": "2026-10-01", "end_date": None}


class DayIndex(unittest.TestCase):
    def test_start_day_is_one(self):
        self.assertEqual(daily.day_index(date(2026, 10, 1), date(2026, 10, 1)), 1)

    def test_counts_inclusive(self):
        self.assertEqual(daily.day_index(date(2026, 10, 1), date(2026, 10, 27)), 27)


class Pick(unittest.TestCase):
    def test_cycles_by_day(self):
        items = ["a", "b", "c"]
        self.assertEqual(daily.pick(items, 1), "a")
        self.assertEqual(daily.pick(items, 3), "c")
        self.assertEqual(daily.pick(items, 4), "a")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            daily.pick([], 1)


class ShouldAsk(unittest.TestCase):
    def test_deterministic_for_same_date(self):
        self.assertEqual(daily.should_ask("2026-10-27", 0.3), daily.should_ask("2026-10-27", 0.3))

    def test_chance_bounds(self):
        self.assertFalse(daily.should_ask("2026-10-27", 0.0))
        self.assertTrue(daily.should_ask("2026-10-27", 1.0))


class Phase(unittest.TestCase):
    def test_before_start(self):
        self.assertEqual(daily.phase(CFG, date(2026, 9, 30), set()), "before")

    def test_active(self):
        self.assertEqual(daily.phase(CFG, date(2026, 10, 15), set()), "active")

    def test_final_on_end_date(self):
        self.assertEqual(daily.phase(CFG, date(2026, 10, 31), set()), "final")

    def test_final_still_pending_after_missed_day(self):
        self.assertEqual(daily.phase(CFG, date(2026, 11, 3), set()), "final")

    def test_done_once_final_sent(self):
        self.assertEqual(daily.phase(CFG, date(2026, 11, 3), {"final.json"}), "done")

    def test_open_ended_never_final(self):
        self.assertEqual(daily.phase(OPEN, date(2027, 5, 1), set()), "active")


class Render(unittest.TestCase):
    def test_bilingual_with_question(self):
        card = daily.build_card(
            today=date(2026, 10, 27), day_n=27, total_days=31,
            meme={"url": "u", "vi": "mv", "en": "me"},
            lesson={"topic": "SQL", "vi": "lv", "en": "le"},
            skill={"name": "X", "vi": "sv", "en": "se"},
            ask_question=True,
        )
        text = daily.render_telegram(card)
        for needle in ("27/31", "lv", "le", "sv", "se", daily.QUESTION_VI, daily.QUESTION_EN):
            self.assertIn(needle, text)

    def test_open_ended_counter_has_no_total(self):
        card = daily.build_card(
            today=date(2026, 10, 27), day_n=27, total_days=None,
            meme={"url": "u", "vi": "mv", "en": "me"},
            lesson={"topic": "SQL", "vi": "lv", "en": "le"},
            skill={"name": "X", "vi": "sv", "en": "se"},
            ask_question=False,
        )
        text = daily.render_telegram(card)
        self.assertEqual(daily.counter(card, "vi"), "Ngày 27")
        self.assertEqual(daily.counter(card, "en"), "Day 27")
        self.assertNotIn("27/", text)
        self.assertNotIn(daily.QUESTION_EN, text)


if __name__ == "__main__":
    unittest.main()
