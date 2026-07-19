#!/usr/bin/env python3
"""Generate the N3 Chugoku/Kansai vocabulary-review night-rain loop.

Deterministic, stdlib-only. Signal chain, by explicit spec:

  1. Brown noise bed (two decorrelated mono streams panned L/R for width),
     shaped with an explicit 3kHz low-pass on top of the noise's own
     natural -6dB/octave rolloff.
  2. Random water-drop impulses scattered over the bed at ~3-8 events/sec
     (the rate itself drifts inside that range so the density never locks
     onto one perceivable tempo -- see the note on ``add_water_drop``
     scheduling in ``arrange()``).
  3. A separately rendered temple-bell sample: 220Hz fundamental plus
     inharmonic partials (a real bell is not a harmonic series), 8-second
     decay, run through a small Schroeder reverb so it reads as struck far
     away in open, misty air. Mixed in once every 30-90 seconds at a peak
     level of -20dBFS.

This stays separate from ``generate_n3_game_bgm.py`` so game and review scenes
can be mixed and tuned independently.
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
DURATION_SECONDS = 120.0
OUTPUT_PATH = PROJECT_ROOT / "generated_audio" / "source_audio" / "n3-chugoku-kansai-review-bgm.wav"

random.seed(20260719)


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


def mix_mono_buffer(buffer: list, start: float, pan: float) -> None:
    """Add a pre-rendered mono buffer (e.g. the reverbed bell) into the master mix."""

    start_index = int(start * SAMPLE_RATE)
    for offset, value in enumerate(buffer):
        add_sample(start_index + offset, value, pan)


def add_brown_noise(start: float, duration: float, amplitude: float, *, pan: float = 0.0) -> None:
    """Brown-noise bed with an explicit 3kHz low-pass on top.

    Brown noise itself comes from the classic "Paul Kellet" leaky integrator:
    accumulating (integrating) white noise gives -6dB/octave color, but a raw
    unfiltered integrator is a random walk and drifts off to extreme values,
    so it needs a small leak (the ``/ 1.02`` below) to stay bounded. That
    already makes the noise much deeper/softer than plain white noise, and
    then a second, explicit one-pole low-pass at 3kHz is chained on top of it
    per spec, trimming whatever top end the brown noise still has left.
    """

    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)

    lp_cutoff_hz = 3000.0
    rc = 1.0 / (2 * math.pi * lp_cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    lp_alpha = dt / (rc + dt)

    brown = 0.0
    lp_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        white = random.random() * 2 - 1
        brown = (brown + 0.02 * white) / 1.02
        lp_state += lp_alpha * (brown - lp_state)
        env = envelope(t, duration, 4.0, 5.0, 0.01)
        add_sample(start_index + offset, lp_state * 3.4 * amplitude * env, pan)


def add_water_drop(start: float, amplitude: float, *, pan: float = 0.0) -> None:
    """A single water-drop impulse: filtered-noise transient plus a soft, low
    resonant "plunk" body. No sine "click" is used for the transient itself
    so it doesn't read as an electronic blip; the low body tone is kept quiet
    and is there only because a real droplet impact has a soft low resonance.
    """

    duration = random.uniform(0.05, 0.16)
    start_index = int(start * SAMPLE_RATE)
    frame_count = int(duration * SAMPLE_RATE)
    fast_coeff = random.uniform(0.55, 0.75)
    body_frequency = random.uniform(180.0, 320.0)
    fast_state = 0.0

    for offset in range(frame_count):
        t = offset / SAMPLE_RATE
        raw = random.random() * 2 - 1
        fast_state = fast_state * fast_coeff + raw * (1 - fast_coeff)
        transient_env = math.exp(-40 * t) * (1 - math.exp(-200 * t))
        body_env = math.exp(-16 * t)
        transient = fast_state * transient_env
        body = math.sin(2 * math.pi * body_frequency * t) * body_env
        add_sample(start_index + offset, (transient * 0.7 + body * 0.10) * amplitude, pan)


def apply_reverb(buffer: list, *, decay: float = 0.55, tail_seconds: float = 2.5) -> list:
    """Small Schroeder-style reverb: 4 parallel comb filters feeding 2 series
    all-pass filters. This is what gives the bell its "struck far away in a
    large, misty space" character instead of sounding like a dry synth note
    -- comb filters build up the diffuse decaying tail, and the all-pass
    stages smear it so the tail doesn't have an audible metallic flutter.
    Delay lengths are the classic Schroeder ratios (mutually near-prime so
    the combs don't reinforce each other into an audible pitch).
    """

    tail_samples = int(tail_seconds * SAMPLE_RATE)
    n = len(buffer) + tail_samples
    padded = list(buffer) + [0.0] * tail_samples

    comb_delays_ms = [29.7, 37.1, 41.1, 43.7]
    comb_gains = [0.805, 0.827, 0.783, 0.764]
    wet = [0.0] * n
    for delay_ms, gain in zip(comb_delays_ms, comb_gains):
        delay_samples = max(1, int(delay_ms / 1000 * SAMPLE_RATE))
        line = [0.0] * delay_samples
        idx = 0
        feedback = gain * decay
        for i in range(n):
            delayed = line[idx]
            line[idx] = padded[i] + delayed * feedback
            wet[i] += delayed
            idx = idx + 1
            if idx == delay_samples:
                idx = 0
    for i in range(n):
        wet[i] *= 0.25

    for delay_ms, gain in [(5.0, 0.7), (1.7, 0.7)]:
        delay_samples = max(1, int(delay_ms / 1000 * SAMPLE_RATE))
        line = [0.0] * delay_samples
        idx = 0
        stage_out = [0.0] * n
        for i in range(n):
            delayed = line[idx]
            inp = wet[i]
            stage_out[i] = -gain * inp + delayed
            line[idx] = inp + delayed * gain
            idx = idx + 1
            if idx == delay_samples:
                idx = 0
        wet = stage_out

    # Keep a little of the dry attack under the diffuse tail so the strike
    # itself stays audible instead of the whole note dissolving into wash.
    blended = [0.0] * n
    for i in range(n):
        dry = padded[i] if i < len(buffer) else 0.0
        blended[i] = dry * 0.35 + wet[i] * 0.65
    return blended


def render_bell() -> list:
    """Render one 220Hz-fundamental temple-bell strike with inharmonic
    partials and an 8-second decay, then send it through ``apply_reverb``.
    Real bronze bells are inharmonic (hum/prime/tierce/quint/nominal
    partials, not a clean 1x/2x/3x series) -- using ratios close to that
    classic structure is what keeps this sounding like a bell instead of a
    synthesizer pad.
    """

    duration = 8.0
    frame_count = int(duration * SAMPLE_RATE)
    base = 220.0
    partials = [
        (base * 0.5, 0.55, 0.0),
        (base * 1.0, 1.00, 0.4),
        (base * 1.19, 0.42, 1.1),
        (base * 1.5, 0.30, 1.8),
        (base * 2.0, 0.20, 2.4),
        (base * 2.7, 0.10, 3.0),
        (base * 3.76, 0.05, 3.6),
    ]
    # Chosen so the tone has decayed roughly 60dB by the 8s mark (exp(-0.86*8) ~= 0.0009).
    decay_rate = 0.86

    buffer = [0.0] * frame_count
    strike_noise_state = 0.0
    for i in range(frame_count):
        t = i / SAMPLE_RATE
        strike = 1 - math.exp(-3.2 * t)
        decay = math.exp(-decay_rate * t)
        tone = 0.0
        for frequency, weight, phase in partials:
            tone += weight * math.sin(2 * math.pi * frequency * t + phase)
        raw = random.random() * 2 - 1
        strike_noise_state = strike_noise_state * 0.90 + raw * 0.10
        strike_noise = strike_noise_state * 0.06 * math.exp(-9 * t)
        buffer[i] = tone * 0.14 * strike * decay + strike_noise

    reverbed = apply_reverb(buffer)

    # Normalize this bell event on its own to a -20dBFS peak (0.1 linear) per
    # spec, before it ever touches the shared master mix. The final master
    # normalize/soft-limit in write_wav() scales every layer by one uniform
    # factor, so fixing this ratio here keeps the bell at -20dB *relative to
    # the rest of the mix* no matter how the other layers are leveled.
    peak = max((abs(v) for v in reverbed), default=0.0) or 1e-6
    target_peak = 10 ** (-20 / 20)
    gain = target_peak / peak
    return [v * gain for v in reverbed]


def arrange() -> None:
    add_brown_noise(0.0, DURATION_SECONDS, 0.85, pan=-0.22)
    add_brown_noise(0.0, DURATION_SECONDS, 0.85, pan=0.22)

    # Water drops: rate itself is redrawn between 3 and 8 events/sec for each
    # gap (via an exponential/Poisson inter-arrival time), so the density
    # wanders inside the requested 3-8/sec range instead of settling on one
    # steady rate the ear could lock onto as a hum.
    current = 0.2
    while current < DURATION_SECONDS - 0.2:
        rate = random.uniform(3.0, 8.0)
        current += random.expovariate(rate)
        if current >= DURATION_SECONDS - 0.2:
            break
        add_water_drop(
            current,
            random.uniform(0.05, 0.13),
            pan=random.uniform(-0.7, 0.7),
        )

    # Bell: first strike well clear of the loop start, then every 30-90s,
    # leaving enough room before the loop end for the ~10.5s (8s decay +
    # 2.5s reverb tail) note to finish instead of getting cut off.
    current = random.uniform(8.0, 22.0)
    while current < DURATION_SECONDS - 11.0:
        mix_mono_buffer(render_bell(), current, random.uniform(-0.08, 0.08))
        current += random.uniform(30.0, 90.0)


def soft_limit(value: float) -> float:
    return math.tanh(value * 1.10) / math.tanh(1.10)


def write_wav() -> None:
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.0001)
    normalize = 0.31 / peak

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
    print(f"Wrote {OUTPUT_PATH} ({DURATION_SECONDS:.2f}s, brown noise + water drops + reverbed 220Hz bell)")


if __name__ == "__main__":
    main()
