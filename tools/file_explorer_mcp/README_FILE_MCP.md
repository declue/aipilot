# 📁 File Operations MCP Server

FastMCP를 이용한 파일 조작 및 코드 편집 도구입니다.

## ✨ 주요 기능

- 📂 **파일 시스템 탐색**: 디렉토리 내용 나열, 현재 디렉토리 확인 및 변경
- 📄 **파일 읽기/쓰기**: 전체 또는 부분 파일 읽기, 파일 생성 및 수정
- 🔍 **파일 검색**: 파일 이름 및 내용 검색
- ✏️ **코드 편집**: 라인 단위 편집, 검색 및 대체
- 🔄 **파일 관리**: 파일 복사, 이동, 삭제
- 🧩 **코드 분석**: 파일 구조 분석 (클래스, 함수, 변수 등)

## 📦 설치

필요한 패키지를 설치합니다:

```bash
pip install fastmcp
```

## 🚀 사용 방법

### 1. MCP 서버 시작

```bash
python tools/file_mcp_tool.py
```

### 2. 사용 가능한 도구들

#### 📂 디렉토리 탐색

```python
# 디렉토리 내용 나열
result = await mcp_client.call_tool("list_directory", {
    "path": "./src",
    "show_hidden": False
})

# 현재 디렉토리 확인
result = await mcp_client.call_tool("get_current_directory")

# 디렉토리 변경
result = await mcp_client.call_tool("change_directory", {
    "path": "../project"
})
```

#### 📄 파일 읽기/쓰기

```python
# 파일 읽기 (전체)
result = await mcp_client.call_tool("read_file", {
    "path": "main.py"
})

# 파일 부분 읽기 (라인 10-20)
result = await mcp_client.call_tool("read_file", {
    "path": "main.py",
    "start_line": 10,
    "end_line": 20
})

# 파일 쓰기 (덮어쓰기)
result = await mcp_client.call_tool("write_file", {
    "path": "output.txt",
    "content": "Hello, World!",
    "mode": "w"
})

# 파일 쓰기 (추가)
result = await mcp_client.call_tool("write_file", {
    "path": "log.txt",
    "content": "New log entry\n",
    "mode": "a"
})
```

#### 🔍 파일 검색

```python
# 파일 이름으로 검색
result = await mcp_client.call_tool("search_files", {
    "path": "./src",
    "pattern": "*.py",
    "recursive": True
})

# 파일 내용으로 검색
result = await mcp_client.call_tool("search_files", {
    "path": "./src",
    "pattern": "*.py",
    "content_pattern": "def main",
    "recursive": True
})
```

#### ✏️ 코드 편집

```python
# 파일의 특정 라인 편집
result = await mcp_client.call_tool("edit_file_lines", {
    "path": "main.py",
    "edit_operations": [
        {
            "action": "replace",
            "line_start": 10,
            "line_end": 12,
            "content": "def main():\n    print('Hello, World!')\n"
        }
    ]
})

# 검색 및 대체
result = await mcp_client.call_tool("search_replace_in_file", {
    "path": "main.py",
    "search": "Hello, World",
    "replace": "Hello, Universe",
    "regex": False
})
```

#### 🔄 파일 관리

```python
# 디렉토리 생성
result = await mcp_client.call_tool("create_directory", {
    "path": "new_folder"
})

# 파일 복사
result = await mcp_client.call_tool("copy_file", {
    "source": "main.py",
    "destination": "backup/main.py",
    "overwrite": True
})

# 파일 이동
result = await mcp_client.call_tool("move_file", {
    "source": "temp.txt",
    "destination": "archive/temp.txt"
})

# 파일 삭제
result = await mcp_client.call_tool("delete_file", {
    "path": "temp.txt"
})

# 디렉토리 삭제 (재귀적)
result = await mcp_client.call_tool("delete_file", {
    "path": "old_folder",
    "recursive": True
})
```

#### 🧩 코드 분석

```python
# 파일 구조 분석
result = await mcp_client.call_tool("get_file_structure", {
    "path": "main.py",
    "include_imports": True
})
```

## 📊 응답 형식

모든 도구는 다음과 같은 형식으로 응답합니다:

```json
{
    "success": true,
    "message": "Operation completed successfully",
    "path": "/path/to/file",
    "...": "기타 작업별 결과 데이터"
}
```

오류 발생 시:

```json
{
    "success": false,
    "error": "Error description",
    "message": "User-friendly error message"
}
```

## 🧪 고급 사용 예제

### 파일 내용 분석 및 수정

```python
async def analyze_and_fix_code(file_path):
    # 파일 구조 분석
    structure = await mcp_client.call_tool("get_file_structure", {
        "path": file_path
    })
    
    # 함수 개수 확인
    functions = structure["structure"]["functions"]
    print(f"Found {len(functions)} functions")
    
    # 특정 패턴 검색
    search_result = await mcp_client.call_tool("search_files", {
        "path": os.path.dirname(file_path),
        "pattern": os.path.basename(file_path),
        "content_pattern": "TODO|FIXME",
        "recursive": False
    })
    
    # TODO 항목이 있으면 수정
    if search_result["results"] and search_result["results"][0]["matches"]:
        for match in search_result["results"][0]["matches"]:
            line_num = match["line_number"]
            line = match["line"]
            
            if "TODO" in line:
                # TODO 항목 수정
                await mcp_client.call_tool("edit_file_lines", {
                    "path": file_path,
                    "edit_operations": [
                        {
                            "action": "replace",
                            "line_start": line_num,
                            "line_end": line_num,
                            "content": line.replace("TODO", "DONE") + "\n"
                        }
                    ]
                })
                print(f"Fixed TODO at line {line_num}")
```

### 프로젝트 구조 분석

```python
async def analyze_project_structure(project_path):
    # 프로젝트 디렉토리 내용 가져오기
    result = await mcp_client.call_tool("list_directory", {
        "path": project_path
    })
    
    # 파이썬 파일 찾기
    python_files = []
    for item in result["items"]:
        if not item["is_directory"] and item.get("extension") == ".py":
            python_files.append(item["path"])
    
    # 각 파일의 구조 분석
    project_structure = {
        "files": len(python_files),
        "classes": 0,
        "functions": 0,
        "imports": set()
    }
    
    for file_path in python_files:
        structure = await mcp_client.call_tool("get_file_structure", {
            "path": file_path
        })
        
        if structure["success"]:
            project_structure["classes"] += len(structure["structure"]["classes"])
            project_structure["functions"] += len(structure["structure"]["functions"])
            
            # 고유한 import 수집
            for imp in structure["structure"]["imports"]:
                if imp["type"] == "import":
                    project_structure["imports"].add(imp["module"])
                else:
                    project_structure["imports"].add(imp["module"])
    
    print(f"Project summary:")
    print(f"- {project_structure['files']} Python files")
    print(f"- {project_structure['classes']} classes")
    print(f"- {project_structure['functions']} functions")
    print(f"- {len(project_structure['imports'])} unique imports")
```

## 📋 요구사항

- Python 3.7+
- Windows, macOS, Linux 지원

## 🛡️ 보안 고려사항

- 파일 시스템 접근 권한이 필요합니다
- 중요한 시스템 파일을 수정하지 않도록 주의하세요
- 프로덕션 환경에서는 적절한 접근 제어를 설정하세요

## 🤝 기여

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🔗 관련 링크

- [FastMCP](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://github.com/modelcontextprotocol)