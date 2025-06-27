import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LoggerConfig:
    """Configuration class for logger settings."""

    name: str
    output_dir: str = "output"
    file_log_level: int = logging.DEBUG
    console_log_level: int = logging.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    encoding: str = "utf-8"


class Logger:
    """Logger class to manage logging configuration and setup."""

    def __init__(self, config: LoggerConfig):
        """Initialize logger with the given configuration.

        Args:
            config: LoggerConfig object containing logger settings
        """
        self.config = config
        self.logger = None

    def _create_output_directory(self) -> None:
        """Create output directory for log files."""
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
        except OSError as exception:
            raise OSError(f"Failed to create output directory: {exception}")

    def _get_log_filename(self) -> str:
        """Generate a log filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.config.output_dir}/{self.config.name}_{timestamp}.log"

    def _create_file_handler(self, log_filename: str) -> logging.FileHandler:
        """Create and configure a file handler.

        Args:
            log_filename: Path to the log file

        Returns:
            Configured FileHandler object
        """
        try:
            file_handler = logging.FileHandler(log_filename, encoding=self.config.encoding)
            file_handler.setLevel(self.config.file_log_level)
            return file_handler
        except (OSError, IOError) as exception:
            raise IOError(f"Failed to create file handler: {exception}")

    def _create_console_handler(self) -> logging.StreamHandler:
        """Create and configure a console handler.

        Returns:
            Configured StreamHandler object
        """
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.config.console_log_level)
        return console_handler

    def _create_formatter(self) -> logging.Formatter:
        """Create a formatter for log messages.

        Returns:
            Configured Formatter object
        """
        return logging.Formatter(self.config.log_format, datefmt=self.config.date_format)

    def setup(self) -> Optional[logging.Logger]:
        """Set up and configure the logger.

        Returns:
            Configured Logger object or None if setup fails
        """
        try:
            self._create_output_directory()
            log_filename = self._get_log_filename()

            # Get logger and clear existing handlers
            logger = logging.getLogger(self.config.name)
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            # Create and configure handlers
            file_handler = self._create_file_handler(log_filename)
            console_handler = self._create_console_handler()

            # Create and set formatter
            formatter = self._create_formatter()
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            self.logger = logger
            return logger

        except Exception as exception:
            print(f"Error setting up logger: {exception}")
            return None


def setup_logger(logger_name: str, **kwargs) -> Optional[logging.Logger]:
    """Create and configure a logger with the given name and optional settings.

    Args:
        logger_name: Name of the logger
        **kwargs: Optional configuration parameters for LoggerConfig

    Returns:
        Configured Logger object or None if setup fails
    """
    config_params = {k: v for k, v in kwargs.items() if hasattr(LoggerConfig, k)}
    config = LoggerConfig(name=logger_name, **config_params)
    logger_manager = Logger(config)
    return logger_manager.setup()
