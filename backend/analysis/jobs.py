from collections import defaultdict

from django.db import transaction
from django.utils import timezone

try:
    import django_rq
except Exception:
    django_rq = None

from analysis.models import AnalysisRequest, AnalysisResult


def enqueue_analysis(analysis_request_id):
    if django_rq is None:
        return run_analysis(analysis_request_id)
    queue = django_rq.get_queue("default")
    return queue.enqueue(run_analysis, analysis_request_id)


def run_analysis(analysis_request_id):
    analysis_request = AnalysisRequest.objects.select_related("user").get(id=analysis_request_id)
    analysis_request.status = "processing"
    analysis_request.updated_at = timezone.now()
    analysis_request.save(update_fields=["status", "updated_at"])

    try:
        from llm_client.client import infer_criticisms
        from nlp.pipeline import cluster_complaints, extract_negative_sentences
        from scraping.search import search_review_pages
        from scraping.fetcher import fetch_reviews_for_urls

        urls = search_review_pages(analysis_request.title, analysis_request.sources)
        snippets = fetch_reviews_for_urls(analysis_request, urls)
        negative_sentences = extract_negative_sentences(snippets)
        clusters = cluster_complaints(negative_sentences)

        llm_payload = infer_criticisms(
            title=analysis_request.title,
            clusters=clusters,
            negative_sentences=negative_sentences,
        )

        source_stats = _build_source_stats(snippets)

        with transaction.atomic():
            AnalysisResult.objects.update_or_create(
                analysis_request=analysis_request,
                defaults={
                    "criticisms": llm_payload.get("criticisms", []),
                    "summary": llm_payload.get("summary", ""),
                    "watch_risk": llm_payload.get("watch_risk", {}),
                    "source_stats": source_stats,
                },
            )
            analysis_request.status = "done"
            analysis_request.updated_at = timezone.now()
            analysis_request.save(update_fields=["status", "updated_at"])

    except Exception as exc:
        analysis_request.status = "failed"
        analysis_request.updated_at = timezone.now()
        analysis_request.save(update_fields=["status", "updated_at"])
        raise exc


def _build_source_stats(snippets):
    by_domain = defaultdict(lambda: {"neg_count": 0, "avg_rating": None, "rating_sum": 0, "rating_count": 0})
    for snippet in snippets:
        domain = snippet.get("domain") or "unknown"
        by_domain[domain]["neg_count"] += 1
        if snippet.get("rating") is not None:
            by_domain[domain]["rating_sum"] += snippet["rating"]
            by_domain[domain]["rating_count"] += 1

    for domain, stats in by_domain.items():
        if stats["rating_count"]:
            stats["avg_rating"] = round(stats["rating_sum"] / stats["rating_count"], 2)
        stats.pop("rating_sum", None)
        stats.pop("rating_count", None)
    return dict(by_domain)
