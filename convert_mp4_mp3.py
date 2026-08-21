from pathlib import Path
import subprocess


def convert_mp4_to_mp3(input_path: Path):
    # 동일 경로 및 파일명에 확장자만 .mp3로 변경
    output_path = input_path.with_suffix(".mp3")

    # 이미 동일한 mp3 파일이 존재하는 경우 건너뛰고 싶다면 주석 해제
    # if output_path.exists():
    #     print(f"이미 존재함 (스킵): {output_path.name}")
    #     return

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
        # ffmpeg 출력 로그를 숨기려면 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL 추가
        subprocess.run(command, check=True)
        print(f"변환 완료: {input_path.name} -> {output_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"변환 실패 ({input_path.name}): {e}")
    except FileNotFoundError:
        print("오류: ffmpeg이 설치되어 있지 않거나 PATH 환경 변수에 등록되지 않았습니다.")
        return False
    return Trues


def batch_convert_folder(folder_path_str: str, recursive: bool = True):
    target_dir = Path(folder_path_str)

    # 폴더 존재 여부 확인
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"오류: 유효한 폴더 경로가 아닙니다 -> {folder_path_str}")
        return

    # rglob: 하위 폴더까지 검색 / glob: 지정 폴더 내만 검색
    # 대소문자 구분 없이 찾기 위해 '*.mp4', '*.MP4' 둘 다 탐색하거나 패턴 사용
    pattern = "**/*.mp4" if recursive else "*.mp4"
    mp4_files = list(target_dir.glob(pattern))

    if not mp4_files:
        print(f"변환할 MP4 파일을 찾지 못했습니다 -> {target_dir}")
        return

    print(f"총 {len(mp4_files)}개의 MP4 파일을 발견했습니다. 변환을 시작합니다...\n")

    for file_path in mp4_files:
        success = convert_mp4_to_mp3(file_path)
        if success is False:  # ffmpeg 미설치 시 조기 종료
            break

    print("\n모든 작업이 완료되었습니다.")


# 실행 코드
if __name__ == "__main__":
    # raw string(r"...")을 사용하면 역슬래시(\) 이스케이프 문제를 방지할 수 있습니다.
    target_folder = r"E:\노래\동요"
    
    # recursive=True: 하위 폴더까지 검색 / recursive=False: 해당 폴더만 검색
    batch_convert_folder(target_folder, recursive=True)