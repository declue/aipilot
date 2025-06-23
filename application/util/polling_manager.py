from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, cast

from application.util.logger import setup_logger

logger = cast(logging.Logger, setup_logger("util") or logging.getLogger("util"))


class PollingManager:  # pylint: disable=too-few-public-methods
    """Runs a polling loop in a background daemon thread."""

    def __init__(
        self,
        fetch_messages: Callable[[], List[Dict[str, Any]]],
        handle_messages: Callable[[List[Dict[str, Any]], bool], None],
        poll_interval: int = 10,
    ) -> None:
        self._fetch_messages = fetch_messages
        self._handle_messages = handle_messages
        self._poll_interval = poll_interval

        self._thread: Optional[threading.Thread] = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._running:
            logger.warning("PollingManager already running.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("PollingManager started.")

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("PollingManager stopped.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _run_loop(self) -> None:
        first_poll = True
        while self._running:
            try:
                messages = self._fetch_messages()
                if not messages:
                    time.sleep(self._poll_interval)
                    continue

                self._handle_messages(messages, first_poll)
                first_poll = False
                time.sleep(self._poll_interval)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Polling loop error: %s", exc)
                time.sleep(self._poll_interval) 