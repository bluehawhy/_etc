import yt_dlp


def download_youtube_video(url: str = None):
    if url is None:
        url = input("다운로드할 유튜브 영상 URL을 입력하세요: ")

    ydl_opts = {
        # 1. 최고의 비디오 + 최고의 오디오를 선택
        'format': 'bestvideo+bestaudio/best',
        
        # 2. 다운로드 완료 후 FFmpeg를 이용해 MP4 컨테이너로 병합
        'merge_output_format': 'mp4',
        
        # 3. 저장 위치 및 파일 이름 설정 (현재 폴더 / 영상 제목)
        'outtmpl': '%(title)s.%(ext)s',
        
        # 4. H.264/AAC 코덱 우선 지정 (MP4 호환성 극대화, 필요 시 선택)
        # 'postprocessor_args': ['-c:v', 'copy', '-c:a', 'aac'],
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print("최고 화질 다운로드 및 MP4 병합 완료!")

if __name__ == "__main__":
    download_youtube_video()