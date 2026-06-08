from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


@dataclass(frozen=True)
class ProcessingConfig:
    input_dir: Path
    output_dir: Path
    midi_extensions: tuple[str, ...]
    segment_seconds: float
    hop_seconds: float
    long_note_min_seconds: float
    dense_phrase_min_singular_notes: int
    counter_phrase_min_overlap: float
    chord_onset_tolerance_seconds: float

    @classmethod
    def from_json(cls, config_path: Path = DEFAULT_CONFIG_PATH) -> "ProcessingConfig":
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))

        return cls(
            input_dir=Path(raw_config["input_dir"]),
            output_dir=Path(raw_config["output_dir"]),
            midi_extensions=raw_config["midi_extensions"],
            segment_seconds=positive_float(
                raw_config["segment_seconds"],
                "segment_seconds"
            ),
            hop_seconds=positive_float(
                raw_config["hop_seconds"],
                "hop_seconds"
            ),
            long_note_min_seconds=positive_float(
                raw_config["long_note_min_seconds"],
                "long_note_min_seconds",
            ),
            dense_phrase_min_singular_notes=positive_int(
                raw_config["dense_phrase_min_singular_notes"],
                "dense_phrase_min_singular_notes",
            ),
            counter_phrase_min_overlap=ratio(
                raw_config["counter_phrase_min_overlap"],
                "counter_phrase_min_overlap",
            ),
            chord_onset_tolerance_seconds=positive_float(
                raw_config["chord_onset_tolerance_seconds"],
                "chord_onset_tolerance_seconds",
                allow_zero=True,
            ),
        )

def positive_float(value: Any, name: str, allow_zero: bool = False) -> float:
    parsed = float(value)
    if allow_zero and parsed < 0:
        raise ValueError(f"{name} must be greater than or equal to 0.")
    if not allow_zero and parsed <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return parsed


def positive_int(value: Any, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return parsed


def ratio(value: Any, name: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 1:
        raise ValueError(f"{name} must be between 0 and 1.")
    return parsed
