import re


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?。])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def format_timestamp(seconds):
    milliseconds = int(round(seconds * 1000))

    hours = milliseconds // 3600000
    milliseconds %= 3600000

    minutes = milliseconds // 60000
    milliseconds %= 60000

    secs = milliseconds // 1000
    milliseconds %= 1000

    return (
        f"{hours:02}:"
        f"{minutes:02}:"
        f"{secs:02},"
        f"{milliseconds:03}"
    )


def create_srt(text, duration, output_path):
    sentences = split_sentences(text)

    if not sentences:
        raise ValueError("Không tìm thấy nội dung phụ đề.")

    total_chars = sum(
        max(len(sentence), 1)
        for sentence in sentences
    )

    current_time = 0
    blocks = []

    for index, sentence in enumerate(sentences):
        if index == len(sentences) - 1:
            end_time = duration
        else:
            sentence_duration = (
                duration
                * len(sentence)
                / total_chars
            )

            end_time = current_time + sentence_duration

        blocks.append(
            f"{index + 1}\n"
            f"{format_timestamp(current_time)} --> "
            f"{format_timestamp(end_time)}\n"
            f"{sentence}\n"
        )

        current_time = end_time

    with open(
        output_path,
        "w",
        encoding="utf-8-sig"
    ) as file:
        file.write("\n".join(blocks))

    return output_path