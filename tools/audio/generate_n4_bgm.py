#!/usr/bin/env python3
"""Generate the N4 Kyushu/Shikoku vocabulary-review valley-stream ASMR loop.

The arrangement is deterministic and uses only Python's standard library.
It is intentionally a non-musical soundscape inspired by valley-stream white
noise: shallow creek flow, bright riffles over stones, and occasional splashes.
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
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n4-kyushu-shikoku-bgm.wav"

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
    body_state = 0.0
    stream_state = 0.0
    surface_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        body_state = body_state * 0.99935 + raw * 0.00065
        stream_state = stream_state * 0.986 + raw * 0.014
        surface_state = surface_state * 0.68 + raw * 0.32
        slow_surge = 0.92 + 0.08 * math.sin(2 * math.pi * 0.055 * (start + t) + 0.7)
        fine_ripple = 0.82 + 0.18 * math.sin(2 * math.pi * 1.9 * (start + t) + 1.3)
        env = envelope(t, duration, 2.8, 4.0, 0.014)
        flow = body_state * 1.15 + stream_state * 0.18 + surface_state * 0.026 * fine_ripple
        add_sample(start_index + offset, flow * amplitude * slow_surge * env, pan)


def add_bamboo_spout(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    stream_state = 0.0
    bead_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        stream_state = stream_state * 0.985 + raw * 0.015
        bead_state = bead_state * 0.35 + raw * 0.65
        narrow_stream = max(0.0, math.sin(2 * math.pi * 7.2 * (start + t))) ** 8
        shimmer = 0.76 + 0.24 * math.sin(2 * math.pi * 3.7 * (start + t) + 0.6)
        env = envelope(t, duration, 0.9, 1.4, 0.012)
        add_sample(start_index + offset, (stream_state * 0.10 + bead_state * 0.026 * narrow_stream) * amplitude * shimmer * env, pan)


def add_steam_air(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    veil_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9991 + raw * 0.0009
        veil_state = veil_state * 0.82 + raw * 0.18
        warmth = 0.78 + 0.22 * math.sin(2 * math.pi * 0.021 * (start + t) + 0.2)
        env = envelope(t, duration, 4.0, 5.4, 0.012)
        add_sample(start_index + offset, (low_state * 2.2 + veil_state * 0.010) * amplitude * warmth * env, pan)


def add_fine_snow(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    snow_state = 0.0
    brush_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        snow_state = snow_state * 0.42 + raw * 0.58
        brush_state = brush_state * 0.93 + raw * 0.07
        flurry = 0.62 + 0.38 * math.sin(2 * math.pi * 0.037 * (start + t) + 1.6)
        env = envelope(t, duration, 5.0, 6.0, 0.01)
        add_sample(start_index + offset, (snow_state * 0.010 + brush_state * 0.020) * amplitude * flurry * env, pan)


def add_creek_body(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    mid_state = 0.0
    surface_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.9992 + raw * 0.0008
        mid_state = mid_state * 0.972 + raw * 0.028
        surface_state = surface_state * 0.62 + raw * 0.38
        current = 0.84 + 0.16 * math.sin(2 * math.pi * 0.085 * (start + t) + 0.5)
        stone_chatter = 0.74 + 0.26 * math.sin(2 * math.pi * 2.7 * (start + t) + 1.2)
        env = envelope(t, duration, 2.2, 3.2, 0.012)
        flow = low_state * 1.35 + mid_state * 0.34 + surface_state * 0.030 * stone_chatter
        add_sample(start_index + offset, flow * amplitude * current * env, pan)


def add_riffle_sheet(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    sheet_state = 0.0
    fizz_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        sheet_state = sheet_state * 0.90 + raw * 0.10
        fizz_state = fizz_state * 0.38 + raw * 0.62
        riffle = 0.72 + 0.28 * math.sin(2 * math.pi * 4.8 * (start + t) + 0.7)
        shimmer = 0.65 + 0.35 * math.sin(2 * math.pi * 0.19 * (start + t) + 1.9)
        env = envelope(t, duration, 1.6, 2.4, 0.010)
        add_sample(start_index + offset, (sheet_state * 0.10 + fizz_state * 0.028 * riffle) * amplitude * shimmer * env, pan)


def add_whitewater_spray(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    spray_state = 0.0
    mist_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        spray_state = spray_state * 0.55 + raw * 0.45
        mist_state = mist_state * 0.965 + raw * 0.035
        pulse = 0.76 + 0.24 * math.sin(2 * math.pi * 0.31 * (start + t) + 0.4)
        env = envelope(t, duration, 1.8, 2.8, 0.014)
        add_sample(start_index + offset, (spray_state * 0.024 + mist_state * 0.050) * amplitude * pulse * env, pan)


def add_stream_splash(start: float, amplitude: float, *, pan: float = 0.0, duration: float = 0.78) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    low_state = 0.0
    splash_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        low_state = low_state * 0.997 + raw * 0.003
        splash_state = splash_state * 0.50 + raw * 0.50
        strike = math.exp(-9.0 * t)
        tail = math.exp(-2.8 * t)
        arc = math.sin(math.pi * min(t / duration, 1.0)) ** 0.7
        hit = low_state * 4.4 * strike + splash_state * 0.13 * tail
        add_sample(start_index + offset, hit * amplitude * arc, pan)


def add_bubble(start: float, amplitude: float = 0.012, *, pan: float = 0.0) -> None:
    duration = 0.24
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    base_freq = 310 + 70 * random.random()

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.sin(math.pi * min(t / duration, 1.0)) ** 2
        chirp = base_freq * (1.0 + 0.42 * t / duration)
        tone = math.sin(2 * math.pi * chirp * t) + 0.18 * math.sin(2 * math.pi * chirp * 2.1 * t)
        noise = (random.random() * 2 - 1) * 0.16
        add_sample(start_index + offset, (tone * 0.34 + noise) * amplitude * env, pan)


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
    add_creek_body(0.0, DURATION_SECONDS, 0.84, pan=-0.06)
    add_creek_body(1.9, DURATION_SECONDS - 1.9, 0.46, pan=0.26)
    add_riffle_sheet(0.0, DURATION_SECONDS, 1.02, pan=0.18)
    add_riffle_sheet(3.4, DURATION_SECONDS - 3.4, 0.58, pan=-0.30)
    add_whitewater_spray(0.0, DURATION_SECONDS, 0.72, pan=0.04)

    splash_time = 2.2
    splash_index = 0
    while splash_time < DURATION_SECONDS - 1.0:
        pan = [-0.30, 0.22, -0.08, 0.34][splash_index % 4]
        amplitude = 0.034 + 0.020 * (0.5 + 0.5 * math.sin(splash_index * 1.47))
        duration = 0.48 + 0.34 * (0.5 + 0.5 * math.sin(splash_index * 0.82 + 0.3))
        add_stream_splash(splash_time, amplitude=amplitude, pan=pan, duration=duration)
        splash_time += 3.4 + 1.6 * (0.5 + 0.5 * math.sin(splash_index * 0.69 + 1.1))
        splash_index += 1


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
