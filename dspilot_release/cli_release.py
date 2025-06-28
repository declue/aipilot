#!/usr/bin/env python3

import ast
import re as _re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set


class CodeProcessor:

    def __init__(self):
        self.processed_files = 0
        self.skipped_files = 0

    def remove_comments_and_docstrings(self, source_code: str) -> str:
        try:
            tree = ast.parse(source_code)
            transformer = CommentRemover()
            cleaned_tree = transformer.visit(tree)
            return ast.unparse(cleaned_tree)
        except SyntaxError:
            return self._remove_comments_manually(source_code)

    def _remove_comments_manually(self, source_code: str) -> str:
        lines = source_code.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            if '#' in line:
                comment_pos = line.find('#')
                in_string = False
                quote_char = None

                for i, char in enumerate(line[:comment_pos]):
                    if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None

                if not in_string:
                    line = line[:comment_pos].rstrip()

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def process_python_file(self, file_path: Path) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            cleaned_content = self.remove_comments_and_docstrings(
                original_content)

            # 간단한 포스트 프로세싱: print 구문의 인용부호를 더블쿼트로 유지
            cleaned_content = _re.sub(r"print\('([^']*)'\)", r'print("\1")', cleaned_content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            self.processed_files += 1
            return True
        except Exception as e:
            print(f"파일 처리 실패 {file_path}: {e}")
            self.skipped_files += 1
            return False


class CommentRemover(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
        self._remove_docstring(node)
        self._ensure_body_not_empty(node)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._remove_docstring(node)
        self._ensure_body_not_empty(node)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        self._remove_docstring(node)
        self._ensure_body_not_empty(node)
        return self.generic_visit(node)

    def visit_Module(self, node):
        self._remove_docstring(node)
        return self.generic_visit(node)

    def _remove_docstring(self, node):
        if (node.body and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)):
            node.body.pop(0)

    def _ensure_body_not_empty(self, node):
        if not node.body:
            node.body.append(ast.Pass())


class FileManager:

    def __init__(self, source_root: Path, target_root: Path):
        self.source_root = source_root
        self.target_root = target_root
        self.copied_files = 0
        self.skipped_files = 0

    def copy_folder(self, folder_name: str, exclude_patterns: Optional[Set[str]] = None) -> bool:
        source_path = self.source_root / folder_name
        target_path = self.target_root / folder_name

        if not source_path.exists():
            print(f"소스 폴더가 존재하지 않습니다: {source_path}")
            return False

        if target_path.exists():
            shutil.rmtree(target_path)

        try:
            shutil.copytree(source_path, target_path,
                            ignore=self._create_ignore_function(exclude_patterns))
            print(f"폴더 복사 완료: {folder_name}")
            return True
        except Exception as e:
            print(f"폴더 복사 실패 {folder_name}: {e}")
            return False

    def _create_ignore_function(self, exclude_patterns: Optional[Set[str]]):
        if not exclude_patterns:
            exclude_patterns = set()

        default_excludes = {
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.pytest_cache',
            '.coverage',
            '.git',
            '.vscode',
            '.idea'
        }
        exclude_patterns.update(default_excludes)

        def ignore_function(dir_path, filenames):
            ignored = []
            for filename in filenames:
                file_path = Path(dir_path) / filename

                if filename in exclude_patterns:
                    ignored.append(filename)
                elif any(filename.endswith(pattern.lstrip('*')) for pattern in exclude_patterns if pattern.startswith('*')):
                    ignored.append(filename)
                elif file_path.is_file() and filename.endswith(('.md', '.txt', '.rst')):
                    ignored.append(filename)

            return ignored

        return ignore_function

    def get_python_files(self, folder_path: Path) -> List[Path]:
        python_files = []
        for file_path in folder_path.rglob('*.py'):
            if not any(part.startswith('.') for part in file_path.parts):
                python_files.append(file_path)
        return python_files


class ReleaseBuilder:

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = project_root
        self.release_root = project_root / 'dspilot_release' / 'release_cli'
        self.code_processor = CodeProcessor()
        self.file_manager = FileManager(project_root, self.release_root)

    def build_clean_release(self, folders_to_copy: List[str], exclude_patterns: Optional[Set[str]] = None) -> bool:
        print("클린 릴리스 빌드 시작")
        print(f"소스: {self.project_root}")
        print(f"타겟: {self.release_root}")

        if self.release_root.exists():
            shutil.rmtree(self.release_root)
        self.release_root.mkdir(parents=True, exist_ok=True)

        success = True

        for folder in folders_to_copy:
            if not self.file_manager.copy_folder(folder, exclude_patterns):
                success = False
                continue

            self._process_folder_files(folder)

        self._create_clean_init_file()
        self._create_clean_setup_files()

        self._print_summary()
        return success

    def _process_folder_files(self, folder_name: str):
        folder_path = self.release_root / folder_name
        python_files = self.file_manager.get_python_files(folder_path)

        print(f"{folder_name} 폴더에서 {len(python_files)}개 Python 파일 처리 중...")

        for file_path in python_files:
            self.code_processor.process_python_file(file_path)

    def _create_clean_init_file(self):
        init_content = '''#!/usr/bin/env python3

__version__ = "1.0.0"
__author__ = "DSPilot Team"

from dspilot_cli.cli_main import main

__all__ = ["main"]
'''

        # 대상 디렉터리 보장
        self.release_root.mkdir(parents=True, exist_ok=True)
        init_file = self.release_root / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(init_content)

    def _create_clean_setup_files(self):
        setup_content = '''#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="dspilot-clean",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "colorama>=0.4.4",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "openai>=1.0.0",
        "pydantic>=2.0.0",
        "PyQt6>=6.5.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "dspilot=dspilot_cli.cli_main:main",
        ],
    },
)
'''

        # 대상 디렉터리 보장
        self.release_root.mkdir(parents=True, exist_ok=True)
        setup_file = self.release_root / 'setup.py'
        with open(setup_file, 'w', encoding='utf-8') as f:
            f.write(setup_content)

        readme_content = '''# DSPilot Clean Release

Clean version of DSPilot without comments and documentation.
'''

        readme_file = self.release_root / 'README.md'
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def _print_summary(self):
        print("=== 릴리스 빌드 완료 ===")
        print(f"처리된 Python 파일: {self.code_processor.processed_files}")
        print(f"건너뛴 파일: {self.code_processor.skipped_files}")
        print(f"릴리스 위치: {self.release_root}")

    def build_executable(self) -> bool:
        """PyInstaller를 사용하여 실행파일 생성"""
        print("\n🔨 PyInstaller로 실행파일 생성 중...")

        if not self._check_pyinstaller():
            return False

        entry_point = self.release_root / 'dspilot_cli' / '__main__.py'
        if not entry_point.exists():
            self._create_entry_point()

        spec_file = self._create_pyinstaller_spec()
        return self._run_pyinstaller(spec_file)

    def _check_pyinstaller(self) -> bool:
        """PyInstaller 설치 확인"""
        try:
            result = subprocess.run(['pyinstaller', '--version'],
                                    capture_output=True, text=True, check=True)
            print(f"✅ PyInstaller 버전: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ PyInstaller가 설치되지 않았습니다.")
            print("설치 명령: pip install pyinstaller")
            return False

    def _create_entry_point(self):
        """PyInstaller용 진입점 파일 생성"""
        entry_content = '''#!/usr/bin/env python3

import sys
import os
import asyncio
from pathlib import Path

# PyInstaller 실행 시 sys.path 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
else:
    # 일반 Python 실행의 경우
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

try:
    from dspilot_cli.cli_main import main
    
    if __name__ == "__main__":
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\\n프로그램이 종료되었습니다.")
        except Exception as e:
            print(f"오류 발생: {e}")
            sys.exit(1)
except ImportError as e:
    print(f"모듈 import 오류: {e}")
    print("dspilot_cli 모듈을 찾을 수 없습니다.")
    sys.exit(1)
'''

        entry_file = self.release_root / 'dspilot_cli' / '__main__.py'
        with open(entry_file, 'w', encoding='utf-8') as f:
            f.write(entry_content)
        print(f"✅ 진입점 파일 생성: {entry_file}")

    def _create_pyinstaller_spec(self) -> Path:
        """PyInstaller spec 파일 생성 (항상 onefile 모드)"""

        # Onefile 모드
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['{self.release_root / "dspilot_cli" / "__main__.py"}'],
    pathex=['{self.release_root}'],
    binaries=[],
    datas=[
        ('{self.release_root / "dspilot_core"}', 'dspilot_core')
    ],
    hiddenimports=[
        'ddc459050edb75a05942__mypyc',
        'asyncio',
        'aiohttp',
        'colorama',
        'langchain',
        'langchain_openai',
        'langchain_core',
        'langchain_community',
        'openai',
        'pydantic',
        'pydantic_core',
        'requests',
        'yaml',
        'json',
        'configparser',
        'pkg_resources',
        'setuptools',
        'distutils',
        'tomli',
        'tomli_w',
        'tomllib',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'pytest',
        'unittest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dspilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=None,
)
'''

        spec_file = self.release_root / 'dspilot.spec'
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        print(f"✅ PyInstaller spec 파일 생성: {spec_file}")
        return spec_file

    def _run_pyinstaller(self, spec_file: Path) -> bool:
        """PyInstaller 실행"""
        try:
            print("🔄 PyInstaller 실행 중... (시간이 오래 걸릴 수 있습니다)")

            cmd = [
                'pyinstaller',
                '--clean',
                '--noconfirm',
                str(spec_file)
            ]

            result = subprocess.run(
                cmd,
                cwd=self.release_root,
                capture_output=True,
                text=True,
                check=True
            )

            dist_dir = self.release_root / 'dist'
            if dist_dir.exists():
                executable_files = list(dist_dir.rglob('dspilot*'))
                if executable_files:
                    print(f"🎉 실행파일 생성 완료!")
                    for exe_file in executable_files:
                        file_size = exe_file.stat().st_size / (1024 * 1024)
                        print(f"   📦 {exe_file} ({file_size:.1f}MB)")
                    return True

            print("❌ 실행파일 생성 실패: dist 폴더를 찾을 수 없습니다")
            return False

        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller 실행 실패:")
            print(f"   명령: {' '.join(cmd)}")
            print(f"   오류: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ 실행파일 생성 중 오류: {e}")
            return False


def main():

    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("사용법: python cli_release.py [옵션]")
        print("dspilot_cli와 dspilot_core 폴더에서 클린 릴리스를 생성합니다.")
        print("\n옵션:")
        print("  --exe, -e          실행파일 생성 (PyInstaller 필요)")
        print("  --help, -h         이 도움말 표시")
        return

    # 명령행 인수 처리
    create_executable = '--exe' in sys.argv or '-e' in sys.argv

    builder = ReleaseBuilder()

    folders_to_copy = ['dspilot_cli', 'dspilot_core']
    exclude_patterns = {
        'tests',
        'test_*.py',
        '*_test.py',
        '*.md',
        '*.txt',
        '*.rst',
        'docs',
        '__pycache__',
        '.pytest_cache'
    }

    # 1단계: 클린 릴리스 빌드
    success = builder.build_clean_release(folders_to_copy, exclude_patterns)

    if not success:
        print("릴리스 빌드 중 일부 오류가 발생했습니다.")
        sys.exit(1)

    # 2단계: 실행파일 생성 (옵션)
    if create_executable:
        exe_success = builder.build_executable()
        if exe_success:
            print("\n🎉 모든 작업이 성공적으로 완료되었습니다!")
            print("📁 클린 릴리스와 실행파일이 생성되었습니다.")
        else:
            print("\n⚠️ 클린 릴리스는 완료되었으나 실행파일 생성에 실패했습니다.")
            sys.exit(1)
    else:
        print("\n✅ 클린 릴리스 빌드가 성공적으로 완료되었습니다.")
        print("💡 실행파일을 생성하려면 --exe 옵션을 사용하세요.")

    sys.exit(0)


if __name__ == "__main__":
    main()
