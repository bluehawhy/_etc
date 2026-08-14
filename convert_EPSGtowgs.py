import pandas as pd
from pyproj import Transformer

# 1. CSV 파일 불러오기 (한글 인코딩 cp949 적용)
file_path = r"C:/Users/miskang/Downloads/서울특별시_노면색깔유도선 위치 현황_20250417.csv"
df = pd.read_csv(file_path, encoding="cp949")

# 2. EPSG:5186 -> EPSG:4326 변환기 정의
transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

# 3. X, Y 좌표를 경도(Lon), 위도(Lat)로 일괄 변환
df["경도"], df["위도"] = transformer.transform(
    df["X좌표"].values, df["Y좌표"].values
)

# 4. 마지막 컬럼에 '좌표값' 헤딩으로 위도, 경도 값만 합성
df["좌표값"] = df.apply(lambda row: f"{row['위도']}, {row['경도']}", axis=1)

# 5. 저장 (Excel/한글 지원을 위해 utf-8-sig 사용)
output_path = r"C:/Users/miskang/Downloads/노면색깔유도선_WGS84.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print("✅ 좌표 변환 및 '좌표값' 컬럼 추가 완료!")