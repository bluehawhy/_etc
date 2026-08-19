import os
import time
from PIL import Image
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class KakaoSkyviewCapturer:

  def __init__(self, headless=False):
    chrome_options = Options()
    chrome_options.add_argument("--start-fullscreen")

    if headless:
      chrome_options.add_argument("--headless=new")

    self.driver = webdriver.Chrome(options=chrome_options)
    print("브라우저 드라이버 시작 완료")

  def _hide_ui(self):
    """사이드바 및 불필요한 UI 숨기기"""
    self.driver.execute_script("""
            var sidebar = document.getElementById('sidebar');
            if(sidebar) sidebar.style.display = 'none';
            var view = document.getElementById('view');
            if(view) view.style.left = '0px';
        """)

  def _find_zoom_button(self):
    """페이지 이동 시마다 확대 버튼을 매번 새로 찾음 (Stale Element 방지)"""
    selectors = [
        (By.CLASS_NAME, "btn_zoom_in"),
        (By.CSS_SELECTOR, "button.ico_btn.ico_plus"),
        (By.XPATH, "//button[contains(@class, 'zoom_in')]"),
        (By.XPATH, "//button[contains(@title, '확대')]"),
    ]

    for by_type, selector in selectors:
      try:
        btn = self.driver.find_element(by_type, selector)
        if btn.is_displayed():
          return btn
      except Exception:
        continue
    return None

  def _apply_max_zoom(self):
    """최대 확대 조작 실행"""
    btn = self._find_zoom_button()
    if btn:
      for _ in range(5):
        self.driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.3)
    else:
      # 버튼을 못 찾았을 경우 마우스 휠 이벤트로 대처
      self.driver.execute_script("""
                var canvas = document.querySelector('canvas');
                if(canvas) {
                    var evt = new WheelEvent('wheel', {
                        deltaY: -1000,
                        clientX: window.innerWidth / 2,
                        clientY: window.innerHeight / 2,
                        bubbles: true
                    });
                    for(var i=0; i<5; i++) { canvas.dispatchEvent(evt); }
                }
            """)

  # ─── 들여쓰기 수정 위치 ──────────────────────────────
  def capture(
      self,
      lat,
      lng,
      save_path,
      crop_size=None,  # 기본값 None (전체 화면)
      wait_time=3,
  ):
    try:
      # 1. 좌표 URL 이동
      url = f"https://map.kakao.com/?map_type=TYPE_SKYVIEW&map_hybrid=true&q={lat}%2C{lng}&urlLevel=1"
      self.driver.get(url)

      # 2. 로딩 대기
      WebDriverWait(self.driver, 10).until(
          EC.presence_of_element_located((By.TAG_NAME, "body"))
      )
      time.sleep(wait_time)

      # 3. UI 정리 및 확대
      self._hide_ui()
      self._apply_max_zoom()
      time.sleep(1.5)  # 확대 완료 및 타일 로딩 대기

      # 4. 스크린샷 및 크롭 처리
      if crop_size is None:
        # 전체 화면 캡처 저장
        self.driver.save_screenshot(save_path)
      else:
        # 크롭 처리 후 저장
        temp_path = "temp_capture.png"
        self.driver.save_screenshot(temp_path)

        img = Image.open(temp_path)
        width, height = img.size

        crop_w, crop_h = crop_size
        left = (width - crop_w) / 2
        top = (height - crop_h) / 2
        right = (width + crop_w) / 2
        bottom = (height + crop_h) / 2

        cropped_img = img.crop((left, top, right, bottom))
        cropped_img.save(save_path)

        if os.path.exists(temp_path):
          os.remove(temp_path)

      print(f"[{lat}, {lng}] -> '{save_path}' 저장 완료")

    except Exception as e:
      print(f"[{lat}, {lng}] 작업 중 오류 발생: {e}")

  def close(self):
    if self.driver:
      self.driver.quit()
      print("브라우저 종료 완료")



# ==========================================
# CSV 파일 처리 및 자동 배치 실행
# ==========================================
def process_uncaptured_images(csv_path, output_dir):
  os.makedirs(output_dir, exist_ok=True)

  try:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
  except UnicodeDecodeError:
    df = pd.read_csv(csv_path, encoding="cp949")

  target_df = df[df["작성여부"].str.upper() == "X"]
  print(f"총 {len(df)}개 항목 중 대상(작성여부 X): {len(target_df)}개")

  if target_df.empty:
    print("처리할 대상이 없습니다.")
    return

  capturer = KakaoSkyviewCapturer()

  try:
    for idx, (_, row) in enumerate(target_df.iterrows(), start=1):
      lat = row["위도"]
      lng = row["경도"]
      orig_filename = str(row["스크린샷"])

      base_name, _ = os.path.splitext(orig_filename)
      new_filename = f"{base_name}_kakaomap.png"
      save_full_path = os.path.join(output_dir, new_filename)

      # 이미 다운로드된 파일은 이어받기(Skip) 처리
      if os.path.exists(save_full_path):
        print(
            f"[{idx}/{len(target_df)}] 이미 존재함 (Pass): {new_filename}"
        )
        continue

      print(f"[{idx}/{len(target_df)}] 진행 중...", end=" ")
      capturer.capture(
          lat=lat,
          lng=lng,
          save_path=save_full_path,
          #crop_size=(800, 600),
      )

  finally:
    capturer.close()


if __name__ == "__main__":
  # 설정 경로
  CSV_FILE_PATH = r"C:\Users\miskang\Downloads\결과_스크린샷검사.csv"
  #r"D:\project\NKM\NKM_부산색상유도선\노면색깔유도선_WGS84_부산_검수.csv"
  OUTPUT_DIRECTORY = r'C:\Users\miskang\Downloads\색상유도선'
  #r"D:\project\NKM\NKM_부산색상유도선\미감지"

  # 실행
  process_uncaptured_images(CSV_FILE_PATH, OUTPUT_DIRECTORY)