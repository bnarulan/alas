from dataclasses import dataclass

SAMPLE_RATES = {0: (11025, 12000, 8000), 2: (22050, 24000, 16000), 3: (44100, 48000, 32000)}
MPEG1_BITRATES = (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
MPEG2_BITRATES = (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)


@dataclass(frozen=True)
class Mp3Info:
    start: int
    end: int
    frames: int
    profile: tuple[int, int, int, int]
    standalone: bool

    @property
    def seconds(self) -> float:
        version, sample_rate, _, _ = self.profile
        return self.frames * (1152 if version == 3 else 576) / sample_rate


def inspect_mp3(audio: bytes) -> Mp3Info | None:
    """Inspect a constant-bitrate MP3 and find the range occupied by MPEG frames."""
    start = 0
    if audio.startswith(b"ID3"):
        if len(audio) < 10 or any(byte & 0x80 for byte in audio[6:10]):
            return None
        start = 10 + sum(byte << (7 * (3 - i)) for i, byte in enumerate(audio[6:10]))
        if audio[3] == 4 and audio[5] & 0x10:
            start += 10

    end = len(audio) - 128 if len(audio) > 128 and audio[-128:-125] == b"TAG" else len(audio)
    offset = start
    frames = 0
    profile = None
    standalone = False
    while offset + 4 <= end:
        header = int.from_bytes(audio[offset:offset + 4], "big")
        version, layer = (header >> 19) & 3, (header >> 17) & 3
        bitrate_index, sample_index = (header >> 12) & 15, (header >> 10) & 3
        if header >> 21 != 0x7FF or version == 1 or layer != 1 or bitrate_index in (0, 15) or sample_index == 3:
            return None
        if version == 3:
            bitrate = MPEG1_BITRATES[bitrate_index - 1]
        else:
            bitrate = MPEG2_BITRATES[bitrate_index - 1]
        sample_rate = SAMPLE_RATES[version][sample_index]
        channel_mode = (header >> 6) & 3
        frame_profile = (version, sample_rate, bitrate, channel_mode)
        frame_size = (144000 if version == 3 else 72000) * bitrate // sample_rate + ((header >> 9) & 1)
        next_offset = offset + frame_size
        if next_offset > end:
            return None

        if profile is None:
            profile = frame_profile
            # At a join the first frame must decode without the previous clip's bit reservoir.
            side_info = offset + (4 if header & (1 << 16) else 6)
            mono = channel_mode == 3
            side_size = (17 if mono else 32) if version == 3 else (9 if mono else 17)
            seek_header = audio[side_info + side_size:side_info + side_size + 4]
            first_bytes = audio[side_info:side_info + 2]
            reservoir = (int.from_bytes(first_bytes, "big") >> 7) if version == 3 else first_bytes[0]
            standalone = reservoir == 0 and seek_header not in (b"Info", b"Xing") and audio[offset + 36:offset + 40] != b"VBRI"
        elif profile != frame_profile:
            return None

        offset = next_offset
        frames += 1

    if profile is None or offset != end:
        return None
    return Mp3Info(start, end, frames, profile, standalone)
