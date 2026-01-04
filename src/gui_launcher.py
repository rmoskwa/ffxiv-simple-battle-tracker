"""GUI launcher for FFXIV Battle Tracker.

Provides a simple dialog to select log file and port before launching the web dashboard.
"""

import json
import subprocess
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

from .parser.log_parser import LogParser
from .web.server import create_app


def get_config_path() -> Path:
    """Get the path to the config file."""
    config_dir = Path.home() / ".config" / "ffxiv-battle-tracker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict:
    """Load configuration from file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"log_path": "", "port": 8080}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass


class LauncherWindow:
    """Main launcher window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FFXIV Battle Tracker")
        self.root.resizable(False, False)

        # Load saved config
        self.config = load_config()

        # Server state
        self.server = None
        self.server_thread = None
        self.parser = None
        self.current_port = None
        self.is_running = False

        # Spinner animation state
        self.spinner_frames = ["◐", "◓", "◑", "◒"]
        self.spinner_index = 0
        self.spinner_after_id = None

        self._setup_ui()
        self._center_window()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Set up the UI elements."""
        # Define fonts for larger UI
        title_font = ("TkDefaultFont", 28, "bold")
        label_font = ("TkDefaultFont", 12)
        entry_font = ("TkDefaultFont", 12)
        button_font = ("TkDefaultFont", 12)
        status_font = ("TkDefaultFont", 11)

        # Main frame with padding
        main_frame = tk.Frame(self.root, padx=40, pady=40)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame,
            text="FFXIV Battle Tracker",
            font=title_font,
        )
        title_label.pack(pady=(0, 30))

        # Log file section
        log_frame = tk.LabelFrame(
            main_frame, text="Log File", padx=20, pady=20, font=label_font
        )
        log_frame.pack(fill=tk.X, pady=(0, 20))

        # Path entry and browse button
        path_row = tk.Frame(log_frame)
        path_row.pack(fill=tk.X)

        self.path_var = tk.StringVar(value=self.config.get("log_path", ""))
        self.path_entry = tk.Entry(
            path_row, textvariable=self.path_var, width=60, font=entry_font
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.browse_btn = tk.Button(
            path_row, text="Browse...", command=self._browse_file, font=button_font
        )
        self.browse_btn.pack(side=tk.RIGHT)

        # Port section
        port_frame = tk.LabelFrame(
            main_frame, text="Web Dashboard Port", padx=20, pady=20, font=label_font
        )
        port_frame.pack(fill=tk.X, pady=(0, 30))

        port_row = tk.Frame(port_frame)
        port_row.pack(fill=tk.X)

        self.port_var = tk.StringVar(value=str(self.config.get("port", 8080)))
        port_label = tk.Label(port_row, text="Port:", font=label_font)
        port_label.pack(side=tk.LEFT)

        self.port_entry = tk.Entry(
            port_row, textvariable=self.port_var, width=10, font=entry_font
        )
        self.port_entry.pack(side=tk.LEFT, padx=(10, 20))

        port_hint = tk.Label(
            port_row, text="(default: 8080)", fg="gray", font=label_font
        )
        port_hint.pack(side=tk.LEFT)

        # Status label (for spinner and messages)
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            main_frame, textvariable=self.status_var, font=status_font, fg="#666666"
        )
        self.status_label.pack(pady=(0, 10))

        # Buttons frame
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        # Exit button (left side)
        self.exit_btn = tk.Button(
            btn_frame, text="Exit", command=self._on_close, width=15, font=button_font
        )
        self.exit_btn.pack(side=tk.LEFT)

        # Right side buttons container
        right_btns = tk.Frame(btn_frame)
        right_btns.pack(side=tk.RIGHT)

        # View in Browser button (initially hidden)
        self.browser_btn = tk.Button(
            right_btns,
            text="View in Browser",
            command=self._open_browser,
            width=15,
            font=button_font,
            bg="#2196F3",
            fg="white",
        )
        # Don't pack yet - will show after server starts

        # Launch button
        self.launch_btn = tk.Button(
            right_btns,
            text="Launch",
            command=self._launch,
            width=15,
            font=button_font,
            bg="#4CAF50",
            fg="white",
        )
        self.launch_btn.pack(side=tk.RIGHT)

        # Bind Enter key to launch
        self.root.bind("<Return>", lambda e: self._launch())
        self.root.bind("<Escape>", lambda e: self._on_close())

    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def _browse_file(self):
        """Open file browser dialog."""
        initial_dir = ""
        current_path = self.path_var.get()
        if current_path:
            parent = Path(current_path).parent
            if parent.exists():
                initial_dir = str(parent)

        filepath = filedialog.askopenfilename(
            title="Select ACT Log File",
            initialdir=initial_dir,
            filetypes=[
                ("Log files", "*.log"),
                ("All files", "*.*"),
            ],
        )
        if filepath:
            self.path_var.set(filepath)

    def _validate(self) -> bool:
        """Validate the input fields."""
        log_path = self.path_var.get().strip()
        if not log_path:
            messagebox.showerror("Error", "Please select a log file.")
            return False

        if not Path(log_path).exists():
            messagebox.showerror("Error", f"File not found:\n{log_path}")
            return False

        port_str = self.port_var.get().strip()
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Port out of range")
        except ValueError:
            messagebox.showerror("Error", "Port must be a number between 1 and 65535.")
            return False

        return True

    def _start_spinner(self):
        """Start the loading spinner animation."""
        self.spinner_index = 0
        self._animate_spinner()

    def _animate_spinner(self):
        """Animate the spinner."""
        spinner = self.spinner_frames[self.spinner_index]
        self.status_var.set(f"{spinner} Parsing log file...")
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self.spinner_after_id = self.root.after(100, self._animate_spinner)

    def _stop_spinner(self):
        """Stop the loading spinner animation."""
        if self.spinner_after_id:
            self.root.after_cancel(self.spinner_after_id)
            self.spinner_after_id = None

    def _set_ui_state(self, parsing: bool = False, running: bool = False):
        """Set UI element states based on current state."""
        if parsing:
            # Disable inputs while parsing
            self.path_entry.config(state=tk.DISABLED)
            self.browse_btn.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.launch_btn.config(state=tk.DISABLED, text="Launching...")
        elif running:
            # Server is running
            self.path_entry.config(state=tk.DISABLED)
            self.browse_btn.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.launch_btn.config(state=tk.DISABLED, text="Running")
            # Show browser button
            self.browser_btn.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            # Ready state
            self.path_entry.config(state=tk.NORMAL)
            self.browse_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.launch_btn.config(state=tk.NORMAL, text="Launch")
            # Hide browser button
            self.browser_btn.pack_forget()

    def _launch(self):
        """Validate and launch the application."""
        if self.is_running:
            return

        if not self._validate():
            return

        log_path = self.path_var.get().strip()
        port = int(self.port_var.get().strip())

        # Save config for next time
        self.config["log_path"] = log_path
        self.config["port"] = port
        save_config(self.config)

        # Update UI for parsing state
        self._set_ui_state(parsing=True)
        self._start_spinner()

        # Parse and start server in background thread
        def parse_and_start():
            try:
                # Parse the log file
                self.parser = LogParser()
                self.parser.parse_file(log_path)

                # Create and start Flask server
                app = create_app(self.parser, log_path)
                self.current_port = port

                # Use werkzeug's make_server for graceful shutdown
                from werkzeug.serving import make_server

                self.server = make_server("0.0.0.0", port, app, threaded=True)

                # Update UI on main thread
                self.root.after(0, self._on_server_started)

                # Start serving (blocks until shutdown)
                self.server.serve_forever()

            except Exception as ex:
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: self._on_error(msg))

        self.server_thread = threading.Thread(target=parse_and_start, daemon=True)
        self.server_thread.start()

    def _on_server_started(self):
        """Called when server has started successfully."""
        self._stop_spinner()
        self.is_running = True
        self.status_var.set(f"✓ Server running on port {self.current_port}")
        self.status_label.config(fg="#4CAF50")
        self._set_ui_state(running=True)

    def _on_error(self, error_msg: str):
        """Called when an error occurs."""
        self._stop_spinner()
        self.status_var.set(f"✗ Error: {error_msg}")
        self.status_label.config(fg="#F44336")
        self._set_ui_state(parsing=False, running=False)
        messagebox.showerror("Error", f"Failed to start server:\n{error_msg}")

    def _open_browser(self):
        """Open the dashboard in the default web browser."""
        if self.current_port:
            url = f"http://localhost:{self.current_port}"
            # Check if running in WSL
            try:
                with open("/proc/version") as f:
                    if "microsoft" in f.read().lower():
                        # WSL: use Windows browser via cmd.exe
                        subprocess.Popen(
                            ["cmd.exe", "/c", "start", url],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        return
            except (FileNotFoundError, OSError):
                pass
            # Standard browser open for native Linux/macOS/Windows
            webbrowser.open(url)

    def _shutdown_server(self):
        """Shutdown the Flask server."""
        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass
            self.server = None

    def _on_close(self):
        """Handle window close - shutdown server and exit."""
        self._stop_spinner()
        self._shutdown_server()
        self.root.destroy()

    def run(self):
        """Run the launcher."""
        self.root.mainloop()


def run_launcher():
    """Run the launcher GUI."""
    launcher = LauncherWindow()
    launcher.run()
