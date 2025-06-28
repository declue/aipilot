import logging
import os
import sys
import time
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

try:
    import ffmpeg
    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False
    print("ffmpeg-python 라이브러리가 설치되지 않았습니다. 'pip install ffmpeg-python'로 설치하세요.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL 라이브러리가 설치되지 않았습니다. 'pip install pillow'로 설치하세요.")

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 video_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "video_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("VIDEO_TOOL_LOG_LEVEL", "WARNING").upper()
log_level_int = getattr(logging, log_level, logging.WARNING)

logging.basicConfig(
    level=log_level_int,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path),
              logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# INFO 레벨 로그는 환경 변수가 DEBUG나 INFO로 설정된 경우에만 출력
if log_level_int <= logging.INFO:
    logger.info("Video Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
    logger.info("운영체제: %s", sys.platform)
    logger.info("ffmpeg-python 사용 가능: %s", FFMPEG_PYTHON_AVAILABLE)
    logger.info("PIL 사용 가능: %s", PIL_AVAILABLE)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Video Analysis Server",
    description="A server for video analysis operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

class VideoAnalysisService:
    """비디오 분석 기능을 제공하는 서비스 클래스"""

    def __init__(self):
        """VideoAnalysisService 초기화"""
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()
        self._check_ffmpeg_installed()

    def _check_dependencies(self):
        """필요한 라이브러리가 설치되어 있는지 확인"""
        if not FFMPEG_PYTHON_AVAILABLE:
            self.logger.error("ffmpeg-python 라이브러리가 설치되지 않았습니다.")
        if not PIL_AVAILABLE:
            self.logger.error("PIL 라이브러리가 설치되지 않았습니다.")

    def _check_ffmpeg_installed(self):
        """시스템에 ffmpeg가 설치되어 있는지 확인"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("ffmpeg 설치 확인: 성공")
                self.ffmpeg_installed = True
            else:
                self.logger.error("ffmpeg가 시스템에 설치되어 있지 않습니다.")
                self.ffmpeg_installed = False
        except FileNotFoundError:
            self.logger.error("ffmpeg가 시스템에 설치되어 있지 않습니다.")
            self.ffmpeg_installed = False

    def get_video_metadata(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        비디오 파일의 모든 메타데이터를 가져옵니다.
        
        Args:
            video_path (str): 비디오 파일 경로
            
        Returns:
            Optional[Dict[str, Any]]: 비디오 메타데이터. 실패 시 None 반환.
        """
        if not os.path.exists(video_path):
            self.logger.error(f"비디오 파일이 존재하지 않습니다: {video_path}")
            return None
            
        if not self.ffmpeg_installed:
            self.logger.error("ffmpeg가 설치되어 있지 않아 메타데이터를 가져올 수 없습니다.")
            return None
            
        try:
            # ffprobe를 사용하여 비디오 메타데이터 가져오기
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"ffprobe 실행 중 오류 발생: {result.stderr}")
                return None
                
            metadata = json.loads(result.stdout)
            
            # 추가 정보 계산
            if 'format' in metadata and 'duration' in metadata['format']:
                duration_sec = float(metadata['format']['duration'])
                hours, remainder = divmod(duration_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                metadata['formatted_duration'] = f"{int(hours):02d}:{int(minutes):02d}:{seconds:.2f}"
            
            # 비디오 스트림 찾기
            video_stream = None
            audio_stream = None
            
            if 'streams' in metadata:
                for stream in metadata['streams']:
                    if stream.get('codec_type') == 'video' and not video_stream:
                        video_stream = stream
                    elif stream.get('codec_type') == 'audio' and not audio_stream:
                        audio_stream = stream
            
            # 요약 정보 추가
            summary = {}
            
            if 'format' in metadata:
                format_info = metadata['format']
                summary['filename'] = format_info.get('filename', '')
                summary['format_name'] = format_info.get('format_long_name', '')
                summary['size'] = format_info.get('size', '0')
                summary['duration'] = format_info.get('duration', '0')
                summary['bit_rate'] = format_info.get('bit_rate', '0')
            
            if video_stream:
                summary['video_codec'] = video_stream.get('codec_long_name', '')
                summary['width'] = video_stream.get('width', 0)
                summary['height'] = video_stream.get('height', 0)
                summary['fps'] = self._calculate_fps(video_stream)
                
            if audio_stream:
                summary['audio_codec'] = audio_stream.get('codec_long_name', '')
                summary['sample_rate'] = audio_stream.get('sample_rate', '')
                summary['channels'] = audio_stream.get('channels', 0)
            
            metadata['summary'] = summary
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"비디오 메타데이터 가져오기 중 오류 발생: {str(e)}")
            return None
    
    def _calculate_fps(self, video_stream: Dict[str, Any]) -> float:
        """
        비디오 스트림에서 FPS를 계산합니다.
        
        Args:
            video_stream (Dict[str, Any]): 비디오 스트림 정보
            
        Returns:
            float: 계산된 FPS
        """
        fps = 0.0
        
        # r_frame_rate 형식은 보통 "30000/1001"과 같음
        if 'r_frame_rate' in video_stream:
            try:
                num, den = video_stream['r_frame_rate'].split('/')
                fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass
        
        # avg_frame_rate도 확인
        if fps == 0.0 and 'avg_frame_rate' in video_stream:
            try:
                num, den = video_stream['avg_frame_rate'].split('/')
                if den != '0':  # 0으로 나누기 방지
                    fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass
        
        return fps
    
    def capture_frame(self, video_path: str, timestamp: float, output_path: str = None) -> Optional[Image.Image]:
        """
        비디오에서 특정 시간의 프레임을 캡처합니다.
        
        Args:
            video_path (str): 비디오 파일 경로
            timestamp (float): 캡처할 시간(초)
            output_path (str, optional): 이미지를 저장할 경로
            
        Returns:
            Optional[Image.Image]: 캡처된 이미지 객체. 실패 시 None 반환.
        """
        if not os.path.exists(video_path):
            self.logger.error(f"비디오 파일이 존재하지 않습니다: {video_path}")
            return None
            
        if not self.ffmpeg_installed:
            self.logger.error("ffmpeg가 설치되어 있지 않아 프레임을 캡처할 수 없습니다.")
            return None
            
        if not PIL_AVAILABLE:
            self.logger.error("PIL 라이브러리가 설치되어 있지 않아 이미지를 처리할 수 없습니다.")
            return None
            
        try:
            # 임시 파일 경로 생성
            temp_output = output_path
            if not temp_output:
                temp_dir = os.path.dirname(os.path.abspath(video_path))
                temp_output = os.path.join(temp_dir, f"frame_{int(timestamp)}_{int(time.time())}.jpg")
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(os.path.abspath(temp_output)), exist_ok=True)
            
            # ffmpeg 명령어로 프레임 추출
            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),  # 시작 시간
                "-i", video_path,       # 입력 파일
                "-vframes", "1",        # 1개 프레임만 추출
                "-q:v", "2",            # 품질 설정 (낮을수록 고품질)
                "-y",                   # 기존 파일 덮어쓰기
                temp_output
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"ffmpeg 실행 중 오류 발생: {result.stderr}")
                return None
                
            # 이미지 로드
            img = Image.open(temp_output)
            
            # 임시 파일 삭제 (output_path가 지정되지 않은 경우)
            if not output_path:
                try:
                    os.remove(temp_output)
                except:
                    pass
                
            self.logger.info(f"비디오 {video_path}에서 {timestamp}초 지점의 프레임을 캡처했습니다.")
            
            return img
            
        except Exception as e:
            self.logger.error(f"프레임 캡처 중 오류 발생: {str(e)}")
            return None

# 전역 서비스 인스턴스
_video_analysis_service = None

def _get_service() -> VideoAnalysisService:
    """
    VideoAnalysisService 인스턴스를 가져옵니다.
    
    Returns:
        VideoAnalysisService: 서비스 인스턴스
    """
    global _video_analysis_service
    if _video_analysis_service is None:
        _video_analysis_service = VideoAnalysisService()
    return _video_analysis_service

@app.tool()
def get_video_metadata(video_path: str) -> dict:
    """
    비디오 파일의 모든 메타데이터를 가져옵니다.
    
    Args:
        video_path (str): 비디오 파일 경로
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> get_video_metadata("/path/to/video.mp4")
        {'result': {'action': 'get_video_metadata', 'video_path': '/path/to/video.mp4', 'metadata': {...}, 'success': True}}
    """
    try:
        metadata = _get_service().get_video_metadata(video_path)
        
        if metadata is None:
            return {"error": f"비디오 메타데이터 가져오기 실패: {video_path}"}
            
        return {
            "result": {
                "action": "get_video_metadata",
                "video_path": video_path,
                "metadata": metadata,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"비디오 메타데이터 가져오기 중 오류 발생: {str(e)}"}

@app.tool()
def capture_frame(video_path: str, timestamp: float, output_path: str = None) -> dict:
    """
    비디오에서 특정 시간의 프레임을 캡처합니다.
    
    Args:
        video_path (str): 비디오 파일 경로
        timestamp (float): 캡처할 시간(초)
        output_path (str, optional): 이미지를 저장할 경로
        
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> capture_frame("/path/to/video.mp4", 10.5, "/path/to/frame.jpg")
        {'result': {'action': 'capture_frame', 'video_path': '/path/to/video.mp4', 'timestamp': 10.5, 'output_path': '/path/to/frame.jpg', 'success': True}}
    """
    try:
        frame = _get_service().capture_frame(video_path, timestamp, output_path)
        
        if frame is None:
            return {"error": f"프레임 캡처 실패: {video_path}, 시간: {timestamp}초"}
            
        return {
            "result": {
                "action": "capture_frame",
                "video_path": video_path,
                "timestamp": timestamp,
                "output_path": output_path if output_path else "이미지가 저장되지 않음",
                "success": True,
                "timestamp_captured": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"error": f"프레임 캡처 중 오류 발생: {str(e)}"}

@app.tool()
def get_tool_info() -> dict:
    """
    비디오 분석 도구 정보를 반환합니다.
    
    Returns:
        dict: 결과를 포함한 딕셔너리
        
    Examples:
        >>> get_tool_info()
        {'result': {'name': 'video_tool', 'description': '비디오 분석 기능을 제공하는 도구', ...}}
    """
    try:
        tool_info = {
            "name": "video_tool",
            "description": "비디오 분석 기능을 제공하는 도구",
            "version": "1.0.0",
            "author": "DS Pilot",
            "functions": [
                {
                    "name": "get_video_metadata",
                    "description": "비디오 파일의 모든 메타데이터를 가져옵니다.",
                    "parameters": [
                        {
                            "name": "video_path",
                            "type": "str",
                            "description": "비디오 파일 경로",
                            "required": True
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                },
                {
                    "name": "capture_frame",
                    "description": "비디오에서 특정 시간의 프레임을 캡처합니다.",
                    "parameters": [
                        {
                            "name": "video_path",
                            "type": "str",
                            "description": "비디오 파일 경로",
                            "required": True
                        },
                        {
                            "name": "timestamp",
                            "type": "float",
                            "description": "캡처할 시간(초)",
                            "required": True
                        },
                        {
                            "name": "output_path",
                            "type": "str",
                            "description": "이미지를 저장할 경로 (선택사항)",
                            "required": False
                        }
                    ],
                    "returns": {
                        "type": "dict",
                        "description": "결과를 포함한 딕셔너리"
                    }
                }
            ],
            "dependencies": [
                {
                    "name": "ffmpeg (system)",
                    "required": True,
                    "installed": _get_service().ffmpeg_installed
                },
                {
                    "name": "ffmpeg-python",
                    "required": True,
                    "installed": FFMPEG_PYTHON_AVAILABLE
                },
                {
                    "name": "PIL (Pillow)",
                    "required": True,
                    "installed": PIL_AVAILABLE
                }
            ]
        }
        
        return {
            "result": tool_info
        }
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}

if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("video_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise