from pathlib import Path

from core.voice_engine import generate_voice
from core.subtitle_engine import create_srt
from core.video_engine import create_video, get_duration


def build_video(
    sources,
    text,
    output_path,
    voice_name,
    orientation,
    progress_callback=None
):
    output_path = Path(output_path).resolve()

    work_dir = output_path.parent / (
        output_path.stem + "_work"
    )

    work_dir.mkdir(parents=True, exist_ok=True)

    voice_path = work_dir / "voice.mp3"
    subtitle_path = work_dir / "captions.srt"

    def report(message):
        if progress_callback:
            progress_callback(message)

    report("Đang tạo giọng đọc tiếng Việt...")

    generate_voice(
        text=text,
        output_path=voice_path,
        voice_name=voice_name
    )

    report("Đang phân tích thời lượng giọng đọc...")

    duration = get_duration(voice_path)

    report("Đang tạo phụ đề...")

    create_srt(
        text=text,
        duration=duration,
        output_path=subtitle_path
    )

    report("Đang dựng video...")

    result = create_video(
        sources=sources,
        voice_path=voice_path,
        subtitle_path=subtitle_path,
        output_path=output_path,
        work_dir=work_dir,
        orientation=orientation,
        progress_callback=progress_callback
    )

    return result