#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze a fireplace ambience audio file and export summary artifacts.

This script intentionally keeps the analysis parameters near the top so they
can be adjusted without digging through the signal-processing code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np


CONFIG = {
    "input_path": Path(
        "/Users/kcwang/Downloads/"
        "asmr-flame!！fire！3-Minute Fireplace Sound for Sleep［三分鐘火爐音效幫助睡眠］_128k.mp3"
    ),
    "output_dir": Path("/Users/kcwang/workspace/dev/fat_shiba/audio_analysis"),
    "output_prefix": "fireplace",
    "sample_rate": 44_100,
    "channels": 2,
    "waveform_size": "1600x360",
    "spectrogram_size": "1600x720",
    "silence_noise_db": -50,
    "silence_min_duration_sec": 0.5,
    "transient_crest_db": 28,
    "transient_peak_dbfs": -18,
    "fft_size": 4096,
    "hop_size": 2048,
    "frequency_bands_hz": [
        (0, 100),
        (100, 500),
        (500, 2_000),
        (2_000, 8_000),
        (8_000, 22_050),
    ],
}


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def probe_audio(input_path: Path) -> dict:
    result = run_command(
        [
            "ffprobe",
            "-hide_banner",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        ]
    )
    return json.loads(result.stdout)


def detect_silence(input_path: Path, noise_db: int, min_duration_sec: float) -> list[dict]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(input_path),
            "-af",
            f"silencedetect=noise={noise_db}dB:d={min_duration_sec}",
            "-f",
            "null",
            "-",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    events: list[dict] = []
    current_start: float | None = None
    for line in result.stderr.splitlines():
        start_match = re.search(r"silence_start: ([0-9.]+)", line)
        end_match = re.search(r"silence_end: ([0-9.]+) \\| silence_duration: ([0-9.]+)", line)
        if start_match:
            current_start = float(start_match.group(1))
        elif end_match:
            events.append(
                {
                    "start_sec": current_start,
                    "end_sec": float(end_match.group(1)),
                    "duration_sec": float(end_match.group(2)),
                }
            )
            current_start = None
    return events


def export_waveform(input_path: Path, output_path: Path, size: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(input_path),
            "-filter_complex",
            f"aformat=channel_layouts=mono,showwavespic=s={size}:colors=2f6f9f",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def export_spectrogram(input_path: Path, output_path: Path, size: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(input_path),
            "-lavfi",
            f"showspectrumpic=s={size}:legend=1:scale=log:color=viridis",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def decode_audio(input_path: Path, sample_rate: int, channels: int) -> np.ndarray:
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(input_path),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return np.frombuffer(result.stdout, dtype=np.float32).reshape(-1, channels)


def dbfs(values: np.ndarray | float) -> np.ndarray | float:
    return 20 * np.log10(np.maximum(values, 1e-12))


def analyze_signal(audio: np.ndarray, config: dict) -> dict:
    sample_rate = int(config["sample_rate"])
    mono = audio.mean(axis=1)
    duration_sec = len(mono) / sample_rate

    channel_rms = np.sqrt(np.mean(audio * audio, axis=0))
    channel_peak = np.max(np.abs(audio), axis=0)
    stereo_corr = float(np.corrcoef(audio[:, 0], audio[:, 1])[0, 1])

    full_seconds = len(mono) // sample_rate
    one_sec_frames = mono[: full_seconds * sample_rate].reshape(full_seconds, sample_rate)
    one_sec_rms = np.sqrt(np.mean(one_sec_frames * one_sec_frames, axis=1))
    one_sec_peak = np.max(np.abs(one_sec_frames), axis=1)
    one_sec_rms_db = dbfs(one_sec_rms)
    one_sec_peak_db = dbfs(one_sec_peak)
    crest_db = one_sec_peak_db - one_sec_rms_db

    loudest_idx = np.argsort(one_sec_rms_db)[-8:][::-1]
    highest_peak_idx = np.argsort(one_sec_peak_db)[-8:][::-1]
    quietest_idx = np.argsort(one_sec_rms_db)[:8]

    fft_size = int(config["fft_size"])
    hop_size = int(config["hop_size"])
    window = np.hanning(fft_size).astype(np.float32)
    freqs = np.fft.rfftfreq(fft_size, 1 / sample_rate)
    band_masks = [
        (freqs >= low_hz) & (freqs < high_hz)
        for low_hz, high_hz in config["frequency_bands_hz"]
    ]

    band_energy = np.zeros(len(band_masks))
    centroid_numerator = 0.0
    centroid_denominator = 0.0
    frame_count = (len(mono) - fft_size) // hop_size + 1
    for frame_index in range(frame_count):
        start = frame_index * hop_size
        frame = mono[start : start + fft_size] * window
        power = np.abs(np.fft.rfft(frame)) ** 2
        power_sum = power.sum() + 1e-20
        centroid_numerator += float((freqs * power).sum())
        centroid_denominator += float(power_sum)
        for band_index, mask in enumerate(band_masks):
            band_energy[band_index] += float(power[mask].sum())

    transient_idx = np.where(
        (crest_db > float(config["transient_crest_db"]))
        & (one_sec_peak_db > float(config["transient_peak_dbfs"]))
    )[0]

    return {
        "duration_sec": round(float(duration_sec), 3),
        "samples": int(len(mono)),
        "rms_dbfs_left_right": [round(float(value), 2) for value in dbfs(channel_rms)],
        "peak_dbfs_left_right": [round(float(value), 2) for value in dbfs(channel_peak)],
        "stereo_corr": round(stereo_corr, 4),
        "rms_1s_dbfs_mean": round(float(np.mean(one_sec_rms_db)), 2),
        "rms_1s_dbfs_median": round(float(np.median(one_sec_rms_db)), 2),
        "rms_1s_dbfs_min_max": [
            round(float(np.min(one_sec_rms_db)), 2),
            round(float(np.max(one_sec_rms_db)), 2),
        ],
        "peak_1s_dbfs_max": round(float(np.max(one_sec_peak_db)), 2),
        "crest_1s_db_mean_median_max": [
            round(float(np.mean(crest_db)), 2),
            round(float(np.median(crest_db)), 2),
            round(float(np.max(crest_db)), 2),
        ],
        "loudest_rms_seconds": seconds_table(loudest_idx, one_sec_rms_db, one_sec_peak_db),
        "highest_peak_seconds": seconds_table(highest_peak_idx, one_sec_rms_db, one_sec_peak_db),
        "quietest_seconds": seconds_table(quietest_idx, one_sec_rms_db, one_sec_peak_db),
        "spectral_centroid_hz": round(float(centroid_numerator / centroid_denominator), 1),
        "band_energy_pct": band_energy_table(config["frequency_bands_hz"], band_energy),
        "transient_candidate_seconds_count": int(len(transient_idx)),
        "transient_candidate_seconds": [int(value) for value in transient_idx],
        "first5s_avg_rms_dbfs": round(float(np.mean(one_sec_rms_db[:5])), 2),
        "last5s_avg_rms_dbfs": round(float(np.mean(one_sec_rms_db[-5:])), 2),
    }


def seconds_table(indices: np.ndarray, rms_db: np.ndarray, peak_db: np.ndarray) -> list[dict]:
    return [
        {
            "second": int(index),
            "rms_dbfs": round(float(rms_db[index]), 2),
            "peak_dbfs": round(float(peak_db[index]), 2),
        }
        for index in indices
    ]


def band_energy_table(bands: list[tuple[int, int]], energy: np.ndarray) -> list[dict]:
    percentages = energy / energy.sum() * 100
    return [
        {
            "range_hz": f"{low_hz}-{high_hz}",
            "pct": round(float(percent), 2),
        }
        for (low_hz, high_hz), percent in zip(bands, percentages)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CONFIG["input_path"])
    parser.add_argument("--output-dir", type=Path, default=CONFIG["output_dir"])
    parser.add_argument("--prefix", default=CONFIG["output_prefix"])
    parser.add_argument("--skip-images", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    waveform_path = args.output_dir / f"{args.prefix}_waveform.png"
    spectrogram_path = args.output_dir / f"{args.prefix}_spectrogram.png"
    report_path = args.output_dir / f"{args.prefix}_analysis_report.json"

    config = dict(CONFIG)
    config["input_path"] = args.input
    config["output_dir"] = args.output_dir
    config["output_prefix"] = args.prefix

    if not args.skip_images:
        export_waveform(args.input, waveform_path, str(config["waveform_size"]))
        export_spectrogram(args.input, spectrogram_path, str(config["spectrogram_size"]))

    audio = decode_audio(args.input, int(config["sample_rate"]), int(config["channels"]))
    report = {
        "config": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in config.items()
        },
        "probe": probe_audio(args.input),
        "silence_events": detect_silence(
            args.input,
            int(config["silence_noise_db"]),
            float(config["silence_min_duration_sec"]),
        ),
        "signal": analyze_signal(audio, config),
        "artifacts": {
            "waveform_png": str(waveform_path),
            "spectrogram_png": str(spectrogram_path),
            "report_json": str(report_path),
        },
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["signal"], ensure_ascii=False, indent=2))
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
