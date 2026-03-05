import json


def build_prompt(title, clusters, negative_sentences):
    guidance = (
        "You are analyzing negative feedback for a movie/show. "
        "Return ONLY valid JSON in the exact schema. "
        "Each criticism must be supported by at least two independent sources; "
        "if not, include it with \"low_confidence\": true. "
        "Do not invent facts."
    )

    payload = {
        "title": title,
        "clusters": clusters,
        "negative_examples": [
            {"text": item["text"], "source": item["domain"], "score": item["score"]}
            for item in negative_sentences
        ][:30],
        "output_schema": {
            "criticisms": [
                {
                    "label": "string",
                    "examples": ["string", "..."],
                    "score": 0.0,
                    "sources": ["imdb.com", "reddit.com"],
                    "low_confidence": False,
                }
            ],
            "summary": "string",
            "watch_risk": {"boring": 0.0, "confusing": 0.0, "slow_pacing": 0.0},
        },
    }

    return guidance + "\n\nINPUT:\n" + json.dumps(payload, ensure_ascii=False)
