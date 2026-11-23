# MPEG-2 Layer III, 24 kHz, 48 kbps. Zeroed audio data decodes as silence.
FRAME = bytes.fromhex("FF F3 64 C4") + bytes(140)
SILENT_MP3 = FRAME * 60
