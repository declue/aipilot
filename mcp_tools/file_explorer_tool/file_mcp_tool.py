#!/usr/bin/env python3
"""
파일 조작 MCP 서버
파일 읽기, 쓰기, 탐색 등을 수행할 수 있는 도구들을 제공합니다.
코딩 에이전트를 위한 파일 조작 기능을 구현합니다.
"""

import base64
import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.CRITICAL + 1)

# MCP 서버 초기화
app = FastMCP(
    title="File Operations Server",
    description="A server for file manipulation operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
DEFAULT_ENCODING = "utf-8"
DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_SEARCH_EXCLUDE = [".git", "__pycache__",
                          "venv", "node_modules", ".idea", ".vscode"]


@dataclass
class FileInfo:
    """파일 정보를 담는 데이터 클래스"""
    path: str
    name: str
    extension: str
    size: int
    is_directory: bool
    created_time: datetime
    modified_time: datetime
    is_hidden: bool
    is_readonly: bool


class FileService:
    """파일 서비스 클래스 - SOLID 원칙에 따른 단일 책임"""

    def __init__(self):
        self.default_encoding = DEFAULT_ENCODING
        self.max_file_size = DEFAULT_MAX_SIZE
        self.search_exclude = DEFAULT_SEARCH_EXCLUDE

    def get_file_info(self, path: str) -> FileInfo:
        """파일 또는 디렉토리 정보를 가져옵니다."""
        file_path = Path(path)
        stats = file_path.stat()

        return FileInfo(
            path=str(file_path.absolute()),
            name=file_path.name,
            extension=file_path.suffix.lower() if not file_path.is_dir() else "",
            size=stats.st_size,
            is_directory=file_path.is_dir(),
            created_time=datetime.fromtimestamp(stats.st_ctime),
            modified_time=datetime.fromtimestamp(stats.st_mtime),
            is_hidden=file_path.name.startswith("."),
            is_readonly=not os.access(path, os.W_OK)
        )

    def is_binary_file(self, file_path: str) -> bool:
        """파일이 바이너리 파일인지 확인합니다."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk  # NULL 바이트가 있으면 바이너리로 간주
        except Exception:
            return True

    def get_file_type(self, file_path: str) -> str:
        """파일 유형을 결정합니다."""
        if not os.path.exists(file_path):
            return "unknown"

        if os.path.isdir(file_path):
            return "directory"

        extension = os.path.splitext(file_path)[1].lower()

        # 코드 파일
        code_extensions = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".java": "java", ".c": "c", ".cpp": "cpp", ".cs": "csharp",
            ".go": "go", ".rb": "ruby", ".php": "php", ".swift": "swift",
            ".kt": "kotlin", ".rs": "rust", ".scala": "scala", ".sh": "shell",
            ".ps1": "powershell", ".html": "html", ".css": "css", ".sql": "sql"
        }

        # 문서 파일
        document_extensions = {
            ".txt": "text", ".md": "markdown", ".json": "json", ".xml": "xml",
            ".yaml": "yaml", ".yml": "yaml", ".csv": "csv", ".tsv": "tsv",
            ".doc": "word", ".docx": "word", ".xls": "excel", ".xlsx": "excel",
            ".ppt": "powerpoint", ".pptx": "powerpoint", ".pdf": "pdf",
            ".rtf": "rtf", ".tex": "latex"
        }

        # 미디어 파일
        media_extensions = {
            ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image",
            ".bmp": "image", ".svg": "image", ".mp3": "audio", ".wav": "audio",
            ".ogg": "audio", ".mp4": "video", ".avi": "video", ".mov": "video",
            ".wmv": "video", ".flv": "video", ".webm": "video"
        }

        # 압축 파일
        archive_extensions = {
            ".zip": "archive", ".rar": "archive", ".7z": "archive",
            ".tar": "archive", ".gz": "archive", ".bz2": "archive"
        }

        if extension in code_extensions:
            return code_extensions[extension]
        elif extension in document_extensions:
            return document_extensions[extension]
        elif extension in media_extensions:
            return media_extensions[extension]
        elif extension in archive_extensions:
            return archive_extensions[extension]
        elif self.is_binary_file(file_path):
            return "binary"
        else:
            return "text"

    def format_size(self, size_bytes: int) -> str:
        """바이트 크기를 사람이 읽기 쉬운 형식으로 변환합니다."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# 전역 서비스 인스턴스
file_service = FileService()


@app.tool()
def list_directory(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """
    디렉토리 내용을 나열합니다.

    Args:
        path: 나열할 디렉토리 경로 (기본값: 현재 디렉토리)
        show_hidden: 숨김 파일 표시 여부 (기본값: False)

    Returns:
        Dict: 디렉토리 내용 정보
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"경로가 존재하지 않습니다: {abs_path}",
                "message": "유효한 디렉토리 경로를 제공해주세요"
            }

        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"디렉토리가 아닙니다: {abs_path}",
                "message": "파일이 아닌 디렉토리 경로를 제공해주세요"
            }

        # 디렉토리 내용 가져오기
        items = []

        for item in os.listdir(abs_path):
            # 숨김 파일 필터링
            if not show_hidden and item.startswith("."):
                continue

            item_path = os.path.join(abs_path, item)
            try:
                file_info = file_service.get_file_info(item_path)

                # 기본 정보
                item_data = {
                    "name": file_info.name,
                    "path": file_info.path,
                    "is_directory": file_info.is_directory,
                    "size": file_info.size,
                    "size_formatted": file_service.format_size(file_info.size),
                    "modified": file_info.modified_time.isoformat(),
                    "is_hidden": file_info.is_hidden,
                    "is_readonly": file_info.is_readonly
                }

                # 파일인 경우 추가 정보
                if not file_info.is_directory:
                    item_data["extension"] = file_info.extension
                    item_data["type"] = file_service.get_file_type(item_path)

                items.append(item_data)
            except Exception:
                # 개별 항목 오류는 건너뛰고 계속 진행
                continue

        # 디렉토리 먼저, 그 다음 파일 이름순으로 정렬
        items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))

        return {
            "success": True,
            "message": f"{abs_path}에서 {len(items)}개 항목을 찾았습니다",
            "path": abs_path,
            "parent_path": os.path.dirname(abs_path),
            "items": items,
            "directories": sum(1 for item in items if item["is_directory"]),
            "files": sum(1 for item in items if not item["is_directory"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"디렉토리 목록 조회 실패: {path}"
        }


@app.tool()
def read_file(path: str, start_line: int = 0, end_line: int = -1, encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일 내용을 읽습니다.

    Args:
        path: 읽을 파일 경로
        start_line: 시작 라인 번호 (0부터 시작, 기본값: 0)
        end_line: 끝 라인 번호 (-1은 파일 끝까지, 기본값: -1)
        encoding: 파일 인코딩 (기본값: utf-8)

    Returns:
        Dict: 파일 내용 및 메타데이터
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"디렉토리를 파일로 읽을 수 없습니다: {abs_path}",
                "message": "디렉토리가 아닌 파일 경로를 제공해주세요"
            }

        # 파일 크기 확인
        file_size = os.path.getsize(abs_path)
        if file_size > DEFAULT_MAX_SIZE:
            return {
                "success": False,
                "error": f"파일이 너무 큽니다: {file_service.format_size(file_size)}",
                "message": f"최대 파일 크기는 {file_service.format_size(DEFAULT_MAX_SIZE)}입니다"
            }

        # 파일 유형 확인
        file_type = file_service.get_file_type(abs_path)
        if file_type == "binary":
            # 바이너리 파일은 base64로 인코딩
            with open(abs_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('ascii')

            return {
                "success": True,
                "message": f"바이너리 파일을 읽었습니다: {abs_path}",
                "path": abs_path,
                "size": file_size,
                "size_formatted": file_service.format_size(file_size),
                "type": file_type,
                "is_binary": True,
                "content_format": "base64",
                "content": content
            }
        else:
            # 텍스트 파일 읽기
            try:
                with open(abs_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # 인코딩 오류 시 다른 인코딩 시도
                try:
                    with open(abs_path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                    encoding = 'latin-1'
                except Exception:
                    return {
                        "success": False,
                        "error": f"파일 인코딩 실패: {encoding}",
                        "message": "다른 인코딩을 시도해보세요"
                    }

            # 라인 범위 처리
            total_lines = len(lines)

            if start_line < 0:
                start_line = 0

            if end_line < 0 or end_line >= total_lines:
                end_line = total_lines - 1

            if start_line > end_line:
                return {
                    "success": False,
                    "error": f"잘못된 라인 범위: {start_line} ~ {end_line}",
                    "message": "시작 라인은 끝 라인보다 작거나 같아야 합니다"
                }

            # 지정된 범위의 라인 추출
            selected_lines = lines[start_line:end_line + 1]
            content = ''.join(selected_lines)

            return {
                "success": True,
                "message": f"파일을 읽었습니다: {abs_path} (라인 {start_line} ~ {end_line})",
                "path": abs_path,
                "size": file_size,
                "size_formatted": file_service.format_size(file_size),
                "type": file_type,
                "is_binary": False,
                "encoding": encoding,
                "total_lines": total_lines,
                "start_line": start_line,
                "end_line": min(end_line, total_lines - 1),
                "content": content
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"파일 읽기 실패: {path}"
        }


@app.tool()
def write_file(path: str, content: str, mode: str = "w", encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일에 내용을 씁니다.

    Args:
        path: 쓸 파일 경로
        content: 파일에 쓸 내용
        mode: 파일 모드 (w: 덮어쓰기, a: 추가, 기본값: w)
        encoding: 파일 인코딩 (기본값: utf-8)

    Returns:
        Dict: 파일 쓰기 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        # content 타입 검증 및 변환
        if not isinstance(content, str):
            if isinstance(content, dict):
                # 딕셔너리인 경우 JSON 형태로 변환
                import json
                try:
                    content = json.dumps(content, indent=2, ensure_ascii=False)
                except Exception:
                    content = str(content)
            elif isinstance(content, (list, tuple)):
                # 리스트나 튜플인 경우 줄바꿈으로 연결
                content = '\n'.join(str(item) for item in content)
            else:
                # 기타 타입은 문자열로 변환
                content = str(content)

        # 디렉토리 확인
        dir_path = os.path.dirname(abs_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # 파일 쓰기 모드 확인
        if mode not in ["w", "a"]:
            return {
                "success": False,
                "error": f"잘못된 파일 모드: {mode}",
                "message": "모드는 'w' (쓰기) 또는 'a' (추가)여야 합니다"
            }

        # 파일 쓰기
        with open(abs_path, mode, encoding=encoding) as f:
            f.write(content)

        # 파일 정보 가져오기
        file_size = os.path.getsize(abs_path)
        file_type = file_service.get_file_type(abs_path)

        return {
            "success": True,
            "message": f"파일에 {'쓰기' if mode == 'w' else '추가'} 완료: {abs_path}",
            "path": abs_path,
            "size": file_size,
            "size_formatted": file_service.format_size(file_size),
            "type": file_type,
            "mode": mode,
            "encoding": encoding
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"파일 쓰기 실패: {path}"
        }


@app.tool()
def create_directory(path: str) -> Dict[str, Any]:
    """
    디렉토리를 생성합니다.

    Args:
        path: 생성할 디렉토리 경로

    Returns:
        Dict: 디렉토리 생성 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        # 이미 존재하는지 확인
        if os.path.exists(abs_path):
            if os.path.isdir(abs_path):
                return {
                    "success": True,
                    "message": f"디렉토리가 이미 존재합니다: {abs_path}",
                    "path": abs_path,
                    "already_existed": True
                }
            else:
                return {
                    "success": False,
                    "error": f"경로가 존재하지만 디렉토리가 아닙니다: {abs_path}",
                    "message": "기존 파일이 있는 경로에 디렉토리를 생성할 수 없습니다"
                }

        # 디렉토리 생성
        os.makedirs(abs_path, exist_ok=True)

        return {
            "success": True,
            "message": f"디렉토리를 생성했습니다: {abs_path}",
            "path": abs_path,
            "already_existed": False
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"디렉토리 생성 실패: {path}"
        }


@app.tool()
def delete_file(path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 삭제합니다.

    Args:
        path: 삭제할 파일 또는 디렉토리 경로
        recursive: 디렉토리를 재귀적으로 삭제할지 여부 (기본값: False)

    Returns:
        Dict: 삭제 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"경로가 존재하지 않습니다: {abs_path}",
                "message": "존재하지 않는 경로는 삭제할 수 없습니다"
            }

        # 파일 또는 디렉토리 삭제
        if os.path.isdir(abs_path):
            if recursive:
                shutil.rmtree(abs_path)
                return {
                    "success": True,
                    "message": f"디렉토리를 재귀적으로 삭제했습니다: {abs_path}",
                    "path": abs_path,
                    "was_directory": True
                }
            else:
                try:
                    os.rmdir(abs_path)
                    return {
                        "success": True,
                        "message": f"빈 디렉토리를 삭제했습니다: {abs_path}",
                        "path": abs_path,
                        "was_directory": True
                    }
                except OSError:
                    return {
                        "success": False,
                        "error": f"디렉토리가 비어있지 않습니다: {abs_path}",
                        "message": "비어있지 않은 디렉토리를 삭제하려면 recursive=True를 사용하세요"
                    }
        else:
            os.remove(abs_path)
            return {
                "success": True,
                "message": f"파일을 삭제했습니다: {abs_path}",
                "path": abs_path,
                "was_directory": False
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"삭제 실패: {path}"
        }


@app.tool()
def copy_file(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 복사합니다.

    Args:
        source: 원본 파일 또는 디렉토리 경로
        destination: 대상 파일 또는 디렉토리 경로
        overwrite: 대상이 이미 존재할 경우 덮어쓸지 여부 (기본값: False)

    Returns:
        Dict: 복사 결과
    """
    try:
        # 경로 정규화
        abs_source = os.path.abspath(source)
        abs_destination = os.path.abspath(destination)

        if not os.path.exists(abs_source):
            return {
                "success": False,
                "error": f"원본 경로가 존재하지 않습니다: {abs_source}",
                "message": "존재하지 않는 경로에서 복사할 수 없습니다"
            }

        # 대상이 이미 존재하는지 확인
        if os.path.exists(abs_destination) and not overwrite:
            return {
                "success": False,
                "error": f"대상이 이미 존재합니다: {abs_destination}",
                "message": "기존 파일이나 디렉토리를 덮어쓰려면 overwrite=True를 사용하세요"
            }

        # 파일 또는 디렉토리 복사
        if os.path.isdir(abs_source):
            if os.path.exists(abs_destination) and overwrite:
                shutil.rmtree(abs_destination)
            shutil.copytree(abs_source, abs_destination)
            return {
                "success": True,
                "message": f"디렉토리를 복사했습니다: {abs_source} → {abs_destination}",
                "source": abs_source,
                "destination": abs_destination,
                "was_directory": True
            }
        else:
            # 대상 디렉토리가 없으면 생성
            dest_dir = os.path.dirname(abs_destination)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            shutil.copy2(abs_source, abs_destination)
            return {
                "success": True,
                "message": f"파일을 복사했습니다: {abs_source} → {abs_destination}",
                "source": abs_source,
                "destination": abs_destination,
                "was_directory": False
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"복사 실패: {source} → {destination}"
        }


@app.tool()
def move_file(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 이동합니다.

    Args:
        source: 원본 파일 또는 디렉토리 경로
        destination: 대상 파일 또는 디렉토리 경로
        overwrite: 대상이 이미 존재할 경우 덮어쓸지 여부 (기본값: False)

    Returns:
        Dict: 이동 결과
    """
    try:
        # 경로 정규화
        abs_source = os.path.abspath(source)
        abs_destination = os.path.abspath(destination)

        if not os.path.exists(abs_source):
            return {
                "success": False,
                "error": f"원본 경로가 존재하지 않습니다: {abs_source}",
                "message": "존재하지 않는 경로에서 이동할 수 없습니다"
            }

        # 대상이 이미 존재하는지 확인
        if os.path.exists(abs_destination) and not overwrite:
            return {
                "success": False,
                "error": f"대상이 이미 존재합니다: {abs_destination}",
                "message": "기존 파일이나 디렉토리를 덮어쓰려면 overwrite=True를 사용하세요"
            }

        # 대상이 이미 존재하고 덮어쓰기가 활성화된 경우 삭제
        if os.path.exists(abs_destination) and overwrite:
            if os.path.isdir(abs_destination):
                shutil.rmtree(abs_destination)
            else:
                os.remove(abs_destination)

        # 대상 디렉토리가 없으면 생성
        dest_dir = os.path.dirname(abs_destination)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        # 파일 또는 디렉토리 이동
        was_directory = os.path.isdir(abs_source)
        shutil.move(abs_source, abs_destination)

        return {
            "success": True,
            "message": f"{'디렉토리' if was_directory else '파일'}을 이동했습니다: {abs_source} → {abs_destination}",
            "source": abs_source,
            "destination": abs_destination,
            "was_directory": was_directory
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"이동 실패: {source} → {destination}"
        }


@app.tool()
def search_files(
    path: str = ".",
    pattern: str = "*",
    content_pattern: str = "",
    recursive: bool = True,
    max_results: int = 100,
    include_binary: bool = False
) -> Dict[str, Any]:
    """
    파일을 검색합니다.

    Args:
        path: 검색할 디렉토리 경로 (기본값: 현재 디렉토리)
        pattern: 파일 이름 패턴 (glob 패턴, 기본값: *)
        content_pattern: 파일 내용 검색 패턴 (정규식, 기본값: "")
        recursive: 하위 디렉토리까지 재귀적으로 검색할지 여부 (기본값: True)
        max_results: 최대 결과 수 (기본값: 100)
        include_binary: 바이너리 파일도 검색할지 여부 (기본값: False)

    Returns:
        Dict: 검색 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"경로가 존재하지 않습니다: {abs_path}",
                "message": "유효한 디렉토리 경로를 제공해주세요"
            }

        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"디렉토리가 아닙니다: {abs_path}",
                "message": "파일이 아닌 디렉토리 경로를 제공해주세요"
            }

        # 컴파일된 정규식 패턴
        content_regex = None
        if content_pattern:
            try:
                content_regex = re.compile(content_pattern)
            except re.error:
                return {
                    "success": False,
                    "error": f"잘못된 정규식 패턴: {content_pattern}",
                    "message": "유효한 정규식을 제공해주세요"
                }

        # 검색 결과
        results = []
        searched_files = 0
        matched_files = 0

        # 파일 검색
        for root, dirs, files in os.walk(abs_path):
            # 제외 디렉토리 필터링
            dirs[:] = [d for d in dirs if d not in DEFAULT_SEARCH_EXCLUDE]

            # 비재귀 모드에서는 첫 번째 레벨만 검색
            if not recursive and root != abs_path:
                continue

            for file in files:
                # 최대 결과 수 확인
                if matched_files >= max_results:
                    break

                # 파일 이름 패턴 매칭
                if not Path(file).match(pattern):
                    continue

                file_path = os.path.join(root, file)
                searched_files += 1

                # 내용 검색이 없으면 파일 이름만으로 결과 추가
                if not content_regex:
                    file_info = file_service.get_file_info(file_path)
                    results.append({
                        "path": file_path,
                        "name": file,
                        "size": file_info.size,
                        "size_formatted": file_service.format_size(file_info.size),
                        "modified": file_info.modified_time.isoformat(),
                        "type": file_service.get_file_type(file_path),
                        "matches": []
                    })
                    matched_files += 1
                    continue

                # 내용 검색이 있으면 파일 내용 검색
                if not include_binary and file_service.is_binary_file(file_path):
                    continue

                try:
                    # 텍스트 파일 내용 검색
                    with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                        content = f.read()
                except UnicodeDecodeError:
                    try:
                        # 다른 인코딩 시도
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except Exception:
                        # 읽기 실패한 파일은 건너뛰기
                        continue

                # 내용 패턴 매칭
                matches = []
                for i, line in enumerate(content.splitlines()):
                    if content_regex.search(line):
                        matches.append({
                            "line_number": i + 1,
                            "line": line.strip()
                        })

                # 매치가 있으면 결과 추가
                if matches:
                    file_info = file_service.get_file_info(file_path)
                    results.append({
                        "path": file_path,
                        "name": file,
                        "size": file_info.size,
                        "size_formatted": file_service.format_size(file_info.size),
                        "modified": file_info.modified_time.isoformat(),
                        "type": file_service.get_file_type(file_path),
                        "matches": matches[:10]  # 최대 10개 매치만 표시
                    })
                    matched_files += 1

        return {
            "success": True,
            "message": f"{len(results)}개의 매칭 파일을 찾았습니다",
            "path": abs_path,
            "pattern": pattern,
            "content_pattern": content_pattern,
            "recursive": recursive,
            "searched_files": searched_files,
            "results": results,
            "has_more": matched_files >= max_results
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"파일 검색 실패: {path}"
        }


@app.tool()
def get_current_directory() -> Dict[str, Any]:
    """
    현재 작업 디렉토리를 반환합니다.

    Returns:
        Dict: 현재 작업 디렉토리 정보
    """
    try:
        current_dir = os.getcwd()

        return {
            "success": True,
            "message": f"현재 디렉토리: {current_dir}",
            "path": current_dir,
            "parent": os.path.dirname(current_dir),
            "name": os.path.basename(current_dir)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "현재 디렉토리 조회 실패"
        }


@app.tool()
def change_directory(path: str) -> Dict[str, Any]:
    """
    작업 디렉토리를 변경합니다.

    Args:
        path: 변경할 디렉토리 경로

    Returns:
        Dict: 디렉토리 변경 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"경로가 존재하지 않습니다: {abs_path}",
                "message": "유효한 디렉토리 경로를 제공해주세요"
            }

        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"디렉토리가 아닙니다: {abs_path}",
                "message": "파일이 아닌 디렉토리 경로를 제공해주세요"
            }

        # 이전 디렉토리 저장
        previous_dir = os.getcwd()

        # 디렉토리 변경
        os.chdir(abs_path)

        return {
            "success": True,
            "message": f"디렉토리를 변경했습니다: {abs_path}",
            "path": abs_path,
            "previous": previous_dir
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"디렉토리 변경 실패: {path}"
        }


if __name__ == "__main__":
    import os

    # 환경 변수로 출력 제어 (기본값: False)
    show_startup_msg = os.getenv("FILE_MCP_VERBOSE", "false").lower() == "true"

    if show_startup_msg:
        print("📁 File Operations MCP Server")
        print("🔧 파일 조작 도구 서버를 시작합니다...")

    try:
        app.run(transport="stdio")
    except KeyboardInterrupt:
        if show_startup_msg:
            print("\n⏹️ 서버를 종료합니다.")
    except Exception as e:
        if show_startup_msg:
            print(f"❌ 서버 실행 중 오류 발생: {e}")
        else:
            # 에러는 항상 출력
            print(f"❌ 서버 실행 중 오류 발생: {e}")
