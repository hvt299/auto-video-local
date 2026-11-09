from __future__ import annotations

import os
from pathlib import Path

from core.app_errors import PipelineError
from core.subtitle_engine import create_srt
from core.video_engine import (
    check_environment,
    create_video,
    get_duration,
    validate_output,
)
from core.voice_engine import generate_voice


def build_video(
    sources: list[str],
    text: str,
    output_path: str,
    voice_name: str,
    orientation: str,
    rate: str = "+0%",
    progress_callback=None,
) -> Path:
    final_path = Path(output_path).resolve()
    final_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir = final_path.parent / f"{final_path.stem}_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    voice_path = work_dir / "voice.mp3"
    subtitle_path = work_dir / "captions.srt"
    staging_path = final_path.with_name(f"{final_path.stem}.rendering{final_path.suffix}")

    def report(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    check_environment()

    report("Đang chuẩn bị giọng đọc tiếng Việt...")
    generate_voice(
        text=text,
        output_path=voice_path,
        voice_name=voice_name,
        rate=rate,
        cache_dir=work_dir / "voice_cache",
        progress_callback=progress_callback,
    )

    report("Đang phân tích thời lượng giọng đọc...")
    try:
        duration = get_duration(voice_path)
    except PipelineError as error:
        raise PipelineError(
            stage="Phân tích giọng đọc",
            code="VOICE_ANALYSIS_FAILED",
            title="Không thể phân tích file giọng đọc",
            message="File giọng đọc đã được tạo nhưng FFprobe không đọc được thời lượng.",
            recovery="Kiểm tra file voice.mp3 trong thư mục làm việc. Nếu file bị lỗi, hãy tạo lại giọng đọc.",
            technical_detail=error.technical_detail or str(error),
        ) from error

    report("Đang tạo phụ đề...")
    try:
        create_srt(text=text, duration=duration, output_path=subtitle_path)
    except Exception as error:
        raise PipelineError(
            stage="Tạo phụ đề",
            code="SUBTITLE_CREATE_FAILED",
            title="Không thể tạo phụ đề",
            message="Nội dung hiện tại không thể chuyển thành file phụ đề.",
            recovery="Kiểm tra lời thoại, dấu câu và thử lại.",
            technical_detail=f"{error.__class__.__name__}: {error}",
        ) from error

    report("Đang dựng video...")
    try:
        staging_path.unlink(missing_ok=True)
    except OSError:
        pass

    create_video(
        sources=sources,
        voice_path=voice_path,
        subtitle_path=subtitle_path,
        output_path=staging_path,
        work_dir=work_dir,
        orientation=orientation,
        progress_callback=progress_callback,
    )

    report("Đang kiểm tra video đầu ra...")
    validate_output(staging_path)

    try:
        os.replace(staging_path, final_path)
    except OSError as error:
        raise PipelineError(
            stage="Lưu video",
            code="OUTPUT_FINALIZE_FAILED",
            title="Không thể lưu video thành phẩm",
            message="Video đã dựng xong nhưng Windows không thể thay thế file đầu ra.",
            recovery="Đóng trình phát đang mở file đích, kiểm tra quyền ghi thư mục và thử lại.",
            technical_detail=str(error),
        ) from error

    report("Hoàn thành xuất video!")
    return final_path