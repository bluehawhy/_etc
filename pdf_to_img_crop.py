import os
from pdf2image import convert_from_path
from PIL import Image

def pdf_to_cropped_images(
    pdf_path: str,
    output_dir: str = "output_images",
    dpi: int = 300,
    page_numbers: list = None,
    crop_box: tuple = None,
    poppler_path: str = None
):
    """
    PDF를 이미지로 변환하고 선택적으로 크롭(Crop)하는 함수

    :param pdf_path: 변환할 PDF 파일 경로
    :param output_dir: 저장할 이미지 폴더 경로
    :param dpi: 해상도 (기본 300 DPI, 높은 화질)
    :param page_numbers: 변환할 페이지 번호 리스트 (예: [1] 은 1페이지, None이면 전체)
    :param crop_box: 크롭 영역 튜플 (left, upper, right, lower) - 픽셀 단위
                     예: (0, 0, 1000, 1000) -> 왼쪽 위 좌표(0,0)부터 우하단(1000,1000)까지
    :param poppler_path: Windows 환경에서 Poppler bin 폴더 경로 (필요시 지정)
    """
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    print(f"📄 PDF 변환 중: {pdf_path}")
    
    # 1. PDF를 PIL Image 객체 리스트로 변환
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_numbers[0] if page_numbers else None,
        last_page=page_numbers[-1] if page_numbers else None,
        poppler_path=poppler_path
    )

    for idx, img in enumerate(images):
        page_num = page_numbers[idx] if page_numbers else idx + 1
        
        # 2. 크롭(Crop) 처리 (crop_box 지정된 경우)
        if crop_box:
            # img.crop((left, upper, right, lower))
            img = img.crop(crop_box)
            print(f"  └ ✂️ {page_num}페이지 크롭 완료 (범위: {crop_box})")

        # 3. 이미지 저장
        output_filename = f"page_{page_num}.png"
        output_path = os.path.join(output_dir, output_filename)
        img.save(output_path, "PNG")
        print(f"  └ 💾 저장 완료: {output_path}")

    print("✨ 모든 작업이 완료되었습니다!")

# ==========================================
# 사용 예제
# ==========================================
if __name__ == "__main__":
    import fitz  # PyMuPDF

    pdf_path = r"C:\Users\ssdef\Downloads\JEJU_MAP_KOREAN.pdf" 
    doc = fitz.open(pdf_path)

    for i, page in enumerate(doc):
        # 이미지 해상도 설정 (zoom_x, zoom_y가 2.0이면 약 150-200 DPI 수준)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        
        # 이미지 저장
        pix.save(f"page_{i + 1}.png")

    doc.close()
    #PDF_FILE = r"C:\Users\ssdef\Downloads\JEJU_MAP_KOREAN.pdf"  # 변환할 PDF 경로
    #
    ## Windows 사용자 중 Poppler 환경변수를 안 잡았을 경우 아래 경로 지정:
    #POPPLER_PATH = r"C:\path\to\poppler-xx\Library\bin"
    #POPPLER_PATH = None 
#
    ## 예제 1: 1페이지 원본 전체를 300 DPI 이미지로 변환
    #pdf_to_cropped_images(
    #    pdf_path=PDF_FILE,
    #    output_dir="converted_full",
    #    dpi=300,
    #    page_numbers=[1],
    #    poppler_path=POPPLER_PATH
    #)
#
    ## 예제 2: 1페이지를 변환 후 특정 영역만 크롭
    ## (300 DPI 기준 A4 크기는 약 2480 x 3508 픽셀입니다)
    ## (left, upper, right, lower) 픽셀 좌표 지정
    #CROP_AREA = (0, 0, 1200, 1200) # 좌상단 1200x1200 영역 자르기
    #
    #pdf_to_cropped_images(
    #    pdf_path=PDF_FILE,
    #    output_dir="converted_cropped",
    #    dpi=300,
    #    page_numbers=[1],
    #    crop_box=CROP_AREA,
    #    poppler_path=POPPLER_PATH
    #)