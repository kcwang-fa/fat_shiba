#!/usr/bin/env python3
"""Generate a slow stream white-noise BGM for N4 vocabulary review.

This script is a parameterized version of the ffmpeg command used to create:
generated_audio/n4_vocab_slow_stream_bgm_10min.m4a

It intentionally keeps the stream slow and unobtrusive:
- stronger brown/pink noise for low-mid stream body
- reduced white-noise layer for less bright "splash"
- slow tremolo for gentle water movement
- conservative loudness so vocabulary audio can sit on top
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "generated_audio" / "n4_vocab_slow_stream_bgm_10min.m4a"


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
class MasterSettings:
    duration_seconds: float = 600.0
    sample_rate: int = 44_100
    audio_bitrate: str = "128k"
    fade_in_seconds: float = 10.0
    fade_out_seconds: float = 10.0
    compressor_threshold_db: int = -25
    compressor_ratio: float = 1.25
    compressor_attack_ms: int = 120
    compressor_release_ms: int = 1200
    limiter: float = 0.74
    loudness_i_lufs: int = -25
    loudness_lra: int = 3
    true_peak_db: int = -4


# Main sound-design knobs. Lower lowpass_hz / white volume = slower, softer water.
STREAM_LAYERS = [
    NoiseLayer(
        label="bl",
        side="left",
        color="brown",
        source_amplitude=0.15,
        highpass_hz=45,
        lowpass_hz=1800,
        tremolo_hz=0.10,
        tremolo_depth=0.13,
        volume=0.74,
    ),
    NoiseLayer(
        label="pl",
        side="left",
        color="pink",
        source_amplitude=0.12,
        highpass_hz=120,
        lowpass_hz=4200,
        tremolo_hz=0.13,
        tremolo_depth=0.08,
        volume=0.42,
    ),
    NoiseLayer(
        label="br",
        side="right",
        color="brown",
        source_amplitude=0.13,
        highpass_hz=55,
        lowpass_hz=1700,
        tremolo_hz=0.11,
        tremolo_depth=0.12,
        volume=0.70,
    ),
    NoiseLayer(
        label="pr",
        side="right",
        color="pink",
        source_amplitude=0.10,
        highpass_hz=140,
        lowpass_hz=3900,
        tremolo_hz=0.12,
        tremolo_depth=0.08,
        volume=0.38,
    ),
    NoiseLayer(
        label="sl",
        side="left",
        color="white",
        source_amplitude=0.012,
        highpass_hz=950,
        lowpass_hz=7600,
        volume=0.07,
    ),
    NoiseLayer(
        label="sr",
        side="right",
        color="white",
        source_amplitude=0.010,
        highpass_hz=1050,
        lowpass_hz=7200,
        volume=0.06,
    ),
]


def build_filter_chain(input_index: int, layer: NoiseLayer) -> str:
    filters = [
        f"[{input_index}:a]highpass=f={layer.highpass_hz}",
        f"lowpass=f={layer.lowpass_hz}",
    ]
    if layer.tremolo_hz is not None and layer.tremolo_depth is not None:
        filters.append(f"tremolo=f={layer.tremolo_hz:.2f}:d={layer.tremolo_depth:.2f}")
    filters.append(f"volume={layer.volume:.2f}[{layer.label}]")
    return ",".join(filters)


def build_ffmpeg_command(output: Path, settings: MasterSettings) -> list[str]:
    command = ["ffmpeg", "-hide_banner", "-y"]

    for layer in STREAM_LAYERS:
        source = (
            f"anoisesrc=color={layer.color}:"
            f"duration={settings.duration_seconds:g}:"
            f"sample_rate={settings.sample_rate}:"
            f"amplitude={layer.source_amplitude:g}"
        )
        command.extend(["-f", "lavfi", "-i", source])

    layer_filters = [build_filter_chain(index, layer) for index, layer in enumerate(STREAM_LAYERS)]
    left_labels = "".join(f"[{layer.label}]" for layer in STREAM_LAYERS if layer.side == "left")
    right_labels = "".join(f"[{layer.label}]" for layer in STREAM_LAYERS if layer.side == "right")
    left_count = sum(1 for layer in STREAM_LAYERS if layer.side == "left")
    right_count = sum(1 for layer in STREAM_LAYERS if layer.side == "right")

    fade_out_start = max(0.0, settings.duration_seconds - settings.fade_out_seconds)
    master_filter = (
        f"{left_labels}amix=inputs={left_count}:normalize=0[left];"
        f"{right_labels}amix=inputs={right_count}:normalize=0[right];"
        "[left][right]amerge=inputs=2,"
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
    parser.add_argument(
        "--duration",
        type=float,
        default=MasterSettings.duration_seconds,
        help="Duration in seconds. Default: 600",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg command without generating audio.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    settings = MasterSettings(duration_seconds=args.duration)
    command = build_ffmpeg_command(output, settings)

    if args.dry_run:
        print(" ".join(shlex.quote(part) for part in command))
        return

    subprocess.run(command, check=True)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
