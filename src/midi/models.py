from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NoteEvent:
    source_path: Path
    note: int
    velocity: int
    channel: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def overlaps(self, start: float, end: float) -> bool:
        return self.start < end and self.end > start


NoteKey = tuple[int, int]


@dataclass(frozen=True)
class ActiveNote:
    start_seconds: float
    velocity: int

    def to_note_event(
        self,
        source_path: Path,
        channel: int,
        note: int,
        end_seconds: float,
    ) -> NoteEvent:
        return NoteEvent(
            source_path=source_path,
            note=note,
            velocity=self.velocity,
            channel=channel,
            start=self.start_seconds,
            end=end_seconds,
        )


@dataclass(frozen=True)
class ParsedMidi:
    source_path: Path
    notes: tuple[NoteEvent, ...]
    duration_seconds: float


@dataclass(frozen=True)
class MidiSegment:
    source_path: Path
    index: int
    start: float
    end: float
    notes: tuple[NoteEvent, ...]
    singular_notes: tuple[NoteEvent, ...]

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def segment_id(self) -> str:
        start_ms = int(round(self.start * 1000))
        end_ms = int(round(self.end * 1000))
        return f"{self.source_path.stem}__{self.index:04d}_{start_ms:08d}-{end_ms:08d}"


@dataclass(frozen=True)
class ClassifiedSegment:
    segment: MidiSegment
    categories: tuple[str, ...]
    counter_source_id: str | None = None
    counter_overlap: float | None = None


@dataclass(frozen=True)
class ExportedSegment:
    classified_segment: ClassifiedSegment
    category: str
    output_path: Path
