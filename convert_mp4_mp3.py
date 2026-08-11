from pathlib import Path
import subprocess


def convert_mp4_to_mp3(input_path_str: str):
    # 경로 객체 생성
    input_path = Path(input_path_str)

    # 파일 존재 확인
    if not input_path.exists():
        print(f"오류: 파일이 존재하지 않습니다 -> {input_path}")
        return

    # 동일 경로 및 파일명에 확장자만 .mp3로 변경 (.with_suffix 사용)
    output_path = input_path.with_suffix(".mp3")

    # ffmpeg 명령어 구성
    command = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-vn",  # 비디오 제외
        "-acodec",
        "libmp3lame",  # MP3 코덱
        "-ab",
        "192k",  # 비트레이트 설정
        "-y",  # 기존 output 파일 덮어쓰기
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True)
        print(f"변환 완료!\n저장 경로: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"변환 실패: {e}")
    except FileNotFoundError:
        print(
            "오류: ffmpeg이 설치되어 있지 않거나 PATH 환경 변수에 등록되지 않았습니다."
        )


# 사용 예시 (절대 경로 또는 상대 경로 사용 가능)
convert_mp4_to_mp3("다음카페다운/나팔꽃반 합창 '힘내' - 전체 영상.mp4")