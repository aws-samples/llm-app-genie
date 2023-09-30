"""
This module includes a handler to integrate log messages into UI components, e.g.: Streamlit.
"""
import logging
from typing import Callable, Union


class LogToUiHandler(logging.Handler):
    """
    Python custom logger to send log events to a list of callbacks.
    This is intended to integrate logs into UI components.
    """

    def __init__(self, callback: Union[Callable[[str], None], None] = None) -> None:
        super().__init__()
        logging.Handler.__init__(self=self)
        self._messages: list[str] = []
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record by storing it in the messages list it can be rendered afterwards.
        """
        self._callback(record.getMessage())
