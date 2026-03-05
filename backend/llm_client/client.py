import json
import os

import requests
from django.conf import settings

from .prompt import build_prompt


class LlmClientError(RuntimeError):
    pass


def infer_criticisms(title, clusters, negative_sentences):
    prompt = build_prompt(title, clusters, negative_sentences)
    payload = {
        "task_type": "criticisms",
        "context_chunks": [prompt],
        "meta": {"title": title},
    }
    url = settings.LLM_SERVICE_URL.rstrip("/") + "/infer"
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
    except Exception as exc:
        raise LlmClientError(str(exc)) from exc

    data = response.json()
    output = data.get("output")
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except Exception:
            output = {}

    if not isinstance(output, dict):
        output = {}
    output.setdefault("criticisms", [])
    output.setdefault("summary", "")
    output.setdefault("watch_risk", {})
    return output
