import asyncio
import subprocess

import imageio_ffmpeg

from .mp3 import inspect_mp3


async def restore_tempo(audio: bytes, factor: float) -> bytes:
    """Restore the requested tempo while keeping the Edge MP3 format for joining."""
    source = inspect_mp3(audio)
    if source is None:
        raise ValueError("Invalid MP3 input for tempo recovery")

    executable = await asyncio.to_thread(imageio_ffmpeg.get_ffmpeg_exe)
    process = await asyncio.create_subprocess_exec(
        executable, "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror",
        "-f", "mp3", "-i", "pipe:0", "-af", f"atempo={factor:.4f}",
        "-c:a", "libmp3lame", "-ar", "24000", "-ac", "1", "-b:a", "48k",
        "-write_xing", "0", "-id3v2_version", "0", "-f", "mp3", "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        output, stderr = await process.communicate(audio)
    except asyncio.CancelledError:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()
        raise

    if process.returncode:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg tempo recovery failed ({process.returncode}): {detail[:500]}")

    result = inspect_mp3(output)
    duration = source.seconds / factor
    if result is None or not result.standalone or result.profile != source.profile:
        raise RuntimeError("FFmpeg tempo recovery returned an invalid or incompatible MP3")
    if abs(result.seconds - duration) > max(0.15, duration * 0.05):
        raise RuntimeError("FFmpeg tempo recovery returned an incomplete or mistimed MP3")
    return output
