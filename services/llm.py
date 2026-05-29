import json
import os
import re

import requests


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"


def groq_available():
    return bool(os.getenv("GROQ_API_KEY"))


def groq_status():
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return {
            "configured": False,
            "connected": False,
            "model": model,
            "source": "Local fallback",
            "message": "GROQ_API_KEY is not set.",
        }

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(GROQ_MODELS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return {
            "configured": True,
            "connected": True,
            "model": model,
            "source": "Groq",
            "message": "Groq API is connected.",
        }
    except Exception as exc:
        return {
            "configured": True,
            "connected": False,
            "model": model,
            "source": "Local fallback",
            "message": f"Groq API check failed: {exc}",
        }


def complete_json(system_prompt, user_prompt, fallback, temperature=0.25, max_tokens=1600):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return fallback

    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_json(content, fallback)
    except Exception as exc:
        result = dict(fallback)
        result["llm_warning"] = f"Groq request failed, fallback used: {exc}"
        return result


def parse_json(content, fallback):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return fallback
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return fallback
