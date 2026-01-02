"""File watcher for real-time log monitoring."""

import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from ..parser.log_parser import LogParser


class LogFileHandler(FileSystemEventHandler):
    """Handler for log file modification events."""

    def __init__(
        self,
        filepath: str,
        parser: LogParser,
        on_new_lines: Optional[Callable[[list], None]] = None,
    ):
        """Initialize the handler.

        Args:
            filepath: Path to the log file to watch
            parser: LogParser instance to feed lines to
            on_new_lines: Optional callback when new lines are parsed
        """
        super().__init__()
        self.filepath = os.path.abspath(filepath)
        self.parser = parser
        self.on_new_lines = on_new_lines
        self._file_position = 0
        self._lock = threading.Lock()

        # Initialize file position to end of current file
        self._init_position()

    def _init_position(self) -> None:
        """Initialize file position to current end of file."""
        try:
            with open(self.filepath, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, 2)  # Seek to end
                self._file_position = f.tell()
        except FileNotFoundError:
            self._file_position = 0

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if this is our watched file
        event_path = os.path.abspath(event.src_path)
        if event_path != self.filepath:
            return

        self._read_new_lines()

    def _read_new_lines(self) -> None:
        """Read and parse new lines from the file."""
        with self._lock:
            try:
                with open(self.filepath, "r", encoding="utf-8", errors="ignore") as f:
                    # Seek to last known position
                    f.seek(self._file_position)

                    # Read new lines
                    new_lines = []
                    for line in f:
                        new_lines.append(line)
                        self.parser.parse_line(line)

                    # Update position
                    self._file_position = f.tell()

                    # Notify callback if we have new lines
                    if new_lines and self.on_new_lines:
                        self.on_new_lines(new_lines)

            except FileNotFoundError:
                pass  # File may have been deleted/rotated

    def read_existing(self) -> None:
        """Read and parse existing content in the file."""
        with self._lock:
            try:
                with open(self.filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        self.parser.parse_line(line)
                    self._file_position = f.tell()
            except FileNotFoundError:
                pass


class LogFileWatcher:
    """Watches a log file for changes and parses new lines in real-time."""

    def __init__(
        self,
        filepath: str,
        parser: LogParser,
        on_new_lines: Optional[Callable[[list], None]] = None,
    ):
        """Initialize the watcher.

        Args:
            filepath: Path to the log file to watch
            parser: LogParser instance to feed lines to
            on_new_lines: Optional callback when new lines are parsed
        """
        self.filepath = filepath
        self.parser = parser
        self.on_new_lines = on_new_lines

        self._observer: Optional[Observer] = None
        self._handler: Optional[LogFileHandler] = None
        self._running = False

    def start(self, read_existing: bool = True) -> None:
        """Start watching the file.

        Args:
            read_existing: If True, parse existing content before watching
        """
        if self._running:
            return

        # Create handler
        self._handler = LogFileHandler(
            self.filepath,
            self.parser,
            self.on_new_lines,
        )

        # Read existing content if requested
        if read_existing:
            self._handler.read_existing()

        # Create and start observer
        self._observer = Observer()
        watch_dir = os.path.dirname(os.path.abspath(self.filepath))
        self._observer.schedule(self._handler, watch_dir, recursive=False)
        self._observer.start()
        self._running = True

    def stop(self) -> None:
        """Stop watching the file."""
        if not self._running:
            return

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        self._handler = None
        self._running = False

    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
