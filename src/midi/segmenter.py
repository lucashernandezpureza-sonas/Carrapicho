from __future__ import annotations

from src.midi.models import MidiSegment, NoteEvent, ParsedMidi


class FixedWindowSegmenter:
    def __init__(
        self,
        segment_seconds: float,
        hop_seconds: float,
        chord_onset_tolerance_seconds: float,
    ) -> None:
        self.segment_seconds = segment_seconds
        self.hop_seconds = hop_seconds
        self.chord_onset_tolerance_seconds = chord_onset_tolerance_seconds

    def segment(self, parsed_midi: ParsedMidi) -> list[MidiSegment]:
        singular_note_indexes = self._find_singular_note_indexes(parsed_midi.notes)
        segments = []
        start = 0.0
        index = 0

        while start + self.segment_seconds <= parsed_midi.duration_seconds + 1e-9:
            end = start + self.segment_seconds
            note_indexes = [
                note_index
                for note_index, note in enumerate(parsed_midi.notes)
                if note.overlaps(start, end)
            ]
            notes = tuple(parsed_midi.notes[note_index] for note_index in note_indexes)
            singular_notes = tuple(
                parsed_midi.notes[note_index]
                for note_index in note_indexes
                if note_index in singular_note_indexes
                and start <= parsed_midi.notes[note_index].start < end
            )

            segments.append(
                MidiSegment(
                    source_path=parsed_midi.source_path,
                    index=index,
                    start=start,
                    end=end,
                    notes=notes,
                    singular_notes=singular_notes,
                )
            )

            start += self.hop_seconds
            index += 1

        return segments

    def _find_singular_note_indexes(self, notes: tuple[NoteEvent, ...]) -> set[int]:
        indexed_notes = sorted(
            enumerate(notes),
            key=lambda item: (item[1].start, item[1].note, item[1].channel),
        )
        singular_note_indexes: set[int] = set()
        onset_cluster: list[int] = []
        previous_start: float | None = None

        for note_index, note in indexed_notes:
            if (
                previous_start is None
                or note.start - previous_start <= self.chord_onset_tolerance_seconds
            ):
                onset_cluster.append(note_index)
            else:
                if len(onset_cluster) == 1:
                    singular_note_indexes.add(onset_cluster[0])
                onset_cluster = [note_index]

            previous_start = note.start

        if len(onset_cluster) == 1:
            singular_note_indexes.add(onset_cluster[0])

        return singular_note_indexes
