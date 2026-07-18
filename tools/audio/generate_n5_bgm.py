#!/usr/bin/env python3
"""Generate the N5 Okinawa vocabulary-review ocean loop.

The arrangement is deterministic and uses only Python's standard library.
It is intentionally a non-musical soundscape: sea breeze, rolling waves,
and soft shoreline foam for vocabulary review.
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
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n5-okinawa-focus-bgm.wav"

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
    duration = 6.4
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    foam_state = 0.0
    hiss_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.99955 + raw * 0.00045
        foam_state = foam_state * 0.80 + raw * 0.20
        hiss_state = hiss_state * 0.48 + raw * 0.52
        swell = math.sin(math.pi * min(t / duration, 1.0)) ** 1.45
        crash = math.exp(-((t - 2.35) / 0.82) ** 2)
        backwash = math.exp(-((t - 4.65) / 1.05) ** 2)
        roll = math.sin(2 * math.pi * (0.17 + 0.025 * math.sin(t * 0.7)) * t) * 0.32
        foam = foam_state * (0.018 * swell + 0.070 * crash + 0.032 * backwash)
        hiss = hiss_state * (0.018 * crash + 0.010 * backwash)
        add_sample(start_index + offset, (low_state * 7.2 + roll + foam + hiss) * amplitude * swell, pan)


def add_distant_surf(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    foam_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.99975 + raw * 0.00025
        foam_state = foam_state * 0.90 + raw * 0.10
        tide = 0.66 + 0.34 * math.sin(2 * math.pi * 0.045 * (start + t) + 0.8)
        env = envelope(t, duration, 4.2, 5.2, 0.02)
        add_sample(start_index + offset, (low_state * 5.8 + foam_state * 0.018) * amplitude * tide * env, pan)


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
    add_breeze(0.0, DURATION_SECONDS, 0.58, pan=-0.08)
    add_distant_surf(0.0, DURATION_SECONDS, 0.62, pan=0.06)

    wave_start = -3.0
    wave_index = 0
    while wave_start < DURATION_SECONDS + 5.0:
        pan = -0.32 if wave_index % 2 == 0 else 0.26
        amplitude = 0.64 + 0.16 * math.sin(wave_index * 0.83)
        add_wave(max(0.0, wave_start), amplitude, pan=pan)
        wave_start += 6.9 + 0.85 * math.sin(wave_index * 0.57)
        wave_index += 1

    # Quieter backwash between larger waves keeps the shoreline moving.
    wave_start = 2.2
    wave_index = 0
    while wave_start < DURATION_SECONDS:
        pan = 0.34 if wave_index % 2 == 0 else -0.22
        amplitude = 0.20 + 0.05 * math.sin(wave_index * 1.17 + 0.4)
        add_wave(wave_start, amplitude, pan=pan)
        wave_start += 9.4 + 0.65 * math.sin(wave_index * 0.41)
        wave_index += 1


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
