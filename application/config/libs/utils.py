"""
설정 관리 유틸리티 함수들

독립성을 위해 최소한의 의존성으로 구현되었습니다.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from application.config.libs.interfaces import ConfigDict, ConfigType, ConfigValue


def get_nested_value(
    data: ConfigDict, key: str, fallback: Optional[ConfigValue] = None
) -> ConfigValue:
    """점 표기법으로 중첩된 설정값 가져오기

    Args:
        data: 설정 데이터
        key: 설정 키 (예: 'section.subsection.key')
        fallback: 기본값

    Returns:
        설정값

    Examples:
        >>> data = {'app': {'ui': {'theme': 'dark'}}}
        >>> get_nested_value(data, 'app.ui.theme')
        'dark'
        >>> get_nested_value(data, 'app.ui.nonexistent', 'light')
        'light'
    """
    try:
        keys = key.split(".")
        value = data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return fallback

        return value
    except Exception:
        return fallback


def set_nested_value(data: ConfigDict, key: str, value: ConfigValue) -> None:
    """점 표기법으로 중첩된 설정값 설정

    Args:
        data: 설정 데이터 (수정됨)
        key: 설정 키 (예: 'section.subsection.key')
        value: 설정값

    Examples:
        >>> data = {}
        >>> set_nested_value(data, 'app.ui.theme', 'dark')
        >>> print(data)
        {'app': {'ui': {'theme': 'dark'}}}
    """
    keys = key.split(".")
    current = data

    # 마지막 키를 제외하고 중간 딕셔너리들 생성
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        elif not isinstance(current[k], dict):
            # 기존 값이 딕셔너리가 아니면 딕셔너리로 변경
            current[k] = {}
        current = current[k]

    # 최종 값 설정
    current[keys[-1]] = value


def has_nested_key(data: ConfigDict, key: str) -> bool:
    """점 표기법으로 중첩된 키 존재 여부 확인

    Args:
        data: 설정 데이터
        key: 설정 키

    Returns:
        키 존재 여부
    """
    try:
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False

        return True
    except Exception:
        return False


def remove_nested_key(data: ConfigDict, key: str) -> bool:
    """점 표기법으로 중첩된 키 제거

    Args:
        data: 설정 데이터 (수정됨)
        key: 설정 키

    Returns:
        제거 성공 여부
    """
    try:
        keys = key.split(".")
        current = data

        # 마지막 키를 제외하고 탐색
        for k in keys[:-1]:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False

        # 최종 키 제거
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return True

        return False
    except Exception:
        return False


def merge_configs(base: ConfigDict, override: ConfigDict, deep: bool = True) -> ConfigDict:
    """설정 딕셔너리 병합

    Args:
        base: 기본 설정
        override: 덮어쓸 설정
        deep: 깊은 병합 여부

    Returns:
        병합된 설정 딕셔너리
    """
    result = base.copy()

    for key, value in override.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value, deep=True)
        else:
            result[key] = value

    return result


def flatten_config(
    data: ConfigDict, separator: str = ".", prefix: str = ""
) -> Dict[str, ConfigValue]:
    """중첩된 설정을 평면화

    Args:
        data: 설정 데이터
        separator: 키 구분자
        prefix: 키 접두사

    Returns:
        평면화된 설정 딕셔너리

    Examples:
        >>> data = {'app': {'ui': {'theme': 'dark', 'size': 14}}}
        >>> flatten_config(data)
        {'app.ui.theme': 'dark', 'app.ui.size': 14}
    """
    result = {}

    for key, value in data.items():
        full_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_config(value, separator, full_key))
        else:
            result[full_key] = value

    return result


def unflatten_config(data: Dict[str, ConfigValue], _separator: str = ".") -> ConfigDict:
    """평면화된 설정을 중첩 구조로 복원

    Args:
        data: 평면화된 설정 데이터
        separator: 키 구분자

    Returns:
        중첩된 설정 딕셔너리

    Examples:
        >>> data = {'app.ui.theme': 'dark', 'app.ui.size': 14}
        >>> unflatten_config(data)
        {'app': {'ui': {'theme': 'dark', 'size': 14}}}
    """
    result = {}

    for key, value in data.items():
        set_nested_value(result, key, value)

    return result


def detect_config_type(file_path: Union[str, Path]) -> ConfigType:
    """파일 확장자로 설정 파일 타입 감지

    Args:
        file_path: 파일 경로

    Returns:
        설정 파일 타입

    Raises:
        ValueError: 지원하지 않는 파일 확장자인 경우
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    mapping = {
        ".json": ConfigType.JSON,
        ".ini": ConfigType.INI,
        ".cfg": ConfigType.INI,
        ".conf": ConfigType.INI,
        ".config": ConfigType.INI,
        ".yaml": ConfigType.YAML,
        ".yml": ConfigType.YAML,
        ".toml": ConfigType.TOML,
        ".xml": ConfigType.XML,
    }

    if ext in mapping:
        return mapping[ext]
    else:
        raise ValueError(f"지원하지 않는 파일 확장자: {ext}")


def ensure_config_dir(file_path: Union[str, Path]) -> None:
    """설정 파일 디렉토리 생성

    Args:
        file_path: 설정 파일 경로
    """
    path = Path(file_path)
    directory = path.parent

    if directory and not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)


def backup_config_file(file_path: Union[str, Path], backup_suffix: str = ".bak") -> Optional[str]:
    """설정 파일 백업

    Args:
        file_path: 원본 파일 경로
        backup_suffix: 백업 파일 접미사

    Returns:
        백업 파일 경로 (실패 시 None)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        backup_path = path.with_suffix(path.suffix + backup_suffix)

        # 기존 백업이 있으면 번호 추가
        counter = 1
        while backup_path.exists():
            backup_path = path.with_suffix(f"{path.suffix}{backup_suffix}.{counter}")
            counter += 1

        import shutil

        shutil.copy2(path, backup_path)
        return str(backup_path)
    except Exception:
        return None


def validate_config_structure(
    data: ConfigDict, required_keys: List[str], optional_keys: Optional[List[str]] = None
) -> List[str]:
    """설정 구조 검증

    Args:
        data: 설정 데이터
        required_keys: 필수 키 목록 (점 표기법 지원)
        optional_keys: 선택적 키 목록

    Returns:
        오류 메시지 목록
    """
    errors = []

    # 필수 키 확인
    for key in required_keys:
        if not has_nested_key(data, key):
            errors.append(f"필수 키가 없습니다: {key}")

    # 모든 키 목록
    all_allowed_keys = set(required_keys)
    if optional_keys:
        all_allowed_keys.update(optional_keys)

    # 허용되지 않은 키 확인
    flattened = flatten_config(data)
    for key in flattened.keys():
        if key not in all_allowed_keys:
            # 부분 매칭도 확인 (중첩 구조 고려)
            is_allowed = any(
                key.startswith(allowed + ".") or allowed.startswith(key + ".")
                for allowed in all_allowed_keys
            )
            if not is_allowed:
                errors.append(f"허용되지 않은 키: {key}")

    return errors


def sanitize_config_value(value: Any) -> ConfigValue:
    """설정값 정리 및 타입 변환

    Args:
        value: 원본 값

    Returns:
        정리된 설정값
    """
    if value is None:
        return ""
    elif isinstance(value, (bool, int, float)):
        return value
    elif isinstance(value, str):
        return value.strip()
    elif isinstance(value, (list, tuple)):
        return [sanitize_config_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: sanitize_config_value(v) for k, v in value.items()}
    else:
        return str(value)


def get_config_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """설정 파일 정보 반환

    Args:
        file_path: 파일 경로

    Returns:
        파일 정보 딕셔너리
    """
    path = Path(file_path)

    info = {
        "path": str(path.absolute()),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "modified": path.stat().st_mtime if path.exists() else 0,
        "is_readable": os.access(path, os.R_OK) if path.exists() else False,
        "is_writable": os.access(path, os.W_OK) if path.exists() else False,
    }

    try:
        info["type"] = detect_config_type(path)
    except ValueError:
        info["type"] = None

    return info
