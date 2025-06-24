#!/usr/bin/env python3
"""
File Operations MCP Server
파일 읽기, 쓰기, 탐색 등을 수행할 수 있는 도구들을 제공합니다.
코딩 에이전트를 위한 파일 조작 기능을 구현합니다.
"""

import asyncio
import base64
import io
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastmcp import FastMCP

# MCP 서버 초기화
mcp = FastMCP("File Operations")

# 기본 설정
DEFAULT_ENCODING = "utf-8"
DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_SEARCH_EXCLUDE = [".git", "__pycache__", "venv", "node_modules", ".idea", ".vscode"]


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


def get_file_info(path: str) -> FileInfo:
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


def is_binary_file(file_path: str) -> bool:
    """파일이 바이너리 파일인지 확인합니다."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk  # NULL 바이트가 있으면 바이너리로 간주
    except Exception:
        return True


def get_file_type(file_path: str) -> str:
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
    elif is_binary_file(file_path):
        return "binary"
    else:
        return "text"


@mcp.tool()
def list_directory(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """
    디렉토리 내용을 나열합니다.
    
    Args:
        path: 나열할 디렉토리 경로
        show_hidden: 숨김 파일 표시 여부
        
    Returns:
        Dict: 디렉토리 내용 정보
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path does not exist: {abs_path}",
                "message": "Please provide a valid directory path"
            }
        
        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Not a directory: {abs_path}",
                "message": "Please provide a directory path, not a file path"
            }
        
        # 디렉토리 내용 가져오기
        items = []
        
        for item in os.listdir(abs_path):
            # 숨김 파일 필터링
            if not show_hidden and item.startswith("."):
                continue
                
            item_path = os.path.join(abs_path, item)
            try:
                file_info = get_file_info(item_path)
                
                # 기본 정보
                item_data = {
                    "name": file_info.name,
                    "path": file_info.path,
                    "is_directory": file_info.is_directory,
                    "size": file_info.size,
                    "size_formatted": format_size(file_info.size),
                    "modified": file_info.modified_time.isoformat(),
                    "is_hidden": file_info.is_hidden,
                    "is_readonly": file_info.is_readonly
                }
                
                # 파일인 경우 추가 정보
                if not file_info.is_directory:
                    item_data["extension"] = file_info.extension
                    item_data["type"] = get_file_type(item_path)
                
                items.append(item_data)
            except Exception as e:
                # 개별 항목 오류는 건너뛰고 계속 진행
                continue
        
        # 디렉토리 먼저, 그 다음 파일 이름순으로 정렬
        items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
        
        return {
            "success": True,
            "message": f"Listed {len(items)} items in {abs_path}",
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
            "message": f"Failed to list directory: {path}"
        }


def format_size(size_bytes: int) -> str:
    """바이트 크기를 사람이 읽기 쉬운 형식으로 변환합니다."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


@mcp.tool()
def read_file(path: str, start_line: int = 0, end_line: int = -1, encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일 내용을 읽습니다.
    
    Args:
        path: 읽을 파일 경로
        start_line: 시작 라인 번호 (0부터 시작)
        end_line: 끝 라인 번호 (-1은 파일 끝까지)
        encoding: 파일 인코딩
        
    Returns:
        Dict: 파일 내용 및 메타데이터
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File does not exist: {abs_path}",
                "message": "Please provide a valid file path"
            }
        
        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Cannot read directory as file: {abs_path}",
                "message": "Please provide a file path, not a directory path"
            }
        
        # 파일 크기 확인
        file_size = os.path.getsize(abs_path)
        if file_size > DEFAULT_MAX_SIZE:
            return {
                "success": False,
                "error": f"File too large: {format_size(file_size)}",
                "message": f"Maximum file size is {format_size(DEFAULT_MAX_SIZE)}"
            }
        
        # 파일 유형 확인
        file_type = get_file_type(abs_path)
        if file_type == "binary":
            # 바이너리 파일은 base64로 인코딩
            with open(abs_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('ascii')
                
            return {
                "success": True,
                "message": f"Read binary file: {abs_path}",
                "path": abs_path,
                "size": file_size,
                "size_formatted": format_size(file_size),
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
                        "error": f"Failed to decode file with encoding: {encoding}",
                        "message": "Try specifying a different encoding"
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
                    "error": f"Invalid line range: {start_line} to {end_line}",
                    "message": "Start line must be less than or equal to end line"
                }
            
            # 지정된 범위의 라인 추출
            selected_lines = lines[start_line:end_line + 1]
            content = ''.join(selected_lines)
            
            return {
                "success": True,
                "message": f"Read file: {abs_path} (lines {start_line} to {end_line})",
                "path": abs_path,
                "size": file_size,
                "size_formatted": format_size(file_size),
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
            "message": f"Failed to read file: {path}"
        }


@mcp.tool()
def write_file(path: str, content: str, mode: str = "w", encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일에 내용을 씁니다.
    
    Args:
        path: 쓸 파일 경로
        content: 파일에 쓸 내용
        mode: 파일 모드 (w: 덮어쓰기, a: 추가)
        encoding: 파일 인코딩
        
    Returns:
        Dict: 파일 쓰기 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        # 디렉토리 확인
        dir_path = os.path.dirname(abs_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        # 파일 쓰기 모드 확인
        if mode not in ["w", "a"]:
            return {
                "success": False,
                "error": f"Invalid file mode: {mode}",
                "message": "Mode must be 'w' (write) or 'a' (append)"
            }
        
        # 파일 쓰기
        with open(abs_path, mode, encoding=encoding) as f:
            f.write(content)
        
        # 파일 정보 가져오기
        file_size = os.path.getsize(abs_path)
        file_type = get_file_type(abs_path)
        
        return {
            "success": True,
            "message": f"{'Wrote to' if mode == 'w' else 'Appended to'} file: {abs_path}",
            "path": abs_path,
            "size": file_size,
            "size_formatted": format_size(file_size),
            "type": file_type,
            "mode": mode,
            "encoding": encoding
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to write to file: {path}"
        }


@mcp.tool()
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
                    "message": f"Directory already exists: {abs_path}",
                    "path": abs_path,
                    "already_existed": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Path exists but is not a directory: {abs_path}",
                    "message": "Cannot create directory at the path of an existing file"
                }
        
        # 디렉토리 생성
        os.makedirs(abs_path, exist_ok=True)
        
        return {
            "success": True,
            "message": f"Created directory: {abs_path}",
            "path": abs_path,
            "already_existed": False
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create directory: {path}"
        }


@mcp.tool()
def delete_file(path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 삭제합니다.
    
    Args:
        path: 삭제할 파일 또는 디렉토리 경로
        recursive: 디렉토리를 재귀적으로 삭제할지 여부
        
    Returns:
        Dict: 삭제 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path does not exist: {abs_path}",
                "message": "Cannot delete non-existent path"
            }
        
        # 파일 또는 디렉토리 삭제
        if os.path.isdir(abs_path):
            if recursive:
                shutil.rmtree(abs_path)
                return {
                    "success": True,
                    "message": f"Deleted directory recursively: {abs_path}",
                    "path": abs_path,
                    "was_directory": True
                }
            else:
                try:
                    os.rmdir(abs_path)
                    return {
                        "success": True,
                        "message": f"Deleted empty directory: {abs_path}",
                        "path": abs_path,
                        "was_directory": True
                    }
                except OSError:
                    return {
                        "success": False,
                        "error": f"Directory not empty: {abs_path}",
                        "message": "Use recursive=True to delete non-empty directories"
                    }
        else:
            os.remove(abs_path)
            return {
                "success": True,
                "message": f"Deleted file: {abs_path}",
                "path": abs_path,
                "was_directory": False
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete: {path}"
        }


@mcp.tool()
def copy_file(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 복사합니다.
    
    Args:
        source: 원본 파일 또는 디렉토리 경로
        destination: 대상 파일 또는 디렉토리 경로
        overwrite: 대상이 이미 존재할 경우 덮어쓸지 여부
        
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
                "error": f"Source path does not exist: {abs_source}",
                "message": "Cannot copy from non-existent path"
            }
        
        # 대상이 이미 존재하는지 확인
        if os.path.exists(abs_destination) and not overwrite:
            return {
                "success": False,
                "error": f"Destination already exists: {abs_destination}",
                "message": "Use overwrite=True to overwrite existing files or directories"
            }
        
        # 파일 또는 디렉토리 복사
        if os.path.isdir(abs_source):
            if os.path.exists(abs_destination) and overwrite:
                shutil.rmtree(abs_destination)
            shutil.copytree(abs_source, abs_destination)
            return {
                "success": True,
                "message": f"Copied directory: {abs_source} to {abs_destination}",
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
                "message": f"Copied file: {abs_source} to {abs_destination}",
                "source": abs_source,
                "destination": abs_destination,
                "was_directory": False
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to copy: {source} to {destination}"
        }


@mcp.tool()
def move_file(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    파일 또는 디렉토리를 이동합니다.
    
    Args:
        source: 원본 파일 또는 디렉토리 경로
        destination: 대상 파일 또는 디렉토리 경로
        overwrite: 대상이 이미 존재할 경우 덮어쓸지 여부
        
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
                "error": f"Source path does not exist: {abs_source}",
                "message": "Cannot move from non-existent path"
            }
        
        # 대상이 이미 존재하는지 확인
        if os.path.exists(abs_destination) and not overwrite:
            return {
                "success": False,
                "error": f"Destination already exists: {abs_destination}",
                "message": "Use overwrite=True to overwrite existing files or directories"
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
            "message": f"Moved {'directory' if was_directory else 'file'}: {abs_source} to {abs_destination}",
            "source": abs_source,
            "destination": abs_destination,
            "was_directory": was_directory
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to move: {source} to {destination}"
        }


@mcp.tool()
def search_files(
    path: str = ".", 
    pattern: str = "*", 
    content_pattern: str = None, 
    recursive: bool = True,
    max_results: int = 100,
    include_binary: bool = False
) -> Dict[str, Any]:
    """
    파일을 검색합니다.
    
    Args:
        path: 검색할 디렉토리 경로
        pattern: 파일 이름 패턴 (glob 패턴)
        content_pattern: 파일 내용 검색 패턴 (정규식)
        recursive: 하위 디렉토리까지 재귀적으로 검색할지 여부
        max_results: 최대 결과 수
        include_binary: 바이너리 파일도 검색할지 여부
        
    Returns:
        Dict: 검색 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path does not exist: {abs_path}",
                "message": "Please provide a valid directory path"
            }
        
        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Not a directory: {abs_path}",
                "message": "Please provide a directory path, not a file path"
            }
        
        # 컴파일된 정규식 패턴
        content_regex = None
        if content_pattern:
            try:
                content_regex = re.compile(content_pattern)
            except re.error:
                return {
                    "success": False,
                    "error": f"Invalid regex pattern: {content_pattern}",
                    "message": "Please provide a valid regular expression"
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
                    file_info = get_file_info(file_path)
                    results.append({
                        "path": file_path,
                        "name": file,
                        "size": file_info.size,
                        "size_formatted": format_size(file_info.size),
                        "modified": file_info.modified_time.isoformat(),
                        "type": get_file_type(file_path),
                        "matches": []
                    })
                    matched_files += 1
                    continue
                
                # 내용 검색이 있으면 파일 내용 검색
                if not include_binary and is_binary_file(file_path):
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
                    file_info = get_file_info(file_path)
                    results.append({
                        "path": file_path,
                        "name": file,
                        "size": file_info.size,
                        "size_formatted": format_size(file_info.size),
                        "modified": file_info.modified_time.isoformat(),
                        "type": get_file_type(file_path),
                        "matches": matches[:10]  # 최대 10개 매치만 표시
                    })
                    matched_files += 1
        
        return {
            "success": True,
            "message": f"Found {len(results)} matching files",
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
            "message": f"Failed to search files: {path}"
        }


@mcp.tool()
def get_file_structure(path: str, include_imports: bool = True) -> Dict[str, Any]:
    """
    파일의 구조를 분석합니다. 주로 코드 파일에 유용합니다.
    
    Args:
        path: 분석할 파일 경로
        include_imports: import 문도 포함할지 여부
        
    Returns:
        Dict: 파일 구조 분석 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File does not exist: {abs_path}",
                "message": "Please provide a valid file path"
            }
        
        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Cannot analyze directory: {abs_path}",
                "message": "Please provide a file path, not a directory path"
            }
        
        # 파일 유형 확인
        file_type = get_file_type(abs_path)
        
        # 파일 내용 읽기
        try:
            with open(abs_path, 'r', encoding=DEFAULT_ENCODING) as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(abs_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to read file: {abs_path}",
                    "message": "File may be binary or use an unsupported encoding"
                }
        
        # 파일 구조 분석
        structure = {
            "imports": [],
            "classes": [],
            "functions": [],
            "variables": []
        }
        
        # 파일 유형에 따라 다른 분석 방법 사용
        if file_type == "python":
            # Python 파일 분석
            import_pattern = r'^import\s+(\w+)|^from\s+(\w+(?:\.\w+)*)\s+import\s+(.+)$'
            class_pattern = r'^class\s+(\w+)(?:\((.+)\))?:'
            function_pattern = r'^def\s+(\w+)\s*\((.+)?\):'
            variable_pattern = r'^(\w+)\s*=\s*(.+)$'
            
            lines = content.splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 주석 및 빈 줄 무시
                if not line or line.startswith('#'):
                    continue
                
                # import 문 찾기
                if include_imports:
                    import_match = re.match(import_pattern, line)
                    if import_match:
                        if import_match.group(1):  # import x
                            structure["imports"].append({
                                "type": "import",
                                "module": import_match.group(1),
                                "line": i + 1
                            })
                        else:  # from x import y
                            module = import_match.group(2)
                            imports = import_match.group(3).split(',')
                            for imp in imports:
                                structure["imports"].append({
                                    "type": "from_import",
                                    "module": module,
                                    "name": imp.strip(),
                                    "line": i + 1
                                })
                        continue
                
                # 클래스 정의 찾기
                class_match = re.match(class_pattern, line)
                if class_match:
                    class_name = class_match.group(1)
                    parent_classes = class_match.group(2)
                    
                    # 클래스 본문 찾기
                    body_start = i + 1
                    body_end = body_start
                    indent_level = len(line) - len(line.lstrip())
                    
                    for j in range(body_start, len(lines)):
                        if j >= len(lines):
                            break
                        
                        next_line = lines[j]
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent_level:
                            body_end = j
                            break
                        body_end = j + 1
                    
                    structure["classes"].append({
                        "name": class_name,
                        "parent_classes": parent_classes.split(',') if parent_classes else [],
                        "line_start": i + 1,
                        "line_end": body_end,
                        "body_length": body_end - body_start
                    })
                    continue
                
                # 함수 정의 찾기
                function_match = re.match(function_pattern, line)
                if function_match:
                    function_name = function_match.group(1)
                    parameters = function_match.group(2)
                    
                    # 함수 본문 찾기
                    body_start = i + 1
                    body_end = body_start
                    indent_level = len(line) - len(line.lstrip())
                    
                    for j in range(body_start, len(lines)):
                        if j >= len(lines):
                            break
                        
                        next_line = lines[j]
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent_level:
                            body_end = j
                            break
                        body_end = j + 1
                    
                    structure["functions"].append({
                        "name": function_name,
                        "parameters": [p.strip() for p in parameters.split(',')] if parameters else [],
                        "line_start": i + 1,
                        "line_end": body_end,
                        "body_length": body_end - body_start
                    })
                    continue
                
                # 전역 변수 찾기 (클래스나 함수 내부가 아닌 경우)
                variable_match = re.match(variable_pattern, line)
                if variable_match:
                    variable_name = variable_match.group(1)
                    variable_value = variable_match.group(2)
                    
                    structure["variables"].append({
                        "name": variable_name,
                        "value": variable_value,
                        "line": i + 1
                    })
        
        elif file_type in ["javascript", "typescript"]:
            # JavaScript/TypeScript 파일 분석
            import_pattern = r'^import\s+.*from\s+[\'"](.+)[\'"];?$|^const\s+(\w+)\s*=\s*require\([\'"](.+)[\'"]\);?$'
            class_pattern = r'^class\s+(\w+)(?:\s+extends\s+(\w+))?.*{$'
            function_pattern = r'^(?:function|const|let|var)\s+(\w+)\s*(?:=\s*(?:function|\(.*\)\s*=>))?.*{$'
            variable_pattern = r'^(?:const|let|var)\s+(\w+)\s*=\s*(.+);?$'
            
            # 분석 로직은 Python과 유사하게 구현
            # (실제 구현은 JavaScript 구문에 맞게 조정 필요)
        
        # 다른 언어에 대한 분석 로직 추가 가능
        
        return {
            "success": True,
            "message": f"Analyzed file structure: {abs_path}",
            "path": abs_path,
            "type": file_type,
            "size": os.path.getsize(abs_path),
            "size_formatted": format_size(os.path.getsize(abs_path)),
            "structure": structure,
            "total_imports": len(structure["imports"]),
            "total_classes": len(structure["classes"]),
            "total_functions": len(structure["functions"]),
            "total_variables": len(structure["variables"])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to analyze file structure: {path}"
        }


@mcp.tool()
def edit_file_lines(path: str, edit_operations: List[Dict[str, Any]], encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일의 특정 라인을 편집합니다.
    
    Args:
        path: 편집할 파일 경로
        edit_operations: 편집 작업 목록 (각 작업은 line_start, line_end, content 또는 action 포함)
        encoding: 파일 인코딩
        
    Returns:
        Dict: 편집 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File does not exist: {abs_path}",
                "message": "Please provide a valid file path"
            }
        
        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Cannot edit directory: {abs_path}",
                "message": "Please provide a file path, not a directory path"
            }
        
        # 파일 읽기
        try:
            with open(abs_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(abs_path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
                encoding = 'latin-1'
            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to decode file with encoding: {encoding}",
                    "message": "Try specifying a different encoding"
                }
        
        # 편집 작업 적용
        operations_applied = []
        total_lines = len(lines)
        
        # 라인 번호 기준으로 정렬 (내림차순)
        sorted_operations = sorted(edit_operations, key=lambda op: op.get("line_start", 0), reverse=True)
        
        for op in sorted_operations:
            op_type = op.get("action", "replace")
            line_start = op.get("line_start", 1) - 1  # 0-based 인덱스로 변환
            line_end = op.get("line_end", line_start + 1) - 1
            
            # 라인 범위 유효성 검사
            if line_start < 0:
                line_start = 0
            if line_end >= total_lines:
                line_end = total_lines - 1
            if line_start > line_end:
                continue
            
            if op_type == "replace":
                # 라인 대체
                content = op.get("content", "")
                new_lines = content.splitlines(True)
                lines[line_start:line_end + 1] = new_lines
                operations_applied.append({
                    "action": "replace",
                    "line_start": line_start + 1,
                    "line_end": line_end + 1,
                    "lines_before": line_end - line_start + 1,
                    "lines_after": len(new_lines)
                })
            
            elif op_type == "insert":
                # 라인 삽입
                content = op.get("content", "")
                new_lines = content.splitlines(True)
                lines.insert(line_start, *new_lines)
                operations_applied.append({
                    "action": "insert",
                    "line": line_start + 1,
                    "lines_added": len(new_lines)
                })
            
            elif op_type == "delete":
                # 라인 삭제
                del lines[line_start:line_end + 1]
                operations_applied.append({
                    "action": "delete",
                    "line_start": line_start + 1,
                    "line_end": line_end + 1,
                    "lines_deleted": line_end - line_start + 1
                })
        
        # 파일 쓰기
        with open(abs_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        
        return {
            "success": True,
            "message": f"Edited file: {abs_path}",
            "path": abs_path,
            "operations_applied": len(operations_applied),
            "operations": operations_applied,
            "encoding": encoding,
            "lines_after_edit": len(lines)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to edit file: {path}"
        }


@mcp.tool()
def search_replace_in_file(path: str, search: str, replace: str, regex: bool = False, encoding: str = DEFAULT_ENCODING) -> Dict[str, Any]:
    """
    파일에서 텍스트를 검색하고 대체합니다.
    
    Args:
        path: 편집할 파일 경로
        search: 검색할 텍스트 또는 패턴
        replace: 대체할 텍스트
        regex: 정규식 사용 여부
        encoding: 파일 인코딩
        
    Returns:
        Dict: 검색 및 대체 결과
    """
    try:
        # 경로 정규화
        abs_path = os.path.abspath(path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File does not exist: {abs_path}",
                "message": "Please provide a valid file path"
            }
        
        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Cannot edit directory: {abs_path}",
                "message": "Please provide a file path, not a directory path"
            }
        
        # 파일 읽기
        try:
            with open(abs_path, 'r', encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(abs_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                encoding = 'latin-1'
            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to decode file with encoding: {encoding}",
                    "message": "Try specifying a different encoding"
                }
        
        # 검색 및 대체
        if regex:
            try:
                pattern = re.compile(search)
                new_content, count = re.subn(pattern, replace, content)
            except re.error:
                return {
                    "success": False,
                    "error": f"Invalid regex pattern: {search}",
                    "message": "Please provide a valid regular expression"
                }
        else:
            count = content.count(search)
            new_content = content.replace(search, replace)
        
        # 변경 사항이 있으면 파일 쓰기
        if count > 0:
            with open(abs_path, 'w', encoding=encoding) as f:
                f.write(new_content)
        
        return {
            "success": True,
            "message": f"Replaced {count} occurrences in file: {abs_path}",
            "path": abs_path,
            "replacements": count,
            "search": search,
            "replace": replace,
            "regex": regex,
            "encoding": encoding
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search and replace in file: {path}"
        }


@mcp.tool()
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
            "message": f"Current directory: {current_dir}",
            "path": current_dir,
            "parent": os.path.dirname(current_dir),
            "name": os.path.basename(current_dir)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get current directory"
        }


@mcp.tool()
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
                "error": f"Path does not exist: {abs_path}",
                "message": "Please provide a valid directory path"
            }
        
        if not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Not a directory: {abs_path}",
                "message": "Please provide a directory path, not a file path"
            }
        
        # 이전 디렉토리 저장
        previous_dir = os.getcwd()
        
        # 디렉토리 변경
        os.chdir(abs_path)
        
        return {
            "success": True,
            "message": f"Changed directory to: {abs_path}",
            "path": abs_path,
            "previous": previous_dir
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to change directory: {path}"
        }


async def main():
    """MCP 서버 실행"""
    try:
        # 서버 실행
        await mcp.run()
    except Exception as e:
        print(f"Error running MCP server: {e}")


if __name__ == "__main__":
    print("📁 File Operations MCP Server")
    print("🔧 FastMCP를 이용한 파일 조작 도구")
    print("🚀 서버를 시작합니다...")
    
    try:
        # 이미 실행 중인 이벤트 루프가 있는지 확인
        try:
            loop = asyncio.get_running_loop()
            print("⚠️  이미 실행 중인 이벤트 루프가 감지되었습니다.")
            print("🔧 nest_asyncio를 사용하여 중첩 이벤트 루프를 활성화합니다.")
            
            # nest_asyncio를 사용하여 중첩된 이벤트 루프 허용
            try:
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(main())
            except ImportError:
                print("❌ nest_asyncio가 설치되지 않았습니다.")
                print("📦 설치 명령: pip install nest-asyncio")
                print("🔄 대신 create_task를 사용합니다.")
                loop.create_task(main())
                
        except RuntimeError:
            # 실행 중인 이벤트 루프가 없음
            asyncio.run(main())
            
    except KeyboardInterrupt:
        print("\n⏹️  서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 해결 방법:")
        print("   1. 새로운 터미널에서 실행해보세요")
        print("   2. pip install nest-asyncio 후 재시도하세요")
        print("   3. 다른 Python 환경에서 실행해보세요")