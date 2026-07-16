#!/usr/bin/env python3
"""Generate the N4 Kyushu/Shikoku focus background music loop.

The arrangement is deterministic and uses only Python's standard library.
It follows the DEV_TECH_SUMMARY direction for N4: a quiet wooden ryokan
after a foot bath, with onsen water, warm room tone, and low-volume
wooden mallet / koto gestures for vocabulary review.
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
BPM = 76
BEAT_SECONDS = 60 / BPM
BARS = 40
BEATS_PER_BAR = 4
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n4-kyushu-shikoku-bgm.wav"

random.seed(20260716)


def midi_to_hz(midi_note: float) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))


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


def add_tone(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    attack: float = 0.08,
    release: float = 0.28,
    waveform: str = "sine",
    vibrato_depth: float = 0.0,
    vibrato_rate: float = 3.0,
    curve: float = 0.45,
    breath: float = 0.0,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    phase = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        current_frequency = frequency * (1 + vibrato_depth * math.sin(2 * math.pi * vibrato_rate * t))
        phase += 2 * math.pi * current_frequency / SAMPLE_RATE
        if waveform == "warm":
            tone = math.sin(phase) + 0.16 * math.sin(phase * 2.0) + 0.05 * math.sin(phase * 3.0)
        elif waveform == "wood":
            tone = math.sin(phase) + 0.24 * math.sin(phase * 2.01) + 0.12 * math.sin(phase * 3.02)
        elif waveform == "triangle":
            tone = 2 * abs(2 * ((phase / (2 * math.pi)) % 1) - 1) - 1
        else:
            tone = math.sin(phase)

        env = envelope(t, duration, attack, release, curve)
        noise = (random.random() * 2 - 1) * breath
        add_sample(start_index + offset, (tone + noise) * amplitude * env, pan)


def add_koto_pluck(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    brightness: float = 0.56,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detune = frequency * 1.004

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        body_env = math.exp(-4.9 * t / max(duration, 0.001))
        pick_env = math.exp(-72 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.42 * brightness * math.sin(2 * math.pi * frequency * 2.0 * t)
            + 0.18 * brightness * math.sin(2 * math.pi * frequency * 3.0 * t)
            + 0.12 * math.sin(2 * math.pi * detune * t)
            + (random.random() * 2 - 1) * 0.07 * pick_env
        )
        add_sample(start_index + offset, tone * amplitude * body_env, pan)


def add_wood_mallet(start: float, duration: float, frequency: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    partials = [(frequency, 1.0), (frequency * 2.98, 0.28), (frequency * 5.04, 0.12)]

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        strike = math.exp(-46 * t)
        body = math.exp(-3.9 * t / max(duration, 0.001))
        tone = sum(weight * math.sin(2 * math.pi * freq * t) for freq, weight in partials)
        noise = (random.random() * 2 - 1) * 0.045 * strike
        add_sample(start_index + offset, (tone + noise) * amplitude * body, pan)


def add_room_tone(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    high_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9990 + raw * 0.0010
        high_state = high_state * 0.88 + raw * 0.12
        warmth = 0.62 + 0.38 * math.sin(2 * math.pi * 0.026 * (start + t) + 0.35)
        env = envelope(t, duration, 4.0, 5.5, 0.02)
        add_sample(start_index + offset, (low_state * 1.9 + high_state * 0.012) * amplitude * warmth * env, pan)


def add_onsen_flow(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    stream_state = 0.0
    ripple_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        stream_state = stream_state * 0.996 + raw * 0.004
        ripple_state = ripple_state * 0.72 + raw * 0.28
        pulse = 0.70 + 0.30 * math.sin(2 * math.pi * 0.17 * (start + t) + 1.1)
        env = envelope(t, duration, 2.8, 3.8, 0.03)
        add_sample(start_index + offset, (stream_state * 0.42 + ripple_state * 0.030) * amplitude * pulse * env, pan)


def add_drip(start: float, amplitude: float = 0.018, *, pan: float = 0.24) -> None:
    duration = 0.72
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    partials = [(1240, 1.0), (1690, 0.32), (2320, 0.15)]

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-6.6 * t)
        tone = sum(weight * math.sin(2 * math.pi * freq * t) for freq, weight in partials)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def note(name: str) -> float:
    midi_notes = {
        "D3": 50,
        "A3": 57,
        "C4": 60,
        "D4": 62,
        "E4": 64,
        "F4": 65,
        "G4": 67,
        "A4": 69,
        "C5": 72,
        "D5": 74,
        "E5": 76,
        "G5": 79,
    }
    return midi_to_hz(midi_notes[name])


def add_pad_chord(start: float, duration: float, names: list[str], amplitude: float) -> None:
    spread = [-0.20, -0.06, 0.10, 0.24]
    for index, name in enumerate(names):
        add_tone(
            start,
            duration,
            note(name),
            amplitude / max(len(names), 1),
            pan=spread[index % len(spread)],
            attack=3.1,
            release=4.2,
            waveform="warm",
            vibrato_depth=0.0012,
            vibrato_rate=0.18 + index * 0.03,
            curve=0.025,
        )


def arrange() -> None:
    add_room_tone(0.0, DURATION_SECONDS, 0.55, pan=-0.08)
    add_onsen_flow(0.0, DURATION_SECONDS, 0.76, pan=0.16)

    chords = [
        (0, ["D3", "A3", "D4", "F4"], 0.046, 8),
        (8, ["C4", "E4", "G4", "A4"], 0.038, 8),
        (16, ["A3", "D4", "E4", "A4"], 0.042, 8),
        (24, ["D3", "A3", "D4", "F4"], 0.048, 8),
        (32, ["C4", "E4", "G4", "A4"], 0.034, 4),
        (36, ["D3", "A3", "D4", "F4"], 0.030, 4),
    ]
    for bar, names, amp, bars in chords:
        add_pad_chord(beat_time(bar), beat_time(bars) - beat_time(0), names, amp)

    koto_phrase = [
        (0.00, "D4", 0.58, -0.18),
        (1.50, "F4", 0.42, -0.08),
        (3.00, "A4", 0.62, 0.08),
        (5.00, "G4", 0.42, 0.18),
        (6.50, "E4", 0.52, -0.04),
        (8.00, "D4", 0.66, -0.14),
        (10.50, "A4", 0.42, 0.12),
        (12.00, "C5", 0.48, 0.20),
        (14.25, "A4", 0.58, -0.02),
        (15.25, "F4", 0.56, -0.16),
    ]
    for section_start, amp in [(0, 0.050), (16, 0.046), (24, 0.054)]:
        for beat, name, length, pan in koto_phrase:
            start_beat = section_start * BEATS_PER_BAR + beat
            if start_beat >= BARS * BEATS_PER_BAR:
                continue
            add_koto_pluck(start_beat * BEAT_SECONDS, length * BEAT_SECONDS, note(name), amp, pan=pan)

    mallet_phrase = [
        (4, 2.00, "A4", 0.58, 0.20),
        (6, 1.50, "G4", 0.52, -0.12),
        (12, 2.50, "D5", 0.50, 0.16),
        (14, 0.50, "C5", 0.54, -0.08),
        (20, 2.00, "A4", 0.56, 0.22),
        (22, 1.50, "G4", 0.52, -0.16),
        (28, 2.50, "D5", 0.48, 0.16),
        (30, 0.50, "C5", 0.52, -0.08),
        (34, 2.00, "G4", 0.44, 0.12),
        (37, 1.50, "D4", 0.64, -0.10),
    ]
    for bar, beat, name, length, pan in mallet_phrase:
        add_wood_mallet(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.034, pan=pan)

    low_koto = [
        (0, "D3", 3.25),
        (8, "C4", 2.75),
        (16, "A3", 3.00),
        (24, "D3", 3.25),
        (32, "C4", 2.50),
        (36, "D3", 3.25),
    ]
    for bar, name, length in low_koto:
        add_koto_pluck(beat_time(bar, 0.0), length * BEAT_SECONDS, note(name), 0.042, pan=-0.24, brightness=0.42)

    for bar, beat, pan in [
        (3, 2.75, 0.28),
        (7, 1.25, -0.22),
        (11, 3.00, 0.18),
        (18, 2.50, -0.26),
        (23, 1.00, 0.30),
        (27, 3.25, -0.20),
        (35, 2.25, 0.24),
    ]:
        add_drip(beat_time(bar, beat), pan=pan)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.12) / math.tanh(1.12)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.64 / peak

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
