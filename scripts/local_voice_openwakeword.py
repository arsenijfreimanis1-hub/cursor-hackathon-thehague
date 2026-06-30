#!/usr/bin/env python3
from __future__ import annotations

import os
import queue
import signal
import sys
import time


def main() -> int:
    try:
        import numpy as np
        import sounddevice as sd
        from openwakeword.model import Model
    except Exception as exc:
        print(f"OPENWAKEWORD_IMPORT_ERROR {exc}", file=sys.stderr, flush=True)
        return 2

    model_path = os.environ.get("WILLIAM_OPENWAKEWORD_MODEL", "").strip()
    threshold = float(os.environ.get("WILLIAM_OPENWAKEWORD_THRESHOLD", "0.45"))
    sample_rate = 16000
    chunk_size = 1280
    cooldown_seconds = float(os.environ.get("WILLIAM_OPENWAKEWORD_COOLDOWN_SECONDS", "2.0"))
    stop_requested = False

    def handle_signal(_signum, _frame):  # noqa: ANN001
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    kwargs: dict = {"inference_framework": "onnx"}
    if model_path:
        kwargs["wakeword_models"] = [model_path]

    model = Model(**kwargs)
    audio_q: queue.Queue[np.ndarray] = queue.Queue()
    last_detection = 0.0

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        if status:
            print(f"OPENWAKEWORD_STATUS {status}", file=sys.stderr, flush=True)
        mono = indata[:, 0].copy()
        audio_q.put(mono)

    with sd.InputStream(
        channels=1,
        samplerate=sample_rate,
        blocksize=chunk_size,
        dtype="int16",
        callback=callback,
    ):
        print("OPENWAKEWORD_READY", flush=True)
        while not stop_requested:
            try:
                chunk = audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            predictions = model.predict(chunk)
            now = time.monotonic()
            for _, score in predictions.items():
                if score >= threshold and now - last_detection >= cooldown_seconds:
                    last_detection = now
                    print("WAKE_DETECTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
