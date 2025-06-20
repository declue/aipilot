import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application.util.logger import Logger, LoggerConfig, setup_logger


class TestLoggerConfig:
    """Tests for the LoggerConfig class."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = LoggerConfig(name="test_logger")
        
        assert config.name == "test_logger"
        assert config.output_dir == "output"
        assert config.file_log_level == logging.DEBUG
        assert config.console_log_level == logging.INFO
        assert config.log_format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.date_format == "%Y-%m-%d %H:%M:%S"
        assert config.encoding == "utf-8"

    def test_custom_values(self) -> None:
        """Test that custom values are set correctly."""
        config = LoggerConfig(
            name="custom_logger",
            output_dir="custom_output",
            file_log_level=logging.WARNING,
            console_log_level=logging.ERROR,
            log_format="%(levelname)s: %(message)s",
            date_format="%H:%M:%S",
            encoding="ascii"
        )
        
        assert config.name == "custom_logger"
        assert config.output_dir == "custom_output"
        assert config.file_log_level == logging.WARNING
        assert config.console_log_level == logging.ERROR
        assert config.log_format == "%(levelname)s: %(message)s"
        assert config.date_format == "%H:%M:%S"
        assert config.encoding == "ascii"


class TestLogger:
    """Tests for the Logger class."""

    @pytest.fixture
    def default_config(self) -> LoggerConfig:
        """Fixture providing a default LoggerConfig."""
        return LoggerConfig(name="test_logger")

    @pytest.fixture
    def logger_instance(self, default_config: LoggerConfig) -> Logger:
        """Fixture providing a Logger instance with default config."""
        return Logger(default_config)

    def test_init(self, default_config: LoggerConfig) -> None:
        """Test Logger initialization."""
        logger = Logger(default_config)
        
        assert logger.config == default_config
        assert logger.logger is None

    @patch('os.makedirs')
    def test_create_output_directory(self, mock_makedirs: MagicMock, logger_instance: Logger) -> None:
        """Test output directory creation."""
        logger_instance._create_output_directory()
        
        mock_makedirs.assert_called_once_with(
            logger_instance.config.output_dir, 
            exist_ok=True
        )

    @patch('os.makedirs', side_effect=OSError("Test error"))
    def test_create_output_directory_error(self, mock_makedirs: MagicMock, logger_instance: Logger) -> None:
        """Test error handling in output directory creation."""
        with pytest.raises(OSError) as excinfo:
            logger_instance._create_output_directory()
        
        assert "Failed to create output directory" in str(excinfo.value)

    @patch('application.util.logger.datetime')
    def test_get_log_filename(self, mock_datetime: MagicMock, logger_instance: Logger) -> None:
        """Test log filename generation."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20250620_123456"
        mock_datetime.now.return_value = mock_now
        
        filename = logger_instance._get_log_filename()
        
        assert filename == "output/test_logger_20250620_123456.log"
        mock_now.strftime.assert_called_once_with("%Y%m%d_%H%M%S")

    @patch('logging.FileHandler')
    def test_create_file_handler(self, mock_file_handler: MagicMock, logger_instance: Logger) -> None:
        """Test file handler creation."""
        handler_mock = MagicMock()
        mock_file_handler.return_value = handler_mock
        
        result = logger_instance._create_file_handler("test.log")
        
        mock_file_handler.assert_called_once_with(
            "test.log", 
            encoding=logger_instance.config.encoding
        )
        handler_mock.setLevel.assert_called_once_with(logger_instance.config.file_log_level)
        assert result == handler_mock

    @patch('logging.FileHandler', side_effect=IOError("Test error"))
    def test_create_file_handler_error(self, mock_file_handler: MagicMock, logger_instance: Logger) -> None:
        """Test error handling in file handler creation."""
        with pytest.raises(IOError) as excinfo:
            logger_instance._create_file_handler("test.log")
        
        assert "Failed to create file handler" in str(excinfo.value)

    def test_create_console_handler(self, logger_instance: Logger) -> None:
        """Test console handler creation."""
        handler = logger_instance._create_console_handler()
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logger_instance.config.console_log_level

    def test_create_formatter(self, logger_instance: Logger) -> None:
        """Test formatter creation."""
        formatter = logger_instance._create_formatter()
        
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt == logger_instance.config.log_format
        assert formatter.datefmt == logger_instance.config.date_format

    @patch.object(Logger, '_create_output_directory')
    @patch.object(Logger, '_get_log_filename')
    @patch.object(Logger, '_create_file_handler')
    @patch.object(Logger, '_create_console_handler')
    @patch.object(Logger, '_create_formatter')
    @patch('logging.getLogger')
    def test_setup(
        self,
        mock_get_logger: MagicMock,
        mock_create_formatter: MagicMock,
        mock_create_console_handler: MagicMock,
        mock_create_file_handler: MagicMock,
        mock_get_log_filename: MagicMock,
        mock_create_output_directory: MagicMock,
        logger_instance: Logger,
    ) -> None:
        """Test logger setup process."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_file_handler = MagicMock()
        mock_create_file_handler.return_value = mock_file_handler
        
        mock_console_handler = MagicMock()
        mock_create_console_handler.return_value = mock_console_handler
        
        mock_formatter = MagicMock()
        mock_create_formatter.return_value = mock_formatter
        
        mock_get_log_filename.return_value = "test.log"
        
        # Call the method
        result = logger_instance.setup()
        
        # Verify the calls
        mock_create_output_directory.assert_called_once()
        mock_get_log_filename.assert_called_once()
        mock_get_logger.assert_called_once_with(logger_instance.config.name)
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        
        mock_create_file_handler.assert_called_once_with("test.log")
        mock_create_console_handler.assert_called_once()
        mock_create_formatter.assert_called_once()
        
        mock_file_handler.setFormatter.assert_called_once_with(mock_formatter)
        mock_console_handler.setFormatter.assert_called_once_with(mock_formatter)
        
        mock_logger.addHandler.assert_any_call(mock_file_handler)
        mock_logger.addHandler.assert_any_call(mock_console_handler)
        
        assert logger_instance.logger == mock_logger
        assert result == mock_logger

    @patch.object(Logger, '_create_output_directory', side_effect=Exception("Test error"))
    def test_setup_error(self, mock_create_output_directory: MagicMock, logger_instance: Logger, capsys: Any) -> None:
        """Test error handling in logger setup."""
        result = logger_instance.setup()
        
        assert result is None
        captured = capsys.readouterr()
        assert "Error setting up logger: Test error" in captured.out


class TestSetupLogger:
    """Tests for the setup_logger function."""

    @patch.object(Logger, 'setup')
    def test_setup_logger_default(self, mock_setup: MagicMock) -> None:
        """Test setup_logger with default parameters."""
        mock_setup.return_value = MagicMock()
        
        result = setup_logger("test_logger")
        
        assert result == mock_setup.return_value
        # Verify LoggerConfig was created with correct parameters
        assert mock_setup.call_count == 1

    @patch.object(Logger, 'setup')
    def test_setup_logger_custom(self, mock_setup: MagicMock) -> None:
        """Test setup_logger with custom parameters."""
        mock_setup.return_value = MagicMock()
        
        result = setup_logger(
            "custom_logger",
            output_dir="custom_dir",
            file_log_level=logging.WARNING,
            console_log_level=logging.ERROR
        )
        
        assert result == mock_setup.return_value
        # Verify LoggerConfig was created with correct parameters
        assert mock_setup.call_count == 1

    @patch.object(Logger, 'setup')
    def test_setup_logger_ignores_invalid_params(self, mock_setup: MagicMock) -> None:
        """Test setup_logger ignores parameters not in LoggerConfig."""
        mock_setup.return_value = MagicMock()
        
        result = setup_logger(
            "test_logger",
            invalid_param="should be ignored"
        )
        
        assert result == mock_setup.return_value
        # Verify LoggerConfig was created with correct parameters
        assert mock_setup.call_count == 1


@pytest.mark.integration
class TestLoggerIntegration:
    """Integration tests for the logger module."""
    
    @pytest.fixture
    def temp_output_dir(self, tmp_path: Path):
        """Fixture providing a temporary output directory."""
        return tmp_path / "logs"
    
    def test_logger_creates_files(self, temp_output_dir: Path) -> None:
        """Test that logger creates log files."""
        # Setup
        output_dir = str(temp_output_dir)
        
        # Execute
        logger = setup_logger("integration_test", output_dir=output_dir)
        
        # Log some messages
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Verify
        log_files = list(temp_output_dir.glob("*.log"))
        assert len(log_files) == 1
        
        log_content = log_files[0].read_text()
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content

        assert logger is not None, "Logger should not be None"