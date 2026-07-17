#!/usr/bin/env python3
"""Generate a fireplace-inspired white-noise background BGM.

The parameters come from audio_analysis/fireplace_analysis_report.json:
low-frequency-heavy spectrum, quiet RMS, stereo image with high correlation,
and occasional soft crackle transients.

This script intentionally uses only Python's standard library so it can run in
the project without installing audio packages globally.
"""

from __future__ import annotations

from array import array
import argparse
import math
import random
import struct
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_RATE = 44_100
DEFAULT_DURATION_SECONDS = 127.617
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "fireplace-white-noise-bgm.wav"

# Reference values measured from the supplied fireplace ambience file.
REFERENCE = {
    "rms_1s_dbfs_mean": -39.66,
    "peak_1s_dbfs_max": -8.46,
    "stereo_corr": 0.9572,
    "spectral_centroid_hz": 514.0,
    "band_energy_pct": {
        "0-100": 80.41,
        "100-500": 11.99,
        "500-2000": 2.05,
        "2000-8000": 3.11,
        "8000-22050": 2.43,
    },
    "transient_candidate_seconds": [19, 25, 51, 53, 58, 79, 90, 97, 121],
}

SEED = 20260717
TARGET_RMS_DBFS = REFERENCE["rms_1s_dbfs_mean"]
TARGET_PEAK_DBFS = -8.5
FADE_SECONDS = 2.5


def db_to_amp(db_value: float) -> float:
    return 10 ** (db_value / 20)


def equal_power_pan(value: float) -> tuple[float, float]:
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def fade_gain(time_sec: float, duration_sec: float) -> float:
    fade_in = min(1.0, time_sec / FADE_SECONDS)
    fade_out = min(1.0, max(0.0, duration_sec - time_sec) / FADE_SECONDS)
    return min(fade_in, fade_out)


def add_sample(left: array, right: array, index: int, value: float, pan: float) -> None:
    if 0 <= index < len(left):
        left_gain, right_gain = equal_power_pan(pan)
        left[index] += value * left_gain
        right[index] += value * right_gain


def add_crackle(left: array, right: array, start_sec: float, amplitude: float, pan: float) -> None:
    """Add a short wood-crackle transient with a bright attack and warm tail."""
    start_index = int(start_sec * SAMPLE_RATE)
    duration = 0.18 + random.random() * 0.18
    frame_count = int(duration * SAMPLE_RATE)
    burst_gap = max(1, int(SAMPLE_RATE * (0.010 + random.random() * 0.018)))
    high_state = 0.0
    warm_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        high_state = high_state * 0.28 + raw * 0.72
        warm_state = warm_state * 0.985 + raw * 0.015
        envelope = math.exp(-24.0 * t) * (0.74 + 0.26 * math.cos(2 * math.pi * 37 * t))
        spark_gate = 1.0 if offset % burst_gap < burst_gap * 0.34 else 0.28
        value = (high_state * 0.82 + warm_state * 5.2) * amplitude * envelope * spark_gate
        add_sample(left, right, start_index + offset, value, pan)


def arrange(duration_seconds: float) -> tuple[array, array]:
    sample_count = int(duration_seconds * SAMPLE_RATE)
    left = array("f", [0.0]) * sample_count
    right = array("f", [0.0]) * sample_count

    low_l = low_r = 0.0
    low_mid_l = low_mid_r = 0.0
    mid_l = mid_r = 0.0
    high_l = high_r = 0.0
    air_l = air_r = 0.0

    for index in range(sample_count):
        time_sec = index / SAMPLE_RATE
        common = random.random() * 2 - 1
        side = random.random() * 2 - 1

        # High stereo correlation like the reference: most motion is shared,
        # with a small side component so headphones do not feel fully mono.
        raw_l = common * 0.99 + side * 0.15
        raw_r = common * 0.99 - side * 0.15

        low_l = low_l * 0.99955 + raw_l * 0.00045
        low_r = low_r * 0.99955 + raw_r * 0.00045
        low_mid_l = low_mid_l * 0.992 + raw_l * 0.008
        low_mid_r = low_mid_r * 0.992 + raw_r * 0.008
        mid_l = mid_l * 0.90 + raw_l * 0.10
        mid_r = mid_r * 0.90 + raw_r * 0.10
        high_l = high_l * 0.48 + raw_l * 0.52
        high_r = high_r * 0.48 + raw_r * 0.52
        air_l = air_l * 0.18 + raw_l * 0.82
        air_r = air_r * 0.18 + raw_r * 0.82

        slow_breath = 0.86 + 0.14 * math.sin(2 * math.pi * 0.031 * time_sec + 0.4)
        ember_lift = 0.92 + 0.08 * math.sin(2 * math.pi * 0.083 * time_sec + 1.1)
        fade = fade_gain(time_sec, duration_seconds)

        left[index] = (
            low_l * 7.2
            + low_mid_l * 1.00
            + mid_l * 0.080
            + high_l * 0.025
            + air_l * 0.015
        ) * slow_breath * ember_lift * fade
        right[index] = (
            low_r * 7.0
            + low_mid_r * 1.04
            + mid_r * 0.078
            + high_r * 0.026
            + air_r * 0.015
        ) * slow_breath * (2.0 - ember_lift) * fade

    for second in REFERENCE["transient_candidate_seconds"]:
        if second < duration_seconds - 1:
            add_crackle(
                left,
                right,
                second + random.uniform(-0.28, 0.36),
                amplitude=random.uniform(0.22, 0.36),
                pan=random.uniform(-0.30, 0.30),
            )

    # Add a few quieter natural events so the loop does not sound grid-locked.
    event_time = 6.5
    while event_time < duration_seconds - 3:
        add_crackle(
            left,
            right,
            event_time + random.uniform(-0.6, 0.6),
            amplitude=random.uniform(0.020, 0.040),
            pan=random.uniform(-0.42, 0.42),
        )
        event_time += random.uniform(8.0, 14.0)

    return left, right


def rms(values: array) -> float:
    return math.sqrt(sum(value * value for value in values) / max(len(values), 1))


def soft_limit(value: float) -> float:
    return math.tanh(value)


def add_master_crackles(left: array, right: array, gain: float) -> None:
    """Place short post-RMS crackles so peak level resembles the reference."""
    target_peak = db_to_amp(TARGET_PEAK_DBFS)
    for event_index, second in enumerate(REFERENCE["transient_candidate_seconds"]):
        center = int((second + 0.04 * math.sin(event_index * 1.7)) * SAMPLE_RATE)
        frame_count = int(0.085 * SAMPLE_RATE)
        pan = 0.24 * math.sin(event_index * 2.1)
        left_gain, right_gain = equal_power_pan(pan)
        # Divide by gain because the write stage applies gain later.
        amplitude = target_peak * (0.70 + 0.12 * math.sin(event_index * 1.3)) / max(gain, 1e-12)

        for offset in range(frame_count):
            index = center + offset
            if not 0 <= index < len(left):
                continue
            t = offset / SAMPLE_RATE
            envelope = math.exp(-62.0 * t)
            click = (
                math.sin(2 * math.pi * 1_650 * t + event_index)
                + 0.52 * math.sin(2 * math.pi * 3_900 * t + event_index * 0.3)
                + 0.20 * math.sin(2 * math.pi * 720 * t)
            ) * amplitude * envelope
            left[index] += click * left_gain
            right[index] += click * right_gain


def write_wav(left: array, right: array, output_path: Path) -> None:
    mono_rms = (rms(left) + rms(right)) / 2
    target_rms = db_to_amp(TARGET_RMS_DBFS)
    gain = target_rms / max(mono_rms, 1e-12)
    add_master_crackles(left, right, gain)

    peak_after_gain = max(
        max(abs(value * gain) for value in left),
        max(abs(value * gain) for value in right),
        1e-12,
    )
    target_peak = db_to_amp(TARGET_PEAK_DBFS)
    if peak_after_gain > target_peak:
        gain *= target_peak / peak_after_gain

    def to_int16(value: float) -> int:
        limited = max(-1.0, min(1.0, soft_limit(value * gain)))
        # TPDF dither keeps very quiet ambience from quantizing into a gritty edge.
        limited += (random.random() - random.random()) / 32768.0
        return max(-32768, min(32767, int(round(limited * 32767))))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for left_value, right_value in zip(left, right):
            frames += struct.pack("<hh", to_int16(left_value), to_int16(right_value))
        output.writeframes(bytes(frames))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_SECONDS)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    left, right = arrange(args.duration)
    write_wav(left, right, args.output)
    print(
        f"Wrote {args.output} "
        f"({args.duration:.3f}s, target RMS {TARGET_RMS_DBFS:.2f} dBFS)"
    )


if __name__ == "__main__":
    main()
