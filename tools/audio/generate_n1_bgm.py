#!/usr/bin/env python3
"""Generate the N1 Tohoku/Hokkaido background music loop.

The arrangement is deterministic and uses only Python's standard library.
It sketches four scenes: a quiet snowy night, a Tohoku festival pulse,
a destination-arrival climax, then a return to still snow.
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
BPM = 96
BEAT_SECONDS = 60 / BPM
BARS = 48
BEATS_PER_BAR = 4
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n1-tohoku-hokkaido-bgm.wav"

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
    attack: float = 0.04,
    release: float = 0.16,
    waveform: str = "sine",
    vibrato_depth: float = 0.0,
    vibrato_rate: float = 4.2,
    breath: float = 0.0,
    curve: float = 0.4,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    phase = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        current_frequency = frequency * (1 + vibrato_depth * math.sin(2 * math.pi * vibrato_rate * t))
        phase += 2 * math.pi * current_frequency / SAMPLE_RATE
        if waveform == "triangle":
            tone = 2 * abs(2 * ((phase / (2 * math.pi)) % 1) - 1) - 1
        elif waveform == "reed":
            tone = math.sin(phase) + 0.22 * math.sin(phase * 2.01) + 0.08 * math.sin(phase * 3.03)
        elif waveform == "warm":
            tone = math.sin(phase) + 0.18 * math.sin(phase * 2.0) + 0.07 * math.sin(phase * 0.5)
        else:
            tone = math.sin(phase)

        env = envelope(t, duration, attack, release, curve)
        noise = (random.random() * 2 - 1) * breath
        add_sample(start_index + offset, (tone + noise) * amplitude * env, pan)


def add_piano(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    softness: float = 0.7,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detune = frequency * 1.004

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        hit = math.exp(-42 * t)
        body = math.exp(-2.8 * t / max(duration, 0.001))
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.28 * softness * math.sin(2 * math.pi * frequency * 2 * t)
            + 0.16 * math.sin(2 * math.pi * detune * t)
            + (random.random() * 2 - 1) * 0.028 * hit
        )
        add_sample(start_index + offset, tone * amplitude * body, pan)


def add_pluck(start: float, duration: float, frequency: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-5.8 * t / max(duration, 0.001))
        snap = math.exp(-85 * t)
        tone = (
            math.sin(2 * math.pi * frequency * t)
            + 0.42 * math.sin(2 * math.pi * frequency * 2 * t)
            + 0.18 * math.sin(2 * math.pi * frequency * 3 * t)
            + (random.random() * 2 - 1) * 0.11 * snap
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_train_pulse(start: float, amplitude: float = 0.12, pan: float = -0.12) -> None:
    duration = 0.38
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        low = math.sin(2 * math.pi * (72 + 22 * math.exp(-9 * t)) * t) * math.exp(-9.4 * t)
        air = (random.random() * 2 - 1) * math.exp(-28 * t) * 0.28
        add_sample(start_index + offset, (low + air) * amplitude, pan)


def add_taiko(start: float, amplitude: float = 0.46, pan: float = -0.08) -> None:
    duration = 0.58
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        pitch = 104 * math.exp(-7.5 * t) + 44
        body = math.sin(2 * math.pi * pitch * t) * math.exp(-7.2 * t)
        slap = (random.random() * 2 - 1) * math.exp(-46 * t) * 0.44
        add_sample(start_index + offset, (body + slap) * amplitude, pan)


def add_shime(start: float, amplitude: float = 0.14, pan: float = 0.24) -> None:
    duration = 0.14
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-34 * t)
        tone = math.sin(2 * math.pi * 360 * t) + 0.48 * math.sin(2 * math.pi * 540 * t)
        noise = (random.random() * 2 - 1) * 0.45
        add_sample(start_index + offset, (tone + noise) * amplitude * env, pan)


def add_kane(start: float, amplitude: float = 0.045, pan: float = 0.18) -> None:
    duration = 1.0
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    partials = [(1380, 1.0), (2075, 0.48), (2920, 0.22)]

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-3.8 * t)
        tone = sum(weight * math.sin(2 * math.pi * freq * t) for freq, weight in partials)
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_snow(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    high_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9991 + raw * 0.0009
        high_state = high_state * 0.90 + raw * 0.10
        gust = 0.58 + 0.42 * math.sin(2 * math.pi * 0.034 * (start + t) + 0.7)
        env = envelope(t, duration, 4.0, 5.5, 0.02)
        add_sample(start_index + offset, (low_state * 1.8 + high_state * 0.028) * amplitude * gust * env, pan)


def note(name: str) -> float:
    midi_notes = {
        "E2": 40,
        "B2": 47,
        "D3": 50,
        "E3": 52,
        "G3": 55,
        "A3": 57,
        "B3": 59,
        "D4": 62,
        "E4": 64,
        "G4": 67,
        "A4": 69,
        "B4": 71,
        "D5": 74,
        "E5": 76,
        "G5": 79,
        "A5": 81,
        "B5": 83,
    }
    return midi_to_hz(midi_notes[name])


def add_pad_chord(start: float, duration: float, names: list[str], amplitude: float, *, pan: float = 0.0) -> None:
    spread = [-0.22, -0.05, 0.14, 0.28]
    for index, name in enumerate(names):
        add_tone(
            start,
            duration,
            note(name),
            amplitude / max(len(names), 1),
            pan=pan + spread[index % len(spread)],
            attack=2.6,
            release=3.8,
            waveform="warm",
            vibrato_depth=0.0018,
            vibrato_rate=0.23 + index * 0.04,
            curve=0.03,
        )


def arrange() -> None:
    add_snow(0.0, DURATION_SECONDS, 0.70, pan=-0.04)

    # 0-8 bars: snowy night, quiet piano and wind.
    for bar, root, amp, bars in [(0, "E2", 0.044, 12), (8, "B2", 0.032, 12), (28, "E2", 0.060, 14), (42, "E2", 0.036, 6)]:
        add_tone(beat_time(bar), beat_time(bars) - beat_time(0), note(root), amp, pan=-0.18, attack=2.8, release=3.2, curve=0.02)

    intro_piano = [
        (0, 0.00, "E4", 1.60, -0.20),
        (1, 1.50, "G4", 1.05, -0.08),
        (3, 0.50, "B4", 1.25, 0.10),
        (5, 0.00, "A4", 1.10, -0.10),
        (6, 2.00, "E4", 1.45, 0.08),
    ]
    for bar, beat, name, length, pan in intro_piano:
        add_piano(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.112, pan=pan)

    chords = [
        (0, ["E3", "G3", "B3", "D4"], 0.050, 8),
        (8, ["E3", "G3", "B3", "E4"], 0.066, 8),
        (16, ["D3", "G3", "A3", "D4"], 0.074, 8),
        (24, ["E3", "A3", "B3", "E4"], 0.078, 4),
        (28, ["E3", "G3", "B3", "E4"], 0.122, 8),
        (36, ["G3", "A3", "D4", "E4"], 0.112, 6),
        (42, ["E3", "G3", "B3", "D4"], 0.046, 6),
    ]
    for bar, names, amp, bars in chords:
        add_pad_chord(beat_time(bar), beat_time(bars) - beat_time(0), names, amp, pan=0.04)

    # 8-28 bars: shamisen and taiko bring in a restrained Tohoku festival feel.
    shamisen_a = [(0.00, "E4", 0.26), (0.50, "B4", 0.20), (1.00, "D5", 0.24), (1.50, "B4", 0.18), (2.00, "A4", 0.24), (2.75, "G4", 0.20), (3.25, "E4", 0.24)]
    shamisen_b = [(0.00, "G4", 0.24), (0.50, "A4", 0.18), (1.25, "B4", 0.22), (2.00, "D5", 0.24), (2.50, "B4", 0.18), (3.25, "A4", 0.20)]
    for bar in range(8, 42):
        if bar >= 28 and bar % 2 == 1:
            continue
        pattern = shamisen_a if bar % 4 in (0, 1) else shamisen_b
        for beat, name, length in pattern:
            amp = 0.075 if bar < 28 else 0.058
            add_pluck(beat_time(bar, beat), length * BEAT_SECONDS, note(name), amp, pan=0.30)

    for bar in range(8, 28):
        add_taiko(beat_time(bar, 0.0), amplitude=0.36 if bar < 16 else 0.43, pan=-0.16)
        add_taiko(beat_time(bar, 2.0), amplitude=0.22 if bar < 16 else 0.28, pan=-0.06)
        if bar >= 12:
            add_shime(beat_time(bar, 1.5), amplitude=0.105, pan=0.22)
            add_shime(beat_time(bar, 3.5), amplitude=0.090, pan=0.30)
        if bar % 8 == 7:
            add_kane(beat_time(bar, 3.0), amplitude=0.043, pan=0.18)

    # 28-42 bars: arrival climax with strings, drums and flute.
    for bar in range(28, 42):
        add_taiko(beat_time(bar, 0.0), amplitude=0.58, pan=-0.18)
        add_taiko(beat_time(bar, 1.5), amplitude=0.28, pan=-0.02)
        add_taiko(beat_time(bar, 2.0), amplitude=0.44, pan=-0.12)
        add_shime(beat_time(bar, 0.75), amplitude=0.105, pan=0.26)
        add_shime(beat_time(bar, 2.75), amplitude=0.125, pan=0.32)
        if bar % 4 == 3:
            add_kane(beat_time(bar, 3.0), amplitude=0.050, pan=0.12)

    festival_flute_phrase = [
        (0, 0.00, "B4", 0.80),
        (1, 2.00, "D5", 0.70),
        (3, 0.00, "E5", 0.90),
        (4, 2.00, "D5", 0.70),
        (6, 0.00, "B4", 1.10),
    ]
    climax_flute_phrase = [
        (0, 0.00, "E5", 1.45),
        (2, 0.00, "G5", 1.35),
        (4, 0.00, "E5", 1.10),
        (5, 2.00, "D5", 0.95),
        (7, 0.00, "B4", 1.25),
        (9, 0.00, "D5", 1.05),
        (10, 2.00, "E5", 1.35),
        (12, 0.00, "G5", 1.70),
    ]
    flute_sections = [
        (festival_flute_phrase, 16, 0.060, -0.26, 28),
        (climax_flute_phrase, 28, 0.112, -0.16, 42),
    ]
    for phrase, section_start, amp, pan, limit in flute_sections:
        for phrase_bar, beat, name, length in phrase:
            bar = section_start + phrase_bar
            if bar >= limit:
                continue
            add_tone(
                beat_time(bar, beat),
                length * BEAT_SECONDS,
                note(name),
                amp,
                pan=pan,
                attack=0.10,
                release=0.28,
                waveform="reed",
                vibrato_depth=0.005,
                vibrato_rate=4.7,
                breath=0.018,
                curve=0.10,
            )

    climax_piano = [(28, 0.0, "E4", 0.9), (30, 0.0, "G4", 0.9), (32, 0.0, "B4", 1.0), (34, 0.0, "D5", 0.9), (36, 0.0, "E5", 1.2), (38, 1.0, "D5", 0.8), (40, 0.0, "B4", 1.1)]
    for bar, beat, name, length in climax_piano:
        add_piano(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.118, pan=-0.04)

    # 42-48 bars: only piano/plucked strings and snow again.
    outro_notes = [
        (42, 0.00, "E4", 1.30, -0.20),
        (43, 2.00, "B3", 1.20, 0.12),
        (45, 0.50, "G4", 1.10, -0.08),
        (46, 2.00, "E4", 1.70, 0.04),
    ]
    for bar, beat, name, length, pan in outro_notes:
        add_piano(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.092, pan=pan)
        add_pluck(beat_time(bar, beat + 0.04), length * BEAT_SECONDS * 0.78, note(name), 0.026, pan=0.22)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.25) / math.tanh(1.25)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.76 / peak

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
