from __future__ import annotations

import csv
import re
from pathlib import Path

import mido

from src.midi.models import ClassifiedSegment, ExportedSegment, MidiSegment


UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


class MidiSegmentExporter:
    def __init__(
        self,
        output_dir: Path,
        long_note_min_seconds: float,
        ticks_per_beat: int = 480,
        tempo: int = 500000,
    ) -> None:
        self.output_dir = output_dir
        self.long_note_min_seconds = long_note_min_seconds
        self.ticks_per_beat = ticks_per_beat
        self.tempo = tempo

    def export(self, classified_segments: list[ClassifiedSegment]) -> list[ExportedSegment]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        exported_segments: list[ExportedSegment] = []

        for classified_segment in classified_segments:
            for category in classified_segment.categories:
                category_dir = self.output_dir / category
                category_dir.mkdir(parents=True, exist_ok=True)
                output_path = category_dir / f"{safe_filename(classified_segment.segment.segment_id)}.mid"
                self._write_segment(classified_segment.segment, output_path)
                exported_segments.append(
                    ExportedSegment(
                        classified_segment=classified_segment,
                        category=category,
                        output_path=output_path,
                    )
                )

        self._write_manifest(exported_segments)
        return exported_segments

    def _write_segment(self, segment: MidiSegment, output_path: Path) -> None:
        midi_file = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)
        track = mido.MidiTrack()
        midi_file.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=self.tempo, time=0))

        events = []
        for note in segment.notes:
            start_offset = max(note.start, segment.start) - segment.start
            end_offset = min(note.end, segment.end) - segment.start
            if end_offset <= start_offset:
                continue

            events.append(
                (
                    start_offset,
                    1,
                    mido.Message(
                        "note_on",
                        note=note.note,
                        velocity=max(1, note.velocity),
                        channel=note.channel,
                    ),
                )
            )
            events.append(
                (
                    end_offset,
                    0,
                    mido.Message(
                        "note_off",
                        note=note.note,
                        velocity=0,
                        channel=note.channel,
                    ),
                )
            )

        total_ticks = seconds_to_ticks(segment.duration, self.ticks_per_beat, self.tempo)
        last_tick = 0
        for event_seconds, _, message in sorted(events, key=lambda event: (event[0], event[1])):
            event_ticks = seconds_to_ticks(
                event_seconds,
                self.ticks_per_beat,
                self.tempo,
            )
            event_ticks = min(max(event_ticks, 0), total_ticks)
            message.time = max(0, event_ticks - last_tick)
            track.append(message)
            last_tick = event_ticks

        track.append(mido.MetaMessage("end_of_track", time=max(0, total_ticks - last_tick)))
        midi_file.save(output_path)

    def _write_manifest(self, exported_segments: list[ExportedSegment]) -> None:
        manifest_path = self.output_dir / "manifest.csv"
        with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
            writer = csv.DictWriter(
                manifest_file,
                fieldnames=[
                    "category",
                    "output_path",
                    "source_file",
                    "segment_id",
                    "segment_index",
                    "start_seconds",
                    "end_seconds",
                    "note_count",
                    "singular_note_count",
                    "long_note_count",
                    "counter_source_id",
                    "counter_overlap",
                ],
            )
            writer.writeheader()
            for exported_segment in exported_segments:
                classified_segment = exported_segment.classified_segment
                segment = classified_segment.segment
                writer.writerow(
                    {
                        "category": exported_segment.category,
                        "output_path": str(exported_segment.output_path),
                        "source_file": str(segment.source_path),
                        "segment_id": segment.segment_id,
                        "segment_index": segment.index,
                        "start_seconds": f"{segment.start:.3f}",
                        "end_seconds": f"{segment.end:.3f}",
                        "note_count": len(segment.notes),
                        "singular_note_count": len(segment.singular_notes),
                        "long_note_count": sum(
                            1
                            for note in segment.notes
                            if note.duration > self.long_note_min_seconds
                        ),
                        "counter_source_id": classified_segment.counter_source_id or "",
                        "counter_overlap": (
                            f"{classified_segment.counter_overlap:.3f}"
                            if classified_segment.counter_overlap is not None
                            else ""
                        ),
                    }
                )


def seconds_to_ticks(seconds: float, ticks_per_beat: int, tempo: int) -> int:
    return int(round(mido.second2tick(seconds, ticks_per_beat, tempo)))


def safe_filename(name: str) -> str:
    cleaned = UNSAFE_FILENAME_CHARS.sub("_", name).strip()
    return cleaned or "segment"
