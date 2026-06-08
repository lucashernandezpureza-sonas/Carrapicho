from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import mido

from src.midi.models import ActiveNote, NoteEvent, NoteKey, ParsedMidi


class MidiParser:
    def parse(self, midi_path: Path) -> ParsedMidi:
        midi_file = mido.MidiFile(midi_path)
        merged_track = mido.merge_tracks(midi_file.tracks)

        tempo = 500000
        current_seconds = 0.0
        active_notes: dict[NoteKey, list[ActiveNote]] = defaultdict(list)
        parsed_notes: list[NoteEvent] = []

        for message in merged_track:
            current_seconds += mido.tick2second(
                message.time,
                midi_file.ticks_per_beat,
                tempo,
            )

            if message.type == "set_tempo":
                tempo = message.tempo
                continue

            if message.type == "note_on" and message.velocity > 0:
                key = (message.channel, message.note)
                active_notes[key].append(
                    ActiveNote(
                        start_seconds=current_seconds,
                        velocity=message.velocity,
                    )
                )
                continue

            if message.type == "note_off" or (
                message.type == "note_on" and message.velocity == 0
            ):
                key = (message.channel, message.note)
                if not active_notes[key]:
                    continue

                active_note = active_notes[key].pop(0)
                parsed_notes.append(
                    active_note.to_note_event(
                        source_path=midi_path,
                        channel=message.channel,
                        note=message.note,
                        end_seconds=current_seconds,
                    )
                )

        for (channel, note), pending_notes in active_notes.items():
            for active_note in pending_notes:
                parsed_notes.append(
                    active_note.to_note_event(
                        source_path=midi_path,
                        channel=channel,
                        note=note,
                        end_seconds=current_seconds,
                    )
                )

        parsed_notes.sort(key=lambda note: (note.start, note.end, note.note))
        duration_seconds = max(
            current_seconds,
            max((note.end for note in parsed_notes), default=0.0),
        )

        return ParsedMidi(
            source_path=midi_path,
            notes=tuple(parsed_notes),
            duration_seconds=duration_seconds,
        )
