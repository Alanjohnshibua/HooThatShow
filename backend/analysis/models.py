import uuid

from django.conf import settings
from django.db import models


class AnalysisRequest(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analysis_requests")
    title = models.CharField(max_length=255)
    sources = models.JSONField(default=list)
    force_refresh = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"


class AnalysisResult(models.Model):
    analysis_request = models.OneToOneField(AnalysisRequest, on_delete=models.CASCADE, related_name="result")
    criticisms = models.JSONField(default=list)
    summary = models.TextField(blank=True)
    watch_risk = models.JSONField(default=dict)
    source_stats = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.analysis_request_id}"
