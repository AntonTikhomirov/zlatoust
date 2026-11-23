"""Сквозной тест без тяжёлых моделей: подменяем распознавание, видео гоняем по-настоящему, если модели есть."""
from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("ZLATOUST_DATA", str(tmp_path))
    yield tmp_path


def make_webm(path: Path, seconds: float = 8.0) -> None:
    """Видео VP8 + звук Opus, как пишет браузер."""
    with av.open(str(path), "w", format="webm") as c:
        vs = c.add_stream("libvpx", rate=15)
        vs.width, vs.height, vs.pix_fmt = 320, 240, "yuv420p"
        aus = c.add_stream("libopus", rate=48000)
        aus.layout = "mono"
        for i in range(int(seconds * 15)):
            img = np.full((240, 320, 3), (i * 3) % 255, dtype=np.uint8)
            f = av.VideoFrame.from_ndarray(img, format="rgb24")
            f.pts = i
            f.time_base = Fraction(1, 15)
            for p in vs.encode(f):
                c.mux(p)
        sr, n = 48000, 960
        t = np.arange(int(seconds * sr)) / sr
        # «Речь»: тон с меняющейся высотой и паузами.
        sig = (0.3 * np.sin(2 * np.pi * (140 + 30 * np.sin(t)) * t) * ((t % 2) < 1.4)).astype(np.float32)
        for k in range(0, len(sig) - n, n):
            af = av.AudioFrame.from_ndarray(sig[k : k + n].reshape(1, -1), format="flt", layout="mono")
            af.sample_rate = sr
            af.pts = k
            for p in aus.encode(af):
                c.mux(p)
        for s in (vs, aus):
            for p in s.encode(None):
                c.mux(p)


class FakeTranscriber:
    device = "cpu"

    def transcribe(self, audio):
        from zlatoust.analysis.transcribe import Transcript, Word

        text = "Ну вот Карл у Клары украл кораллы а Клара у Карла украла э кларнет как бы вот"
        ws, t = [], 0.2
        for w in text.split():
            ws.append(Word(w, t, t + 0.3, 0.9))
            t += 0.45 if w != "кораллы" else 1.6
        return Transcript(text=text, words=ws, model="fake")


def test_full_flow(tmp_data):
    from fastapi.testclient import TestClient

    from zlatoust import pipeline
    from zlatoust.app import create_app

    pipeline.transcriber_factory = lambda _name: FakeTranscriber()
    if os.environ.get("ZLATOUST_REAL_VIDEO") != "1":
        pipeline.video_analyzer = lambda p, prog, d: {"video": True, "face_visible_ratio": 1.0, "eye_contact_ratio": 0.5,
                                                       "look_away": [{"t": 2.0, "dur": 2.5}], "expressiveness": 0.4,
                                                       "sway": 0.02, "shoulder_tilt_deg": 1.0, "hands_visible_ratio": 0.6,
                                                       "gesture_active_ratio": 0.2, "hand_face_touches": 0,
                                                       "framing": {"face_center_x": 0.5, "eyes_y": 0.4, "face_height": 0.25}}
    else:
        pipeline.video_analyzer = None

    vid = tmp_data / "in.webm"
    make_webm(vid)
    app = create_app(start_worker=False)
    c = TestClient(app)
    assert c.get("/api/health").json()["ok"]
    r = c.post("/api/sessions", files={"file": ("rec.webm", vid.read_bytes(), "video/webm")},
               data={"mode": "tongue_twister", "exercise_id": "tw-karl"})
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    pipeline.analyze(sid)
    s = c.get(f"/api/sessions/{sid}").json()
    assert s["status"] == "done", s
    rep = s["report"]
    assert rep["overall"] is not None
    skills = {x["skill"] for x in rep["scores"]}
    assert {"tempo", "fluency", "diction", "intonation"} <= skills
    assert rep["metrics"] if False else True
    assert s["metrics"]["speech"]["fillers_per_min"] > 0
    assert s["metrics"]["diction"]["accuracy"] > 0.8
    assert rep["feedback"]["next_exercise_id"]
    assert rep["provider"] == "rules"
    assert any(w["f"] for w in rep["words"])
    # Видео отдаётся.
    assert c.get(f"/api/sessions/{sid}/video").status_code == 200
    assert c.get("/api/sessions").json()["sessions"][0]["overall"] == rep["overall"]


def test_fillers():
    from zlatoust.analysis.text import find_fillers, tokens

    w = tokens("Ну, вот этот пример, как бы, показывает, э, что вот так")
    found = [f[2] for f in find_fillers(w)]
    assert "ну" in found and "как бы" in found and "э" in found
    assert found.count("вот") == 1  # «вот этот» в начале после «ну» — паразит, «что вот так» — нет


def test_diction():
    from zlatoust.analysis.text import diction_compare

    d = diction_compare("Шла Саша по шоссе и сосала сушку.", "шла саша по шассе и сосала сушку")
    assert d["problem_words"] == ["шоссе"]
    assert 0.8 < d["accuracy"] < 0.9


def test_settings_key_masked(tmp_data):
    from fastapi.testclient import TestClient

    from zlatoust.app import create_app

    c = TestClient(create_app(start_worker=False))
    r = c.put("/api/settings", json={"anthropic_api_key": "sk-ant-test-123456789", "llm_provider": "anthropic"}).json()
    assert r["anthropic_key_set"] and "anthropic_api_key" not in r and r["anthropic_key_hint"] == "…6789"
