import asyncio
import edge_tts


VOICES = {
    "Nữ - Hoài My": "vi-VN-HoaiMyNeural",
    "Nam - Minh": "vi-VN-NamMinhNeural",
}


async def _generate(text, output_path, voice, rate):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate
    )

    await communicate.save(str(output_path))


def generate_voice(
    text,
    output_path,
    voice_name="Nữ - Hoài My",
    rate="+0%"
):
    if not text.strip():
        raise ValueError("Nội dung giọng đọc đang trống.")

    voice = VOICES.get(voice_name)

    if not voice:
        raise ValueError("Giọng đọc không hợp lệ.")

    asyncio.run(
        _generate(text, output_path, voice, rate)
    )

    return output_path