import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError
from shared.contracts import ChatRequest
from .service import chat
from .tools import load_demo_reader


def main():
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    fixture = root / "examples/prediction_response_example_only.json"
    parser = argparse.ArgumentParser(description="Demo chatbot Gemini dengan record contoh kelompok")
    parser.add_argument("--id", default=json.loads(fixture.read_text())["prediction_id"])
    selected = parser.parse_args().id
    reader = load_demo_reader(fixture)
    session = None
    print("ProdPulse | Gemini | Data contoh README | /exit untuk keluar")
    while True:
        try:
            message = input("Lu > ").strip()
            if message == "/exit":
                break
            request = ChatRequest(message=message, prediction_id=selected, conversation_id=session)
            result = chat(request, get_prediction_by_id=reader)
            session = result.conversation_id
            print(result.model_dump_json(indent=2))
        except (EOFError, KeyboardInterrupt):
            break
        except ValidationError as error:
            print(error)


if __name__ == "__main__":
    main()
