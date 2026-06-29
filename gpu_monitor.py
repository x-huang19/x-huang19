import logging
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk

try:
    import paramiko
except ImportError:  # pragma: no cover - handled by UI
    paramiko = None

DEFAULT_COMMAND = "nvidia-smi"
DEFAULT_INTERVAL = 10
DEFAULT_PORT = 22


@dataclass
class ConnectionConfig:
    host: str
    user: str
    password: str
    port: int
    command: str


class MonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GPU Monitor (SSH + nvidia-smi)")
        self.root.geometry("900x620")
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.is_running = False
        self.worker_thread: threading.Thread | None = None

        self._build_ui()
        self._poll_output_queue()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        form = ttk.Frame(container)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Host").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.host_entry = ttk.Entry(form, width=25)
        self.host_entry.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="User").grid(row=0, column=2, sticky=tk.W, padx=4, pady=4)
        self.user_entry = ttk.Entry(form, width=20)
        self.user_entry.grid(row=0, column=3, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Port").grid(row=0, column=4, sticky=tk.W, padx=4, pady=4)
        self.port_entry = ttk.Entry(form, width=6)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.grid(row=0, column=5, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Password").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.password_entry = ttk.Entry(form, width=25, show="*")
        self.password_entry.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)

        self.show_password_var = tk.BooleanVar(value=False)
        show_password = ttk.Checkbutton(
            form,
            text="Show",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        )
        show_password.grid(row=1, column=2, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Command").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.command_entry = ttk.Entry(form, width=50)
        self.command_entry.insert(0, DEFAULT_COMMAND)
        self.command_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Interval (s)").grid(row=2, column=4, sticky=tk.W, padx=4, pady=4)
        self.interval_entry = ttk.Entry(form, width=6)
        self.interval_entry.insert(0, str(DEFAULT_INTERVAL))
        self.interval_entry.grid(row=2, column=5, sticky=tk.W, padx=4, pady=4)

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=6)

        self.start_button = ttk.Button(button_row, text="Start", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=4)

        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=4)

        self.status_label = ttk.Label(button_row, text="Idle")
        self.status_label.pack(side=tk.LEFT, padx=12)

        output_frame = ttk.Frame(container)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(output_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.configure(yscrollcommand=scrollbar_y.set)

    def _toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def start_monitoring(self) -> None:
        if self.is_running:
            return

        if paramiko is None:
            messagebox.showerror(
                "Missing dependency",
                "paramiko is required. Please install it with: pip install paramiko",
            )
            return

        host = self.host_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get()
        if not host or not user or not password:
            self._append_output("Please enter host, user, and password.\n")
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Running")
        self._schedule_next_run(immediate=True)

    def stop_monitoring(self) -> None:
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Stopped")

    def _schedule_next_run(self, immediate: bool = False) -> None:
        if not self.is_running:
            return

        try:
            interval = int(self.interval_entry.get())
        except ValueError:
            interval = DEFAULT_INTERVAL
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(DEFAULT_INTERVAL))

        delay_ms = 0 if immediate else max(interval, 1) * 1000
        self.root.after(delay_ms, self._run_monitor_command)

    def _run_monitor_command(self) -> None:
        if not self.is_running:
            return

        config = self._collect_config()
        if config is None:
            self.stop_monitoring()
            return

        self.worker_thread = threading.Thread(
            target=self._execute_ssh_command,
            args=(config,),
            daemon=True,
        )
        self.worker_thread.start()
        self._schedule_next_run()

    def _collect_config(self) -> ConnectionConfig | None:
        host = self.host_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get()
        command = self.command_entry.get().strip() or DEFAULT_COMMAND

        try:
            port = int(self.port_entry.get())
        except ValueError:
            port = DEFAULT_PORT
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(DEFAULT_PORT))

        if not host or not user or not password:
            self._append_output("Missing host, user, or password.\n")
            return None

        return ConnectionConfig(
            host=host,
            user=user,
            password=password,
            port=port,
            command=command,
        )

    def _execute_ssh_command(self, config: ConnectionConfig) -> None:
        self.output_queue.put("\n" + "=" * 80 + "\n")
        self.output_queue.put(
            f"Connecting to {config.user}@{config.host}:{config.port} running {config.command}\n",
        )

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=config.host,
                port=config.port,
                username=config.user,
                password=config.password,
                timeout=15,
                auth_timeout=15,
                banner_timeout=15,
            )
            stdin, stdout, stderr = client.exec_command(config.command, timeout=30)
            output = stdout.read().decode("utf-8", errors="replace")
            error_output = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()
        except Exception as exc:  # pragma: no cover - UI feedback
            self.output_queue.put(f"Error: {exc}\n")
            return
        finally:
            try:
                client.close()
            except Exception:
                pass

        if output:
            self.output_queue.put(output)

        if error_output:
            self.output_queue.put("\n[stderr]\n")
            self.output_queue.put(error_output)

        if exit_status != 0:
            self.output_queue.put(f"\nCommand exited with code {exit_status}.\n")

    def _poll_output_queue(self) -> None:
        while True:
            try:
                message = self.output_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self._append_output(message)

        self.root.after(200, self._poll_output_queue)

    def _append_output(self, message: str) -> None:
        self.output_text.insert(tk.END, message)
        self.output_text.see(tk.END)


def main() -> None:
    log_path = _configure_logging()
    _install_exception_hook(log_path)
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()


def _configure_logging() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path.cwd()
    log_path = base_dir / "gpu_monitor.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("GPU Monitor started")
    return log_path


def _install_exception_hook(log_path: Path) -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        logging.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror(
            "Unexpected Error",
            f"An unexpected error occurred. See the log for details:\\n{log_path}",
        )

    sys.excepthook = handle_exception


if __name__ == "__main__":
    main()
