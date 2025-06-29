"""PlanHistoryManager – 실행 계획 해시 장기 저장소

• ~/.dspilot/cli_plan_history.json 파일에 해시 목록을 저장
• 파일이 없으면 자동 생성, 최대 1000개 유지(오래된 항목 삭제)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Set


class PlanHistoryManager:  # pylint: disable=too-few-public-methods
    """장기 중복 계획 감지용 해시 저장소"""

    MAX_ENTRIES = 1000

    def __init__(self, store_path: Path | None = None):
        if store_path is None:
            store_path = Path.home() / ".dspilot" / "cli_plan_history.json"
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        self._hashes: Set[str] = set()
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            if isinstance(data, list):
                self._hashes = set(data)
        except Exception:
            # 손상된 파일 – 무시하고 덮어쓰기
            self._hashes = set()

    def _save(self) -> None:
        try:
            # 오래된 항목 제거
            if len(self._hashes) > self.MAX_ENTRIES:
                self._hashes = set(list(self._hashes)[-self.MAX_ENTRIES:])
            self.store_path.write_text(json.dumps(sorted(self._hashes)))
        except Exception:
            pass  # 경고 로그 대신 침묵 – CLI 성능 우선

    # ------------------------------------------------------------------
    def has(self, plan_hash: str) -> bool:
        return plan_hash in self._hashes

    def add(self, plan_hash: str) -> None:
        if plan_hash not in self._hashes:
            self._hashes.add(plan_hash)
            self._save()
