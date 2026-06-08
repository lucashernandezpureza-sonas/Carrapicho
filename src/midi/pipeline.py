from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from src.midi.classifiers import SegmentClassifier
from src.midi.exporter import MidiSegmentExporter
from src.midi.models import ClassifiedSegment, ExportedSegment
from src.midi.parser import MidiParser
from src.midi.segmenter import FixedWindowSegmenter
from src.processing_config import ProcessingConfig


class MidiProcessingPipeline:
    """
    Pipeline for parsing MIDI files, segmenting them, classifying the segments,
    and exporting the selected segments.

    Parameters
    ----------
    config : ProcessingConfig
        Configuration for the processing pipeline.
    """

    def __init__(self, config: ProcessingConfig) -> None:
        self.config = config

    def process(self, midi_paths: list[Path], output_dir: Path) -> list[ExportedSegment]:
        """
        Parse, segment, classify, and export MIDI segments.

        Parameters
        ----------
        midi_paths : list[Path]
            MIDI files to process.
        output_dir : Path
            Directory where exported segments will be saved.

        Returns
        -------
        list[ExportedSegment]
            Exported MIDI segments.
        """
        # Step 1: Create the objects responsible for each stage of the pipeline.
        parser = MidiParser()

        segmenter = FixedWindowSegmenter(
            segment_seconds=self.config.segment_seconds,
            hop_seconds=self.config.hop_seconds,
            chord_onset_tolerance_seconds=self.config.chord_onset_tolerance_seconds,
        )

        classifier = SegmentClassifier(
            long_note_min_seconds=self.config.long_note_min_seconds,
            dense_phrase_min_singular_notes=self.config.dense_phrase_min_singular_notes,
            counter_phrase_min_overlap=self.config.counter_phrase_min_overlap,
        )

        exporter = MidiSegmentExporter(
            output_dir=output_dir,
            long_note_min_seconds=self.config.long_note_min_seconds,
        )

        # Step 2: Create a container to store all classified segments.
        classified_segments: list[ClassifiedSegment] = []

        # Step 3: Process each MIDI file independently.
        for midi_path in midi_paths:
            # Step 3.1: Read and parse the MIDI file.
            parsed_midi = parser.parse(midi_path)

            # Step 3.2: Split the parsed MIDI into fixed-window segments.
            segments = segmenter.segment(parsed_midi)

            # Step 3.3: Classify each segment according to musical patterns.
            file_classified_segments = classifier.classify(segments)

            # Step 3.4: Add the classified segments from this file to the global list.
            classified_segments.extend(file_classified_segments)

        # Step 4: Export all classified segments to the output directory.
        exported_segments = exporter.export(classified_segments)

        # Step 5: Return metadata about the exported segments.
        return exported_segments


def discover_midi_files(input_dir: Path, midi_extensions: Collection[str]) -> list[Path]:
    normalized_extensions = {extension.lower() for extension in midi_extensions}
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in normalized_extensions
    )
