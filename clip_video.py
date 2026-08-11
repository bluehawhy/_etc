from moviepy.video.io.VideoFileClip import VideoFileClip

def trim_video(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    input_path: 원본 영상 파일 경로
    output_path: 저장할 자른 영상 경로
    start_time: 시작 시간 (초 단위 또는 "00:01:30" 형태 문자열)
    end_time: 종료 시간 (초 단위 또는 "00:02:15" 형태 문자열)
    """
    print("영상 자르는 중...")
    with VideoFileClip(input_path) as video:
        # 지정한 시간 구간만 추출
        new_video = video.subclipped(start_time, end_time)
        # 파일 저장
        new_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
    print("완료되었습니다!")

# 사용 예시 (1분 30초 ~ 2분 45초 구간 자르기)
trim_video(
    "백창우 아저씨네 노래창고 - 10 울보 자숙이.mp4",
    "강아지꽃.mp4", 
    "00:29:25", 
    "00:31:39")