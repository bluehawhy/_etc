import json
import re
import subprocess
import time
from pathlib import Path
import requests
import pyperclip
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ==============================================================================
# 1. 카페 주소 HTML에서 동영상 제목 및 iframe URL 추출 Class
# ==============================================================================
class DaumCafeExtractor:
    def extract_videos_with_titles(self, html_content: str) -> list:
        soup = BeautifulSoup(html_content, 'html.parser')
        video_list = []

        # 게시글 본문 영역 탐색
        user_contents = soup.find(id="user_contents") or soup.find(id="bbs_contents") or soup

        # figure-video 태그 찾기
        video_divs = user_contents.find_all('div', class_='figure-video')

        for idx, div in enumerate(video_divs, 1):
            # iframe 또는 data-video-url 주소 추출
            iframe = div.find('iframe')
            video_url = None
            if iframe and iframe.get('src'):
                video_url = iframe['src']
            elif div.get('data-video-url'):
                video_url = div['data-video-url']

            if not video_url:
                continue

            # 바로 이전 <p> 태그에서 제목 추출
            title = None
            prev_node = div.find_previous_sibling()

            while prev_node:
                text = prev_node.get_text(strip=True).replace('\xa0', '').strip()
                if text:
                    title = text
                    break
                prev_node = prev_node.find_previous_sibling()

            if not title:
                title = f"동영상_{idx}"

            # 파일명으로 사용할 수 없는 특수문자 제거 및 정제
            clean_title = re.sub(r'^[<＜\s]+|[>＞\s]+$', '', title)
            clean_title = re.sub(r'[\/:*?"<>|]', '_', clean_title)

            video_list.append({
                "index": idx,
                "title": clean_title,
                "iframe_url": video_url
            })

        return video_list


# ==============================================================================
# 2. Selenium을 이용해 iframe URL에서 MPD 네트워크 주소 추출하는 Class
# ==============================================================================
class MpdUrlFinder:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 창을 띄우지 않는 모드
        chrome_options.add_argument("--mute-audio")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def find_mpd_url(self, iframe_url: str) -> tuple:
        """iframe 페이지에 접근하여 네트워크 로그 중 adaptive.mpd URL과 헤더, 쿠키를 추출합니다."""
        print(f"  🔍 MPD 스트리밍 주소 탐색 중...")
        self.driver.get(iframe_url)
        time.sleep(3)  # 재생 준비 대기

        mpd_url = None
        logs = self.driver.get_log("performance")

        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
                if message["method"] == "Network.requestWillBeSent":
                    url = message["params"]["request"]["url"]
                    if "adaptive.mpd" in url:
                        mpd_url = url
                        break
            except Exception:
                continue

        cookies = self.driver.get_cookies()
        user_agent = self.driver.execute_script("return navigator.userAgent;")
        
        headers = {"User-Agent": user_agent}
        return mpd_url, headers, cookies

    def close(self):
        self.driver.quit()


# ==============================================================================
# 3. Target URL(MPD)을 통해 동영상을 다운로드하고 합성하는 Class
# ==============================================================================
class KakaoMpdDownloader:
    def __init__(
        self,
        mpd_url: str,
        headers: dict = None,
        cookies: list = None,
        output_filename: str = "output.mp4",
    ):
        self.mpd_url = mpd_url
        self.headers = headers or {}
        self.cookies = cookies or []
        self.output_filename = output_filename

        self.v_dir = "v_t0_mp4_1920_1080_4M_T1"
        self.a_dir = "a_t1_96-44100"

    def _build_req_headers(self):
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in self.cookies])
        return {
            "User-Agent": self.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            ),
            "Referer": "https://tv.kakao.com/",
            "Origin": "https://tv.kakao.com",
            "Cookie": cookie_str,
        }

    def _download_track(self, track_name, track_dir, output_path, req_headers, base_url, query_string):
        print(f"  [1/3] {track_name} 다운로드 진행...")
        with output_path.open("wb") as f:
            # init.m4s
            init_url = f"{base_url}{track_dir}/init.m4s{query_string}"
            r_init = requests.get(init_url, headers=req_headers)
            if r_init.status_code != 200:
                print(f"  ❌ {track_name} init 받기 실패 (상태: {r_init.status_code})")
                return False
            f.write(r_init.content)

            # 세그먼트 순차 수집
            idx = 1
            while True:
                seg_name = f"{idx:06d}.m4s"
                seg_url = f"{base_url}{track_dir}/{seg_name}{query_string}"
                r_seg = requests.get(seg_url, headers=req_headers)

                if r_seg.status_code != 200:
                    print(f"\n  -> {track_name} 총 {idx - 1}개 조각 수집 완료!")
                    break

                f.write(r_seg.content)
                print(
                    f"\r  -> {track_name} 조각 {seg_name} 수집 중...",
                    end="",
                    flush=True,
                )
                idx += 1
        return True

    def download(self):
        if not self.mpd_url:
            print("❌ MPD 주소가 없어 다운로드를 진행할 수 없습니다.")
            return False

        req_headers = self._build_req_headers()

        base_url = self.mpd_url.split("adaptive.mpd")[0]
        query_string = (
            f"?{self.mpd_url.split('?', 1)[1]}" if "?" in self.mpd_url else ""
        )

        temp_v = Path("temp_v.m4s")
        temp_a = Path("temp_a.m4s")

        v_ok = self._download_track(
            "비디오", self.v_dir, temp_v, req_headers, base_url, query_string
        )
        a_ok = self._download_track(
            "오디오", self.a_dir, temp_a, req_headers, base_url, query_string
        )

        if v_ok and a_ok:
            print(f"\n  [2/3] FFmpeg 합성 진행 중...")
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                "temp_v.m4s",
                "-i",
                "temp_a.m4s",
                "-c",
                "copy",
                self.output_filename,
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 임시 파일 삭제
            temp_v.unlink(missing_ok=True)
            temp_a.unlink(missing_ok=True)
            
            print(f"  ✅ [3/3] 변환 성공! -> {self.output_filename}\n")
            return True

        return False


# ==============================================================================
# 메인 실행 로직
# ==============================================================================
if __name__ == "__main__":
    print("📋 클립보드에 복사된 HTML을 분석합니다...")
    html_data = pyperclip.paste()

    # 1. HTML 추출
    extractor = DaumCafeExtractor()
    videos = extractor.extract_videos_with_titles(html_data)

    if not videos:
        print("\n⚠️ 추출된 동영상이 없습니다. 카페 HTML을 복사(Ctrl+C)했는지 확인해주세요!")
    else:
        print(f"\n✅ 총 {len(videos)}개의 동영상을 찾았습니다. 다운로드를 시작하겠습니다.\n")
        
        # 2. Selenium 탐색기 초기화
        finder = MpdUrlFinder()

        try:
            for item in videos:
                idx = item['index']
                title = item['title']
                iframe_url = item['iframe_url']
                output_filename = f"{title}.mp4"

                print("=" * 70)
                print(f"[{idx}/{len(videos)}] 제목: {title}")
                print(f"🎬 파일명: {output_filename}")

                # 3. Selenium으로 MPD 스트리밍 주소 파싱
                mpd_url, headers, cookies = finder.find_mpd_url(iframe_url)

                if not mpd_url:
                    print("  ❌ MPD URL을 찾는 데 실패했습니다. 다음 영상으로 넘어갑니다.")
                    continue

                # 4. m4s 분할 파일 다운로드 및 FFmpeg mp4 변환 실행
                downloader = KakaoMpdDownloader(
                    mpd_url=mpd_url,
                    headers=headers,
                    cookies=cookies,
                    output_filename=output_filename
                )
                downloader.download()

        finally:
            finder.close()

        print("🎉 모든 동영상 작업이 종료되었습니다!")