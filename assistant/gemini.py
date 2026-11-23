import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .prompts import FORMAT, SYSTEM, TOPICS


class ProviderUnavailable(RuntimeError):
    pass


def select_topics(message: str) -> list[str]:
    if os.getenv("LLM_PROVIDER", "gemini").strip().lower() != "gemini":
        raise ProviderUnavailable("Atur LLM_PROVIDER=gemini.")
    key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    if not key or not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", model):
        raise ProviderUnavailable("Periksa LLM_API_KEY dan LLM_MODEL di konfigurasi lokal.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": FORMAT},
    }
    request = Request(url, data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        parts = payload["candidates"][0]["content"]["parts"]
        content = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        topics = json.loads(content)["topics"]
        if not isinstance(topics, list) or not topics or any(t not in TOPICS for t in topics):
            raise ValueError("Topik tidak valid")
        return list(dict.fromkeys(topics))
    except HTTPError as error:
        hint = {400: "Periksa model, key, dan format permintaan.", 403: "Periksa izin API key.",
                404: "Periksa model yang tersedia di AI Studio.", 429: "Periksa kuota dan coba lagi nanti."}
        raise ProviderUnavailable(f"Gemini HTTP {error.code}. {hint.get(error.code, 'Coba lagi nanti.')}") from error
    except (URLError, OSError) as error:
        raise ProviderUnavailable("Koneksi Gemini gagal atau timeout.") from error
    except (KeyError, ValueError, IndexError, TypeError, AttributeError) as error:
        raise ProviderUnavailable("Gemini belum memberikan keluaran yang dapat dipakai.") from error
