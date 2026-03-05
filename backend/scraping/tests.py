from django.test import TestCase

from scraping.fetcher import _extract_review_texts


class ScraperTests(TestCase):
    def test_extract_review_texts(self):
        html = """
        <html>
          <body>
            <div class="review">
              <p>This movie is too long.</p>
            </div>
          </body>
        </html>
        """
        texts = _extract_review_texts(html)
        self.assertTrue(any("too long" in t for t in texts))
