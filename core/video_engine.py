import subprocess
from pathlib import Path


def run_command(command, cwd=None):
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr[-3000:]
        )

    return result


def get_duration(path):
    result = run_command([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ])

    return float(result.stdout.strip())


def create_video(
    sources,
    voice_path,
    subtitle_path,
    output_path,
    work_dir,
    orientation="portrait",
    progress_callback=None
):
    sources = [Path(p).resolve() for p in sources]
    voice_path = Path(voice_path).resolve()
    subtitle_path = Path(subtitle_path).resolve()
    output_path = Path(output_path).resolve()
    work_dir = Path(work_dir).resolve()

    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not sources:
        raise ValueError("Chưa có video source.")

    for path in sources:
        if not path.exists():
            raise FileNotFoundError(path)

    if not voice_path.exists():
        raise FileNotFoundError(voice_path)

    if orientation == "portrait":
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080

    total_voice_duration = get_duration(voice_path)

    source_durations = [
        get_duration(path)
        for path in sources
    ]

    total_source_duration = sum(source_durations)

    if total_source_duration <= 0:
        raise ValueError("Thời lượng video không hợp lệ.")

    # Phân bổ thời lượng theo tỷ lệ thời lượng source.
    allocations = [
        total_voice_duration * duration / total_source_duration
        for duration in source_durations
    ]

    normalized_clips = []

    for index, (source, duration) in enumerate(
        zip(sources, allocations)
    ):
        clip_path = work_dir / f"clip_{index:03d}.mp4"

        if progress_callback:
            progress_callback(
                f"Đang xử lý source {index + 1}/{len(sources)}"
            )

        # Loop source nếu thời lượng được phân bổ dài hơn source.
        command = [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",
            "-i", str(source),
            "-t", f"{duration:.4f}",
            "-an",
            "-vf",
            (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                "setsar=1,fps=30"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            str(clip_path)
        ]

        run_command(command)

        normalized_clips.append(clip_path)

    if progress_callback:
        progress_callback("Đang ghép các video source...")

    concat_file = work_dir / "concat.txt"

    concat_file.write_text(
        "".join(
            f"file '{clip.name}'\n"
            for clip in normalized_clips
        ),
        encoding="utf-8"
    )

    merged_video = work_dir / "merged.mp4"

    run_command([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file.name,
        "-c", "copy",
        str(merged_video)
    ], cwd=work_dir)

    if progress_callback:
        progress_callback("Đang lồng giọng đọc và phụ đề...")

    # Đưa subtitle về thư mục làm việc để tránh vấn đề
    # đường dẫn Windows có dấu hai chấm.
    local_subtitle = work_dir / "captions.srt"

    local_subtitle.write_bytes(
        subtitle_path.read_bytes()
    )

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

    run_command([
        "ffmpeg",
        "-y",
        "-i", str(merged_video),
        "-i", str(voice_path),
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
        str(output_path)
    ], cwd=work_dir)

    if progress_callback:
        progress_callback("Hoàn thành xuất video!")

    return output_path