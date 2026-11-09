from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from core.app_errors import PipelineError

ProgressCallback = Callable[[str], None] | None


def _executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        code = "FFMPEG_NOT_FOUND" if name == "ffmpeg" else "FFPROBE_NOT_FOUND"
        title = "Không tìm thấy FFmpeg" if name == "ffmpeg" else "Không tìm thấy FFprobe"
        raise PipelineError(
            stage="Kiểm tra môi trường",
            code=code,
            title=title,
            message=f"Không tìm thấy {name} trong Windows PATH.",
            recovery="Cài đặt FFmpeg và thêm thư mục chứa ffmpeg.exe, ffprobe.exe vào PATH. Sau đó mở lại AutoVideoLocal.",
        )
    return path


def check_environment() -> None:
    ffmpeg = _executable("ffmpeg")
    _executable("ffprobe")

    try:
        filters = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        encoders = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PipelineError(
            stage="Kiểm tra môi trường",
            code="FFMPEG_CHECK_FAILED",
            title="Không thể kiểm tra FFmpeg",
            message="AutoVideoLocal không thể kiểm tra các thành phần FFmpeg cần thiết.",
            recovery="Kiểm tra cài đặt FFmpeg và thử chạy lệnh ffmpeg -version trong PowerShell.",
            technical_detail=str(error),
        ) from error

    filter_text = filters.stdout + filters.stderr
    encoder_text = encoders.stdout + encoders.stderr
    if filters.returncode != 0 or "subtitles" not in filter_text:
        raise PipelineError(
            stage="Kiểm tra môi trường",
            code="FFMPEG_SUBTITLES_MISSING",
            title="FFmpeg thiếu bộ lọc phụ đề",
            message="Bản FFmpeg hiện tại không hỗ trợ bộ lọc subtitles cần thiết.",
            recovery="Cài bản FFmpeg có hỗ trợ libass, sau đó kiểm tra lại bằng: ffmpeg -filters | findstr subtitles.",
            technical_detail=filter_text[-3000:],
        )

    if encoders.returncode != 0 or "libx264" not in encoder_text:
        raise PipelineError(
            stage="Kiểm tra môi trường",
            code="FFMPEG_H264_MISSING",
            title="FFmpeg thiếu bộ mã hóa H.264",
            message="Bản FFmpeg hiện tại không có bộ mã hóa libx264.",
            recovery="Cài bản FFmpeg có hỗ trợ libx264 rồi thử lại.",
            technical_detail=encoder_text[-3000:],
        )


def run_command(
    command: list[str],
    cwd: str | Path | None = None,
    *,
    code: str = "FFMPEG_PROCESS_FAILED",
    title: str = "Không thể xử lý video",
    message: str = "FFmpeg không thể hoàn thành công đoạn xử lý.",
    recovery: str = "Kiểm tra file nguồn và dung lượng ổ đĩa, sau đó thử lại.",
) -> subprocess.CompletedProcess[str]:
    executable = command[0]
    if executable == "ffmpeg":
        command = [
            _executable(executable),
            "-hide_banner", "-loglevel", "error", "-nostats",
            *command[1:],
        ]
    elif executable == "ffprobe":
        command = [_executable(executable), *command[1:]]

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as error:
        raise PipelineError(
            stage="Xử lý video",
            code="MEDIA_EXECUTABLE_NOT_FOUND",
            title="Không tìm thấy công cụ xử lý video",
            message="Windows không thể khởi chạy FFmpeg hoặc FFprobe.",
            recovery="Kiểm tra lại thư mục cài đặt FFmpeg và Windows PATH.",
            technical_detail=str(error),
        ) from error
    except OSError as error:
        raise PipelineError(
            stage="Xử lý video",
            code="MEDIA_PROCESS_START_FAILED",
            title="Không thể khởi chạy tiến trình xử lý",
            message="AutoVideoLocal không thể khởi động tiến trình xử lý video.",
            recovery="Kiểm tra quyền truy cập file, thư mục làm việc và cài đặt FFmpeg.",
            technical_detail=str(error),
        ) from error

    if result.returncode != 0:
        raise PipelineError(
            stage="Xử lý video",
            code=code,
            title=title,
            message=message,
            recovery=recovery,
            technical_detail=result.stderr[-5000:],
        )
    return result


def get_duration(path: str | Path) -> float:
    media_path = Path(path).resolve()
    if not media_path.exists():
        raise PipelineError(
            stage="Phân tích thời lượng",
            code="MEDIA_FILE_NOT_FOUND",
            title="Không tìm thấy file cần phân tích",
            message=f"Không tìm thấy file: {media_path.name}",
            recovery="Kiểm tra lại file nguồn hoặc tạo lại file trung gian.",
        )

    result = run_command(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        code="MEDIA_PROBE_FAILED",
        title="Không thể đọc thông tin media",
        message=f"Không thể đọc thời lượng của file {media_path.name}.",
        recovery="Kiểm tra file có bị hỏng hoặc có định dạng được FFmpeg hỗ trợ không.",
    )

    try:
        duration = float(result.stdout.strip())
    except (TypeError, ValueError) as error:
        raise PipelineError(
            stage="Phân tích thời lượng",
            code="MEDIA_DURATION_INVALID",
            title="Thời lượng media không hợp lệ",
            message=f"Không đọc được thời lượng của file {media_path.name}.",
            recovery="Thử mở file bằng trình phát video hoặc chuyển đổi sang MP4.",
            technical_detail=result.stdout + "\n" + result.stderr,
        ) from error

    if duration <= 0:
        raise PipelineError(
            stage="Phân tích thời lượng",
            code="MEDIA_DURATION_ZERO",
            title="Media không có thời lượng hợp lệ",
            message=f"File {media_path.name} có thời lượng bằng 0 hoặc không xác định.",
            recovery="Chọn một file video khác có dữ liệu hình ảnh hợp lệ.",
        )
    return duration


def get_stream_types(path: str | Path) -> set[str]:
    result = run_command(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            str(Path(path).resolve()),
        ],
        code="MEDIA_STREAM_PROBE_FAILED",
        title="Không thể đọc cấu trúc video",
        message="Không thể xác định các luồng dữ liệu trong file nguồn.",
        recovery="Kiểm tra file nguồn hoặc thử chuyển đổi sang MP4.",
    )
    try:
        payload = json.loads(result.stdout)
        return {stream.get("codec_type", "") for stream in payload.get("streams", [])}
    except (json.JSONDecodeError, AttributeError, TypeError) as error:
        raise PipelineError(
            stage="Kiểm tra file nguồn",
            code="MEDIA_METADATA_INVALID",
            title="Thông tin file nguồn không hợp lệ",
            message="Không thể phân tích thông tin bên trong file nguồn.",
            recovery="Chọn file khác hoặc chuyển đổi file sang định dạng MP4.",
            technical_detail=str(error),
        ) from error


def validate_output(path: str | Path) -> float:
    output = Path(path)
    if not output.is_file() or output.stat().st_size < 1024:
        raise PipelineError(
            stage="Kiểm tra video đầu ra",
            code="OUTPUT_FILE_EMPTY",
            title="File video đầu ra không hợp lệ",
            message="FFmpeg đã kết thúc nhưng file video đầu ra bị thiếu hoặc quá nhỏ.",
            recovery="Giữ lại thư mục làm việc để kiểm tra và thử xuất lại.",
        )

    stream_types = get_stream_types(output)
    if "video" not in stream_types or "audio" not in stream_types:
        raise PipelineError(
            stage="Kiểm tra video đầu ra",
            code="OUTPUT_STREAM_MISSING",
            title="Video đầu ra thiếu hình ảnh hoặc âm thanh",
            message="File MP4 chưa có đủ luồng hình ảnh và âm thanh cần thiết.",
            recovery="Kiểm tra file giọng đọc và thử xuất video lại.",
        )
    return get_duration(output)


def create_video(
    sources: list[str | Path],
    voice_path: str | Path,
    subtitle_path: str | Path,
    output_path: str | Path,
    work_dir: str | Path,
    orientation: str = "portrait",
    progress_callback: ProgressCallback = None,
) -> Path:
    source_paths = [Path(item).resolve() for item in sources]
    voice_file = Path(voice_path).resolve()
    subtitle_file = Path(subtitle_path).resolve()
    output_file = Path(output_path).resolve()
    working_dir = Path(work_dir).resolve()

    working_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not source_paths:
        raise PipelineError(
            stage="Kiểm tra nguồn",
            code="SOURCE_LIST_EMPTY",
            title="Chưa có video nguồn",
            message="Bạn cần thêm ít nhất một video nguồn.",
            recovery="Nhấn Thêm video và chọn file cần ghép.",
        )

    for source in source_paths:
        if not source.is_file():
            raise PipelineError(
                stage="Kiểm tra nguồn",
                code="SOURCE_FILE_MISSING",
                title="Không tìm thấy video nguồn",
                message=f"Không tìm thấy file {source.name}.",
                recovery="Chọn lại video nguồn hoặc khôi phục file đã bị di chuyển.",
            )
        if "video" not in get_stream_types(source):
            raise PipelineError(
                stage="Kiểm tra nguồn",
                code="SOURCE_HAS_NO_VIDEO",
                title="File nguồn không chứa hình ảnh video",
                message=f"File {source.name} không có luồng hình ảnh video hợp lệ.",
                recovery="Chọn một file video khác. File âm thanh đơn thuần không được hỗ trợ ở bước này.",
            )

    if not voice_file.is_file():
        raise PipelineError(
            stage="Lồng giọng đọc",
            code="VOICE_FILE_MISSING",
            title="Không tìm thấy file giọng đọc",
            message="File giọng đọc chưa được tạo hoặc đã bị di chuyển.",
            recovery="Tạo lại giọng đọc trước khi dựng video.",
        )
    if not subtitle_file.is_file():
        raise PipelineError(
            stage="Tạo phụ đề",
            code="SUBTITLE_FILE_MISSING",
            title="Không tìm thấy file phụ đề",
            message="File phụ đề chưa được tạo.",
            recovery="Tạo lại phụ đề rồi thử dựng video.",
        )

    if orientation == "portrait":
        width, height = 1080, 1920
    elif orientation == "landscape":
        width, height = 1920, 1080
    else:
        raise PipelineError(
            stage="Cấu hình video",
            code="INVALID_ORIENTATION",
            title="Tỷ lệ video không hợp lệ",
            message="Định dạng video đã chọn không được hỗ trợ.",
            recovery="Chọn video dọc 9:16 hoặc video ngang 16:9.",
        )

    total_voice_duration = get_duration(voice_file)
    source_durations = [get_duration(source) for source in source_paths]
    total_source_duration = sum(source_durations)
    if total_source_duration <= 0:
        raise PipelineError(
            stage="Phân tích nguồn",
            code="SOURCE_DURATION_INVALID",
            title="Tổng thời lượng video nguồn không hợp lệ",
            message="Không xác định được thời lượng hợp lệ của các video nguồn.",
            recovery="Kiểm tra các video nguồn và thử lại.",
        )

    allocations = [
        total_voice_duration * duration / total_source_duration
        for duration in source_durations
    ]
    normalized_clips: list[Path] = []

    for index, (source, duration) in enumerate(zip(source_paths, allocations)):
        clip_path = working_dir / f"clip_{index:03d}.mp4"
        if progress_callback:
            progress_callback(f"Đang chuẩn hóa video {index + 1}/{len(source_paths)}: {source.name}")

        run_command(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(source),
                "-t", f"{duration:.4f}",
                "-an",
                "-vf",
                (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},setsar=1,fps=30"
                ),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",
                str(clip_path),
            ],
            code="VIDEO_NORMALIZE_FAILED",
            title=f"Không thể xử lý video {index + 1}",
            message=f"Không thể chuẩn hóa video nguồn {source.name}.",
            recovery="Kiểm tra video có phát được không, sau đó thử chuyển đổi video sang MP4 (H.264).",
        )
        normalized_clips.append(clip_path)

    if progress_callback:
        progress_callback("Đang ghép các video nguồn...")

    concat_file = working_dir / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{clip.name}'\n" for clip in normalized_clips),
        encoding="utf-8",
    )
    merged_video = working_dir / "merged.mp4"
    run_command(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file.name,
            "-c", "copy",
            str(merged_video),
        ],
        cwd=working_dir,
        code="VIDEO_MERGE_FAILED",
        title="Không thể ghép các video nguồn",
        message="FFmpeg không thể ghép các đoạn video đã chuẩn hóa.",
        recovery="Kiểm tra các file clip trung gian trong thư mục làm việc rồi thử lại.",
    )

    if progress_callback:
        progress_callback("Đang lồng giọng đọc và phụ đề...")

    local_subtitle = working_dir / "captions.srt"
    local_subtitle.write_bytes(subtitle_file.read_bytes())

    subtitle_filter = (
        "subtitles=captions.srt:"
        "force_style='FontName=Arial,"
        "FontSize=20,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=80'"
    )

    run_command(
        [
            "ffmpeg", "-y",
            "-i", str(merged_video),
            "-i", str(voice_file),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{total_voice_duration:.3f}",
            "-movflags", "+faststart",
            str(output_file),
        ],
        cwd=working_dir,
        code="FINAL_RENDER_FAILED",
        title="Không thể xuất video hoàn chỉnh",
        message="Không thể lồng giọng đọc và phụ đề vào video.",
        recovery="Kiểm tra file merged.mp4, voice.mp3 và captions.srt trong thư mục làm việc rồi thử lại.",
    )

    if progress_callback:
        progress_callback("Đã hoàn thành công đoạn dựng video.")
    return output_file