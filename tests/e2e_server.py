"""Сервер для сквозной проверки интерфейса без модели Whisper (распознавание подменено)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uvicorn  # noqa: E402

from test_pipeline import FakeTranscriber  # noqa: E402
from zlatoust import pipeline  # noqa: E402
from zlatoust.app import create_app  # noqa: E402

pipeline.transcriber_factory = lambda _n: FakeTranscriber()
uvicorn.run(create_app(), host="127.0.0.1", port=8765, log_level="warning")
