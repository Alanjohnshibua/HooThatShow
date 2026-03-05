from django.db import models

from analysis.models import AnalysisRequest


class SourcePage(models.Model):
    url = models.URLField(unique=True)
    domain = models.CharField(max_length=255)
    fetched_at = models.DateTimeField(auto_now_add=True)
    robots_ok = models.BooleanField(default=True)
    fetch_method = models.CharField(max_length=50, default="requests")

    def __str__(self):
        return self.url


class ReviewSnippet(models.Model):
    source_page = models.ForeignKey(SourcePage, on_delete=models.CASCADE, related_name="snippets")
    analysis_request = models.ForeignKey(AnalysisRequest, on_delete=models.CASCADE, related_name="snippets")
    text = models.TextField()
    rating = models.FloatField(null=True, blank=True)
    author = models.CharField(max_length=255, blank=True)
    date = models.CharField(max_length=64, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_page.domain} snippet"
