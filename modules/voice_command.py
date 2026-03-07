import os
import sys
import threading
import time
import queue

class VoiceCommander:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console
        self.running = False
        self.audio_queue = queue.Queue()
        self._thread = None

    def _check_dependencies(self):
        """Check for both python and system dependencies."""
        is_termux = os.path.exists("/data/data/com.termux")
        
        try:
            import speech_recognition as sr
            import pyaudio
            return True
        except ImportError:
            self.console.print("\n  [yellow]Missing voice dependencies...[/yellow]")
            if is_termux:
                self.console.print("  [bold cyan]Termux detected![/bold cyan] Run these commands first:")
                self.console.print("  [white]1. pkg install portaudio libspeechd[/white]")
                self.console.print("  [white]2. pip install pyaudio SpeechRecognition[/white]\n")
            else:
                self.console.print("  [dim]Attempting auto-install of python packages...[/dim]")
                os.system(f"{sys.executable} -m pip install SpeechRecognition pyaudio --quiet")
            return False

    def start(self):
        """Starts the background voice listener."""
        if not self._check_dependencies():
            return False

        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        self.console.print("  [bold green]🎙️ Voice Control Active.[/bold green] [dim]Say 'HexMind' to trigger.[/dim]")
        return True

    def stop(self):
        """Stops the listener."""
        self.running = False
        self.console.print("  [bold red]🎙️ Voice Control Deactivated.[/bold red]")

    def _listen_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        
        try:
            mic = sr.Microphone()
        except Exception as e:
            self.console.print(f"  [red]Audio Error: {e}[/red]")
            self.running = False
            return

        while self.running:
            try:
                with mic as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                    text = r.recognize_google(audio)
                    
                    if "hexmind" in text.lower():
                        cmd = text.lower().split("hexmind", 1)[1].strip()
                        if cmd:
                            self.console.print(f"\n[bold cyan]🎙️ Voice Detected:[/bold cyan] {cmd}")
                            self.engine.chat(cmd)
            except Exception:
                pass
            time.sleep(0.1)

def start_voice(engine, console):
    commander = VoiceCommander(engine, console)
    if commander.start():
        return commander
    return None
