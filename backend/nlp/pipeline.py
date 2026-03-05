from math import sqrt
import re

from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


_analyzer = SentimentIntensityAnalyzer()


def extract_negative_sentences(snippets, threshold=-0.2):
    negative = []
    for snippet in snippets:
        text = snippet.get("text", "")
        domain = snippet.get("domain", "unknown")
        for sentence in _split_sentences(text):
            score = _analyzer.polarity_scores(sentence)["compound"]
            if score <= threshold:
                negative.append(
                    {
                        "text": sentence,
                        "domain": domain,
                        "score": score,
                    }
                )
    return negative


def cluster_complaints(negative_sentences):
    if not negative_sentences:
        return []

    texts = [item["text"] for item in negative_sentences]
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    vectors = vectorizer.fit_transform(texts)

    k = min(8, max(2, int(sqrt(len(texts)))))
    if len(texts) < k:
        k = max(1, len(texts))

    if k == 1:
        return [_build_cluster("general complaints", negative_sentences)]

    model = MiniBatchKMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = model.fit_predict(vectors)

    clusters = []
    for idx in range(k):
        items = [negative_sentences[i] for i, label in enumerate(labels) if label == idx]
        if not items:
            continue
        label = _derive_label(vectorizer, vectors, labels, idx)
        clusters.append(_build_cluster(label, items))
    return clusters


def _derive_label(vectorizer, vectors, labels, cluster_id):
    feature_names = vectorizer.get_feature_names_out()
    cluster_vectors = vectors[[i for i, label in enumerate(labels) if label == cluster_id]]
    if cluster_vectors.shape[0] == 0:
        return "misc"
    avg = cluster_vectors.mean(axis=0)
    top_indices = avg.A1.argsort()[-3:][::-1]
    terms = [feature_names[i] for i in top_indices if i < len(feature_names)]
    return " ".join(terms) if terms else "misc"


def _build_cluster(label, items):
    examples = [item["text"] for item in items[:3]]
    sources = sorted({item["domain"] for item in items})
    return {
        "label": label,
        "examples": examples,
        "sources": sources,
    }


def _split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+", text)
