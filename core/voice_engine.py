from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Callable

import edge_tts

from core.app_errors import PipelineError
from core.usage_store import get_last_request_epoch, record_request

VOICES = {
    "Nữ - Hoài My": "vi-VN-HoaiMyNeural",
    "Nam - Minh": "vi-VN-NamMinhNeural",
}

# This is a conservative local pacing rule, NOT a Microsoft-published quota.
MIN_REQUEST_INTERVAL_SECONDS = 15
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 20
REQUEST_TIMEOUT_SECONDS = 180

_REQUEST_LOCK = threading.Lock()
ProgressCallback = Callable[[str], None] | None


def _report(callback: ProgressCallback, message: str) -> None:
    if callback:
        callback(message)


def _cache_key(text: str, voice: str, rate: str) -> str:
    payload = "\0".join((text, voice, rate)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_valid_audio(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= 128
    except OSError:
        return False


async def _generate(
    text: str,
    output_path: Path,
    voice: str,
    rate: str,
) -> None:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        connect_timeout=15,
        receive_timeout=60,
    )
    await asyncio.wait_for(
        communicate.save(str(output_path)),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def _wait_for_pacing(progress_callback: ProgressCallback) -> None:
    last_request = get_last_request_epoch()
    if last_request is None:
        return

    elapsed = time.time() - last_request
    remaining = MIN_REQUEST_INTERVAL_SECONDS - elapsed
    if remaining > 0:
        wait_seconds = int(remaining + 0.999)
        _report(
            progress_callback,
            f"Đang chờ {wait_seconds} giây để giãn cách các yêu cầu giọng đọc...",
        )
        time.sleep(remaining)


def _classify_error(error: Exception) -> tuple[str, str, str, bool]:
    detail = str(error) or error.__class__.__name__
    lower = detail.lower()

    if re.search(r"\b(401|403|429)\b", lower):
        return (
            "TTS_ACCESS_LIMITED",
            "Dịch vụ giọng đọc đang từ chối yêu cầu",
            "AutoVideoLocal đã dừng gửi yêu cầu để tránh tiếp tục gây tải lên dịch vụ.",
            False,
        )

    if "no audio was received" in lower or "noaudioreceived" in lower:
        return (
            "TTS_NO_AUDIO",
            "Không nhận được dữ liệu âm thanh",
            "Hãy kiểm tra kết nối Internet và thử lại sau. Ứng dụng chỉ tự thử lại một lần.",
            True,
        )

    if any(token in lower for token in ("503", "service unavailable", "server disconnected")):
        return (
            "TTS_SERVICE_UNAVAILABLE",
            "Dịch vụ giọng đọc tạm thời không phản hồi",
            "Hãy chờ dịch vụ ổn định rồi thử lại. Ứng dụng chỉ tự thử lại một lần.",
            True,
        )

    if isinstance(error, (asyncio.TimeoutError, TimeoutError, ConnectionError)) or any(
        token in lower
        for token in ("timed out", "timeout", "connection reset", "network is unreachable")
    ):
        return (
            "TTS_CONNECTION_ERROR",
            "Không thể kết nối dịch vụ giọng đọc",
            "Kiểm tra Internet, tường lửa hoặc thử lại sau ít phút.",
            True,
        )

    return (
        "TTS_GENERATION_FAILED",
        "Không thể tạo giọng đọc",
        "Kiểm tra nội dung và kết nối Internet. Nếu lỗi tiếp tục, hãy thử lại sau.",
        False,
    )


def generate_voice(
    text: str,
    output_path: str | Path,
    voice_name: str = "Nữ - Hoài My",
    rate: str = "+0%",
    cache_dir: str | Path | None = None,
    progress_callback: ProgressCallback = None,
) -> Path:
    cleaned_text = text.strip()
    if not cleaned_text:
        raise PipelineError(
            stage="Giọng đọc",
            code="TTS_EMPTY_TEXT",
            title="Chưa có nội dung giọng đọc",
            message="Vui lòng nhập nội dung tiếng Việt trước khi tạo giọng đọc.",
            recovery="Nhập lời thoại rồi thử lại.",
        )

    voice = VOICES.get(voice_name)
    if not voice:
        raise PipelineError(
            stage="Giọng đọc",
            code="TTS_INVALID_VOICE",
            title="Giọng đọc không hợp lệ",
            message="Giọng đọc đã chọn không nằm trong danh sách hỗ trợ.",
            recovery="Chọn giọng Hoài My hoặc Nam Minh rồi thử lại.",
        )

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_root = Path(cache_dir).resolve() if cache_dir else output.parent / "voice_cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    cache_file = cache_root / f"{_cache_key(cleaned_text, voice, rate)}.mp3"
    if _is_valid_audio(cache_file):
        shutil.copy2(cache_file, output)
        _report(progress_callback, "Đã sử dụng giọng đọc đã lưu; không gửi yêu cầu mới.")
        return output

    temporary_audio = cache_file.with_name(f"{cache_file.stem}.partial.mp3")

    # One process-wide lock prevents concurrent Edge TTS requests.
    with _REQUEST_LOCK:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            _wait_for_pacing(progress_callback)
            record_request(len(cleaned_text))
            _report(
                progress_callback,
                f"Đang gửi yêu cầu tạo giọng đọc (lần {attempt}/{MAX_ATTEMPTS})...",
            )

            try:
                if temporary_audio.exists():
                    temporary_audio.unlink()

                asyncio.run(
                    _generate(cleaned_text, temporary_audio, voice, rate)
                )

                if not _is_valid_audio(temporary_audio):
                    raise RuntimeError("No audio was received or the audio file is empty")

                os.replace(temporary_audio, cache_file)
                shutil.copy2(cache_file, output)
                return output

            except Exception as error:
                try:
                    temporary_audio.unlink(missing_ok=True)
                except OSError:
                    pass

                code, title, recovery, retryable = _classify_error(error)
                if retryable and attempt < MAX_ATTEMPTS:
                    _report(
                        progress_callback,
                        f"Yêu cầu chưa thành công. Ứng dụng sẽ chờ {RETRY_DELAY_SECONDS} giây rồi thử lại một lần.",
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue

                raise PipelineError(
                    stage="Giọng đọc",
                    code=code,
                    title=title,
                    message=title + ". " + recovery,
                    recovery=recovery,
                    technical_detail=detail_for_error(error),
                ) from error

    raise PipelineError(
        stage="Giọng đọc",
        code="TTS_UNKNOWN",
        title="Không thể tạo giọng đọc",
        message="Quá trình tạo giọng đọc đã dừng.",
        recovery="Thử lại sau ít phút.",
    )


def detail_for_error(error: Exception) -> str:
    return f"{error.__class__.__name__}: {error}"