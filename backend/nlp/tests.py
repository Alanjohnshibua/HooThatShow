from django.test import TestCase

from nlp.pipeline import extract_negative_sentences


class SentimentTests(TestCase):
    def test_extracts_negative_sentences(self):
        snippets = [{"text": "Great visuals. The plot is boring and slow.", "domain": "imdb.com"}]
        negatives = extract_negative_sentences(snippets, threshold=-0.1)
        self.assertTrue(any("boring" in item["text"].lower() for item in negatives))
