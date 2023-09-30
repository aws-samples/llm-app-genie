"""
Module to help logging application activity.
"""
import logging

from .llm_logging_handler import LlmLoggingHandler
from .log_to_ui_handler import LogToUiHandler

LLM_LOGGER_NAME = "LLM_LOGGER"
TECHNICAL_LOGGER_NAME = "TECHNICAL_LOGGER"


class SessionLogFilter(logging.Filter):
    """
    This filter only show log entries for specified thread name.
    """

    def __init__(self, session_id, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.session_id = session_id

    def filter(self, record):
        return not record.getMessage().startswith(self.session_id)


def get_llm_logger(
    ui_handler: LogToUiHandler, session_id: str, level: int = logging.DEBUG
) -> logging.Logger:
    """
    NOTE: Call this function only once per thread in the application.
    This function initializes a global Python logger for LLM usage with the provided ui_handler.


    Args:
        ui_handler: UI handler that will receive the LLM logs.
        level: logging level. Default is logging.DEBUG.

    Returns:
        A logger that calls the ui_handler on every log line.
    """
    logger = _get_logger(ui_handler, session_id, LLM_LOGGER_NAME, level=level)
    return logger


def get_llm_log_handler(logger: logging.Logger) -> LlmLoggingHandler:
    """
    NOTE: Call this function only once per thread in the application.
    This function creates an LlmLoggingHandler object that captures LLM outputs.

    Args:
        logger: the logger to use for capturing LLM outputs.

    Returns:
        A handler object that captures LLM outputs and passes it to the UI handler.
        This handler needs to be passed to LangChain.
    """
    handler = LlmLoggingHandler(logger=logger)
    return handler


def get_technical_logger(
    ui_handler: LogToUiHandler, session_id: str, level: int = logging.DEBUG
) -> logging.Logger:
    """
    NOTE: Call this function only once per thread in the application.
    This function initializes a global Python logger for technical usage with the provided ui_handler.

    Returns
        A logger that calls the ui_handler on every log line.
    """
    logger = _get_logger(ui_handler, TECHNICAL_LOGGER_NAME, session_id, level=level)
    logger.addHandler(logging.StreamHandler())
    return logger


def _get_logger(
    ui_handler: LogToUiHandler,
    logger_name: str,
    session_id: str,
    level: int = logging.DEBUG,
) -> logging.Logger:
    """
    NOTE: Call this function only once per thread in the application.
    This function initializes a global Python logger with the provided logger_name.

    Args:
        ui_handler: UI handler that will receive the logs.
        logger_name: name of the logger.
        level: logging level. Default is logging.DEBUG.

    Returns:
        A logger that calls the ui_handler on every log line.
    """
    ui_handler.addFilter(SessionLogFilter(session_id))
    logger = logging.getLogger(f"{session_id}.{logger_name}")
    logger.addHandler(ui_handler)
    logger.setLevel(level)
    return logger
