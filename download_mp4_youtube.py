import re
import pyperclip
import yt_dlp



def is_youtube_url(url: str) -> bool:
    """유튜브 영상 URL(일반/단축)인지 검증"""
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+'
    return bool(re.match(youtube_regex, url)) if url else False

def clean_youtube_url(url: str) -> str:
    """&list=..., &start_radio=1 같은 믹스/재생목록 파라미터를 완전히 제거하고 순수 영상 URL만 남김"""
    if not url:
        return ""
    
    # youtube.com/watch?v=ID 형태에서 v=ID 부분만 추출
    match = re.search(r'(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    # youtu.be/ID 단축 URL 형태 추출
    match_short = re.search(r'(https?://youtu\.be/[a-zA-Z0-9_-]+)', url)
    if match_short:
        return match_short.group(1)
        
    return url

def download_youtube_video(url: str = None):
    # 1. 전달받은 URL이 없거나 유튜브 링크가 아니면 직접 입력 요청
    if not is_youtube_url(url):
        if url:
            print(f"❌ 클립보드 값('{url[:30]}...')이 올바른 유튜브 링크가 아닙니다.")
        
        url = input("다운로드할 유튜브 영상 URL을 입력하세요: ").strip()
        
        # 재검증 후 실패 시 종료
        if not is_youtube_url(url):
            print("❌ 올바른 유튜브 링크가 아닙니다. 프로그램을 종료합니다.")
            return
    else:
        print(f"📋 클립보드 링크 감지: {url}")
        url = clean_youtube_url(url)

    # 2. yt-dlp 옵션 설정
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': '%(title)s.%(ext)s',
        'noplaylist': True,
        # 🔥 이 부분을 추가해 주세요
        'remote_components': ['ejs:github'],
    }

    # 3. 다운로드 실행
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("🎉 최고 화질 다운로드 및 MP4 병합 완료!")
    except Exception as e:
        print(f"❌ 다운로드 중 오류 발생: {e}")

if __name__ == "__main__":
    # 메인은 단순하게 클립보드 값만 뽑아서 전달
    clipboard_text = pyperclip.paste().strip()
    download_youtube_video(clipboard_text)