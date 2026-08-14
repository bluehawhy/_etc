import os
import cv2
import numpy as np
import pandas as pd

# ==============================================================================
# 공통 유틸리티 함수: CSV 안전 로드
# ==============================================================================
def load_csv_safely(file_path: str) -> pd.DataFrame:
    """다양한 인코딩을 고려하여 CSV 파일을 안전하게 로드"""
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            print(f"✅ CSV 로드 성공 (인코딩: {enc})")
            return df
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"❌ 파일 인코딩을 읽을 수 없습니다: {file_path}")


# ==============================================================================
# [기능 1] 스크린샷 이미지 내 유도선 색상 검사 기능 (단독 실행 가능)
# ==============================================================================
def check_color_in_image(
    image_path: str, color_threshold: float = 0.05, crop_size: int = 100
) -> bool:
    """어두운 환경/밝은 파스텔 유도선까지 검사하되, 도로(아스팔트) 위 색상만 검출하여 지도 그래픽 오탐지 방지"""
    if not os.path.exists(image_path):
        print(f"⚠️ 이미지를 찾을 수 없음: {image_path}")
        return False

    try:
        img_array = np.fromfile(image_path, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"⚠️ 이미지 로드 오류 [{image_path}]: {e}")
        return False

    if img is None:
        return False

    # 1. 중앙 100x100 영역 크롭
    h, w = img.shape[:2]
    center_y, center_x = h // 2, w // 2
    half_size = crop_size // 2

    startY = max(0, center_y - half_size)
    endY = min(h, center_y + half_size)
    startX = max(0, center_x - half_size)
    endX = min(w, center_x + half_size)

    cropped_img = img[startY:endY, startX:endX]
    hsv = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2HSV)

    # ----------------------------------------------------
    # 2. HSV 유도선 색상 범위 (밝은색 + 어두운색)
    # ----------------------------------------------------
    # 2-A. 분홍~어두운 자주~밝은 핫핑크/연분홍
    lower_pink = np.array([140, 15, 30])
    upper_pink = np.array([179, 255, 255])

    # 2-B. 어두운 적갈색~밝은 진홍색
    lower_dark_red = np.array([0, 15, 30])
    upper_dark_red = np.array([15, 255, 255])

    # 2-C. 청록~밝은 민트~연두색
    lower_cyan = np.array([70, 15, 30])
    upper_cyan = np.array([105, 255, 255])

    # 마스크 생성 및 병합
    mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
    mask_dark_red = cv2.inRange(hsv, lower_dark_red, upper_dark_red)
    mask_cyan = cv2.inRange(hsv, lower_cyan, upper_cyan)

    combined_color_mask = cv2.bitwise_or(mask_pink, mask_dark_red)
    combined_color_mask = cv2.bitwise_or(combined_color_mask, mask_cyan)

    # ----------------------------------------------------
    # 3. [추가] 도로(아스팔트 회색/검은색) 영역 필터링
    # ----------------------------------------------------
    # 도로 특성: 채도가 낮고(S: 0~60), 명도가 적당히 어두움(V: 20~130)
    lower_road = np.array([0, 0, 20])
    upper_road = np.array([180, 60, 130])
    road_mask = cv2.inRange(hsv, lower_road, upper_road)

    # 도로 영역을 픽셀 단위로 넓혀서(Dilate) 유도선 바로 옆에 도로가 인접해 있는지 확인
    kernel = np.ones((5, 5), np.uint8)
    road_dilated = cv2.dilate(road_mask, kernel, iterations=2)

    # 도로 바닥 영역과 겹쳐있는 유도선 색상만 최종 인정
    final_mask = cv2.bitwise_and(combined_color_mask, road_dilated)

    # ----------------------------------------------------
    # 4. 감지 비율 계산
    # ----------------------------------------------------
    color_pixel_count = cv2.countNonZero(final_mask)
    total_pixels = cropped_img.shape[0] * cropped_img.shape[1]

    if total_pixels == 0:
        return False

    color_ratio = (color_pixel_count / total_pixels) * 100

    return color_ratio >= color_threshold

def process_screenshot_colors(csv_path: str, image_dir: str, output_path: str):
    """CSV 내 스크린샷 이미지들을 검사하여 색상 감지 시 'O', 미감지 시 'X' 기록"""
    print("\n📸 [기능 1] 스크린샷 이미지 유도선 색상 검사 시작...")
    df = load_csv_safely(csv_path)

    if "작성여부" not in df.columns:
        df["작성여부"] = ""

    for idx, row in df.iterrows():
        img_name = str(row.get("스크린샷", "")).strip()

        if img_name and img_name.lower() != "nan":
            img_full_path = os.path.join(image_dir, img_name)
            has_color = check_color_in_image(img_full_path)

            if has_color:
                df.at[idx, "작성여부"] = "O"
                print(f"  ✅ [{img_name}] 색상 감지 -> 'O' 입력")
            else:
                df.at[idx, "작성여부"] = "X"
                print(f"  ❌ [{img_name}] 색상 미감지 -> 'X' 입력")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"🎉 스크린샷 검사 완료! 결과 저장: {output_path}")


# ==============================================================================
# [기능 2] 'O' 기준 50m 이내 미검토 건 'x' 자동 채우기 기능 (단독 실행 가능)
# ==============================================================================
def process_distance_fill(csv_path: str, output_path: str, radius_m: float = 50.0):
    """이미 'O'로 표시된 좌표 기준으로 N미터 이내의 빈 항목들을 'x'로 자동 채움"""
    print(f"\n📏 [기능 2] 'O' 지점 기준 {radius_m}m 이내 미검토 건 'x' 채우기 시작...")
    df = load_csv_safely(csv_path)

    if "작성여부" not in df.columns:
        df["작성여부"] = ""

    # 작성여부 값 정리 및 'O' 지점 추출
    df["작성여부_clean"] = df["작성여부"].fillna("").astype(str).str.strip().str.upper()
    o_points = df[df["작성여부_clean"] == "O"][["X좌표", "Y좌표"]].to_numpy()

    if len(o_points) > 0:
        empty_mask = df["작성여부_clean"] == ""
        filled_count = 0

        for idx in df[empty_mask].index:
            current_pt = df.loc[idx, ["X좌표", "Y좌표"]].to_numpy()

            # 미터 단위 직선 거리 계산
            distances = np.linalg.norm(o_points - current_pt, axis=1)

            # 반경 이내에 'O' 지점이 존재하면 'x' 처리
            if np.any(distances <= radius_m):
                df.at[idx, "작성여부"] = "x"
                filled_count += 1

        print(f"  ✅ {radius_m}m 이내 미검토 건 {filled_count}개 'x' 채우기 완료!")
    else:
        print("  ⚠️ 'O'로 표시된 지점이 없어 거리 검사를 진행하지 않았습니다.")

    # 임시 정리용 컬럼 제거 후 저장
    df.drop(columns=["작성여부_clean"], errors="ignore", inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"🎉 거리 검사 완료! 결과 저장: {output_path}")


# ==============================================================================
# 실행 블록 (원하는 기능의 주석을 해제하거나 별도로 호출)
# ==============================================================================
if __name__ == "__main__":
    CSV_INPUT = r"C:\Users\miskang\Downloads\서울특별시_노면색깔유도선 위치 현황_20250417_WGS84.csv"
    IMAGE_DIR = r"C:\Users\miskang\Downloads\색상유도선"

    # 색상유도선만 먼저 체크
    #ch_result = check_color_in_image(image_path=os.path.join(IMAGE_DIR,'Screenshot_20260814_030456.png'),color_threshold=0.05)
    #print(ch_result)
    
    # ----------------------------------------------------
    # 실행 방법 1: 스크린샷 이미지 색상 검사만 실행하고 싶을 때
    # ----------------------------------------------------
    process_screenshot_colors(
        csv_path=CSV_INPUT,
        image_dir=IMAGE_DIR,
        output_path=r"C:\Users\miskang\Downloads\결과_스크린샷검사.csv"
    )

    # ----------------------------------------------------
    # 실행 방법 2: 50m 이내 거리 비교 'x' 채우기만 실행하고 싶을 때
    # ----------------------------------------------------
    #process_distance_fill(
    #    csv_path=CSV_INPUT,
    #    output_path=r"C:\Users\miskang\Downloads\결과_50m거리검토.csv",
    #    radius_m=50.0
    #)