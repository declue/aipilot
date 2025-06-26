#!/usr/bin/env python3
"""
코딩 에이전트 MCP 서버
코드 분석, 버그 수정, 리팩토링, diff 패치 생성 등을 수행하는 도구들을 제공합니다.
SWE-Agent처럼 다양한 코드 편집 및 수정 기능을 구현합니다.
"""

import ast
import difflib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# MCP 서버 초기화
app = FastMCP(
    title="Coding Agent Server",
    description="A server for code analysis, bug fixing, and refactoring operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
DEFAULT_ENCODING = "utf-8"
SUPPORTED_LANGUAGES = ["python", "javascript",
                       "typescript", "java", "cpp", "c", "go", "rust"]
CODE_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".c": "c", ".cpp": "cpp", ".cc": "cpp",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php"
}


@dataclass
class CodeIssue:
    """코드 이슈를 담는 데이터 클래스"""
    type: str  # "bug", "style", "performance", "security"
    severity: str  # "low", "medium", "high", "critical"
    line_number: int
    description: str
    suggestion: str
    file_path: str


@dataclass
class CodeChange:
    """코드 변경사항을 담는 데이터 클래스"""
    file_path: str
    original_content: str
    modified_content: str
    change_type: str  # "fix", "refactor", "optimize", "add"
    description: str
    line_start: int
    line_end: int


class CodeAnalysisService:
    """코드 분석 서비스 클래스 - SOLID 원칙에 따른 단일 책임"""

    def __init__(self):
        self.encoding = DEFAULT_ENCODING
        self.supported_languages = SUPPORTED_LANGUAGES
        self.code_extensions = CODE_EXTENSIONS

    def detect_language(self, file_path: str) -> str:
        """파일 확장자로 프로그래밍 언어를 감지합니다."""
        extension = os.path.splitext(file_path)[1].lower()
        return self.code_extensions.get(extension, "text")

    def read_file_safely(self, file_path: str) -> Optional[str]:
        """파일을 안전하게 읽습니다."""
        try:
            with open(file_path, 'r', encoding=self.encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception:
                return None
        except Exception:
            return None

    def write_file_safely(self, file_path: str, content: str) -> bool:
        """파일을 안전하게 씁니다."""
        try:
            # 백업 생성
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding=self.encoding) as f:
                    backup_content = f.read()
                with open(backup_path, 'w', encoding=self.encoding) as f:
                    f.write(backup_content)

            # 새 내용 쓰기
            with open(file_path, 'w', encoding=self.encoding) as f:
                f.write(content)
            return True
        except Exception:
            return False

    def generate_diff(self, original: str, modified: str, file_path: str = "file") -> str:
        """두 텍스트 간의 diff를 생성합니다."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )

        return ''.join(diff)

    def analyze_python_code(self, content: str, file_path: str) -> List[CodeIssue]:
        """Python 코드를 분석하여 이슈를 찾습니다."""
        issues = []
        lines = content.splitlines()

        try:
            # AST 파싱으로 구문 오류 확인
            ast.parse(content)
        except SyntaxError as e:
            issues.append(CodeIssue(
                type="bug",
                severity="high",
                line_number=e.lineno or 1,
                description=f"구문 오류: {e.msg}",
                suggestion="구문을 수정하세요",
                file_path=file_path
            ))
            return issues

        # 기본적인 코드 품질 검사
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # 긴 라인 검사
            if len(line) > 100:
                issues.append(CodeIssue(
                    type="style",
                    severity="low",
                    line_number=i,
                    description="라인이 너무 깁니다 (100자 초과)",
                    suggestion="라인을 분할하거나 줄여보세요",
                    file_path=file_path
                ))

            # TODO/FIXME 주석 검사
            if "TODO" in line_stripped or "FIXME" in line_stripped:
                issues.append(CodeIssue(
                    type="style",
                    severity="low",
                    line_number=i,
                    description="미완성 작업이 있습니다",
                    suggestion="TODO/FIXME 항목을 완료하세요",
                    file_path=file_path
                ))

            # 잠재적 보안 이슈
            if "eval(" in line_stripped or "exec(" in line_stripped:
                issues.append(CodeIssue(
                    type="security",
                    severity="high",
                    line_number=i,
                    description="eval() 또는 exec() 사용은 보안 위험이 있습니다",
                    suggestion="더 안전한 대안을 사용하세요",
                    file_path=file_path
                ))

            # 하드코딩된 패스워드나 키
            if re.search(r'(password|key|secret)\s*=\s*["\'][^"\']+["\']', line_stripped, re.IGNORECASE):
                issues.append(CodeIssue(
                    type="security",
                    severity="critical",
                    line_number=i,
                    description="하드코딩된 비밀번호나 키가 발견되었습니다",
                    suggestion="환경변수나 설정 파일을 사용하세요",
                    file_path=file_path
                ))

        return issues

    def suggest_python_improvements(self, content: str, file_path: str) -> List[str]:
        """Python 코드 개선사항을 제안합니다."""
        suggestions = []
        lines = content.splitlines()

        # import 문 정리 제안
        import_lines = [line for line in lines if line.strip(
        ).startswith(('import ', 'from '))]
        if len(import_lines) > 5:
            suggestions.append("import 문을 정리하고 사용하지 않는 import를 제거하세요")

        # 함수 길이 검사
        in_function = False
        function_lines = 0
        for line in lines:
            if line.strip().startswith('def '):
                in_function = True
                function_lines = 0
            elif in_function:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    if function_lines > 50:
                        suggestions.append("일부 함수가 너무 깁니다. 더 작은 함수로 분할을 고려하세요")
                    in_function = False
                else:
                    function_lines += 1

        # 주석 비율 검사
        comment_lines = len(
            [line for line in lines if line.strip().startswith('#')])
        code_lines = len([line for line in lines if line.strip()
                         and not line.strip().startswith('#')])
        if code_lines > 0 and comment_lines / code_lines < 0.1:
            suggestions.append("코드에 주석을 더 추가하여 가독성을 높이세요")

        return suggestions


# 전역 서비스 인스턴스
code_service = CodeAnalysisService()


@app.tool()
def analyze_code(file_path: str, check_style: bool = True, check_security: bool = True) -> Dict[str, Any]:
    """
    코드 파일을 분석하여 이슈와 개선사항을 찾습니다.

    Args:
        file_path: 분석할 코드 파일 경로
        check_style: 스타일 검사 수행 여부 (기본값: True)
        check_security: 보안 검사 수행 여부 (기본값: True)

    Returns:
        Dict: 코드 분석 결과
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        if os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"디렉토리를 분석할 수 없습니다: {abs_path}",
                "message": "파일 경로를 제공해주세요"
            }

        # 파일 읽기
        content = code_service.read_file_safely(abs_path)
        if content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        # 코드 분석
        issues = []
        suggestions = []

        if language == "python":
            issues = code_service.analyze_python_code(content, abs_path)
            suggestions = code_service.suggest_python_improvements(
                content, abs_path)
        else:
            # 다른 언어는 기본적인 분석만 수행
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    issues.append(CodeIssue(
                        type="style",
                        severity="low",
                        line_number=i,
                        description="라인이 너무 깁니다",
                        suggestion="라인을 분할하세요",
                        file_path=abs_path
                    ))

        # 필터링
        if not check_style:
            issues = [issue for issue in issues if issue.type != "style"]
        if not check_security:
            issues = [issue for issue in issues if issue.type != "security"]

        # 결과 구성
        issue_summary = {
            "critical": len([i for i in issues if i.severity == "critical"]),
            "high": len([i for i in issues if i.severity == "high"]),
            "medium": len([i for i in issues if i.severity == "medium"]),
            "low": len([i for i in issues if i.severity == "low"])
        }

        return {
            "success": True,
            "message": f"코드 분석 완료: {len(issues)}개 이슈 발견",
            "file_path": abs_path,
            "language": language,
            "lines_of_code": len(content.splitlines()),
            "issue_summary": issue_summary,
            "issues": [
                {
                    "type": issue.type,
                    "severity": issue.severity,
                    "line": issue.line_number,
                    "description": issue.description,
                    "suggestion": issue.suggestion
                }
                for issue in issues
            ],
            "suggestions": suggestions
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"코드 분석 실패: {file_path}"
        }


@app.tool()
def fix_code_issues(file_path: str, issue_types: List[str] = None, severity_threshold: str = "medium") -> Dict[str, Any]:
    """
    발견된 코드 이슈를 자동으로 수정합니다.

    Args:
        file_path: 수정할 코드 파일 경로
        issue_types: 수정할 이슈 타입 목록 (기본값: 모든 타입)
        severity_threshold: 수정할 최소 심각도 (low, medium, high, critical)

    Returns:
        Dict: 코드 수정 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        if language != "python":
            return {
                "success": False,
                "error": f"현재 {language} 언어는 자동 수정을 지원하지 않습니다",
                "message": "Python 파일만 자동 수정이 가능합니다"
            }

        # 이슈 분석
        issues = code_service.analyze_python_code(original_content, abs_path)

        # 심각도 필터링
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold_level = severity_order.get(severity_threshold, 1)
        filtered_issues = [
            issue for issue in issues
            if severity_order.get(issue.severity, 0) >= threshold_level
        ]

        # 타입 필터링
        if issue_types:
            filtered_issues = [
                issue for issue in filtered_issues
                if issue.type in issue_types
            ]

        if not filtered_issues:
            return {
                "success": True,
                "message": "수정할 이슈가 없습니다",
                "file_path": abs_path,
                "changes_made": 0,
                "diff": ""
            }

        # 코드 수정
        modified_content = original_content
        changes_made = []

        # 간단한 수정만 자동으로 수행
        for issue in filtered_issues:
            if issue.type == "style" and "라인이 너무 깁니다" in issue.description:
                # 긴 라인 분할 (간단한 경우만)
                lines = modified_content.splitlines()
                if issue.line_number <= len(lines):
                    line = lines[issue.line_number - 1]
                    if len(line) > 100 and ',' in line:
                        # 쉼표에서 분할
                        parts = line.split(',')
                        if len(parts) > 1:
                            indent = len(line) - len(line.lstrip())
                            new_lines = [parts[0] + ',']
                            for part in parts[1:-1]:
                                new_lines.append(
                                    ' ' * (indent + 4) + part.strip() + ',')
                            new_lines.append(
                                ' ' * (indent + 4) + parts[-1].strip())

                            lines[issue.line_number -
                                  1:issue.line_number] = new_lines
                            modified_content = '\n'.join(lines)
                            changes_made.append(
                                f"라인 {issue.line_number}: 긴 라인을 분할했습니다")

        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)

        return {
            "success": True,
            "message": f"{len(changes_made)}개 이슈를 수정했습니다",
            "file_path": abs_path,
            "changes_made": len(changes_made),
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content if changes_made else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"코드 수정 실패: {file_path}"
        }


@app.tool()
def refactor_code(file_path: str, refactor_type: str = "extract_function", target_lines: List[int] = None) -> Dict[str, Any]:
    """
    코드 리팩토링을 수행합니다.

    Args:
        file_path: 리팩토링할 코드 파일 경로
        refactor_type: 리팩토링 유형 (extract_function, rename_variable, extract_class)
        target_lines: 리팩토링 대상 라인 번호 목록

    Returns:
        Dict: 리팩토링 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        if language != "python":
            return {
                "success": False,
                "error": f"현재 {language} 언어는 리팩토링을 지원하지 않습니다",
                "message": "Python 파일만 리팩토링이 가능합니다"
            }

        # 기본 리팩토링 수행 (간단한 예시)
        modified_content = original_content
        changes_made = []

        if refactor_type == "extract_function" and target_lines:
            lines = original_content.splitlines()
            if len(target_lines) >= 2:
                start_line = min(target_lines) - 1
                end_line = max(target_lines)

                if 0 <= start_line < len(lines) and end_line <= len(lines):
                    extracted_lines = lines[start_line:end_line]

                    # 새 함수 생성
                    function_name = f"extracted_function_{start_line + 1}"
                    new_function = [
                        f"def {function_name}():",
                        "    \"\"\"추출된 함수\"\"\"",
                    ]

                    for line in extracted_lines:
                        new_function.append("    " + line)

                    new_function.extend(["", ""])

                    # 원본 라인들을 함수 호출로 교체
                    lines[start_line:end_line] = [f"    {function_name}()"]

                    # 함수 정의를 파일 시작 부분에 추가
                    lines = new_function + lines

                    modified_content = '\n'.join(lines)
                    changes_made.append(
                        f"라인 {start_line + 1}-{end_line}을 {function_name} 함수로 추출했습니다")

        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)

        return {
            "success": True,
            "message": f"리팩토링 완료: {len(changes_made)}개 변경",
            "file_path": abs_path,
            "refactor_type": refactor_type,
            "changes_made": len(changes_made),
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content if changes_made else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"리팩토링 실패: {file_path}"
        }


@app.tool()
def generate_code(file_path: str, code_type: str, specification: str, insert_line: int = -1) -> Dict[str, Any]:
    """
    새로운 코드를 생성합니다.

    Args:
        file_path: 코드를 추가할 파일 경로
        code_type: 생성할 코드 유형 (function, class, test, docstring)
        specification: 코드 사양 설명
        insert_line: 코드를 삽입할 라인 번호 (-1은 파일 끝)

    Returns:
        Dict: 코드 생성 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)

        # 파일이 없으면 생성
        if not os.path.exists(abs_path):
            original_content = ""
        else:
            original_content = code_service.read_file_safely(abs_path)
            if original_content is None:
                return {
                    "success": False,
                    "error": "파일을 읽을 수 없습니다",
                    "message": "파일 인코딩이나 권한을 확인해주세요"
                }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        if language != "python":
            return {
                "success": False,
                "error": f"현재 {language} 언어는 코드 생성을 지원하지 않습니다",
                "message": "Python 파일만 코드 생성이 가능합니다"
            }

        # 코드 생성
        generated_code = []

        if code_type == "function":
            function_name = specification.split(
            )[0] if specification else "new_function"
            generated_code = [
                f"def {function_name}():",
                f'    """',
                f'    {specification}',
                f'    """',
                f'    # TODO: 구현 필요',
                f'    pass',
                "",
                ""
            ]

        elif code_type == "class":
            class_name = specification.split(
            )[0] if specification else "NewClass"
            generated_code = [
                f"class {class_name}:",
                f'    """',
                f'    {specification}',
                f'    """',
                "",
                f'    def __init__(self):',
                f'        """초기화 메서드"""',
                f'        pass',
                "",
                ""
            ]

        elif code_type == "test":
            test_name = f"test_{specification.replace(' ', '_').lower()}" if specification else "test_function"
            generated_code = [
                f"def {test_name}():",
                f'    """',
                f'    테스트: {specification}',
                f'    """',
                f'    # Arrange',
                f'    # TODO: 테스트 데이터 설정',
                f'    ',
                f'    # Act',
                f'    # TODO: 테스트할 동작 실행',
                f'    ',
                f'    # Assert',
                f'    # TODO: 결과 검증',
                f'    assert True  # 임시 통과',
                "",
                ""
            ]

        elif code_type == "docstring":
            generated_code = [
                f'    """',
                f'    {specification}',
                f'    ',
                f'    Args:',
                f'        # TODO: 매개변수 설명',
                f'    ',
                f'    Returns:',
                f'        # TODO: 반환값 설명',
                f'    """'
            ]

        # 코드 삽입
        lines = original_content.splitlines() if original_content else []

        if insert_line == -1 or insert_line > len(lines):
            # 파일 끝에 추가
            lines.extend(generated_code)
        else:
            # 지정된 라인에 삽입
            insert_pos = max(0, insert_line - 1)
            lines[insert_pos:insert_pos] = generated_code

        modified_content = '\n'.join(lines)

        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)

        return {
            "success": True,
            "message": f"{code_type} 코드를 생성했습니다",
            "file_path": abs_path,
            "code_type": code_type,
            "specification": specification,
            "lines_added": len(generated_code),
            "diff": diff,
            "modified_content": modified_content
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"코드 생성 실패: {file_path}"
        }


@app.tool()
def apply_diff_patch(file_path: str, diff_content: str, create_backup: bool = True) -> Dict[str, Any]:
    """
    diff 패치를 파일에 적용합니다.

    Args:
        file_path: 패치를 적용할 파일 경로
        diff_content: 적용할 diff 내용
        create_backup: 백업 파일 생성 여부 (기본값: True)

    Returns:
        Dict: 패치 적용 결과
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        # 원본 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 백업 생성
        backup_path = None
        if create_backup:
            backup_path = f"{abs_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            except Exception:
                backup_path = None

        # diff 내용이 단순 텍스트인지 확인 (실제 diff 형식이 아닌 경우)
        if not diff_content.strip().startswith(('---', '+++')):
            # 단순 텍스트라면 파일 전체를 교체
            try:
                if not code_service.write_file_safely(abs_path, diff_content):
                    return {
                        "success": False,
                        "error": "파일 쓰기에 실패했습니다",
                        "message": "파일 권한을 확인해주세요"
                    }

                return {
                    "success": True,
                    "message": "파일 내용을 성공적으로 교체했습니다",
                    "file_path": abs_path,
                    "backup_path": backup_path,
                    "operation": "full_replace"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"파일 교체 실패: {str(e)}",
                    "message": "파일 쓰기 권한을 확인해주세요"
                }

        # 실제 diff 형식 파싱 및 적용
        try:
            original_lines = original_content.splitlines(keepends=True)
            
            # difflib.unified_diff 역방향 적용을 위한 개선된 파싱
            diff_lines = diff_content.splitlines()
            
            result_lines = []
            i = 0
            
            # diff 헤더 스킵
            while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                i += 1
            
            if i >= len(diff_lines):
                # diff 형식이 아닌 경우 전체 교체
                if not code_service.write_file_safely(abs_path, diff_content):
                    return {
                        "success": False,
                        "error": "파일 쓰기에 실패했습니다",
                        "message": "파일 권한을 확인해주세요"
                    }
                return {
                    "success": True,
                    "message": "파일 내용을 성공적으로 교체했습니다",
                    "file_path": abs_path,
                    "backup_path": backup_path,
                    "operation": "content_replace"
                }
            
            # @@ 라인 파싱
            original_line_num = 0
            
            while i < len(diff_lines):
                line = diff_lines[i]
                
                if line.startswith('@@'):
                    # @@ -1,12 +1,12 @@ 형식 파싱
                    match = re.search(r'-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?', line)
                    if match:
                        orig_start = int(match.group(1)) - 1  # 0-based index
                        new_start = int(match.group(3)) - 1
                        
                        # 이전 라인들까지 복사
                        while original_line_num < orig_start and original_line_num < len(original_lines):
                            result_lines.append(original_lines[original_line_num])
                            original_line_num += 1
                    
                    i += 1
                    continue
                
                elif line.startswith(' '):
                    # 변경되지 않은 라인
                    if original_line_num < len(original_lines):
                        result_lines.append(original_lines[original_line_num])
                        original_line_num += 1
                
                elif line.startswith('-'):
                    # 삭제된 라인 - 원본에서 건너뛰기
                    if original_line_num < len(original_lines):
                        original_line_num += 1
                
                elif line.startswith('+'):
                    # 추가된 라인
                    new_line = line[1:]
                    if not new_line.endswith('\n'):
                        new_line += '\n'
                    result_lines.append(new_line)
                
                i += 1
            
            # 나머지 원본 라인들 추가
            while original_line_num < len(original_lines):
                result_lines.append(original_lines[original_line_num])
                original_line_num += 1
            
            # 결과를 문자열로 변환
            modified_content = ''.join(result_lines)
            
            # 파일 쓰기
            if not code_service.write_file_safely(abs_path, modified_content):
                return {
                    "success": False,
                    "error": "파일 쓰기에 실패했습니다",
                    "message": "파일 권한을 확인해주세요"
                }

            return {
                "success": True,
                "message": "diff 패치를 성공적으로 적용했습니다",
                "file_path": abs_path,
                "backup_path": backup_path,
                "operation": "diff_patch",
                "lines_original": len(original_lines),
                "lines_modified": len(result_lines)
            }

        except Exception as e:
            # 패치 적용 실패 시 원본 복원
            if backup_path and os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        backup_content = f.read()
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(backup_content)
                except Exception:
                    pass

            return {
                "success": False,
                "error": f"패치 적용 실패: {str(e)}",
                "message": "diff 형식을 확인하거나 파일 전체 내용을 제공해주세요"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"패치 적용 실패: {file_path}"
        }


@app.tool()
def optimize_code(file_path: str, optimization_type: str = "performance") -> Dict[str, Any]:
    """
    코드를 최적화합니다.

    Args:
        file_path: 최적화할 코드 파일 경로
        optimization_type: 최적화 유형 (performance, memory, readability)

    Returns:
        Dict: 코드 최적화 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        if language != "python":
            return {
                "success": False,
                "error": f"현재 {language} 언어는 최적화를 지원하지 않습니다",
                "message": "Python 파일만 최적화가 가능합니다"
            }

        # 기본적인 최적화 수행
        modified_content = original_content
        optimizations = []

        if optimization_type == "performance":
            # 성능 최적화
            lines = original_content.splitlines()
            for i, line in enumerate(lines):
                # 간단한 최적화 예시
                if "len(list)" in line and "for" in line:
                    optimizations.append(
                        f"라인 {i + 1}: 리스트 길이 확인을 루프 밖으로 이동 권장")

                if ".append(" in line and "for" in line:
                    optimizations.append(f"라인 {i + 1}: 리스트 컴프리헨션 사용 고려")

        elif optimization_type == "memory":
            # 메모리 최적화
            lines = original_content.splitlines()
            for i, line in enumerate(lines):
                if "list(" in line and "range(" in line:
                    optimizations.append(
                        f"라인 {i + 1}: range() 객체를 리스트로 변환하지 말고 직접 사용")

        elif optimization_type == "readability":
            # 가독성 최적화
            lines = original_content.splitlines()
            new_lines = []

            for line in lines:
                # 간단한 포맷팅 개선
                if line.strip():
                    # 연산자 주변 공백 추가
                    line = re.sub(r'(\w)=(\w)', r'\1 = \2', line)
                    line = re.sub(r'(\w)\+(\w)', r'\1 + \2', line)
                    line = re.sub(r'(\w)-(\w)', r'\1 - \2', line)

                new_lines.append(line)

            if new_lines != lines:
                modified_content = '\n'.join(new_lines)
                optimizations.append("연산자 주변에 공백을 추가하여 가독성을 개선했습니다")

        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)

        return {
            "success": True,
            "message": f"코드 최적화 완료: {len(optimizations)}개 제안",
            "file_path": abs_path,
            "optimization_type": optimization_type,
            "optimizations": optimizations,
            "diff": diff,
            "modified_content": modified_content if optimizations else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"코드 최적화 실패: {file_path}"
        }


@app.tool()
def validate_syntax(file_path: str) -> Dict[str, Any]:
    """
    코드 파일의 구문을 검증합니다.

    Args:
        file_path: 검증할 코드 파일 경로

    Returns:
        Dict: 구문 검증 결과
    """
    try:
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }

        # 파일 읽기
        content = code_service.read_file_safely(abs_path)
        if content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }

        # 언어 감지
        language = code_service.detect_language(abs_path)

        validation_result = {
            "file_path": abs_path,
            "language": language,
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        if language == "python":
            try:
                # Python 구문 검사
                ast.parse(content)
                validation_result["message"] = "Python 구문이 유효합니다"
            except SyntaxError as e:
                validation_result["is_valid"] = False
                validation_result["errors"].append({
                    "line": e.lineno or 1,
                    "column": e.offset or 1,
                    "message": e.msg,
                    "type": "SyntaxError"
                })
                validation_result["message"] = f"Python 구문 오류: {e.msg}"

        else:
            # 다른 언어는 기본적인 검사만
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                # 기본적인 괄호 매칭 검사
                open_brackets = line.count(
                    '(') + line.count('[') + line.count('{')
                close_brackets = line.count(
                    ')') + line.count(']') + line.count('}')

                if open_brackets != close_brackets:
                    validation_result["warnings"].append({
                        "line": i,
                        "message": "괄호가 일치하지 않을 수 있습니다",
                        "type": "BracketMismatch"
                    })

            validation_result["message"] = f"{language} 파일 기본 검증 완료"

        return {
            "success": True,
            **validation_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"구문 검증 실패: {file_path}"
        }


@app.tool()
def edit_specific_lines(file_path: str, line_edits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    파일의 특정 라인들을 직접 수정합니다.
    
    Args:
        file_path: 수정할 파일 경로
        line_edits: 라인 편집 정보 목록
                   [{"line": 10, "action": "replace", "content": "new content"},
                    {"line": 15, "action": "insert", "content": "inserted line"},
                    {"line": 20, "action": "delete"}]
        
    Returns:
        Dict: 라인 편집 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        lines = original_content.splitlines()
        modified_lines = lines.copy()
        changes_made = []
        
        # 라인 번호 기준으로 내림차순 정렬 (뒤에서부터 수정해야 라인 번호가 안 틀어짐)
        sorted_edits = sorted(line_edits, key=lambda x: x.get("line", 0), reverse=True)
        
        for edit in sorted_edits:
            line_num = edit.get("line", 0)
            action = edit.get("action", "replace")
            content = edit.get("content", "")
            
            # 라인 번호 유효성 검사 (1-based index)
            if line_num < 1:
                continue
                
            line_index = line_num - 1  # 0-based index로 변환
            
            if action == "replace":
                if line_index < len(modified_lines):
                    old_content = modified_lines[line_index]
                    modified_lines[line_index] = content
                    changes_made.append(f"라인 {line_num}: '{old_content.strip()}' → '{content.strip()}'")
                
            elif action == "insert":
                if line_index <= len(modified_lines):
                    modified_lines.insert(line_index, content)
                    changes_made.append(f"라인 {line_num}: 새 라인 삽입 '{content.strip()}'")
                
            elif action == "delete":
                if line_index < len(modified_lines):
                    deleted_content = modified_lines.pop(line_index)
                    changes_made.append(f"라인 {line_num}: 삭제됨 '{deleted_content.strip()}'")
        
        modified_content = '\n'.join(modified_lines)
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"{len(changes_made)}개 라인을 수정했습니다",
            "file_path": abs_path,
            "changes_made": len(changes_made),
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"라인 편집 실패: {file_path}"
        }


@app.tool()
def replace_in_code(file_path: str, search_replace_pairs: List[Dict[str, str]], 
                   use_regex: bool = False, whole_words_only: bool = False) -> Dict[str, Any]:
    """
    코드에서 텍스트를 검색하고 치환합니다.
    
    Args:
        file_path: 수정할 파일 경로
        search_replace_pairs: 검색-치환 쌍 목록
                             [{"search": "old_function", "replace": "new_function"},
                              {"search": "old_var", "replace": "new_var"}]
        use_regex: 정규식 사용 여부 (기본값: False)
        whole_words_only: 전체 단어만 매칭 (기본값: False)
        
    Returns:
        Dict: 텍스트 치환 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        modified_content = original_content
        total_replacements = 0
        changes_made = []
        
        for pair in search_replace_pairs:
            search_text = pair.get("search", "")
            replace_text = pair.get("replace", "")
            
            if not search_text:
                continue
            
            if use_regex:
                try:
                    if whole_words_only:
                        pattern = r'\b' + re.escape(search_text) + r'\b'
                    else:
                        pattern = search_text
                    
                    new_content, count = re.subn(pattern, replace_text, modified_content)
                    modified_content = new_content
                    
                except re.error as e:
                    changes_made.append(f"정규식 오류 '{search_text}': {str(e)}")
                    continue
            else:
                if whole_words_only:
                    # 전체 단어 매칭을 위한 정규식 사용
                    pattern = r'\b' + re.escape(search_text) + r'\b'
                    new_content, count = re.subn(pattern, replace_text, modified_content)
                    modified_content = new_content
                else:
                    # 단순 문자열 치환
                    count = modified_content.count(search_text)
                    modified_content = modified_content.replace(search_text, replace_text)
            
            if count > 0:
                total_replacements += count
                changes_made.append(f"'{search_text}' → '{replace_text}' ({count}회 치환)")
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"총 {total_replacements}회 치환 완료",
            "file_path": abs_path,
            "total_replacements": total_replacements,
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content if total_replacements > 0 else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"텍스트 치환 실패: {file_path}"
        }


@app.tool()
def rename_function(file_path: str, old_name: str, new_name: str, 
                   rename_calls: bool = True) -> Dict[str, Any]:
    """
    함수명을 변경합니다 (정의와 호출 모두).
    
    Args:
        file_path: 수정할 파일 경로
        old_name: 기존 함수명
        new_name: 새로운 함수명
        rename_calls: 함수 호출도 함께 변경할지 여부 (기본값: True)
        
    Returns:
        Dict: 함수명 변경 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        # 언어 감지
        language = code_service.detect_language(abs_path)
        
        modified_content = original_content
        total_changes = 0
        changes_made = []
        
        if language == "python":
            # Python 함수 정의 변경: def old_name( → def new_name(
            def_pattern = rf'\bdef\s+{re.escape(old_name)}\s*\('
            def_replacement = f'def {new_name}('
            
            new_content, def_count = re.subn(def_pattern, def_replacement, modified_content)
            modified_content = new_content
            
            if def_count > 0:
                total_changes += def_count
                changes_made.append(f"함수 정의 변경: def {old_name}( → def {new_name}( ({def_count}회)")
            
            if rename_calls:
                # Python 함수 호출 변경: old_name( → new_name(
                # 단, 앞에 . 이 없는 경우만 (메서드 호출 제외)
                call_pattern = rf'(?<!\.)(?<!\w){re.escape(old_name)}\s*\('
                call_replacement = f'{new_name}('
                
                new_content, call_count = re.subn(call_pattern, call_replacement, modified_content)
                modified_content = new_content
                
                if call_count > 0:
                    total_changes += call_count
                    changes_made.append(f"함수 호출 변경: {old_name}( → {new_name}( ({call_count}회)")
        
        elif language in ["javascript", "typescript"]:
            # JavaScript/TypeScript 함수 정의 변경
            # function old_name( → function new_name(
            func_pattern = rf'\bfunction\s+{re.escape(old_name)}\s*\('
            func_replacement = f'function {new_name}('
            
            new_content, func_count = re.subn(func_pattern, func_replacement, modified_content)
            modified_content = new_content
            
            if func_count > 0:
                total_changes += func_count
                changes_made.append(f"함수 정의 변경: function {old_name}( → function {new_name}( ({func_count}회)")
            
            # const/let/var old_name = function/arrow function
            var_pattern = rf'\b(const|let|var)\s+{re.escape(old_name)}\s*='
            var_replacement = rf'\1 {new_name} ='
            
            new_content, var_count = re.subn(var_pattern, var_replacement, modified_content)
            modified_content = new_content
            
            if var_count > 0:
                total_changes += var_count
                changes_made.append(f"변수 함수 정의 변경: {old_name} = → {new_name} = ({var_count}회)")
            
            if rename_calls:
                # 함수 호출 변경
                call_pattern = rf'(?<!\.)(?<!\w){re.escape(old_name)}\s*\('
                call_replacement = f'{new_name}('
                
                new_content, call_count = re.subn(call_pattern, call_replacement, modified_content)
                modified_content = new_content
                
                if call_count > 0:
                    total_changes += call_count
                    changes_made.append(f"함수 호출 변경: {old_name}( → {new_name}( ({call_count}회)")
        
        else:
            # 다른 언어는 기본적인 패턴 매칭
            if rename_calls:
                # 전체 단어 매칭으로 함수명 변경
                pattern = rf'\b{re.escape(old_name)}\b'
                new_content, count = re.subn(pattern, new_name, modified_content)
                modified_content = new_content
                
                if count > 0:
                    total_changes += count
                    changes_made.append(f"'{old_name}' → '{new_name}' ({count}회 변경)")
        
        if total_changes == 0:
            return {
                "success": True,
                "message": f"함수 '{old_name}'을 찾을 수 없습니다",
                "file_path": abs_path,
                "changes_made": 0,
                "diff": ""
            }
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"함수명 변경 완료: {old_name} → {new_name} (총 {total_changes}회)",
            "file_path": abs_path,
            "old_name": old_name,
            "new_name": new_name,
            "total_changes": total_changes,
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"함수명 변경 실패: {file_path}"
        }


@app.tool()
def insert_code_at_line(file_path: str, line_number: int, code_content: str, 
                       indent_level: int = 0) -> Dict[str, Any]:
    """
    지정된 라인에 코드를 삽입합니다.
    
    Args:
        file_path: 수정할 파일 경로
        line_number: 삽입할 라인 번호 (1-based)
        code_content: 삽입할 코드 내용
        indent_level: 들여쓰기 레벨 (기본값: 0)
        
    Returns:
        Dict: 코드 삽입 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        lines = original_content.splitlines()
        
        # 라인 번호 유효성 검사
        if line_number < 1:
            line_number = 1
        elif line_number > len(lines) + 1:
            line_number = len(lines) + 1
        
        # 들여쓰기 적용
        indent = ' ' * (indent_level * 4)  # 4칸 단위 들여쓰기
        indented_lines = []
        
        for line in code_content.splitlines():
            if line.strip():  # 빈 줄이 아닌 경우만 들여쓰기 적용
                indented_lines.append(indent + line)
            else:
                indented_lines.append(line)
        
        # 코드 삽입
        insert_index = line_number - 1  # 0-based index로 변환
        lines[insert_index:insert_index] = indented_lines
        
        modified_content = '\n'.join(lines)
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"라인 {line_number}에 {len(indented_lines)}줄의 코드를 삽입했습니다",
            "file_path": abs_path,
            "line_number": line_number,
            "lines_inserted": len(indented_lines),
            "indent_level": indent_level,
            "diff": diff,
            "modified_content": modified_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"코드 삽입 실패: {file_path}"
        }


@app.tool()
def delete_lines_range(file_path: str, start_line: int, end_line: int = None) -> Dict[str, Any]:
    """
    지정된 범위의 라인들을 삭제합니다.
    
    Args:
        file_path: 수정할 파일 경로
        start_line: 삭제 시작 라인 번호 (1-based)
        end_line: 삭제 끝 라인 번호 (None이면 start_line만 삭제)
        
    Returns:
        Dict: 라인 삭제 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        lines = original_content.splitlines()
        
        # 기본값 설정
        if end_line is None:
            end_line = start_line
        
        # 라인 번호 유효성 검사
        if start_line < 1:
            start_line = 1
        if end_line < start_line:
            end_line = start_line
        if start_line > len(lines):
            return {
                "success": False,
                "error": f"시작 라인 {start_line}이 파일 범위를 벗어났습니다 (총 {len(lines)}줄)",
                "message": "유효한 라인 번호를 제공해주세요"
            }
        
        # 삭제할 라인들 저장 (미리보기용)
        start_idx = start_line - 1
        end_idx = min(end_line, len(lines))
        deleted_lines = lines[start_idx:end_idx]
        
        # 라인 삭제
        del lines[start_idx:end_idx]
        
        modified_content = '\n'.join(lines)
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"라인 {start_line}-{end_line} ({len(deleted_lines)}줄)을 삭제했습니다",
            "file_path": abs_path,
            "start_line": start_line,
            "end_line": end_line,
            "lines_deleted": len(deleted_lines),
            "deleted_content": deleted_lines,
            "diff": diff,
            "modified_content": modified_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"라인 삭제 실패: {file_path}"
        }


@app.tool()
def apply_smart_patch(file_path: str, target_function: str = None, 
                     target_class: str = None, patch_content: str = "",
                     patch_type: str = "replace") -> Dict[str, Any]:
    """
    스마트 패치를 적용합니다. 함수나 클래스를 찾아서 수정합니다.
    
    Args:
        file_path: 수정할 파일 경로
        target_function: 수정할 함수명 (선택)
        target_class: 수정할 클래스명 (선택)
        patch_content: 패치 내용
        patch_type: 패치 유형 (replace, insert_before, insert_after, append_to_body)
        
    Returns:
        Dict: 스마트 패치 결과 및 diff
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {abs_path}",
                "message": "유효한 파일 경로를 제공해주세요"
            }
        
        # 파일 읽기
        original_content = code_service.read_file_safely(abs_path)
        if original_content is None:
            return {
                "success": False,
                "error": "파일을 읽을 수 없습니다",
                "message": "파일 인코딩이나 권한을 확인해주세요"
            }
        
        # 언어 감지
        language = code_service.detect_language(abs_path)
        
        if language != "python":
            return {
                "success": False,
                "error": f"현재 {language} 언어는 스마트 패치를 지원하지 않습니다",
                "message": "Python 파일만 스마트 패치가 가능합니다"
            }
        
        lines = original_content.splitlines()
        modified_lines = lines.copy()
        changes_made = []
        
        if target_function:
            # 함수 찾기
            function_start = None
            function_end = None
            
            for i, line in enumerate(lines):
                if re.match(rf'^\s*def\s+{re.escape(target_function)}\s*\(', line):
                    function_start = i
                    # 함수 끝 찾기
                    indent_level = len(line) - len(line.lstrip())
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if (next_line.strip() and 
                            len(next_line) - len(next_line.lstrip()) <= indent_level and
                            not next_line.lstrip().startswith(('@', '"""', "'''"))):
                            function_end = j
                            break
                    if function_end is None:
                        function_end = len(lines)
                    break
            
            if function_start is not None:
                if patch_type == "replace":
                    # 함수 전체 교체
                    modified_lines[function_start:function_end] = patch_content.splitlines()
                    changes_made.append(f"함수 '{target_function}' 전체를 교체했습니다")
                    
                elif patch_type == "insert_before":
                    # 함수 앞에 삽입
                    modified_lines[function_start:function_start] = patch_content.splitlines()
                    changes_made.append(f"함수 '{target_function}' 앞에 코드를 삽입했습니다")
                    
                elif patch_type == "insert_after":
                    # 함수 뒤에 삽입
                    modified_lines[function_end:function_end] = patch_content.splitlines()
                    changes_made.append(f"함수 '{target_function}' 뒤에 코드를 삽입했습니다")
                    
                elif patch_type == "append_to_body":
                    # 함수 본문 끝에 추가
                    insert_pos = function_end - 1
                    # 함수의 들여쓰기 레벨 맞추기
                    func_line = lines[function_start]
                    base_indent = len(func_line) - len(func_line.lstrip())
                    body_indent = ' ' * (base_indent + 4)
                    
                    indented_content = []
                    for line in patch_content.splitlines():
                        if line.strip():
                            indented_content.append(body_indent + line)
                        else:
                            indented_content.append(line)
                    
                    modified_lines[insert_pos:insert_pos] = indented_content
                    changes_made.append(f"함수 '{target_function}' 본문에 코드를 추가했습니다")
            else:
                return {
                    "success": False,
                    "error": f"함수 '{target_function}'을 찾을 수 없습니다",
                    "message": "파일에서 해당 함수를 찾을 수 없습니다"
                }
        
        elif target_class:
            # 클래스 찾기 (비슷한 로직)
            class_start = None
            class_end = None
            
            for i, line in enumerate(lines):
                if re.match(rf'^\s*class\s+{re.escape(target_class)}\s*[\(:]', line):
                    class_start = i
                    # 클래스 끝 찾기
                    indent_level = len(line) - len(line.lstrip())
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if (next_line.strip() and 
                            len(next_line) - len(next_line.lstrip()) <= indent_level):
                            class_end = j
                            break
                    if class_end is None:
                        class_end = len(lines)
                    break
            
            if class_start is not None:
                if patch_type == "append_to_body":
                    # 클래스 본문 끝에 추가
                    insert_pos = class_end - 1
                    class_line = lines[class_start]
                    base_indent = len(class_line) - len(class_line.lstrip())
                    body_indent = ' ' * (base_indent + 4)
                    
                    indented_content = []
                    for line in patch_content.splitlines():
                        if line.strip():
                            indented_content.append(body_indent + line)
                        else:
                            indented_content.append(line)
                    
                    modified_lines[insert_pos:insert_pos] = indented_content
                    changes_made.append(f"클래스 '{target_class}' 본문에 코드를 추가했습니다")
            else:
                return {
                    "success": False,
                    "error": f"클래스 '{target_class}'을 찾을 수 없습니다",
                    "message": "파일에서 해당 클래스를 찾을 수 없습니다"
                }
        
        else:
            # 타겟이 지정되지 않은 경우 파일 끝에 추가
            modified_lines.extend(patch_content.splitlines())
            changes_made.append("파일 끝에 코드를 추가했습니다")
        
        modified_content = '\n'.join(modified_lines)
        
        # diff 생성
        diff = code_service.generate_diff(
            original_content, modified_content, abs_path)
        
        return {
            "success": True,
            "message": f"스마트 패치 완료: {len(changes_made)}개 변경",
            "file_path": abs_path,
            "target_function": target_function,
            "target_class": target_class,
            "patch_type": patch_type,
            "changes": changes_made,
            "diff": diff,
            "modified_content": modified_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"스마트 패치 실패: {file_path}"
        }


@app.tool()
def write_file_with_content(file_path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
    """
    파일에 새로운 내용을 씁니다 (전체 교체).

    Args:
        file_path: 쓸 파일 경로
        content: 파일에 쓸 전체 내용
        create_backup: 기존 파일의 백업 생성 여부 (기본값: True)

    Returns:
        Dict: 파일 쓰기 결과
    """
    try:
        abs_path = os.path.abspath(file_path)

        # 백업 생성 (파일이 존재하는 경우)
        backup_path = None
        if os.path.exists(abs_path) and create_backup:
            original_content = code_service.read_file_safely(abs_path)
            if original_content is not None:
                backup_path = f"{abs_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                except Exception:
                    backup_path = None

        # 디렉토리 생성 (필요한 경우)
        dir_path = os.path.dirname(abs_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # 파일 쓰기
        if not code_service.write_file_safely(abs_path, content):
            return {
                "success": False,
                "error": "파일 쓰기에 실패했습니다",
                "message": "파일 권한을 확인해주세요"
            }

        # 파일 정보
        file_size = len(content.encode('utf-8'))
        line_count = len(content.splitlines())

        return {
            "success": True,
            "message": f"파일을 성공적으로 작성했습니다: {abs_path}",
            "file_path": abs_path,
            "backup_path": backup_path,
            "file_size": file_size,
            "line_count": line_count,
            "operation": "write_complete"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"파일 쓰기 실패: {file_path}"
        }


if __name__ == "__main__":
    print("🤖 Coding Agent MCP Server")
    print("🔧 코드 분석, 수정, 리팩토링 도구 서버를 시작합니다...")

    try:
        app.run(transport="stdio")
    except KeyboardInterrupt:
        print("\n⏹️ 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {e}")
