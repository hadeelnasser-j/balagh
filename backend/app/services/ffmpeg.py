"""FFmpeg / FFprobe wrapper: probing, audio extraction, cutting and final rendering."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    pass


@dataclass
class DubClip:
    """A synthesized clip placed on the timeline."""
    path: Path
    start: float
    window: float      # seconds available before the next segment / video end
    tempo: float = 1.0
    segment_end: float | None = None   # original speech end; ducked even if the clip is shorter


class FFmpegService:
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe", sample_rate: int = 16000,
                 audio_bitrate: str = "192k") -> None:
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path
        self.sample_rate = sample_rate
        self.audio_bitrate = audio_bitrate

    # ------------------------------------------------------------------ status
    def _tool_available(self, binary: str) -> bool:
        if not shutil.which(binary):
            return False
        try:
            subprocess.run([binary, "-version"], capture_output=True, timeout=10, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def ffmpeg_available(self) -> bool:
        return self._tool_available(self.ffmpeg)

    def ffprobe_available(self) -> bool:
        return self._tool_available(self.ffprobe)

    def _run(self, args: list[str], timeout: float = 1800) -> subprocess.CompletedProcess[str]:
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args]
        logger.debug("ffmpeg %s", " ".join(args))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise FFmpegError("انتهت مهلة معالجة FFmpeg.") from exc
        except OSError as exc:
            raise FFmpegError("FFmpeg غير متاح على الخادم.") from exc
        if proc.returncode != 0:
            raise FFmpegError(f"FFmpeg failed: {proc.stderr.strip()[-800:]}")
        return proc

    # ------------------------------------------------------------------ probing
    def probe(self, path: Path) -> dict:
        try:
            proc = subprocess.run(
                [self.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                capture_output=True, text=True, timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise FFmpegError("FFprobe غير متاح على الخادم.") from exc
        if proc.returncode != 0:
            raise FFmpegError("الملف المرفوع ليس فيديو صالحًا أو أنه تالف.")
        return json.loads(proc.stdout or "{}")

    def probe_duration(self, path: Path) -> float | None:
        try:
            info = self.probe(path)
        except FFmpegError:
            return None
        value = info.get("format", {}).get("duration")
        return round(float(value), 3) if value else None

    def has_stream(self, path: Path, kind: str) -> bool:
        return any(s.get("codec_type") == kind for s in self.probe(path).get("streams", []))

    # ------------------------------------------------------------------ audio
    def extract_audio(self, video: Path, wav_out: Path, mp3_out: Path) -> None:
        """16 kHz mono WAV (processing) + compact MP3 (provider upload, < 25 MB)."""
        wav_out.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-i", str(video), "-vn", "-ac", "1", "-ar", str(self.sample_rate), "-c:a", "pcm_s16le",
                   str(wav_out)])
        self._run(["-i", str(wav_out), "-ac", "1", "-ar", str(self.sample_rate), "-c:a", "libmp3lame",
                   "-b:a", "48k", str(mp3_out)])

    def cut_audio(self, source: Path, out: Path, start: float, end: float) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.1, end - start)
        codec = ["-c:a", "libmp3lame", "-b:a", "64k"] if out.suffix == ".mp3" else ["-c:a", "pcm_s16le"]
        self._run(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source), "-ac", "1", *codec, str(out)])

    def generate_tone(self, out: Path, seconds: float, frequency: int = 440) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=24000:duration={seconds:.3f}",
                   "-ac", "1", str(out)])

    # ------------------------------------------------------------------ render
    def render_dubbed(self, video: Path, clips: list[DubClip], audio_out: Path, video_out: Path,
                      duck_volume: float = 0.0) -> None:
        """Mix TTS clips over the original track and mux with the original video.

        The original audio is kept everywhere except inside TTS windows, where it is
        ducked to `duck_volume`. Segments without a clip (Quran) keep their original
        audio untouched.
        """
        audio_out.parent.mkdir(parents=True, exist_ok=True)
        duration = self.probe_duration(video) or 0.0
        has_audio = self.has_stream(video, "audio")

        inputs: list[str] = ["-i", str(video)]
        if not has_audio:
            inputs += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        base_index = 0 if has_audio else 1
        first_clip_index = base_index + 1
        for clip in clips:
            inputs += ["-i", str(clip.path)]

        filters: list[str] = []
        base = f"[{base_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
        if clips:
            windows = "+".join(f"between(t,{c.start:.3f},{self._duck_end(c):.3f})" for c in clips)
            base += f",volume={duck_volume:.3f}:enable='{windows}'"
        filters.append(base + "[orig]")
        labels = ["[orig]"]
        for i, clip in enumerate(clips):
            delay_ms = int(round(clip.start * 1000))
            chain = f"[{first_clip_index + i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
            if abs(clip.tempo - 1.0) > 0.005:
                chain += f",atempo={clip.tempo:.4f}"
            chain += f",atrim=duration={max(0.05, clip.window):.3f},adelay={delay_ms}|{delay_ms}[c{i}]"
            filters.append(chain)
            labels.append(f"[c{i}]")
        if len(labels) > 1:
            filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:dropout_transition=0:"
                           f"normalize=0[mix]")
        else:
            filters.append("[orig]anull[mix]")

        self._run([*inputs, "-filter_complex", ";".join(filters), "-map", "[mix]", "-t", f"{duration:.3f}",
                   "-c:a", "aac", "-b:a", self.audio_bitrate, str(audio_out)])
        self._run(["-i", str(video), "-i", str(audio_out), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                   "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(video_out)])

    def _duck_end(self, clip: DubClip) -> float:
        spoken = max((clip.segment_end or clip.start) - clip.start, self._clip_len(clip))
        return clip.start + min(clip.window, spoken)

    def _clip_len(self, clip: DubClip) -> float:
        length = self.probe_duration(clip.path) or clip.window
        return length / max(clip.tempo, 0.01)
