import os
import cv2
import numpy as np
import pandas as pd

import shutil
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
    image_path: str, color_threshold: float = 0.3, crop_size: int = 200
) -> bool:
    """정확한 중앙 좌표(X: 540, Y: 1170) 기준으로 +-100px 영역만 크롭하여 검사"""
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

    # ----------------------------------------------------
    # 1. 정확한 중앙 ROI(관심영역) 좌표 계산 (1080x2340 대응)
    # ----------------------------------------------------
    height, width = img.shape[:2]  # height = 2340, width = 1080

    center_y = height // 2  # 1170
    center_x = width // 2  # 540
    half_size = crop_size // 2  # 100

    # Y축(세로): 1070 ~ 1270, X축(가로): 440 ~ 640
    startY = max(0, center_y - half_size)
    endY = min(height, center_y + half_size)
    startX = max(0, center_x - half_size)
    endX = min(width, center_x + half_size)

    # NumPy 슬라이싱: img[Y범위, X범위] -> 정확한 중앙 200x200 추출
    cropped_img = img[startY:endY, startX:endX]

    # [디버깅용 옵션] 오려낸 중앙 이미지가 맞는지 눈으로 확인하고 싶다면 주석 해제
    #cv2.imwrite("debug_crop.png", cropped_img)

    hsv = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2HSV)

    # ----------------------------------------------------
    # 2. 유도선 HSV 범위 설정
    # ----------------------------------------------------
    # 분홍~핫핑크
    lower_pink, upper_pink = np.array([140, 30, 40]), np.array([175, 255, 255])
    # 청록~민트
    lower_cyan, upper_cyan = np.array([75, 30, 40]), np.array([105, 255, 255])

    mask_pink = cv2.inRange(hsv, lower_pink, upper_pink)
    mask_cyan = cv2.inRange(hsv, lower_cyan, upper_cyan)
    combined_color_mask = cv2.bitwise_or(mask_pink, mask_cyan)

    # ----------------------------------------------------
    # 3. 도로(아스팔트 회색) 바닥 영역 필터링
    # ----------------------------------------------------
    lower_road, upper_road = np.array([0, 0, 30]), np.array([180, 40, 110])
    road_mask = cv2.inRange(hsv, lower_road, upper_road)

    kernel = np.ones((5, 5), np.uint8)
    road_dilated = cv2.dilate(road_mask, kernel, iterations=2)

    # 도로 위 유도선만 최종 인가
    final_mask = cv2.bitwise_and(combined_color_mask, road_dilated)

    # ----------------------------------------------------
    # 4. 판별 비율 계산
    # ----------------------------------------------------
    color_pixel_count = cv2.countNonZero(final_mask)
    total_pixels = cropped_img.shape[0] * cropped_img.shape[1]

    if total_pixels == 0:
        return False

    color_ratio = (color_pixel_count / total_pixels) * 100

    return color_ratio >= color_threshold


import os
import shutil


def process_screenshot_colors(csv_path: str, image_dir: str, output_path: str):
    """CSV 내 스크린샷 이미지들을 검사하여 색상 감지 시 'O', 미감지 시 'X' 기록 및 미감지 이미지를 '미감지' 폴더로 이동"""
    print("\n📸 [기능 1] 스크린샷 이미지 유도선 색상 검사 시작...")
    df = load_csv_safely(csv_path)
    column_name = "색상 검수"

    # 미감지 이미지를 모아둘 하위 폴더 생성
    unmothered_dir = os.path.join(image_dir, "미감지")
    os.makedirs(unmothered_dir, exist_ok=True)

    if column_name not in df.columns:
        df[column_name] = ""

    df[column_name] = df[column_name].astype(object)
    for idx, row in df.iterrows():
        img_name = str(row.get("스크린샷", "")).strip()

        if img_name and img_name.lower() != "nan":
            img_full_path = os.path.join(image_dir, img_name)
            has_color = check_color_in_image(img_full_path)

            if has_color:
                df.at[idx, column_name] = "O"
                print(f"  ✅ [{img_name}] 색상 감지 -> 'O' 입력")
            else:
                df.at[idx, column_name] = "X"
                print(f"  ❌ [{img_name}] 색상 미감지 -> 'X' 입력")

                # ----------------------------------------------------
                # [추가] 미감지 파일 이동 로직
                # ----------------------------------------------------
                if os.path.exists(img_full_path):
                    target_path = os.path.join(unmothered_dir, img_name)
                    shutil.move(
                        img_full_path, target_path
                    )  # 원본에서 이동 (복사를 원하시면 shutil.copy2 사용)
                    print(f"     └─ 📁 '미감지' 폴더로 이동 완료: {img_name}")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n🎉 스크린샷 검사 완료! 결과 저장: {output_path}")


# ==============================================================================
# [기능 2] 'O' 기준 50m 이내 미검토 건 'x' 자동 채우기 기능 (단독 실행 가능)
# ==============================================================================
def process_distance_fill(csv_path: str, output_path: str, radius_m: float = 50.0):
    """이미 'O'로 표시된 좌표 기준으로 N미터 이내의 빈 항목들을 'x'로 자동 채움"""
    print(f"\n📏 [기능 2] 'O' 지점 기준 {radius_m}m 이내 미검토 건 'x' 채우기 시작...")
    df = load_csv_safely(csv_path)
    column_name = '거리비교'

    if column_name not in df.columns:
        df[column_name] = ""

    # 작성여부 값 정리 및 'O' 지점 추출
    df[f"{column_name}_clean"] = df[column_name].fillna("").astype(str).str.strip().str.upper()
    o_points = df[df[f"{column_name}_clean"] == "O"][["X좌표", "Y좌표"]].to_numpy()

    if len(o_points) > 0:
        empty_mask = df[f"{column_name}_clean"] == ""
        filled_count = 0

        for idx in df[empty_mask].index:
            current_pt = df.loc[idx, ["X좌표", "Y좌표"]].to_numpy()

            # 미터 단위 직선 거리 계산
            distances = np.linalg.norm(o_points - current_pt, axis=1)

            # 반경 이내에 'O' 지점이 존재하면 'x' 처리
            if np.any(distances <= radius_m):
                df.at[idx, column_name] = "x"
                filled_count += 1

        print(f"  ✅ {radius_m}m 이내 미검토 건 {filled_count}개 'x' 채우기 완료!")
    else:
        print("  ⚠️ 'O'로 표시된 지점이 없어 거리 검사를 진행하지 않았습니다.")

    # 임시 정리용 컬럼 제거 후 저장
    df.drop(columns=[f"{column_name}_clean"], errors="ignore", inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"🎉 거리 검사 완료! 결과 저장: {output_path}")



import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN


def load_csv_safely(file_path: str) -> pd.DataFrame:
  """인코딩 방식(utf-8-sig / cp949)에 맞춰 CSV 읽기"""
  try:
    return pd.read_csv(file_path, encoding='utf-8-sig')
  except UnicodeDecodeError:
    return pd.read_csv(file_path, encoding='cp949')


def group_and_sort_by_distance(
    csv_path: str,
    output_path: str,
    radius_m: float = 50.0,
    lat_col: str = '위도',  # 37.xxx 값 있는 컬럼
    lng_col: str = '경도',  # 126~127.xxx 값 있는 컬럼
):
  """50m 반경 내 좌표들을 동일한 그룹으로 묶고 정렬"""
  print(f'\n📍 [{lat_col}], [{lng_col}] 기준 {radius_m}m 이내 그룹화 및 정렬 시작...')
  df = load_csv_safely(csv_path)

  # 좌표값 결측치 제외 처리
  valid_coords_mask = df[lat_col].notnull() & df[lng_col].notnull()
  coords_df = df[valid_coords_mask][[lat_col, lng_col]].copy()

  # 1. 위도/경도를 라디안 단위로 변환
  coords_rad = np.radians(coords_df[[lat_col, lng_col]].to_numpy())

  # 2. 지구 반지름(6,371,000m) 기준 50m에 해당하는 라디안 값
  earth_radius_m = 6371000.0
  epsilon = radius_m / earth_radius_m

  # 3. DBSCAN (Haversine 공식 적용)
  db = DBSCAN(eps=epsilon, min_samples=1, metric='haversine')
  clusters = db.fit_predict(coords_rad)

  # 4. 데이터프레임에 그룹 결과 반영
  df['Group_ID'] = -1
  df.loc[valid_coords_mask, 'Group_ID'] = clusters

  # 그룹별 포함된 데이터 개수 파악
  group_counts = df['Group_ID'].value_counts()
  df['Group_Size'] = df['Group_ID'].map(group_counts)

  # 5. 그룹 ID 순서로 데이터 정렬 (인접한 지점끼리 뭉치게 됨)
  df.sort_values(by=['Group_ID'], ascending=True, inplace=True)
  df.reset_index(drop=True, inplace=True)

  # 결과 통계
  total_count = len(df)
  total_groups = df['Group_ID'].nunique()
  multi_item_groups = (df['Group_Size'] > 1).sum()

  print(f' ✅ 그룹화 완료!')
  print(f' 📊 총 데이터: {total_count}개')
  print(f' 📊 생성된 위치 그룹: {total_groups}개')
  print(f' 📊 50m 이내에 다른 데이터와 묶인 데이터: {multi_item_groups}개')

  # 저장
  df.to_csv(output_path, index=False, encoding='utf-8-sig')
  print(f'🎉 정렬 완료! 저장 파일: {output_path}')


if __name__ == '__main__':
  CSV_INPUT = r'C:\Users\miskang\Downloads\노면색깔유도선_WGS84_부산.csv'
  CSV_OUTPUT = (
      r'C:\Users\miskang\Downloads\노면색깔유도선_WGS84_부산_위치별정리.csv'
  )

  group_and_sort_by_distance(
      csv_path=CSV_INPUT,
      output_path=CSV_OUTPUT,
      radius_m=50.0,
      lat_col='위도',
      lng_col='경도',
  )


    # 색상유도선만 먼저 체크
    #ch_result = check_color_in_image(
    #    image_path=os.path.join(IMAGE_DIR,'Screenshot_20260813_182438.png'),
    #    color_threshold=0.05)
    #print(ch_result)
    
    # ----------------------------------------------------
    # 실행 방법 1: 스크린샷 이미지 색상 검사만 실행하고 싶을 때
    # ----------------------------------------------------
    #process_screenshot_colors(
    #    csv_path=CSV_INPUT,
    #    image_dir=IMAGE_DIR,
    #    output_path=r"D:\project\NKM\NKM_부산색상유도선\노면색깔유도선_WGS84_부산_검수.csv"
    #)