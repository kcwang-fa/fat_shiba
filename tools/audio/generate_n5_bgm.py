#!/usr/bin/env python3
"""Generate the N5 Okinawa focus background music loop.

The arrangement is deterministic and uses only Python's standard library.
It follows the DEV_TECH_SUMMARY direction for N5: an afternoon by the Okinawa
dog house, with sea breeze, distant waves, and very light sanshin plucks.
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
BPM = 82
BEAT_SECONDS = 60 / BPM
BARS = 40
BEATS_PER_BAR = 4
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n5-okinawa-focus-bgm.wav"

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
    release: float = 0.22,
    waveform: str = "sine",
    vibrato_depth: float = 0.0,
    vibrato_rate: float = 3.0,
    curve: float = 0.5,
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
        elif waveform == "triangle":
            tone = 2 * abs(2 * ((phase / (2 * math.pi)) % 1) - 1) - 1
        else:
            tone = math.sin(phase)

        env = envelope(t, duration, attack, release, curve)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_sanshin_pluck(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    brightness: float = 0.72,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detune = frequency * 1.006

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        body_env = math.exp(-5.4 * t / max(duration, 0.001))
        pick_env = math.exp(-92 * t)
        tremolo = 0.93 + 0.07 * math.sin(2 * math.pi * 6.3 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.50 * brightness * math.sin(2 * math.pi * frequency * 2.0 * t)
            + 0.20 * brightness * math.sin(2 * math.pi * frequency * 3.0 * t)
            + 0.14 * math.sin(2 * math.pi * detune * t)
            + (random.random() * 2 - 1) * 0.09 * pick_env
        )
        add_sample(start_index + offset, tone * amplitude * body_env * tremolo, pan)


def add_breeze(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    high_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9988 + raw * 0.0012
        high_state = high_state * 0.92 + raw * 0.08
        gust = 0.58 + 0.42 * math.sin(2 * math.pi * 0.031 * (start + t) + 0.4)
        env = envelope(t, duration, 3.6, 4.8, 0.02)
        add_sample(start_index + offset, (low_state * 1.8 + high_state * 0.018) * amplitude * gust * env, pan)


def add_wave(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    duration = 4.8
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    foam_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9992 + raw * 0.0008
        foam_state = foam_state * 0.84 + raw * 0.16
        swell = math.sin(math.pi * min(t / duration, 1.0)) ** 1.7
        roll = math.sin(2 * math.pi * (0.33 + 0.05 * math.sin(t)) * t) * 0.08
        add_sample(start_index + offset, (low_state * 2.5 + foam_state * 0.026 + roll) * amplitude * swell, pan)


def add_water_bowl(start: float, amplitude: float = 0.025, *, pan: float = 0.28) -> None:
    duration = 0.9
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    partials = [(980, 1.0), (1320, 0.42), (1780, 0.20)]

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-5.8 * t)
        tone = sum(weight * math.sin(2 * math.pi * freq * t) for freq, weight in partials)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def note(name: str) -> float:
    midi_notes = {
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
    }
    return midi_to_hz(midi_notes[name])


def add_pad_chord(start: float, duration: float, names: list[str], amplitude: float) -> None:
    spread = [-0.18, -0.04, 0.14, 0.24]
    for index, name in enumerate(names):
        add_tone(
            start,
            duration,
            note(name),
            amplitude / max(len(names), 1),
            pan=spread[index % len(spread)],
            attack=2.8,
            release=3.8,
            waveform="warm",
            vibrato_depth=0.0014,
            vibrato_rate=0.19 + index * 0.03,
            curve=0.03,
        )


def arrange() -> None:
    add_breeze(0.0, DURATION_SECONDS, 0.72, pan=-0.10)

    for bar in range(-1, BARS + 1, 2):
        add_wave(max(0.0, beat_time(bar, 0.0)), 0.54, pan=-0.18)
        add_wave(max(0.0, beat_time(bar, 2.15)), 0.36, pan=0.20)

    chords = [
        (0, ["C3", "G3", "C4", "E4"], 0.054, 8),
        (8, ["A3", "C4", "E4", "G4"], 0.046, 8),
        (16, ["G3", "C4", "D4", "G4"], 0.050, 8),
        (24, ["C3", "G3", "C4", "E4"], 0.058, 8),
        (32, ["A3", "C4", "E4", "G4"], 0.042, 4),
        (36, ["C3", "G3", "C4", "E4"], 0.038, 4),
    ]
    for bar, names, amp, bars in chords:
        add_pad_chord(beat_time(bar), beat_time(bars) - beat_time(0), names, amp)

    base_phrase = [
        (0.00, "C4", 0.52, -0.20),
        (1.50, "E4", 0.42, -0.12),
        (2.50, "G4", 0.56, 0.10),
        (4.00, "E4", 0.40, -0.06),
        (5.25, "D4", 0.44, 0.16),
        (6.50, "C4", 0.62, 0.02),
        (8.00, "G4", 0.44, 0.20),
        (9.50, "A4", 0.42, 0.12),
        (10.75, "G4", 0.52, -0.04),
        (12.50, "E4", 0.44, -0.16),
        (14.00, "D4", 0.42, 0.10),
        (15.00, "C4", 0.68, -0.06),
    ]
    for section_start, amp in [(0, 0.064), (16, 0.058), (24, 0.070)]:
        for beat, name, length, pan in base_phrase:
            start_beat = section_start * BEATS_PER_BAR + beat
            if start_beat >= BARS * BEATS_PER_BAR:
                continue
            add_sanshin_pluck(
                start_beat * BEAT_SECONDS,
                length * BEAT_SECONDS,
                note(name),
                amp,
                pan=pan,
            )

    answer_phrase = [
        (8, 0.50, "E5", 0.38, 0.22),
        (8, 1.50, "D5", 0.34, 0.14),
        (9, 0.25, "C5", 0.52, -0.02),
        (24, 2.00, "G5", 0.32, 0.24),
        (25, 0.00, "E5", 0.42, 0.12),
        (26, 1.50, "D5", 0.38, -0.08),
        (27, 0.50, "C5", 0.56, 0.04),
    ]
    for bar, beat, name, length, pan in answer_phrase:
        add_sanshin_pluck(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.045, pan=pan, brightness=0.62)

    for bar in (6, 13, 21, 30, 37):
        add_water_bowl(beat_time(bar, 2.75), pan=0.32 if bar % 2 else -0.24)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.18) / math.tanh(1.18)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.68 / peak

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
