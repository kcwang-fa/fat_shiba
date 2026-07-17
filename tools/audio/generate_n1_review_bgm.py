#!/usr/bin/env python3
"""Generate the N1 Tohoku/Hokkaido vocabulary-review fireplace loop.

The arrangement is deterministic and uses only Python's standard library.
It is a quiet non-musical soundscape for vocabulary review, tuned from a
fireplace ASMR reference: sparse flame bed noise, faint white noise, dry wood
crackles, and occasional low wooden thumps.
"""

from __future__ import annotations

from array import array
import math
import random
import struct
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_RATE = 44_100
BPM = 72
BEAT_SECONDS = 60 / BPM
BARS = 36
BEATS_PER_BAR = 4
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n1-tohoku-hokkaido-review-bgm.wav"

random.seed(20260717)


def beat_time(bar: int, beat: float = 0.0) -> float:
    return (bar * BEATS_PER_BAR + beat) * BEAT_SECONDS


def equal_power_pan(value: float) -> tuple[float, float]:
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def envelope(position: float, duration: float, attack: float, release: float, curve: float = 1.0) -> float:
    if duration <= 0:
        return 0.0
    if position < attack:
        return position / max(attack, 0.0001)
    if position > duration - release:
        return max(0.0, (duration - position) / max(release, 0.0001))
    body = (position - attack) / max(duration - attack - release, 0.0001)
    return math.exp(-body * curve)


sample_count = int(DURATION_SECONDS * SAMPLE_RATE)
left = array("f", [0.0]) * sample_count
right = array("f", [0.0]) * sample_count


def add_sample(index: int, value: float, pan: float) -> None:
    if 0 <= index < sample_count:
        left_gain, right_gain = equal_power_pan(pan)
        left[index] += value * left_gain
        right[index] += value * right_gain


def add_fire_bed(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    """Continuous fireplace body: warm flame wash with only a little hiss."""

    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    warm_state = 0.0
    hiss_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        absolute_t = start + t
        raw = random.random() * 2 - 1
        low_state = low_state * 0.99925 + raw * 0.00075
        warm_state = warm_state * 0.988 + raw * 0.012
        hiss_state = hiss_state * 0.62 + raw * 0.38
        breath = 0.76 + 0.16 * math.sin(2 * math.pi * 0.042 * absolute_t + 0.3)
        breath += 0.08 * math.sin(2 * math.pi * 0.096 * absolute_t + 1.6)
        ember_pulse = 0.91 + 0.09 * max(0.0, math.sin(2 * math.pi * 0.58 * absolute_t + 0.9)) ** 7
        env = envelope(t, duration, 4.5, 5.5, 0.012)
        flame = low_state * 1.75 + warm_state * 0.0095 + hiss_state * 0.0011
        add_sample(start_index + offset, flame * amplitude * breath * ember_pulse * env, pan)


def add_white_noise_bed(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    """Very quiet white-noise layer so the fireplace feels stable in headphones."""

    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    smooth_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        smooth_state = smooth_state * 0.72 + raw * 0.28
        shimmer = 0.78 + 0.22 * math.sin(2 * math.pi * 0.037 * (start + t) + 2.1)
        env = envelope(t, duration, 3.8, 4.8, 0.012)
        add_sample(start_index + offset, smooth_state * amplitude * shimmer * env, pan)


def add_crackle(start: float, amplitude: float, *, pan: float = 0.0, brightness: float = 1.0) -> None:
    duration = random.uniform(0.018, 0.075)
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    crackle_state = 0.0
    pop_frequency = random.uniform(620, 1_850)
    low_frequency = random.uniform(86, 210)
    snap_decay = random.uniform(28, 60)
    grit_decay = random.uniform(11, 24)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        crackle_state = crackle_state * 0.54 + raw * 0.46
        snap_env = math.exp(-snap_decay * t) * (1 - math.exp(-220 * t))
        grit_env = math.exp(-grit_decay * t) * (1 - math.exp(-110 * t))
        snap = math.sin(2 * math.pi * pop_frequency * t) * snap_env * 0.088 * brightness
        grit = crackle_state * grit_env * 0.026 * brightness
        wood = math.sin(2 * math.pi * low_frequency * t) * grit_env * 0.014
        add_sample(start_index + offset, (snap + grit + wood) * amplitude, pan)


def add_crackle_cluster(start: float, count: int, amplitude: float, *, pan: float = 0.0) -> None:
    for _ in range(count):
        add_crackle(
            start + random.uniform(0.0, 1.2),
            amplitude * random.uniform(0.62, 1.15),
            pan=pan + random.uniform(-0.18, 0.18),
            brightness=random.uniform(0.76, 1.32),
        )


def add_hot_pop(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    """Short foreground pop: high peak, low total energy."""

    duration = random.uniform(0.010, 0.024)
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    frequency = random.uniform(680, 1_450)
    click_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        click_state = click_state * 0.38 + raw * 0.62
        env = math.exp(-125 * t) * (1 - math.exp(-600 * t))
        tone = math.sin(2 * math.pi * frequency * t) * 0.18
        add_sample(start_index + offset, (tone + click_state * 0.055) * amplitude * env, pan)


def add_low_wood_thump(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    """Low muted knock from wood shifting in the fireplace."""

    duration = random.uniform(0.58, 1.15)
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    fundamental = random.uniform(46, 74)
    resonance = random.uniform(92, 135)
    rub_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        rub_state = rub_state * 0.91 + raw * 0.09
        knock_env = math.exp(-5.2 * t) * (1 - math.exp(-62 * t))
        body_env = math.exp(-2.8 * t)
        knock = math.sin(2 * math.pi * fundamental * t) * knock_env * 0.34
        body = math.sin(2 * math.pi * resonance * t) * body_env * 0.090
        rub = rub_state * body_env * 0.020
        add_sample(start_index + offset, (knock + body + rub) * amplitude, pan)


def add_soft_log_shift(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    """A dull sliding sound before some larger crackle clusters."""

    duration = random.uniform(1.1, 1.9)
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.996 + raw * 0.004
        slide = math.sin(math.pi * min(t / duration, 1.0)) ** 1.8
        wobble = 0.70 + 0.30 * math.sin(2 * math.pi * 0.42 * t + 0.6)
        add_sample(start_index + offset, low_state * amplitude * 9.5 * slide * wobble, pan)


def arrange() -> None:
    add_fire_bed(0.0, DURATION_SECONDS, 0.680, pan=-0.03)
    add_white_noise_bed(0.0, DURATION_SECONDS, 0.0045, pan=0.02)

    current = 0.6
    while current < DURATION_SECONDS - 1.4:
        current += random.uniform(6.00, 16.00)
        add_crackle(
            current,
            random.uniform(0.04, 0.12),
            pan=random.uniform(-0.22, 0.22),
            brightness=random.uniform(0.52, 0.88),
        )

    for bar in range(5, BARS, 10):
        cluster_start = beat_time(bar, random.uniform(0.0, 2.8))
        add_crackle_cluster(
            cluster_start,
            random.randint(1, 2),
            random.uniform(0.08, 0.18),
            pan=random.choice([-0.20, -0.10, 0.10, 0.22]),
        )

    for bar in [8, 19, 31]:
        start = beat_time(bar, random.uniform(0.25, 3.3))
        add_soft_log_shift(start - random.uniform(0.45, 0.85), 0.007, pan=random.uniform(-0.18, 0.18))
        add_low_wood_thump(start, random.uniform(0.12, 0.18), pan=random.uniform(-0.20, 0.20))
        add_crackle_cluster(start + random.uniform(0.12, 0.42), random.randint(1, 2), 0.16, pan=random.uniform(-0.24, 0.24))

    for bar in range(7, BARS, 12):
        add_low_wood_thump(beat_time(bar, 3.55), 0.13, pan=-0.16)

    for bar in [2, 14, 25, 32]:
        add_hot_pop(
            beat_time(bar, random.uniform(0.4, 3.2)),
            random.uniform(2.4, 3.4),
            pan=random.uniform(-0.18, 0.18),
        )


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.18) / math.tanh(1.18)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.30 / peak

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT_PATH), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for l_value, r_value in zip(left, right):
            l_int = int(max(-1, min(1, soft_limit(l_value * normalize))) * 32767)
            r_int = int(max(-1, min(1, soft_limit(r_value * normalize))) * 32767)
            output.writeframes(struct.pack("<hh", l_int, r_int))


def main() -> None:
    arrange()
    write_wav()
    print(f"Wrote {OUTPUT_PATH} ({DURATION_SECONDS:.2f}s, {BPM} BPM)")


if __name__ == "__main__":
    main()
