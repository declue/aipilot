#!/usr/bin/env python3

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dspilot_release.cli_release import CodeProcessor, CommentRemover, FileManager, ReleaseBuilder


class TestCodeProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = CodeProcessor()
    
    def test_remove_comments_and_docstrings_basic(self):
        source_code = '''
def test_function():
    """이것은 docstring입니다."""
    # 이것은 주석입니다
    x = 1  # 인라인 주석
    return x
'''
        result = self.processor.remove_comments_and_docstrings(source_code)
        
        self.assertNotIn('docstring', result)
        self.assertNotIn('주석', result)
        self.assertIn('x = 1', result)
        self.assertIn('return x', result)
    
    def test_remove_comments_manual_fallback(self):
        source_code = '''
# 이것은 파일 상단 주석입니다
x = 1  # 이것은 인라인 주석입니다
y = "문자열 # 이것은 주석이 아닙니다"
# 또 다른 주석
z = 2
'''
        result = self.processor._remove_comments_manually(source_code)
        
        self.assertNotIn('파일 상단 주석', result)
        self.assertNotIn('인라인 주석', result)
        self.assertNotIn('또 다른 주석', result)
        self.assertIn('x = 1', result)
        self.assertIn('문자열 # 이것은 주석이 아닙니다', result)
        self.assertIn('z = 2', result)
    
    def test_process_python_file_success(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def test():
    """테스트 함수"""
    # 주석
    return True
''')
            temp_file = Path(f.name)
        
        try:
            result = self.processor.process_python_file(temp_file)
            self.assertTrue(result)
            self.assertEqual(self.processor.processed_files, 1)
            
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertNotIn('테스트 함수', content)
                self.assertNotIn('주석', content)
        finally:
            temp_file.unlink()
    
    def test_process_python_file_syntax_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def broken_syntax(:\n    pass')
            temp_file = Path(f.name)
        
        try:
            result = self.processor.process_python_file(temp_file)
            self.assertTrue(result)
        finally:
            temp_file.unlink()


class TestCommentRemover(unittest.TestCase):
    
    def setUp(self):
        self.remover = CommentRemover()
    
    def test_visit_function_def(self):
        source = '''
def test_function():
    """함수 docstring"""
    pass
'''
        tree = ast.parse(source)
        cleaned_tree = self.remover.visit(tree)
        
        func_node = cleaned_tree.body[0]
        self.assertEqual(len(func_node.body), 1)
        self.assertIsInstance(func_node.body[0], ast.Pass)
    
    def test_visit_class_def(self):
        source = '''
class TestClass:
    """클래스 docstring"""
    
    def method(self):
        """메서드 docstring"""
        pass
'''
        tree = ast.parse(source)
        cleaned_tree = self.remover.visit(tree)
        
        class_node = cleaned_tree.body[0]
        self.assertEqual(len(class_node.body), 1)
        
        method_node = class_node.body[0]
        self.assertEqual(len(method_node.body), 1)
        self.assertIsInstance(method_node.body[0], ast.Pass)
    
    def test_visit_module(self):
        source = '''
"""모듈 docstring"""

def function():
    pass
'''
        tree = ast.parse(source)
        cleaned_tree = self.remover.visit(tree)
        
        self.assertEqual(len(cleaned_tree.body), 1)
        self.assertIsInstance(cleaned_tree.body[0], ast.FunctionDef)


class TestFileManager(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.source_root = Path(self.temp_dir) / 'source'
        self.target_root = Path(self.temp_dir) / 'target'
        self.source_root.mkdir()
        self.target_root.mkdir()
        self.file_manager = FileManager(self.source_root, self.target_root)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_copy_folder_success(self):
        test_folder = self.source_root / 'test_folder'
        test_folder.mkdir()
        
        test_file = test_folder / 'test.py'
        test_file.write_text('print("hello")')
        
        result = self.file_manager.copy_folder('test_folder')
        self.assertTrue(result)
        
        copied_file = self.target_root / 'test_folder' / 'test.py'
        self.assertTrue(copied_file.exists())
        self.assertEqual(copied_file.read_text(), 'print("hello")')
    
    def test_copy_folder_nonexistent(self):
        result = self.file_manager.copy_folder('nonexistent_folder')
        self.assertFalse(result)
    
    def test_copy_folder_with_excludes(self):
        test_folder = self.source_root / 'test_folder'
        test_folder.mkdir()
        
        (test_folder / 'keep.py').write_text('keep this')
        (test_folder / 'exclude.md').write_text('exclude this')
        (test_folder / '__pycache__').mkdir()
        
        exclude_patterns = {'*.md', '__pycache__'}
        result = self.file_manager.copy_folder('test_folder', exclude_patterns)
        self.assertTrue(result)
        
        self.assertTrue((self.target_root / 'test_folder' / 'keep.py').exists())
        self.assertFalse((self.target_root / 'test_folder' / 'exclude.md').exists())
        self.assertFalse((self.target_root / 'test_folder' / '__pycache__').exists())
    
    def test_get_python_files(self):
        test_folder = self.source_root / 'test_folder'
        test_folder.mkdir()
        
        (test_folder / 'file1.py').write_text('# python file 1')
        (test_folder / 'file2.py').write_text('# python file 2')
        (test_folder / 'not_python.txt').write_text('not python')
        
        subfolder = test_folder / 'subfolder'
        subfolder.mkdir()
        (subfolder / 'file3.py').write_text('# python file 3')
        
        python_files = self.file_manager.get_python_files(test_folder)
        
        self.assertEqual(len(python_files), 3)
        file_names = [f.name for f in python_files]
        self.assertIn('file1.py', file_names)
        self.assertIn('file2.py', file_names)
        self.assertIn('file3.py', file_names)


class TestReleaseBuilder(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.builder = ReleaseBuilder(self.project_root)
        
        self._create_test_structure()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_structure(self):
        (self.project_root / 'dspilot_cli').mkdir()
        (self.project_root / 'dspilot_core').mkdir()
        
        cli_file = self.project_root / 'dspilot_cli' / 'main.py'
        cli_file.write_text('''
"""CLI 모듈 docstring"""
# 주석
def main():
    """메인 함수"""
    # 또 다른 주석
    print("hello")
''')
        
        core_file = self.project_root / 'dspilot_core' / 'config.py'
        core_file.write_text('''
"""Core 모듈 docstring"""
class Config:
    """설정 클래스"""
    def __init__(self):
        # 초기화 주석
        self.value = 1
''')
    
    def test_build_clean_release(self):
        folders_to_copy = ['dspilot_cli', 'dspilot_core']
        result = self.builder.build_clean_release(folders_to_copy)
        
        self.assertTrue(result)
        self.assertTrue(self.builder.release_root.exists())
        
        cli_file = self.builder.release_root / 'dspilot_cli' / 'main.py'
        self.assertTrue(cli_file.exists())
        
        content = cli_file.read_text()
        self.assertNotIn('CLI 모듈 docstring', content)
        self.assertNotIn('메인 함수', content)
        self.assertNotIn('주석', content)
        self.assertIn('print("hello")', content)
    
    def test_create_clean_init_file(self):
        self.builder._create_clean_init_file()
        
        init_file = self.builder.release_root / '__init__.py'
        self.assertTrue(init_file.exists())
        
        content = init_file.read_text()
        self.assertIn('__version__ = "1.0.0"', content)
        self.assertIn('from dspilot_cli.cli_main import main', content)
    
    def test_create_clean_setup_files(self):
        self.builder._create_clean_setup_files()
        
        setup_file = self.builder.release_root / 'setup.py'
        readme_file = self.builder.release_root / 'README.md'
        
        self.assertTrue(setup_file.exists())
        self.assertTrue(readme_file.exists())
        
        setup_content = setup_file.read_text()
        self.assertIn('name="dspilot-clean"', setup_content)
        self.assertIn('dspilot=dspilot_cli.cli_main:main', setup_content)
    
    @patch('builtins.print')
    def test_print_summary(self, mock_print):
        self.builder.code_processor.processed_files = 5
        self.builder.code_processor.skipped_files = 1
        
        self.builder._print_summary()
        
        mock_print.assert_any_call("=== 릴리스 빌드 완료 ===")
        mock_print.assert_any_call("처리된 Python 파일: 5")
        mock_print.assert_any_call("건너뛴 파일: 1")


class TestMainFunction(unittest.TestCase):
    
    @patch('sys.argv', ['cli_release.py', '--help'])
    @patch('builtins.print')
    def test_main_help(self, mock_print):
        from dspilot_release.cli_release import main
        
        main()
        
        mock_print.assert_any_call("사용법: python cli_release.py")
    
    @patch('sys.argv', ['cli_release.py'])
    @patch('dspilot_release.cli_release.ReleaseBuilder')
    def test_main_success(self, mock_builder_class):
        mock_builder = Mock()
        mock_builder.build_clean_release.return_value = True
        mock_builder_class.return_value = mock_builder
        
        from dspilot_release.cli_release import main
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_with(0)
    
    @patch('sys.argv', ['cli_release.py'])
    @patch('dspilot_release.cli_release.ReleaseBuilder')
    def test_main_failure(self, mock_builder_class):
        mock_builder = Mock()
        mock_builder.build_clean_release.return_value = False
        mock_builder_class.return_value = mock_builder
        
        from dspilot_release.cli_release import main
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_with(1)


if __name__ == '__main__':
    unittest.main() 