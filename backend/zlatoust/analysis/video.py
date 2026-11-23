"""Подача на камеру: взгляд, мимика, осанка, покачивание, жесты, кадрирование. MediaPipe Tasks."""
from __future__ import annotations

import logging
import math
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np

from ..media import iter_frames
from ..paths import models_dir

log = logging.getLogger(__name__)

MODEL_URLS = {
    "pose_landmarker_full.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
}


def ensure_models() -> dict[str, Path]:
    d = models_dir() / "mediapipe"
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in MODEL_URLS.items():
        p = d / name
        if not p.exists() or p.stat().st_size < 1000:
            log.info("Скачиваю %s", name)
            tmp = p.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(p)
        out[name] = p
    return out


def models_ready() -> bool:
    d = models_dir() / "mediapipe"
    return all((d / n).exists() for n in MODEL_URLS)


def _runs(mask: list[bool], times: list[float], min_len: float) -> list[dict]:
    """Непрерывные отрезки, где mask=True, длиннее min_len секунд."""
    res, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = times[i]
        if (not m or i == len(mask) - 1) and start is not None:
            end = times[i]
            if end - start >= min_len:
                res.append({"t": round(start, 1), "dur": round(end - start, 1)})
            start = None
    return res


def video_metrics(path: Path, progress: Callable[[float], None] | None = None, duration: float | None = None) -> dict:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision

    models = ensure_models()
    pose = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models["pose_landmarker_full.task"])),
            running_mode=vision.RunningMode.VIDEO,
        )
    )
    face = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models["face_landmarker.task"])),
            running_mode=vision.RunningMode.VIDEO,
            output_face_blendshapes=True,
        )
    )

    times: list[float] = []
    face_present: list[bool] = []
    looking: list[bool] = []
    yaw_list: list[float] = []
    face_box: list[tuple[float, float, float]] = []  # cx, cy(глаза), высота лица
    expr: list[list[float]] = []
    smile: list[float] = []
    blinks = 0
    eye_closed_prev = False

    sh_mid_x: list[float] = []
    sh_w: list[float] = []
    sh_tilt: list[float] = []
    head_tilt: list[float] = []
    wrists: list[tuple[np.ndarray | None, np.ndarray | None]] = []
    pose_times: list[float] = []
    hand_face_touch = 0
    touching_prev = False

    EXPR_KEYS = ["browInnerUp", "browOuterUpLeft", "browOuterUpRight", "mouthSmileLeft", "mouthSmileRight", "cheekSquintLeft", "cheekSquintRight", "eyeWideLeft", "eyeWideRight"]

    last_ts = -1
    try:
        for fr in iter_frames(path, fps=10):
            ts = int(fr.t * 1000)
            if ts <= last_ts:
                ts = last_ts + 1
            last_ts = ts
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(fr.rgb))
            times.append(fr.t)

            fres = face.detect_for_video(img, ts)
            if fres.face_landmarks:
                lm = fres.face_landmarks[0]
                bs = {c.category_name: c.score for c in fres.face_blendshapes[0]} if fres.face_blendshapes else {}
                face_present.append(True)
                # Поворот головы по положению кончика носа между скулами: 0.5 — смотрит прямо.
                left, right, nose = lm[234], lm[454], lm[1]
                span = right.x - left.x
                ratio = (nose.x - left.x) / span if abs(span) > 1e-4 else 0.5
                yaw = (ratio - 0.5) * 2  # -1..1
                yaw_list.append(yaw)
                gaze_side = max(bs.get("eyeLookOutLeft", 0), bs.get("eyeLookOutRight", 0), bs.get("eyeLookInLeft", 0), bs.get("eyeLookInRight", 0))
                gaze_down = (bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0)) / 2
                gaze_up = (bs.get("eyeLookUpLeft", 0) + bs.get("eyeLookUpRight", 0)) / 2
                looking.append(abs(yaw) < 0.35 and gaze_side < 0.55 and gaze_down < 0.55 and gaze_up < 0.55)
                ys = [p.y for p in lm]
                eye_y = (lm[159].y + lm[386].y) / 2
                face_box.append(((left.x + right.x) / 2, eye_y, max(ys) - min(ys)))
                expr.append([bs.get(k, 0.0) for k in EXPR_KEYS])
                smile.append((bs.get("mouthSmileLeft", 0) + bs.get("mouthSmileRight", 0)) / 2)
                closed = (bs.get("eyeBlinkLeft", 0) + bs.get("eyeBlinkRight", 0)) / 2 > 0.5
                if closed and not eye_closed_prev:
                    blinks += 1
                eye_closed_prev = closed
            else:
                face_present.append(False)
                looking.append(False)

            pres = pose.detect_for_video(img, ts)
            if pres.pose_landmarks:
                L = pres.pose_landmarks[0]
                ls, rs = L[11], L[12]
                if min(ls.visibility or 0, rs.visibility or 0) > 0.5:
                    w = math.hypot(ls.x - rs.x, ls.y - rs.y)
                    if w > 0.02:
                        pose_times.append(fr.t)
                        sh_mid_x.append((ls.x + rs.x) / 2)
                        sh_w.append(w)
                        sh_tilt.append(math.degrees(math.atan2(ls.y - rs.y, ls.x - rs.x)))
                        le, re_ = L[7], L[8]
                        head_tilt.append(math.degrees(math.atan2(le.y - re_.y, le.x - re_.x)))

                        mid = np.array([(ls.x + rs.x) / 2, (ls.y + rs.y) / 2])

                        def wr(p):
                            # Относительно центра плеч: движение всего корпуса — не жест.
                            return np.array([p.x, p.y]) - mid if (p.visibility or 0) > 0.5 and 0 <= p.y <= 1.0 else None

                        wl, wrr = wr(L[15]), wr(L[16])
                        wrists.append((wl, wrr))
                        nose = np.array([L[0].x, L[0].y]) - mid
                        touching = any(x is not None and np.linalg.norm(x - nose) < 0.6 * w for x in (wl, wrr))
                        if touching and not touching_prev:
                            hand_face_touch += 1
                        touching_prev = touching
            if progress and duration:
                progress(min(1.0, fr.t / max(1.0, duration)))
    finally:
        pose.close()
        face.close()

    n = len(times)
    if n == 0:
        return {"video": False}
    span = times[-1] - times[0] if n > 1 else 1.0
    out: dict = {"video": True, "frames": n}
    out["face_visible_ratio"] = round(sum(face_present) / n, 3)

    face_n = sum(face_present)
    if face_n:
        look_ratio = sum(looking) / max(1, face_n)
        out["eye_contact_ratio"] = round(look_ratio, 3)
        out["look_away"] = _runs([fp and not lk for fp, lk in zip(face_present, looking)], times, 2.0)
        out["head_yaw_mean"] = round(float(np.mean(np.abs(yaw_list))), 3)
        fb = np.array(face_box)
        out["framing"] = {
            "face_center_x": round(float(np.median(fb[:, 0])), 3),
            "eyes_y": round(float(np.median(fb[:, 1])), 3),
            "face_height": round(float(np.median(fb[:, 2])), 3),
        }
        E = np.array(expr)
        out["expressiveness"] = round(float(np.mean(np.std(E, axis=0))) * 10, 2)  # ~0..3
        out["smile_ratio"] = round(float(np.mean(np.array(smile) > 0.3)), 3)
        out["blinks_per_min"] = round(blinks / max(1 / 60, span / 60), 1)

    if len(pose_times) > 5:
        W = float(np.median(sh_w))
        mx = np.array(sh_mid_x)
        # Покачивание: разброс центра плеч в долях ширины плеч, после удаления медленного дрейфа.
        k = 15
        trend = np.convolve(mx, np.ones(k) / k, mode="same") if len(mx) > k else np.full_like(mx, mx.mean())
        out["sway"] = round(float(np.std(mx - trend) / W), 3)
        out["drift"] = round(float((mx.max() - mx.min()) / W), 3)
        out["shoulder_tilt_deg"] = round(float(np.median(sh_tilt)), 1)
        out["head_tilt_deg"] = round(float(np.median(head_tilt)), 1)

        vis = [(a is not None) or (b is not None) for a, b in wrists]
        out["hands_visible_ratio"] = round(sum(vis) / len(wrists), 3)
        speeds, amps, active = [], [], []
        for i in range(1, len(wrists)):
            dt = max(1e-3, pose_times[i] - pose_times[i - 1])
            frame_speed = 0.0
            for j in (0, 1):
                a, b = wrists[i - 1][j], wrists[i][j]
                if a is not None and b is not None:
                    frame_speed = max(frame_speed, float(np.linalg.norm(b - a)) / W / dt)
                if b is not None:
                    amps.append(abs(float(b[0])) / W)
            speeds.append(frame_speed)
            active.append(frame_speed > 0.8)
        out["gesture_active_ratio"] = round(float(np.mean(active)) if active else 0.0, 3)
        out["gesture_amplitude"] = round(float(np.percentile(amps, 90)) if amps else 0.0, 2)
        out["gesture_count"] = len(_runs(active, pose_times[1:], 0.3))
        out["hand_face_touches"] = hand_face_touch
    else:
        out["pose_found"] = False
    return out
