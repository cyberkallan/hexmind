import os
import sys
import threading
import subprocess
import time

class InteractiveRunner:
    def __init__(self, terminal, emit_func):
        self.terminal = terminal
        self.emit = emit_func
        self.process = None
        self._running = False

    def spawn(self, cmd, cwd=None):
        """Spawns an interactive CLI tool and bridges its I/O to the WebUI terminal."""
        if self.process and self._running:
            self.emit(f"\r\n\x1b[31mA process is already running: {self.process.pid}\x1b[0m\r\n")
            return

        try:
            self.emit(f"\r\n\x1b[36m[HexMind Runner] Spawning: {cmd}\x1b[0m\r\n")
            
            # Use appropriate shell flag for OS
            is_windows = os.name == 'nt'
            
            self.process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            self._running = True
            
            # Start background thread to read output
            threading.Thread(target=self._read_output, daemon=True).start()
            
        except Exception as e:
            self._running = False
            self.emit(f"\r\n\x1b[31m[Error Spawning] {e}\x1b[0m\r\n")

    def _read_output(self):
        """Continuously read from the process stdout and emit to WebUI."""
        try:
            # Read character by character to handle interactive prompts that don't emit newlines
            while self._running and self.process:
                # Need to read raw or handle lines. Reading 1 char is more responsive for prompts.
                char = self.process.stdout.read(1)
                if not char and self.process.poll() is not None:
                    break
                
                if char:
                    # Replace pure newlines with \r\n for xterm.js
                    if char == '\n':
                        self.emit('\r\n')
                    else:
                        self.emit(char)
                        
        except Exception as e:
            self.emit(f"\r\n\x1b[31m[Runner Error] {e}\x1b[0m\r\n")
        finally:
            self._cleanup()

    def write_input(self, text: str):
        """Send input to the running interactive process."""
        if self._running and self.process and self.process.stdin:
            try:
                self.process.stdin.write(text)
                self.process.stdin.flush()
            except Exception as e:
                self.emit(f"\r\n\x1b[31m[Input Error] {e}\x1b[0m\r\n")

    def kill(self):
        """Aggressively terminate the process."""
        self._cleanup()

    def _cleanup(self):
        self._running = False
        if self.process:
            try:
                self.process.terminate()
                # give it a second
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                pass
            
            exit_code = self.process.poll()
            self.emit(f"\r\n\x1b[33m[Process Completed: Exit Code {exit_code}]\x1b[0m\r\n")
            self.process = None

        # Re-prompt in the terminal
        if self.terminal:
            self.terminal._prompt()
