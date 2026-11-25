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
        for term in ("74%", "80%", "6 poin persentase di bawah target", source_id):
            self.assertIn(term, result.answer)
        self.assertEqual(result.evidence[0].id, source_id)

    def test_same_target_and_small_gap_are_distinguished(self):
        req = ChatRequest(message="Bagaimana targetnya?", prediction_id=source_id)
        for predicted, gap, expected in [
            (0.8, 0, "tepat mencapai target 80%"),
            (0.79999, -0.001, "kurang dari 0,01 poin persentase di bawah target"),
        ]:
            with self.subTest(gap=gap):
                record = {**lookup(source_id), "predicted_productivity": predicted,
                          "gap_percentage_points": gap,
                          "target_status": "below_target" if gap < 0 else "meets_or_exceeds_target"}
                reply = chat(req, get_prediction_by_id=lambda _: record, classify=lambda _: ["target"])
                self.assertIn(expected, reply.answer)
                self.assertEqual(reply.evidence[0].id, source_id)

    def test_history_is_distinct_from_estimate(self):
        result = self.ask(classify=lambda _: ["target", "history"],
                          get_team_history_summary=lambda _: {"mean": 0.8473, "records": 37})
        self.assertIn("diperkirakan 74%", result.answer)
        self.assertIn("rata-rata produktivitas aktual", result.answer)
        self.assertIn("84,73% dari 37 catatan", result.answer)
        self.assertEqual([e.type for e in result.evidence], ["prediction", "historical_summary"])
        self.assertEqual(result.status, "answered")

    def test_missing_history_has_no_invented_average(self):
        reply = self.ask(classify=lambda _: ["history"],
                         get_team_history_summary=lambda _: {"mean": None, "records": 0})
        self.assertIn("Belum ada ringkasan historis", reply.answer)
        self.assertNotIn("%", reply.answer)
        self.assertEqual(reply.evidence, [])
        self.assertEqual(reply.status, "insufficient_data")

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
        self.assertIn("Produktivitas aktual untuk shift tersebut belum tercatat", result.answer)
        self.assertIn("penyebab selisih dan dampak mengubah rencana kerja belum bisa dipastikan", result.answer)
        self.assertEqual(result.status, "insufficient_data")

    @patch.dict(os.environ, {"LLM_API_KEY": "test-only", "LLM_MODEL": "gemini-test", "LLM_PROVIDER": "gemini"})
    def test_quota(self):
        with patch("assistant.gemini.urlopen", side_effect=HTTPError("", 429, "", {}, None)):
            result = self.ask()
        self.assertEqual(result.status, "unavailable")
        self.assertIn("429", result.answer)
