#!/usr/bin/env python3
"""Generate the N5 Okinawa game background music loop.

This is the brighter gameplay arrangement for Okinawa. The quieter
``generate_n5_bgm.py`` script remains the vocabulary-review focus BGM.
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
BPM = 112
BEAT_SECONDS = 60 / BPM
BEATS_PER_BAR = 4
BARS = 48
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n5-okinawa-game-bgm.wav"

random.seed(20260717)

sample_count = int(DURATION_SECONDS * SAMPLE_RATE)
left = array("f", [0.0]) * sample_count
right = array("f", [0.0]) * sample_count


def midi_to_hz(midi_note: float) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))


NOTE_MIDI = {
    "C3": 48,
    "G3": 55,
    "A3": 57,
    "C4": 60,
    "D4": 62,
    "E4": 64,
    "G4": 67,
    "A4": 69,
    "C5": 72,
    "D5": 74,
    "E5": 76,
    "G5": 79,
    "A5": 81,
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


def add_sanshin_pluck(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    brightness: float = 0.86,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detune = frequency * 1.007

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        body_env = math.exp(-7.2 * t / max(duration, 0.001))
        pick_env = math.exp(-120 * t)
        tremolo = 0.94 + 0.06 * math.sin(2 * math.pi * 7.1 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.54 * brightness * math.sin(2 * math.pi * frequency * 2.0 * t)
            + 0.22 * brightness * math.sin(2 * math.pi * frequency * 3.0 * t)
            + 0.12 * math.sin(2 * math.pi * detune * t)
            + (random.random() * 2 - 1) * 0.07 * pick_env
        )
        add_sample(start_index + offset, tone * amplitude * body_env * tremolo, pan)


def add_soft_bass(start: float, duration: float, frequency: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = min(1.0, t / 0.035) * math.exp(-1.45 * t / max(duration, 0.001))
        tone = math.sin(2 * math.pi * frequency * t) + 0.16 * math.sin(2 * math.pi * frequency * 2 * t)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_wood_click(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 0.075
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-58 * t)
        tone = (
            0.7 * math.sin(2 * math.pi * 920 * t)
            + 0.3 * math.sin(2 * math.pi * 1380 * t)
            + (random.random() * 2 - 1) * 0.18
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_breeze(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    high_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9985 + raw * 0.0015
        high_state = high_state * 0.90 + raw * 0.10
        gust = 0.62 + 0.38 * math.sin(2 * math.pi * 0.045 * (start + t) + 0.8)
        fade_in = min(1.0, t / 3.0)
        fade_out = min(1.0, (duration - t) / 3.8)
        env = max(0.0, min(fade_in, fade_out))
        add_sample(start_index + offset, (low_state * 1.6 + high_state * 0.012) * amplitude * gust * env, pan)


def add_wave(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 3.2
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    foam_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.999 + raw * 0.001
        foam_state = foam_state * 0.83 + raw * 0.17
        swell = math.sin(math.pi * min(t / duration, 1.0)) ** 1.9
        add_sample(start_index + offset, (low_state * 2.1 + foam_state * 0.020) * amplitude * swell, pan)


def add_pad(start: float, duration: float, names: list[str], amplitude: float) -> None:
    pans = [-0.20, -0.06, 0.12, 0.24]
    for index, name in enumerate(names):
        frequency = note(name)
        start_index = int(start * SAMPLE_RATE)
        frame_count = int(duration * SAMPLE_RATE)
        phase = 0.0
        for offset in range(frame_count):
            t = offset / SAMPLE_RATE
            phase += 2 * math.pi * frequency * (1 + 0.0012 * math.sin(2 * math.pi * 0.18 * t)) / SAMPLE_RATE
            fade_in = min(1.0, t / 1.6)
            fade_out = min(1.0, (duration - t) / 2.2)
            env = max(0.0, min(fade_in, fade_out)) * math.exp(-0.08 * t / max(duration, 0.001))
            tone = math.sin(phase) + 0.12 * math.sin(phase * 2)
            add_sample(start_index + offset, tone * amplitude * env / len(names), pans[index % len(pans)])


def arrange() -> None:
    add_breeze(0.0, DURATION_SECONDS, 0.42, pan=-0.12)

    for bar in range(0, BARS, 2):
        add_wave(beat_time(bar, 0.2), 0.23, pan=-0.20)
        add_wave(beat_time(bar, 2.2), 0.18, pan=0.22)

    chord_cycle = [
        (["C3", "G3", "C4", "E4"], "C3"),
        (["A3", "C4", "E4", "G4"], "A3"),
        (["G3", "C4", "D4", "G4"], "G3"),
        (["C3", "G3", "C4", "E4"], "C3"),
    ]
    for block_start in range(0, BARS, 8):
        for offset, (chord, bass) in enumerate(chord_cycle):
            bar = block_start + offset * 2
            add_pad(beat_time(bar), beat_time(2), chord, 0.030)
            add_soft_bass(beat_time(bar, 0.0), BEAT_SECONDS * 1.65, note(bass), 0.050, pan=-0.04)
            add_soft_bass(beat_time(bar, 2.0), BEAT_SECONDS * 1.25, note(bass), 0.035, pan=0.05)

    motif = [
        (0.00, "C4", 0.36, -0.22),
        (0.75, "E4", 0.30, -0.10),
        (1.25, "G4", 0.34, 0.12),
        (2.00, "A4", 0.30, 0.20),
        (2.50, "G4", 0.34, 0.08),
        (3.25, "E4", 0.42, -0.14),
        (4.00, "G4", 0.30, 0.18),
        (4.75, "A4", 0.28, 0.24),
        (5.25, "C5", 0.38, 0.10),
        (6.00, "G4", 0.30, -0.06),
        (6.50, "E4", 0.30, -0.18),
        (7.25, "C4", 0.44, -0.02),
    ]
    for section_start in range(0, BARS, 8):
        phrase_amp = 0.070 if section_start % 16 == 0 else 0.060
        for beat, name, length, pan in motif:
            add_sanshin_pluck(
                beat_time(section_start, beat),
                length * BEAT_SECONDS,
                note(name),
                phrase_amp,
                pan=pan,
            )

    answer = [
        (3, 2.50, "E5", 0.26, 0.24),
        (3, 3.00, "D5", 0.24, 0.10),
        (3, 3.50, "C5", 0.30, -0.02),
        (7, 2.25, "G5", 0.24, 0.22),
        (7, 2.75, "E5", 0.28, 0.14),
        (7, 3.25, "C5", 0.36, -0.06),
    ]
    for section_start in range(0, BARS, 8):
        for bar, beat, name, length, pan in answer:
            add_sanshin_pluck(
                beat_time(section_start + bar, beat),
                length * BEAT_SECONDS,
                note(name),
                0.042,
                pan=pan,
                brightness=0.74,
            )

    for bar in range(0, BARS):
        add_wood_click(beat_time(bar, 1.0), 0.022, pan=-0.28)
        add_wood_click(beat_time(bar, 3.0), 0.018, pan=0.28)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.05) / math.tanh(1.05)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.66 / peak

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
