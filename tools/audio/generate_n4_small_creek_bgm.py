#!/usr/bin/env python3
"""Generate a small-creek white-noise BGM for N4 vocabulary review.

Compared with generate_n4_slow_stream_bgm.py, this preset intentionally avoids
the "waterfall wall" effect:
- less brown-noise body
- more narrow low-mid filtering
- reduced continuous white-noise mist
- quiet, randomized ripple bursts for small-creek texture
"""

from __future__ import annotations

import argparse
import math
import random
import shlex
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "generated_audio" / "n4_vocab_small_creek_bgm_10min.m4a"


@dataclass(frozen=True)
class NoiseLayer:
    label: str
    side: str
    color: str
    source_amplitude: float
    highpass_hz: int
    lowpass_hz: int
    volume: float
    tremolo_hz: float | None = None
    tremolo_depth: float | None = None


@dataclass(frozen=True)
class RippleSettings:
    min_gap_seconds: float = 0.16
    max_gap_seconds: float = 0.85
    min_duration_seconds: float = 0.045
    max_duration_seconds: float = 0.18
    min_frequency_hz: float = 900.0
    max_frequency_hz: float = 3200.0
    max_amplitude: float = 0.010
    output_gain: float = 0.70


@dataclass(frozen=True)
class MasterSettings:
    duration_seconds: float = 600.0
    sample_rate: int = 44_100
    audio_bitrate: str = "128k"
    fade_in_seconds: float = 10.0
    fade_out_seconds: float = 10.0
    compressor_threshold_db: int = -27
    compressor_ratio: float = 1.08
    compressor_attack_ms: int = 140
    compressor_release_ms: int = 1300
    limiter: float = 0.65
    loudness_i_lufs: int = -28
    loudness_lra: int = 6
    true_peak_db: int = -5


STREAM_LAYERS = [
    NoiseLayer(
        label="bl",
        side="left",
        color="brown",
        source_amplitude=0.07,
        highpass_hz=120,
        lowpass_hz=1200,
        tremolo_hz=0.11,
        tremolo_depth=0.08,
        volume=0.38,
    ),
    NoiseLayer(
        label="pl",
        side="left",
        color="pink",
        source_amplitude=0.10,
        highpass_hz=180,
        lowpass_hz=3200,
        tremolo_hz=0.14,
        tremolo_depth=0.07,
        volume=0.34,
    ),
    NoiseLayer(
        label="br",
        side="right",
        color="brown",
        source_amplitude=0.06,
        highpass_hz=130,
        lowpass_hz=1100,
        tremolo_hz=0.12,
        tremolo_depth=0.08,
        volume=0.34,
    ),
    NoiseLayer(
        label="pr",
        side="right",
        color="pink",
        source_amplitude=0.09,
        highpass_hz=200,
        lowpass_hz=3000,
        tremolo_hz=0.15,
        tremolo_depth=0.07,
        volume=0.31,
    ),
    NoiseLayer(
        label="sl",
        side="left",
        color="white",
        source_amplitude=0.006,
        highpass_hz=1150,
        lowpass_hz=5200,
        volume=0.025,
    ),
    NoiseLayer(
        label="sr",
        side="right",
        color="white",
        source_amplitude=0.005,
        highpass_hz=1250,
        lowpass_hz=5000,
        volume=0.022,
    ),
]


def equal_power_pan(value: float) -> tuple[float, float]:
    pan = max(-1.0, min(1.0, value))
    angle = (pan + 1.0) * math.pi / 4
    return math.cos(angle), math.sin(angle)


def build_filter_chain(input_index: int, layer: NoiseLayer) -> str:
    filters = [
        f"[{input_index}:a]highpass=f={layer.highpass_hz}",
        f"lowpass=f={layer.lowpass_hz}",
    ]
    if layer.tremolo_hz is not None and layer.tremolo_depth is not None:
        filters.append(f"tremolo=f={layer.tremolo_hz:.2f}:d={layer.tremolo_depth:.2f}")
    filters.append(f"volume={layer.volume:.3f}[{layer.label}]")
    return ",".join(filters)


def make_ripple_events(duration_seconds: float, sample_rate: int, settings: RippleSettings) -> list[dict[str, float]]:
    events: list[dict[str, float]] = []
    current = random.uniform(0.25, 1.2)
    while current < duration_seconds - 0.2:
        event_duration = random.uniform(settings.min_duration_seconds, settings.max_duration_seconds)
        frequency = random.uniform(settings.min_frequency_hz, settings.max_frequency_hz)
        pan = random.uniform(-0.38, 0.38)
        amplitude = random.uniform(settings.max_amplitude * 0.35, settings.max_amplitude)
        events.append(
            {
                "start": int(current * sample_rate),
                "end": int(min(duration_seconds, current + event_duration) * sample_rate),
                "duration": event_duration,
                "frequency_a": frequency,
                "frequency_b": frequency * random.uniform(1.36, 1.92),
                "phase_a": random.random() * 2 * math.pi,
                "phase_b": random.random() * 2 * math.pi,
                "pan": pan,
                "amplitude": amplitude,
                "hiss_state": 0.0,
            }
        )
        current += random.uniform(settings.min_gap_seconds, settings.max_gap_seconds)
    return events


def write_ripple_wav(path: Path, duration_seconds: float, sample_rate: int, settings: RippleSettings) -> None:
    events = make_ripple_events(duration_seconds, sample_rate, settings)
    event_cursor = 0
    active_events: list[dict[str, float]] = []
    total_samples = int(duration_seconds * sample_rate)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for sample_index in range(total_samples):
            while event_cursor < len(events) and events[event_cursor]["start"] <= sample_index:
                active_events.append(events[event_cursor])
                event_cursor += 1

            left = 0.0
            right = 0.0
            still_active: list[dict[str, float]] = []

            for event in active_events:
                if sample_index >= event["end"]:
                    continue

                position = (sample_index - event["start"]) / sample_rate
                duration = event["duration"]
                attack = min(0.018, duration * 0.35)
                if position < attack:
                    envelope = position / max(attack, 0.0001)
                else:
                    envelope = math.exp(-5.0 * (position - attack) / max(duration - attack, 0.0001))

                raw = random.random() * 2 - 1
                event["hiss_state"] = event["hiss_state"] * 0.35 + raw * 0.65
                tone = (
                    0.24 * math.sin(2 * math.pi * event["frequency_a"] * position + event["phase_a"])
                    + 0.12 * math.sin(2 * math.pi * event["frequency_b"] * position + event["phase_b"])
                    + 0.64 * event["hiss_state"]
                )
                value = tone * event["amplitude"] * envelope
                left_gain, right_gain = equal_power_pan(event["pan"])
                left += value * left_gain
                right += value * right_gain
                still_active.append(event)

            active_events = still_active
            left_i = int(max(-1.0, min(1.0, left * settings.output_gain)) * 32767)
            right_i = int(max(-1.0, min(1.0, right * settings.output_gain)) * 32767)
            wav.writeframesraw(struct.pack("<hh", left_i, right_i))


def build_ffmpeg_command(output: Path, ripple_wav: Path, settings: MasterSettings) -> list[str]:
    command = ["ffmpeg", "-hide_banner", "-y"]

    for layer in STREAM_LAYERS:
        source = (
            f"anoisesrc=color={layer.color}:"
            f"duration={settings.duration_seconds:g}:"
            f"sample_rate={settings.sample_rate}:"
            f"amplitude={layer.source_amplitude:g}"
        )
        command.extend(["-f", "lavfi", "-i", source])

    ripple_input_index = len(STREAM_LAYERS)
    command.extend(["-i", str(ripple_wav)])

    layer_filters = [build_filter_chain(index, layer) for index, layer in enumerate(STREAM_LAYERS)]
    left_labels = "".join(f"[{layer.label}]" for layer in STREAM_LAYERS if layer.side == "left")
    right_labels = "".join(f"[{layer.label}]" for layer in STREAM_LAYERS if layer.side == "right")
    left_count = sum(1 for layer in STREAM_LAYERS if layer.side == "left")
    right_count = sum(1 for layer in STREAM_LAYERS if layer.side == "right")

    fade_out_start = max(0.0, settings.duration_seconds - settings.fade_out_seconds)
    master_filter = (
        f"{left_labels}amix=inputs={left_count}:normalize=0[left];"
        f"{right_labels}amix=inputs={right_count}:normalize=0[right];"
        "[left][right]amerge=inputs=2[base];"
        f"[{ripple_input_index}:a]volume=1.0[ripples];"
        "[base][ripples]amix=inputs=2:normalize=0,"
        f"afade=t=in:st=0:d={settings.fade_in_seconds:g},"
        f"afade=t=out:st={fade_out_start:g}:d={settings.fade_out_seconds:g},"
        f"acompressor=threshold={settings.compressor_threshold_db}dB:"
        f"ratio={settings.compressor_ratio:g}:"
        f"attack={settings.compressor_attack_ms}:"
        f"release={settings.compressor_release_ms},"
        f"alimiter=limit={settings.limiter:g},"
        f"loudnorm=I={settings.loudness_i_lufs}:"
        f"LRA={settings.loudness_lra}:"
        f"TP={settings.true_peak_db},"
        f"aresample={settings.sample_rate}[a]"
    )

    command.extend(
        [
            "-filter_complex",
            ";".join(layer_filters + [master_filter]),
            "-map",
            "[a]",
            "-ar",
            str(settings.sample_rate),
            "-c:a",
            "aac",
            "-b:a",
            settings.audio_bitrate,
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output .m4a path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument("--duration", type=float, default=MasterSettings.duration_seconds)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep-ripple-wav",
        action="store_true",
        help="Keep the temporary ripple WAV next to the output for debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    settings = MasterSettings(duration_seconds=args.duration)
    ripple_settings = RippleSettings()

    if args.keep_ripple_wav:
        ripple_wav = output.with_name(f"{output.stem}_ripples.wav")
        write_ripple_wav(ripple_wav, settings.duration_seconds, settings.sample_rate, ripple_settings)
        command = build_ffmpeg_command(output, ripple_wav, settings)
        if args.dry_run:
            print(" ".join(shlex.quote(part) for part in command))
            return
        subprocess.run(command, check=True)
    else:
        with tempfile.TemporaryDirectory(prefix="n4_small_creek_") as tmpdir:
            ripple_wav = Path(tmpdir) / "ripples.wav"
            write_ripple_wav(ripple_wav, settings.duration_seconds, settings.sample_rate, ripple_settings)
            command = build_ffmpeg_command(output, ripple_wav, settings)
            if args.dry_run:
                print(" ".join(shlex.quote(part) for part in command))
                return
            subprocess.run(command, check=True)

    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
