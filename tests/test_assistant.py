import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from shared.contracts import ChatRequest, ChatResponse
from assistant.service import chat
from assistant.tools import load_demo_reader

fixture = Path(__file__).resolve().parents[1] / "examples/prediction_response_example_only.json"
lookup = load_demo_reader(fixture)
source_id = json.loads(fixture.read_text())["prediction_id"]


class TestGeminiAssistant(unittest.TestCase):
    def ask(self, **kwargs):
        request = ChatRequest(message="Tim ini mencapai target?", prediction_id=source_id)
        return chat(request, get_prediction_by_id=lookup, **kwargs)

    @patch.dict(os.environ, {"LLM_API_KEY": "test-only", "LLM_MODEL": "gemini-test", "LLM_PROVIDER": "gemini"})
    def test_gemini_wire_format_and_grounded_answer(self):
        candidate = {"content": {"parts": [{"text": '{"topics":["target"]}'}]}}
        wire = json.dumps({"candidates": [candidate]}).encode()
        with patch("assistant.gemini.urlopen", return_value=io.BytesIO(wire)) as call:
            result = self.ask()
        request = call.call_args.args[0]
        self.assertIn(":generateContent", request.full_url)
        self.assertNotIn("test-only", request.full_url)
        self.assertEqual(json.loads(request.data)["generationConfig"]["responseMimeType"], "application/json")
        self.assertIsInstance(result, ChatResponse)
        self.assertEqual(result.status, "answered")
        for term in ("74.0%", "80.0%", "6.0 poin persentase", source_id):
            self.assertIn(term, result.answer)
        self.assertEqual(result.evidence[0].id, source_id)

    def test_unknown_prediction(self):
        provider = Mock()
        req = ChatRequest(message="Apa targetnya?", prediction_id="missing")
        result = chat(req, get_prediction_by_id=lookup, classify=provider)
        self.assertEqual(result.status, "insufficient_data")
        self.assertEqual(result.evidence, [])
        provider.assert_not_called()

    @patch.dict(os.environ, {"LLM_API_KEY": ""})
    def test_unconfigured(self):
        self.assertEqual(self.ask().status, "unavailable")

    def test_actual_and_cause(self):
        result = self.ask(classify=lambda message: ["actual", "cause"])
        self.assertIn("Realisasi shift belum tersedia", result.answer)
        self.assertIn("bukti penyebab", result.answer)
        self.assertEqual(result.status, "insufficient_data")

    @patch.dict(os.environ, {"LLM_API_KEY": "test-only", "LLM_MODEL": "gemini-test", "LLM_PROVIDER": "gemini"})
    def test_quota(self):
        with patch("assistant.gemini.urlopen", side_effect=HTTPError("", 429, "", {}, None)):
            result = self.ask()
        self.assertEqual(result.status, "unavailable")
        self.assertIn("429", result.answer)
