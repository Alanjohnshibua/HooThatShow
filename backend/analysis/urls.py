from django.urls import path

from .views import AnalyzeView, AnalysisDetailView, HistoryView


urlpatterns = [
    path("analyze", AnalyzeView.as_view(), name="analyze"),
    path("analyze/<uuid:id>", AnalysisDetailView.as_view(), name="analyze-detail"),
    path("history", HistoryView.as_view(), name="history"),
]
