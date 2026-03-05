from rest_framework import serializers

from .models import AnalysisRequest, AnalysisResult


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = ("criticisms", "summary", "watch_risk", "source_stats")


class AnalysisRequestSerializer(serializers.ModelSerializer):
    result = AnalysisResultSerializer(read_only=True)

    class Meta:
        model = AnalysisRequest
        fields = ("id", "title", "sources", "force_refresh", "status", "result", "created_at", "updated_at")


class AnalyzeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    sources = serializers.ListField(child=serializers.CharField(), required=False)
    force_refresh = serializers.BooleanField(default=False)
