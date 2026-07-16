#!/usr/bin/env python3
"""Generate the N4 Kyushu/Shikoku game background music loop.

This is the brighter onsen-street arrangement for gameplay. The existing
``generate_n4_bgm.py`` script remains the quiet vocabulary-review focus BGM.
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
BPM = 124
BEAT_SECONDS = 60 / BPM
BEATS_PER_BAR = 4
BARS = 48
DURATION_SECONDS = BARS * BEATS_PER_BAR * BEAT_SECONDS
OUTPUT_PATH = PROJECT_ROOT / "web" / "assets" / "audio" / "n4-kyushu-shikoku-game-bgm.wav"

random.seed(20260716)


def midi_to_hz(midi_note: float) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))


NOTE_MIDI = {
    "G2": 43,
    "D3": 50,
    "E3": 52,
    "G3": 55,
    "A3": 57,
    "B3": 59,
    "C4": 60,
    "D4": 62,
    "E4": 64,
    "F#4": 66,
    "G4": 67,
    "A4": 69,
    "B4": 71,
    "C5": 72,
    "D5": 74,
    "E5": 76,
    "G5": 79,
    "A5": 81,
    "B5": 83,
    "D6": 86,
}


def note(name: str) -> float:
    return midi_to_hz(NOTE_MIDI[name])


def beat_time(bar: int, beat: float = 0.0) -> float:
    return (bar * BEATS_PER_BAR + beat) * BEAT_SECONDS


sample_count = int(DURATION_SECONDS * SAMPLE_RATE)
left = array("f", [0.0]) * sample_count
right = array("f", [0.0]) * sample_count


def equal_power_pan(value: float) -> tuple[float, float]:
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def add_sample(index: int, value: float, pan: float) -> None:
    if 0 <= index < sample_count:
        left_gain, right_gain = equal_power_pan(pan)
        left[index] += value * left_gain
        right[index] += value * right_gain


def envelope(position: float, duration: float, attack: float, release: float, curve: float = 0.8) -> float:
    if position < 0 or position >= duration:
        return 0.0
    if position < attack:
        return position / max(attack, 0.0001)
    if position > duration - release:
        return max(0.0, (duration - position) / max(release, 0.0001))
    body = (position - attack) / max(duration - attack - release, 0.0001)
    return math.exp(-body * curve)


def add_tone(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    attack: float = 0.02,
    release: float = 0.18,
    waveform: str = "sine",
    vibrato_depth: float = 0.0,
    vibrato_rate: float = 4.8,
    curve: float = 0.65,
    breath: float = 0.0,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    phase = random.random() * math.tau

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        current_frequency = frequency * (1 + vibrato_depth * math.sin(math.tau * vibrato_rate * t))
        phase += math.tau * current_frequency / SAMPLE_RATE
        if waveform == "flute":
            tone = (
                math.sin(phase)
                + 0.13 * math.sin(phase * 2.01)
                + 0.05 * math.sin(phase * 3.0)
            )
        elif waveform == "warm":
            tone = math.sin(phase) + 0.20 * math.sin(phase * 2.0) + 0.06 * math.sin(phase * 3.0)
        elif waveform == "triangle":
            tone = 2 * abs(2 * ((phase / math.tau) % 1) - 1) - 1
        else:
            tone = math.sin(phase)
        air = (random.random() * 2 - 1) * breath
        env = envelope(t, duration, attack, release, curve)
        add_sample(start_index + offset, (tone + air) * amplitude * env, pan)


def add_pluck(
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    pan: float = 0.0,
    brightness: float = 0.8,
    twang: float = 0.0,
) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    detuned = frequency * (1.003 + twang)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        body = math.exp(-5.4 * t / max(duration, 0.001))
        pick = math.exp(-90 * t)
        tone = (
            math.sin(math.tau * frequency * t)
            + 0.48 * brightness * math.sin(math.tau * frequency * 2.0 * t)
            + 0.22 * brightness * math.sin(math.tau * frequency * 3.02 * t)
            + 0.12 * math.sin(math.tau * detuned * t)
            + (random.random() * 2 - 1) * 0.10 * pick
        )
        add_sample(start_index + offset, tone * amplitude * body, pan)


def add_bass(start: float, duration: float, frequency: float, amplitude: float) -> None:
    add_tone(
        start,
        duration,
        frequency,
        amplitude,
        pan=-0.05,
        attack=0.012,
        release=0.16,
        waveform="warm",
        curve=0.92,
    )


def add_shamisen(start: float, frequency: float, amplitude: float, *, pan: float = -0.18) -> None:
    add_pluck(start, 0.34, frequency, amplitude, pan=pan, brightness=1.18, twang=0.004)


def add_koto(start: float, duration: float, frequency: float, amplitude: float, *, pan: float = 0.18) -> None:
    add_pluck(start, duration, frequency, amplitude, pan=pan, brightness=0.66)


def add_marimba(start: float, frequency: float, amplitude: float, *, pan: float = 0.24) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(0.55 * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-7.2 * t)
        tone = (
            math.sin(math.tau * frequency * t)
            + 0.30 * math.sin(math.tau * frequency * 2.99 * t)
            + 0.11 * math.sin(math.tau * frequency * 5.01 * t)
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_bell(start: float, frequency: float, amplitude: float, *, pan: float = 0.36) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(1.4 * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-4.2 * t)
        tone = (
            math.sin(math.tau * frequency * t)
            + 0.46 * math.sin(math.tau * frequency * 2.41 * t)
            + 0.18 * math.sin(math.tau * frequency * 3.98 * t)
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_taiko(start: float, amplitude: float = 0.19, *, pan: float = -0.06) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(0.34 * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        pitch = 112 * math.exp(-5.4 * t) + 48
        env = math.exp(-13.5 * t)
        skin = math.sin(math.tau * pitch * t)
        click = (random.random() * 2 - 1) * math.exp(-70 * t) * 0.18
        add_sample(start_index + offset, (skin + click) * amplitude * env, pan)


def add_hyoshigi(start: float, amplitude: float = 0.07, *, pan: float = 0.16) -> None:
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(0.12 * SAMPLE_RATE)

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        env = math.exp(-36 * t)
        tone = (
            math.sin(math.tau * 1520 * t)
            + 0.38 * math.sin(math.tau * 2440 * t)
            + (random.random() * 2 - 1) * 0.28
        )
        add_sample(start_index + offset, tone * amplitude * env, pan)


def add_warm_street_air() -> None:
    low_l = 0.0
    low_r = 0.0
    for index in range(sample_count):
        t = index / SAMPLE_RATE
        raw_l = random.random() * 2 - 1
        raw_r = random.random() * 2 - 1
        low_l = low_l * 0.9993 + raw_l * 0.0007
        low_r = low_r * 0.9991 + raw_r * 0.0009
        pulse = 0.64 + 0.36 * math.sin(math.tau * 0.035 * t + 0.4)
        left[index] += low_l * 0.015 * pulse
        right[index] += low_r * 0.015 * pulse


def add_flute_phrase(bar: int, phrase: list[tuple[float, str, float]], *, amp: float = 0.094) -> None:
    for beat, name, length in phrase:
        add_tone(
            beat_time(bar, beat),
            length * BEAT_SECONDS,
            note(name),
            amp,
            pan=0.07,
            attack=0.035,
            release=0.12,
            waveform="flute",
            vibrato_depth=0.003,
            vibrato_rate=5.2,
            curve=0.30,
            breath=0.010,
        )


def add_chord_bar(bar: int, names: tuple[str, str, str], bass_name: str) -> None:
    start = beat_time(bar)
    for index, name in enumerate(names):
        add_koto(start + index * 0.048, 1.15, note(name), 0.035, pan=-0.18 + index * 0.18)
    add_bass(start, 1.7 * BEAT_SECONDS, note(bass_name), 0.066)


def arrange() -> None:
    add_warm_street_air()

    chord_cycle = [
        (("G3", "B3", "D4"), "G2"),
        (("D3", "A3", "D4"), "D3"),
        (("E3", "G3", "B3"), "E3"),
        (("B3", "D4", "F#4"), "B3"),
        (("C4", "E4", "G4"), "C4"),
        (("G3", "B3", "D4"), "G2"),
        (("A3", "C4", "E4"), "A3"),
        (("D3", "A3", "D4"), "D3"),
    ]
    for bar in range(BARS):
        names, bass_name = chord_cycle[bar % len(chord_cycle)]
        add_chord_bar(bar, names, bass_name)

    intro = [(0.0, "B4", 0.42), (0.5, "D5", 0.48), (1.0, "G5", 0.84), (2.5, "A5", 0.42), (3.0, "G5", 0.70)]
    a_phrase = [
        (0.0, "G4", 0.40),
        (0.5, "A4", 0.40),
        (1.0, "B4", 0.42),
        (1.5, "D5", 0.72),
        (2.5, "B4", 0.36),
        (3.0, "A4", 0.36),
        (3.5, "G4", 0.48),
        (4.0, "E4", 0.38),
        (4.5, "G4", 0.38),
        (5.0, "A4", 0.40),
        (5.5, "B4", 0.66),
        (6.5, "A4", 0.38),
        (7.0, "G4", 0.38),
        (7.5, "E4", 0.50),
    ]
    a_turn = [
        (0.0, "G4", 0.38),
        (0.5, "A4", 0.38),
        (1.0, "B4", 0.38),
        (1.5, "D5", 0.48),
        (2.0, "E5", 0.40),
        (2.5, "D5", 0.38),
        (3.0, "B4", 0.36),
        (3.5, "A4", 0.44),
        (4.0, "G4", 0.36),
        (4.5, "A4", 0.36),
        (5.0, "B4", 0.38),
        (5.5, "G4", 0.46),
        (6.5, "A4", 0.46),
        (7.25, "G4", 0.62),
    ]
    b_phrase = [
        (0.0, "C5", 0.62),
        (1.0, "D5", 0.62),
        (2.0, "G5", 0.84),
        (3.0, "E5", 0.56),
        (4.0, "C5", 0.54),
        (5.0, "D5", 0.56),
        (6.0, "B4", 0.42),
        (6.5, "D5", 0.42),
        (7.0, "E5", 0.72),
    ]
    loop_tag = [
        (0.0, "B4", 0.36),
        (0.5, "D5", 0.36),
        (1.0, "G5", 0.58),
        (2.0, "A5", 0.36),
        (2.5, "G5", 0.36),
        (3.0, "E5", 0.48),
        (4.0, "D5", 0.42),
        (4.5, "B4", 0.42),
        (5.0, "A4", 0.46),
        (6.0, "G4", 0.84),
    ]
    add_flute_phrase(0, intro, amp=0.082)
    add_flute_phrase(4, a_phrase)
    add_flute_phrase(12, a_turn)
    add_flute_phrase(20, a_phrase)
    add_flute_phrase(28, b_phrase, amp=0.088)
    add_flute_phrase(36, a_turn)
    add_flute_phrase(44, loop_tag, amp=0.086)

    shamisen_pattern = [
        (0.0, "G4", 0.048),
        (1.0, "D4", 0.040),
        (1.5, "G4", 0.044),
        (2.5, "B4", 0.038),
        (3.0, "D5", 0.044),
    ]
    for bar in range(2, BARS):
        for beat, name, amp in shamisen_pattern:
            add_shamisen(beat_time(bar, beat), note(name), amp, pan=-0.24 if bar % 2 == 0 else -0.14)

    for bar in range(4, BARS, 4):
        add_marimba(beat_time(bar, 3.0), note("D5"), 0.035, pan=0.30)
        add_bell(beat_time(bar, 3.55), note("G5"), 0.018, pan=0.42)
    for bar in range(6, BARS, 8):
        add_marimba(beat_time(bar, 2.0), note("B4"), 0.031, pan=-0.30)

    for bar in range(BARS):
        add_taiko(beat_time(bar, 0.0), 0.140 if bar % 4 else 0.175)
        if bar >= 4:
            add_taiko(beat_time(bar, 3.0), 0.090, pan=-0.02)
            add_hyoshigi(beat_time(bar, 1.5), 0.044, pan=0.22)
            add_hyoshigi(beat_time(bar, 3.5), 0.050, pan=0.30)

    for bar in [15, 23, 31, 39, 47]:
        add_bell(beat_time(bar, 3.25), note("D6"), 0.020, pan=0.38)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.10) / math.tanh(1.10)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.74 / peak

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
