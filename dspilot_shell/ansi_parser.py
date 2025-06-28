"""
ANSI 이스케이프 시퀀스 파서
터미널 색상, 커서 제어, 텍스트 속성 처리
"""
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from PySide6.QtGui import QColor, QTextCharFormat, QFont


class AnsiColor(Enum):
    """ANSI 색상 코드"""
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    BRIGHT_BLACK = 8
    BRIGHT_RED = 9
    BRIGHT_GREEN = 10
    BRIGHT_YELLOW = 11
    BRIGHT_BLUE = 12
    BRIGHT_MAGENTA = 13
    BRIGHT_CYAN = 14
    BRIGHT_WHITE = 15


@dataclass
class TerminalStyle:
    """터미널 스타일 정보"""
    foreground: Optional[QColor] = None
    background: Optional[QColor] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False


class AnsiParser:
    """ANSI 이스케이프 시퀀스 파서"""
    
    # ANSI 색상 매핑 (어두운 배경에 적합)
    ANSI_COLORS = {
        AnsiColor.BLACK: QColor(0, 0, 0),
        AnsiColor.RED: QColor(205, 49, 49),
        AnsiColor.GREEN: QColor(13, 188, 121),
        AnsiColor.YELLOW: QColor(229, 229, 16),
        AnsiColor.BLUE: QColor(36, 114, 200),
        AnsiColor.MAGENTA: QColor(188, 63, 188),
        AnsiColor.CYAN: QColor(17, 168, 205),
        AnsiColor.WHITE: QColor(229, 229, 229),
        AnsiColor.BRIGHT_BLACK: QColor(102, 102, 102),
        AnsiColor.BRIGHT_RED: QColor(241, 76, 76),
        AnsiColor.BRIGHT_GREEN: QColor(35, 209, 139),
        AnsiColor.BRIGHT_YELLOW: QColor(245, 245, 67),
        AnsiColor.BRIGHT_BLUE: QColor(59, 142, 234),
        AnsiColor.BRIGHT_MAGENTA: QColor(214, 112, 214),
        AnsiColor.BRIGHT_CYAN: QColor(41, 184, 219),
        AnsiColor.BRIGHT_WHITE: QColor(255, 255, 255),
    }
    
    def __init__(self):
        # ANSI 이스케이프 시퀀스 패턴
        self.escape_pattern = re.compile(r'\x1b\[[0-9;]*[mKHfABCDsuhl]|\x1b\][0-9];.*?\x07|\x1b\]0;.*?\x07|\x1b\[.*?[hl]|\x1b\[.*?[LM]|\x1b\[\?.*?[hl]')
        
        # 현재 스타일 상태
        self.current_style = TerminalStyle()
        self.default_style = TerminalStyle(foreground=QColor(255, 255, 255))
        
        # 커서 상태
        self.cursor_position = [0, 0]  # [row, col]
        
    def parse_text(self, text: str) -> List[Tuple[str, TerminalStyle]]:
        """
        텍스트를 파싱하여 스타일이 적용된 텍스트 청크 리스트 반환
        
        Returns:
            List[Tuple[str, TerminalStyle]]: (텍스트, 스타일) 튜플 리스트
        """
        chunks = []
        last_pos = 0
        
        for match in self.escape_pattern.finditer(text):
            # 이스케이프 시퀀스 이전의 텍스트
            if match.start() > last_pos:
                plain_text = text[last_pos:match.start()]
                if plain_text:
                    # 제어 문자 처리
                    plain_text = self._process_control_chars(plain_text)
                    if plain_text:
                        chunks.append((plain_text, self._copy_style(self.current_style)))
            
            # 이스케이프 시퀀스 처리
            escape_seq = match.group()
            self._process_escape_sequence(escape_seq)
            
            last_pos = match.end()
        
        # 마지막 텍스트
        if last_pos < len(text):
            plain_text = text[last_pos:]
            if plain_text:
                plain_text = self._process_control_chars(plain_text)
                if plain_text:
                    chunks.append((plain_text, self._copy_style(self.current_style)))
        
        return chunks
    
    def _process_control_chars(self, text: str) -> str:
        """제어 문자 처리"""
        # 백스페이스, 캐리지 리턴 등 처리
        text = text.replace('\x08', '')  # 백스페이스 제거
        text = text.replace('\x0D', '')  # 캐리지 리턴 제거 (줄바꿈은 \n만 사용)
        text = text.replace('\x00', '')  # NULL 문자 제거
        
        # 기타 출력할 수 없는 제어 문자 제거
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        return text
    
    def _process_escape_sequence(self, seq: str):
        """이스케이프 시퀀스 처리"""
        if seq.startswith('\x1b[') and seq.endswith('m'):
            # SGR (Select Graphic Rendition) 처리
            self._process_sgr(seq)
        elif seq.startswith('\x1b[') and seq.endswith('K'):
            # 라인 지우기
            pass  # 현재는 무시
        elif seq.startswith('\x1b[') and seq.endswith('H'):
            # 커서 위치 설정
            self._process_cursor_position(seq)
        elif seq.startswith('\x1b[') and seq[-1] in 'ABCD':
            # 커서 이동
            self._process_cursor_movement(seq)
        elif seq.startswith('\x1b]'):
            # OSC (Operating System Command) - 제목 설정 등
            pass  # 현재는 무시
        elif '\x1b[?' in seq:
            # 모드 설정/해제
            pass  # 현재는 무시
    
    def _process_sgr(self, seq: str):
        """SGR (텍스트 속성) 처리"""
        # \x1b[숫자;숫자;...m 형태
        codes_str = seq[2:-1]  # \x1b[ 와 m 제거
        
        if not codes_str:
            codes = [0]
        else:
            try:
                codes = [int(x) for x in codes_str.split(';') if x]
            except ValueError:
                return
        
        i = 0
        while i < len(codes):
            code = codes[i]
            
            if code == 0:
                # 리셋
                self.current_style = self._copy_style(self.default_style)
            elif code == 1:
                # 굵게
                self.current_style.bold = True
            elif code == 3:
                # 기울임
                self.current_style.italic = True
            elif code == 4:
                # 밑줄
                self.current_style.underline = True
            elif code == 9:
                # 취소선
                self.current_style.strikethrough = True
            elif code == 22:
                # 굵게 해제
                self.current_style.bold = False
            elif code == 23:
                # 기울임 해제
                self.current_style.italic = False
            elif code == 24:
                # 밑줄 해제
                self.current_style.underline = False
            elif code == 29:
                # 취소선 해제
                self.current_style.strikethrough = False
            elif 30 <= code <= 37:
                # 전경색 (일반)
                color_index = AnsiColor(code - 30)
                self.current_style.foreground = self.ANSI_COLORS[color_index]
            elif code == 39:
                # 기본 전경색
                self.current_style.foreground = self.default_style.foreground
            elif 40 <= code <= 47:
                # 배경색 (일반)
                color_index = AnsiColor(code - 40)
                self.current_style.background = self.ANSI_COLORS[color_index]
            elif code == 49:
                # 기본 배경색
                self.current_style.background = None
            elif 90 <= code <= 97:
                # 전경색 (밝은)
                color_index = AnsiColor(code - 90 + 8)
                self.current_style.foreground = self.ANSI_COLORS[color_index]
            elif 100 <= code <= 107:
                # 배경색 (밝은)
                color_index = AnsiColor(code - 100 + 8)
                self.current_style.background = self.ANSI_COLORS[color_index]
            elif code == 38:
                # 256색 또는 RGB 전경색
                if i + 1 < len(codes):
                    if codes[i + 1] == 5 and i + 2 < len(codes):
                        # 256색
                        color_code = codes[i + 2]
                        self.current_style.foreground = self._get_256_color(color_code)
                        i += 2
                    elif codes[i + 1] == 2 and i + 4 < len(codes):
                        # RGB
                        r, g, b = codes[i + 2], codes[i + 3], codes[i + 4]
                        self.current_style.foreground = QColor(r, g, b)
                        i += 4
            elif code == 48:
                # 256색 또는 RGB 배경색
                if i + 1 < len(codes):
                    if codes[i + 1] == 5 and i + 2 < len(codes):
                        # 256색
                        color_code = codes[i + 2]
                        self.current_style.background = self._get_256_color(color_code)
                        i += 2
                    elif codes[i + 1] == 2 and i + 4 < len(codes):
                        # RGB
                        r, g, b = codes[i + 2], codes[i + 3], codes[i + 4]
                        self.current_style.background = QColor(r, g, b)
                        i += 4
            
            i += 1
    
    def _get_256_color(self, code: int) -> QColor:
        """256색 팔레트에서 색상 반환"""
        if code < 16:
            # 기본 16색
            return self.ANSI_COLORS[AnsiColor(code)]
        elif code < 232:
            # 216색 큐브 (6x6x6)
            code -= 16
            r = (code // 36) * 51
            g = ((code % 36) // 6) * 51
            b = (code % 6) * 51
            return QColor(r, g, b)
        else:
            # 24단계 그레이스케일
            gray = (code - 232) * 10 + 8
            return QColor(gray, gray, gray)
    
    def _process_cursor_position(self, seq: str):
        """커서 위치 설정"""
        # \x1b[행;열H 형태
        coords = seq[2:-1]
        if coords:
            try:
                parts = coords.split(';')
                if len(parts) >= 2:
                    row = int(parts[0]) - 1 if parts[0] else 0
                    col = int(parts[1]) - 1 if parts[1] else 0
                    self.cursor_position = [max(0, row), max(0, col)]
            except ValueError:
                pass
    
    def _process_cursor_movement(self, seq: str):
        """커서 이동"""
        direction = seq[-1]
        amount_str = seq[2:-1]
        
        try:
            amount = int(amount_str) if amount_str else 1
        except ValueError:
            amount = 1
        
        if direction == 'A':  # 위로
            self.cursor_position[0] = max(0, self.cursor_position[0] - amount)
        elif direction == 'B':  # 아래로
            self.cursor_position[0] += amount
        elif direction == 'C':  # 오른쪽으로
            self.cursor_position[1] += amount
        elif direction == 'D':  # 왼쪽으로
            self.cursor_position[1] = max(0, self.cursor_position[1] - amount)
    
    def _copy_style(self, style: TerminalStyle) -> TerminalStyle:
        """스타일 복사"""
        return TerminalStyle(
            foreground=style.foreground,
            background=style.background,
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strikethrough=style.strikethrough
        )
    
    def create_text_format(self, style: TerminalStyle) -> QTextCharFormat:
        """TerminalStyle을 QTextCharFormat으로 변환"""
        fmt = QTextCharFormat()
        
        # 전경색
        if style.foreground:
            fmt.setForeground(style.foreground)
        
        # 배경색
        if style.background:
            fmt.setBackground(style.background)
        
        # 텍스트 속성
        if style.bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        
        if style.italic:
            fmt.setFontItalic(True)
        
        if style.underline:
            fmt.setFontUnderline(True)
        
        if style.strikethrough:
            fmt.setFontStrikeOut(True)
        
        return fmt
    
    def reset(self):
        """파서 상태 리셋"""
        self.current_style = self._copy_style(self.default_style)
        self.cursor_position = [0, 0]
