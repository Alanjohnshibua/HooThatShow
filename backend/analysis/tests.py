from django.test import TestCase

from analysis.jobs import _build_source_stats


class AnalysisStatsTests(TestCase):
    def test_build_source_stats(self):
        snippets = [
            {"domain": "imdb.com", "rating": 6.0},
            {"domain": "imdb.com", "rating": 4.0},
            {"domain": "reddit.com", "rating": None},
        ]
        stats = _build_source_stats(snippets)
        self.assertEqual(stats["imdb.com"]["neg_count"], 2)
        self.assertEqual(stats["imdb.com"]["avg_rating"], 5.0)
