from __future__ import annotations

from collections import Counter

from src.midi.pipeline import MidiProcessingPipeline, discover_midi_files
from src.processing_config import ProcessingConfig


def main() -> None:
    config = ProcessingConfig.from_json()
    midi_paths = discover_midi_files(config.input_dir, config.midi_extensions)
    if not midi_paths:
        raise SystemExit(f"No MIDI files found in {config.input_dir}")

    pipeline = MidiProcessingPipeline(config)
    exported_segments = pipeline.process(
        midi_paths=midi_paths,
        output_dir=config.output_dir,
    )

    category_counts = Counter(export.category for export in exported_segments)
    print(f"Processed {len(midi_paths)} MIDI file(s).")
    print(f"Exported {len(exported_segments)} classified segment file(s).")
    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")
    print(f"Manifest: {config.output_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
