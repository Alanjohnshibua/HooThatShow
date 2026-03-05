from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .jobs import enqueue_analysis
from .models import AnalysisRequest
from .serializers import AnalyzeCreateSerializer, AnalysisRequestSerializer


DEFAULT_SOURCES = ["imdb", "rotten", "metacritic", "letterboxd", "reddit"]


class AnalyzeView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalyzeCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        title = serializer.validated_data["title"]
        sources = serializer.validated_data.get("sources") or DEFAULT_SOURCES
        force_refresh = serializer.validated_data.get("force_refresh", False)

        if not force_refresh:
            existing = AnalysisRequest.objects.filter(
                user=request.user,
                title__iexact=title,
                status="done",
            ).order_by("-updated_at")
            for item in existing:
                if sorted(item.sources) == sorted(sources):
                    return Response(AnalysisRequestSerializer(item).data, status=status.HTTP_200_OK)

        analysis_request = AnalysisRequest.objects.create(
            user=request.user,
            title=title,
            sources=sources,
            force_refresh=force_refresh,
            status="queued",
        )
        enqueue_analysis(analysis_request.id)
        return Response(AnalysisRequestSerializer(analysis_request).data, status=status.HTTP_202_ACCEPTED)


class AnalysisDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = AnalysisRequest.objects.all()
    serializer_class = AnalysisRequestSerializer
    lookup_field = "id"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class HistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisRequestSerializer

    def get_queryset(self):
        return AnalysisRequest.objects.filter(user=self.request.user).order_by("-created_at")
