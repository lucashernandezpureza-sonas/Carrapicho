from __future__ import annotations

from collections import Counter

from src.midi.models import ClassifiedSegment, MidiSegment


LONG_NOTES_CATEGORY = "long_notes"
DENSE_PHRASES_CATEGORY = "dense_phrases"
COUNTER_PHRASES_CATEGORY = "counter_phrases"


class SegmentClassifier:
    def __init__(
        self,
        long_note_min_seconds: float,
        dense_phrase_min_singular_notes: int,
        counter_phrase_min_overlap: float,
    ) -> None:
        self.long_note_min_seconds = long_note_min_seconds
        self.dense_phrase_min_singular_notes = dense_phrase_min_singular_notes
        self.counter_phrase_min_overlap = counter_phrase_min_overlap

    def classify(self, segments: list[MidiSegment]) -> list[ClassifiedSegment]:
        dense_segments = [
            segment
            for segment in segments
            if self._is_dense_phrase(segment)
        ]
        dense_pitch_counters = {
            segment.segment_id: self._pitch_counter(segment)
            for segment in dense_segments
        }

        classified_segments = []
        for segment in segments:
            categories = []
            counter_source_id = None
            counter_overlap = None

            if self._has_long_note(segment):
                categories.append(LONG_NOTES_CATEGORY)

            if self._is_dense_phrase(segment):
                categories.append(DENSE_PHRASES_CATEGORY)

            best_counter_source_id, best_counter_overlap = self._best_counter_match(
                segment,
                dense_pitch_counters,
            )
            if (
                best_counter_source_id is not None
                and best_counter_overlap is not None
                and best_counter_overlap >= self.counter_phrase_min_overlap
            ):
                categories.append(COUNTER_PHRASES_CATEGORY)
                counter_source_id = best_counter_source_id
                counter_overlap = best_counter_overlap

            if categories:
                classified_segments.append(
                    ClassifiedSegment(
                        segment=segment,
                        categories=tuple(categories),
                        counter_source_id=counter_source_id,
                        counter_overlap=counter_overlap,
                    )
                )

        return classified_segments

    def _has_long_note(self, segment: MidiSegment) -> bool:
        return any(
            note.duration > self.long_note_min_seconds
            for note in segment.notes
        )

    def _is_dense_phrase(self, segment: MidiSegment) -> bool:
        return (
            len(segment.singular_notes)
            > self.dense_phrase_min_singular_notes
        )

    def _best_counter_match(
        self,
        segment: MidiSegment,
        dense_pitch_counters: dict[str, Counter[int]],
    ) -> tuple[str | None, float | None]:
        segment_counter = self._pitch_counter(segment)
        if not segment_counter:
            return None, None

        best_source_id = None
        best_overlap = 0.0

        for dense_segment_id, dense_counter in dense_pitch_counters.items():
            if dense_segment_id == segment.segment_id:
                continue

            dense_note_count = sum(dense_counter.values())
            if dense_note_count == 0:
                continue

            shared_note_count = sum((segment_counter & dense_counter).values())
            overlap = shared_note_count / dense_note_count
            if overlap > best_overlap:
                best_source_id = dense_segment_id
                best_overlap = overlap

        return best_source_id, best_overlap

    def _pitch_counter(self, segment: MidiSegment) -> Counter[int]:
        return Counter(note.note for note in segment.singular_notes)
