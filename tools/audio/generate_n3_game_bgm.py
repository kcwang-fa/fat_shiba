#!/usr/bin/env python3
"""Generate the N3 Chugoku/Kansai game background music loop.

This is the brighter street-festival arrangement for gameplay. It is built
with only Python's standard library so the audio pipeline stays reproducible
inside the project.
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
BPM = 122
BEAT_SECONDS = 60 / BPM
BEATS_PER_BAR = 4
BARS = 48
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n3-chugoku-kansai-game-bgm.wav"

random.seed(20260718)

sample_count = int(DURATION_SECONDS * SAMPLE_RATE)
left = array("f", [0.0]) * sample_count
right = array("f", [0.0]) * sample_count


def midi_to_hz(midi_note: float) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))


NOTE_MIDI = {
    "D3": 50,
    "F3": 53,
    "G3": 55,
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
    "F5": 77,
    "G5": 79,
    "A5": 81,
    "C6": 84,
}


def note(name: str) -> float:
    return midi_to_hz(NOTE_MIDI[name])


def beat_time(bar: int, beat: float = 0.0) -> float:
    return (bar * BEATS_PER_BAR + beat) * BEAT_SECONDS


def equal_power_pan(value: float) -> tuple[float, float]:
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def add_sample(index: int, value: float, pan: float) -> None:
    if 0 <= index < sample_count:
        left_gain, right_gain = equal_power_pan(pan)
        left[index] += value * left_gain
        right[index] += value * right_gain


def add_street_air() -> None:
    low_state = 0.0
    high_state = 0.0
    for index in range(sample_count):
        t = index / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9991 + raw * 0.0009
        high_state = high_state * 0.88 + raw * 0.12
        pulse = 0.72 + 0.28 * math.sin(2 * math.pi * 0.034 * t + 0.5)
        value = (low_state * 0.95 + high_state * 0.004) * 0.070 * pulse
        add_sample(index, value, -0.08)


def add_shamisen_pluck(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    brightness: float = 0.9,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detune = frequency * 1.006

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        body_env = math.exp(-7.8 * t / max(duration, 0.001))
        pick_env = math.exp(-140 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.62 * brightness * math.sin(2 * math.pi * frequency * 2.0 * t)
            + 0.30 * brightness * math.sin(2 * math.pi * frequency * 3.0 * t)
            + 0.16 * math.sin(2 * math.pi * detune * t)
            + (random.random() * 2 - 1) * 0.10 * pick_env
        )
        add_sample(start_index + offset, tone * amplitude * body_env, pan)


def add_shinobue(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    vibrato_depth: float = 0.0048,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    phase = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        fade_in = min(1.0, t / 0.035)
        fade_out = min(1.0, (duration - t) / 0.20)
        env = max(0.0, min(fade_in, fade_out))
        vibrato = 1 + vibrato_depth * math.sin(2 * math.pi * 5.6 * t)
        phase += 2 * math.pi * frequency * vibrato / SAMPLE_RATE
        breath = (random.random() * 2 - 1) * 0.016
        tone = math.sin(phase) + 0.22 * math.sin(phase * 2) + 0.08 * math.sin(phase * 3) + breath
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_soft_bass(start: float, duration: float, frequency: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = min(1.0, t / 0.025) * math.exp(-1.6 * t / max(duration, 0.001))
        tone = math.sin(2 * math.pi * frequency * t) + 0.14 * math.sin(2 * math.pi * frequency * 2 * t)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_warm_pad(start: float, duration: float, names: list[str], amplitude: float) -> None:
    pans = [-0.30, -0.10, 0.12, 0.30]
    for index, name in enumerate(names):
        frequency = note(name)
        start_index = int(start * SAMPLE_RATE)
        frame_count = int(duration * SAMPLE_RATE)
        phase = random.random() * math.tau
        for offset in range(frame_count):
            t = offset / SAMPLE_RATE
            wobble = 1 + 0.0014 * math.sin(2 * math.pi * 0.16 * t + index)
            phase += 2 * math.pi * frequency * wobble / SAMPLE_RATE
            fade_in = min(1.0, t / 1.1)
            fade_out = min(1.0, (duration - t) / 1.4)
            env = max(0.0, min(fade_in, fade_out))
            tone = math.sin(phase) + 0.10 * math.sin(phase * 2)
            add_sample(start_index + offset, tone * amplitude * env / len(names), pans[index % len(pans)])


def add_hyoshigi(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 0.060
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-68 * t)
        tone = (
            0.62 * math.sin(2 * math.pi * 1160 * t)
            + 0.34 * math.sin(2 * math.pi * 1740 * t)
            + (random.random() * 2 - 1) * 0.22
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_small_taiko(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 0.18
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        pitch = 108 * (1 + 0.26 * math.exp(-32 * t))
        env = math.exp(-18 * t)
        noise_env = math.exp(-54 * t)
        tone = math.sin(2 * math.pi * pitch * t) + (random.random() * 2 - 1) * 0.32 * noise_env
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_kane(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 0.34
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-7.5 * t)
        tone = (
            0.55 * math.sin(2 * math.pi * 1320 * t)
            + 0.32 * math.sin(2 * math.pi * 1980 * t)
            + 0.18 * math.sin(2 * math.pi * 2460 * t)
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def arrange() -> None:
    add_street_air()

    chord_cycle = [
        (["D4", "F4", "A4", "C5"], "D3"),
        (["G3", "C4", "D4", "G4"], "G3"),
        (["C4", "E4", "G4", "A4"], "C4"),
        (["A3", "D4", "F4", "A4"], "A3"),
    ]
    for block_start in range(0, BARS, 8):
        for offset, (chord, bass) in enumerate(chord_cycle):
            bar = block_start + offset * 2
            add_warm_pad(beat_time(bar), beat_time(2), chord, 0.026)
            add_soft_bass(beat_time(bar, 0.0), BEAT_SECONDS * 1.55, note(bass), 0.048, pan=-0.04)
            add_soft_bass(beat_time(bar, 2.0), BEAT_SECONDS * 1.05, note(bass), 0.032, pan=0.05)

    shamisen_motif = [
        (0.00, "D4", 0.28, -0.24),
        (0.50, "F4", 0.22, -0.16),
        (1.00, "A4", 0.26, 0.10),
        (1.50, "C5", 0.22, 0.20),
        (2.00, "A4", 0.28, 0.12),
        (2.75, "G4", 0.24, -0.08),
        (3.25, "F4", 0.36, -0.18),
        (4.00, "G4", 0.24, 0.18),
        (4.50, "A4", 0.22, 0.24),
        (5.00, "C5", 0.28, 0.10),
        (5.50, "D5", 0.24, -0.02),
        (6.25, "C5", 0.24, -0.18),
        (6.75, "A4", 0.26, -0.08),
        (7.40, "D4", 0.40, 0.04),
    ]
    for section_start in range(0, BARS, 8):
        phrase_amp = 0.066 if section_start in (0, 16, 32) else 0.058
        for beat, name, length, pan in shamisen_motif:
            add_shamisen_pluck(
                beat_time(section_start, beat),
                length * BEAT_SECONDS,
                note(name),
                phrase_amp,
                pan=pan,
            )

    flute_phrase = [
        (0, 0.25, "A4", 0.74, -0.16),
        (0, 0.95, "C5", 0.68, -0.10),
        (0, 1.62, "D5", 0.86, -0.02),
        (0, 2.45, "F5", 0.74, 0.08),
        (1, 0.10, "E5", 0.74, 0.15),
        (1, 0.82, "D5", 0.92, 0.08),
        (1, 1.70, "C5", 0.68, -0.03),
        (1, 2.36, "A4", 0.92, -0.12),
        (2, 0.20, "C5", 0.74, -0.14),
        (2, 0.92, "D5", 0.66, -0.06),
        (2, 1.56, "F5", 0.86, 0.06),
        (2, 2.38, "G5", 0.74, 0.16),
        (3, 0.10, "A5", 0.82, 0.20),
        (3, 0.88, "G5", 0.70, 0.12),
        (3, 1.56, "F5", 0.78, 0.02),
        (3, 2.32, "D5", 1.05, -0.10),
        (4, 0.22, "F5", 0.74, -0.14),
        (4, 0.94, "G5", 0.66, -0.04),
        (4, 1.58, "A5", 0.84, 0.08),
        (4, 2.38, "C6", 0.72, 0.18),
        (5, 0.12, "A5", 0.80, 0.22),
        (5, 0.88, "G5", 0.78, 0.12),
        (5, 1.62, "F5", 0.78, 0.02),
        (5, 2.36, "D5", 0.98, -0.08),
        (6, 0.16, "C5", 0.72, -0.18),
        (6, 0.84, "D5", 0.74, -0.10),
        (6, 1.54, "F5", 0.80, 0.02),
        (6, 2.32, "G5", 0.78, 0.12),
        (7, 0.08, "A5", 0.78, 0.20),
        (7, 0.82, "G5", 0.70, 0.12),
        (7, 1.50, "F5", 0.78, -0.02),
        (7, 2.24, "D5", 1.18, -0.12),
    ]
    late_flute_phrase = [
        (0, 0.20, "D5", 1.06, -0.12),
        (0, 1.20, "F5", 0.86, -0.04),
        (0, 2.04, "G5", 1.14, 0.08),
        (1, 0.96, "F5", 0.92, 0.10),
        (1, 1.84, "D5", 1.12, -0.06),
        (2, 0.28, "C5", 1.02, -0.14),
        (2, 1.24, "D5", 0.92, -0.06),
        (2, 2.10, "F5", 1.10, 0.06),
        (3, 0.92, "G5", 0.78, 0.12),
        (3, 1.64, "F5", 0.72, 0.02),
        (3, 2.30, "D5", 0.98, -0.08),
        (4, 0.24, "F5", 1.08, -0.10),
        (4, 1.28, "G5", 0.92, 0.02),
        (4, 2.14, "A5", 1.08, 0.14),
        (5, 1.00, "G5", 0.94, 0.12),
        (5, 1.90, "F5", 1.16, 0.02),
        (6, 0.22, "D5", 1.06, -0.14),
        (6, 1.24, "F5", 0.92, -0.04),
        (6, 2.10, "G5", 1.02, 0.08),
        (7, 1.00, "F5", 0.92, 0.02),
        (7, 1.86, "D5", 1.30, -0.12),
    ]
    for section_start in range(0, BARS, 8):
        phrase = late_flute_phrase if section_start >= 24 else flute_phrase
        phrase_amp = 0.034 if section_start >= 24 else 0.040
        if section_start == 8:
            phrase_amp = 0.036
        for bar, beat, name, length, pan in phrase:
            add_shinobue(
                beat_time(section_start + bar, beat),
                length * BEAT_SECONDS,
                note(name),
                phrase_amp,
                pan=pan,
            )

    flute_turns = [
        (16, 3.05, "F5", 0.58, -0.08),
        (17, 0.00, "G5", 0.58, 0.02),
        (17, 0.56, "A5", 0.66, 0.14),
        (17, 1.18, "C6", 0.92, 0.22),
        (46, 0.00, "F5", 0.86, -0.08),
        (46, 0.82, "G5", 0.82, 0.02),
        (47, 0.12, "D5", 1.46, -0.10),
    ]
    for bar, beat, name, length, pan in flute_turns:
        add_shinobue(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.038, pan=pan)

    for bar in range(BARS):
        add_small_taiko(beat_time(bar, 0.0), 0.038, pan=-0.10)
        add_small_taiko(beat_time(bar, 2.0), 0.030, pan=0.12)
        add_hyoshigi(beat_time(bar, 1.0), 0.022, pan=-0.30)
        add_hyoshigi(beat_time(bar, 3.0), 0.019, pan=0.30)
        if bar % 4 == 3:
            add_kane(beat_time(bar, 3.50), 0.016, pan=0.20)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.08) / math.tanh(1.08)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.68 / peak

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT_PATH), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for l_value, r_value in zip(left, right):
            l_int = int(max(-1.0, min(1.0, soft_limit(l_value * normalize))) * 32767)
            r_int = int(max(-1.0, min(1.0, soft_limit(r_value * normalize))) * 32767)
            frames += struct.pack("<hh", l_int, r_int)
        output.writeframes(bytes(frames))


def main() -> None:
    arrange()
    write_wav()
    print(f"Wrote {OUTPUT_PATH} ({DURATION_SECONDS:.2f}s, {BPM} BPM)")


if __name__ == "__main__":
    main()
