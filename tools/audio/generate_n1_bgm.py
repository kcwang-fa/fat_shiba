#!/usr/bin/env python3
"""Generate the N1 Tohoku/Hokkaido background music loop.

The arrangement is deterministic and uses only Python's standard library.
It is an original, lighter gameplay loop inspired by Nebuta Matsuri hayashi:
bright fue-like melody, bouncing taiko, small kane hits, and crisp plucked
strings over a colder Tohoku/Hokkaido pad.
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
BPM = 116
BEAT_SECONDS = 60 / BPM
BARS = 48
BEATS_PER_BAR = 4
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n1-tohoku-hokkaido-bgm.wav"

random.seed(20260717)


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


def add_chappa(start: float, amplitude: float = 0.030, pan: float = 0.34) -> None:
    duration = 0.18
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    partials = [(2100, 1.0), (3180, 0.58), (4620, 0.28), (6200, 0.16)]

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-24 * t)
        noise = (random.random() * 2 - 1) * 0.38
        tone = sum(weight * math.sin(2 * math.pi * freq * t) for freq, weight in partials)
        add_sample(start_index + offset, (tone + noise) * amplitude * env, pan)


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
        "C4": 60,
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
        "D6": 86,
        "E6": 88,
        "G6": 91,
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
    add_snow(0.0, DURATION_SECONDS, 0.30, pan=-0.04)

    for bar, root, amp, bars in [
        (0, "E2", 0.030, 16),
        (16, "B2", 0.026, 8),
        (24, "E2", 0.032, 16),
        (40, "E2", 0.024, 8),
    ]:
        add_tone(beat_time(bar), beat_time(bars) - beat_time(0), note(root), amp, pan=-0.18, attack=1.6, release=2.0, curve=0.02)

    chord_cycle = [
        (["E3", "G3", "B3", "E4"], 0.050),
        (["G3", "B3", "D4", "G4"], 0.046),
        (["A3", "D4", "E4", "A4"], 0.048),
        (["E3", "A3", "B3", "E4"], 0.052),
    ]
    for block_start in range(0, BARS, 8):
        section_gain = 1.10 if 24 <= block_start < 40 else 0.92 if block_start >= 40 else 1.0
        for offset, (names, amp) in enumerate(chord_cycle):
            bar = block_start + offset * 2
            add_pad_chord(beat_time(bar), beat_time(2), names, amp * section_gain, pan=0.02)

    intro_notes = [
        (0, 0.00, "E4", 0.72, -0.20),
        (1, 0.50, "G4", 0.46, -0.08),
        (2, 0.00, "A4", 0.58, 0.10),
        (3, 1.50, "B4", 0.50, -0.12),
        (4, 0.00, "D5", 0.62, 0.08),
        (6, 2.00, "B4", 0.82, -0.04),
    ]
    for bar, beat, name, length, pan in intro_notes:
        add_piano(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.086, pan=pan)

    pluck_a = [(0.00, "E4", 0.18), (0.50, "B4", 0.15), (1.00, "D5", 0.18), (1.50, "B4", 0.13), (2.00, "A4", 0.18), (2.50, "G4", 0.15), (3.25, "E4", 0.20)]
    pluck_b = [(0.00, "G4", 0.17), (0.50, "A4", 0.14), (1.00, "B4", 0.16), (1.75, "D5", 0.18), (2.25, "B4", 0.15), (3.00, "A4", 0.18), (3.50, "G4", 0.14)]
    for bar in range(4, BARS):
        pattern = pluck_a if bar % 4 in (0, 1) else pluck_b
        amp = 0.058 if bar < 16 else 0.073 if bar < 40 else 0.052
        for beat, name, length in pattern:
            add_pluck(beat_time(bar, beat), length * BEAT_SECONDS, note(name), amp, pan=0.28)

    # Nebuta-inspired hayashi groove: light taiko bounce, shime accents, and kane.
    for bar in range(4, BARS):
        section = 0 if bar < 16 else 1 if bar < 32 else 2 if bar < 40 else 3
        main_amp = [0.25, 0.36, 0.46, 0.28][section]
        add_taiko(beat_time(bar, 0.0), amplitude=main_amp, pan=-0.16)
        add_taiko(beat_time(bar, 2.0), amplitude=main_amp * 0.62, pan=-0.06)
        if bar >= 8:
            add_shime(beat_time(bar, 0.75), amplitude=0.060 + section * 0.016, pan=0.22)
            add_shime(beat_time(bar, 1.50), amplitude=0.070 + section * 0.014, pan=0.30)
            add_shime(beat_time(bar, 2.75), amplitude=0.064 + section * 0.016, pan=0.26)
            add_chappa(beat_time(bar, 1.0), amplitude=0.018 + section * 0.004, pan=0.34)
            add_chappa(beat_time(bar, 3.0), amplitude=0.022 + section * 0.005, pan=0.26)
        if bar % 8 == 7:
            add_kane(beat_time(bar, 3.0), amplitude=0.042 if bar < 40 else 0.030, pan=0.14)

    hayashi_phrase = [
        (0.00, "B4", 0.38),
        (0.50, "D5", 0.30),
        (1.00, "E5", 0.44),
        (1.75, "D5", 0.26),
        (2.25, "B4", 0.34),
        (3.00, "A4", 0.42),
        (4.00, "B4", 0.32),
        (4.50, "D5", 0.32),
        (5.00, "E5", 0.50),
        (6.00, "G5", 0.34),
        (6.50, "E5", 0.34),
        (7.25, "D5", 0.44),
    ]
    answer_phrase = [
        (0.00, "E5", 0.36),
        (0.50, "G5", 0.30),
        (1.00, "A5", 0.40),
        (1.75, "G5", 0.28),
        (2.25, "E5", 0.34),
        (3.00, "D5", 0.42),
        (4.00, "B4", 0.34),
        (4.75, "D5", 0.30),
        (5.25, "E5", 0.46),
        (6.25, "B4", 0.42),
        (7.00, "A4", 0.44),
    ]
    for section_start in range(8, 40, 8):
        phrase = hayashi_phrase if section_start % 16 == 8 else answer_phrase
        amp = 0.068 if section_start < 24 else 0.088
        for beat, name, length in phrase:
            add_tone(
                beat_time(section_start, beat),
                length * BEAT_SECONDS,
                note(name),
                amp,
                pan=-0.24,
                attack=0.035,
                release=0.18,
                waveform="reed",
                vibrato_depth=0.0048,
                vibrato_rate=5.2,
                breath=0.016,
                curve=0.06,
            )

    high_flourish = [
        (32, 0.00, "E5", 0.34),
        (32, 0.50, "G5", 0.28),
        (32, 1.00, "A5", 0.28),
        (32, 1.50, "B5", 0.42),
        (33, 0.00, "D6", 0.32),
        (33, 0.50, "B5", 0.28),
        (33, 1.00, "A5", 0.34),
        (34, 0.00, "G5", 0.38),
        (34, 0.75, "E5", 0.42),
        (35, 1.00, "D5", 0.52),
        (36, 0.00, "E5", 0.34),
        (36, 0.50, "G5", 0.28),
        (36, 1.00, "A5", 0.30),
        (36, 1.50, "B5", 0.44),
        (37, 0.00, "D6", 0.36),
        (37, 0.50, "E6", 0.46),
        (38, 0.00, "B5", 0.44),
        (39, 0.00, "G5", 0.62),
    ]
    for bar, beat, name, length in high_flourish:
        add_tone(
            beat_time(bar, beat),
            length * BEAT_SECONDS,
            note(name),
            0.076,
            pan=-0.16,
            attack=0.028,
            release=0.16,
            waveform="reed",
            vibrato_depth=0.0052,
            vibrato_rate=5.4,
            breath=0.018,
            curve=0.05,
        )

    closing_phrase = [
        (40, 0.00, "B4", 0.44, -0.20),
        (40, 1.00, "D5", 0.34, 0.08),
        (41, 0.00, "E5", 0.52, -0.10),
        (42, 1.00, "B4", 0.48, 0.12),
        (43, 2.00, "A4", 0.50, -0.06),
        (44, 0.00, "G4", 0.56, 0.10),
        (45, 1.50, "B4", 0.46, -0.16),
        (46, 2.00, "E4", 0.70, 0.04),
    ]
    for bar, beat, name, length, pan in closing_phrase:
        add_piano(beat_time(bar, beat), length * BEAT_SECONDS, note(name), 0.068, pan=pan)
        add_pluck(beat_time(bar, beat + 0.035), length * BEAT_SECONDS * 0.72, note(name), 0.030, pan=0.24)


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
