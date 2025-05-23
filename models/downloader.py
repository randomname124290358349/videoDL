import subprocess
import os
import tempfile
import shutil
import requests
import platform
import signal
import psutil
import atexit
import sys
import time
import uuid
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class VideoDownloader(QObject):
    """Class responsible for downloading videos using yt-dlp"""

    # Signals for communication with the interface
    download_started = pyqtSignal(str)
    download_progress = pyqtSignal(str, int)
    download_completed = pyqtSignal(str, str)
    download_error = pyqtSignal(str, str)
    download_log = pyqtSignal(str, str)  # Signal for logs (url, message)

    # New signal to indicate yt-dlp status
    yt_dlp_status = pyqtSignal(str)  # yt-dlp status (starting, downloading, ready, error)

    def __init__(self, output_dir=""):
        super().__init__()
        self.output_dir = output_dir
        self.yt_dlp_path = None
        self.temp_dir = None
        self.active_processes = []  # List to track active processes
        self.download_process_pids = set()  # Set to keep PIDs of processes
        self.is_shutting_down = False  # Flag to control shutdown

        # Create temporary directory without downloading yt-dlp
        self._create_temp_dir()

    def _create_temp_dir(self):
        """Creates only the temporary directory without downloading yt-dlp"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="videodl_")
            self.download_log.emit("System", f"Creating temporary directory: {self.temp_dir}")
        except Exception as e:
            self.download_log.emit("System", f"Error creating temporary directory: {str(e)}")

    def start_cleanup_timer(self):
        """Start the cleanup timer - separate from init for testing purposes"""
        # Set up timer to check processes
        self.cleanup_timer = QTimer()
        self.cleanup_timer.setInterval(500)  # 500ms
        self.cleanup_timer.timeout.connect(self.check_processes)
        self.cleanup_timer.start()

        # Ensure cleanup on termination
        atexit.register(self.cleanup)

    def initialize_yt_dlp(self):
        """Initializes yt-dlp, downloading the latest version"""
        if self.is_shutting_down:
            return False

        try:
            # Emit start signal
            self.yt_dlp_status.emit("starting")

            # Determine the correct filename for the operating system
            if platform.system() == "Windows":
                yt_dlp_filename = "yt-dlp.exe"
            else:
                yt_dlp_filename = "yt-dlp"

            self.yt_dlp_path = os.path.join(self.temp_dir, yt_dlp_filename)

            # Download the latest version of yt-dlp
            self.download_log.emit("System", "Downloading the latest version of yt-dlp...")
            self.yt_dlp_status.emit("downloading")

            # Get information about the latest version
            # Using direct requests.get instead of session.get for test compatibility
            try:
                response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=30)
                response.raise_for_status()  # Check for HTTP response errors
                latest_release = response.json()
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to get information about the latest version of yt-dlp: {str(e)}"
                self.download_log.emit("System", f"Request error: {str(e)}")
                self.download_error.emit("System", f"Failed to initialize yt-dlp: {error_msg}")
                self.yt_dlp_status.emit("error")
                return False

            # Find the asset for the current operating system
            download_url = None
            for asset in latest_release.get("assets", []):
                if platform.system() == "Windows" and asset.get("name") == yt_dlp_filename:
                    download_url = asset.get("browser_download_url")
                    break
                elif platform.system() != "Windows" and asset.get("name") == yt_dlp_filename:
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                error_msg = "Could not find the yt-dlp version for your platform"
                self.download_log.emit("System", error_msg)
                self.download_error.emit("System", f"Failed to initialize yt-dlp: {error_msg}")
                self.yt_dlp_status.emit("error")
                return False

            # Download the file
            self.download_log.emit("System", f"Downloading from: {download_url}")
            try:
                # Use direct requests.get instead of session.get for test compatibility
                response = requests.get(download_url, stream=True, timeout=60)
                response.raise_for_status()  # Check for HTTP response errors

                with open(self.yt_dlp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                        # Check if we're shutting down during download
                        if self.is_shutting_down:
                            return False
            except requests.exceptions.RequestException as e:
                self.download_log.emit("System", f"Error downloading the file: {str(e)}")
                error_msg = f"Failed to download the yt-dlp file: {str(e)}"
                self.download_error.emit("System", f"Failed to initialize yt-dlp: {error_msg}")
                self.yt_dlp_status.emit("error")
                return False
            except IOError as e:
                self.download_log.emit("System", f"Error saving the file: {str(e)}")
                error_msg = f"Failed to save the yt-dlp file: {str(e)}"
                self.download_error.emit("System", f"Failed to initialize yt-dlp: {error_msg}")
                self.yt_dlp_status.emit("error")
                return False

            # Make the file executable (for Unix systems)
            if platform.system() != "Windows":
                try:
                    os.chmod(self.yt_dlp_path, 0o755)
                except OSError as e:
                    self.download_log.emit("System",
                                           f"Warning: Could not set executable permissions: {str(e)}")
                    # Continue even if permissions can't be set

            self.download_log.emit("System", f"yt-dlp downloaded to {self.yt_dlp_path}")
            self.yt_dlp_status.emit("ready")
            return True

        except Exception as e:
            # Ensure all errors are logged and signaled
            self.download_log.emit("System", f"Error initializing yt-dlp: {str(e)}")
            self.download_error.emit("System", f"Failed to initialize yt-dlp: {str(e)}")
            self.yt_dlp_status.emit("error")
            # Don't pass the exception to avoid breaking the application
            return False

    def check_processes(self):
        """Periodically checks if processes are still active"""
        if self.is_shutting_down:
            return

        # Check if any process has terminated
        for process in self.active_processes[:]:  # Work with a copy
            if process.poll() is not None:  # Process has terminated
                self.active_processes.remove(process)

        # Check if any PID no longer exists
        for pid in list(self.download_process_pids):
            if not psutil.pid_exists(pid):
                self.download_process_pids.remove(pid)

    def cleanup(self):
        """Cleans up temporary resources when the program is terminated"""
        try:
            # Set flag to prevent new operations
            self.is_shutting_down = True

            # Stop the timer if it exists
            if hasattr(self, 'cleanup_timer'):
                self.cleanup_timer.stop()

            # Terminate all active processes
            self.terminate_processes()

            # Remove temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    self.download_log.emit("System", f"Temporary directory removed: {self.temp_dir}")
                except Exception as e:
                    self.download_log.emit("System", f"Error during cleanup: {str(e)}")
        except Exception as e:
            self.download_log.emit("System", f"Error during cleanup: {str(e)}")

    def terminate_processes(self):
        """Terminates all active processes"""
        # First, try to terminate processes tracked by our list
        for process in self.active_processes[:]:  # Use a copy to avoid modification during iteration
            try:
                if process.poll() is None:  # Process is still running
                    # Try to terminate gracefully first
                    process.terminate()

                    # Give a short timeout for graceful termination
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate quickly
                        if platform.system() == "Windows":
                            process.kill()
                        else:
                            process.send_signal(signal.SIGKILL)

                    print(f"Terminated process with PID {process.pid}")

                # Remove from our list regardless of whether it was running
                if process in self.active_processes:
                    self.active_processes.remove(process)

            except Exception as e:
                print(f"Error terminating process: {str(e)}")

        # Next, try to terminate processes tracked by their PIDs
        for pid in list(self.download_process_pids):
            try:
                if psutil.pid_exists(pid):
                    # Get the process and terminate it
                    proc = psutil.Process(pid)
                    # Try to terminate children first
                    for child in proc.children(recursive=True):
                        try:
                            child.terminate()
                            # Wait a moment for graceful termination
                            try:
                                child.wait(timeout=1)
                            except psutil.TimeoutExpired:
                                child.kill()
                        except psutil.NoSuchProcess:
                            pass

                    # Now terminate the parent
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        proc.kill()  # Force kill if necessary

                    print(f"Terminated process with PID {pid}")

                # Remove from our set regardless
                self.download_process_pids.discard(pid)

            except psutil.NoSuchProcess:
                # Process is already gone, just remove from our set
                self.download_process_pids.discard(pid)
            except Exception as e:
                print(f"Error terminating process by PID {pid}: {str(e)}")

        # Clear our collections
        self.active_processes.clear()
        self.download_process_pids.clear()

    def download_video(self, url):
        """Function to download video from a specific URL"""
        if self.is_shutting_down:
            return False

        try:
            self.download_started.emit(url)

            if not self.output_dir:
                self.download_error.emit(url, "No output directory has been selected")
                return False

            if not self.yt_dlp_path or not os.path.exists(self.yt_dlp_path):
                self.download_error.emit(url, "yt-dlp is not available")
                return False

            temp_uuid = uuid.uuid4()

            # Build the command as a list of arguments instead of a string
            command = [
                self.yt_dlp_path,  # Use the path to the downloaded executable
                '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b',
                '-o', f'{self.output_dir}/%(title)s_{str(temp_uuid)}.%(ext)s',
                url
            ]

            # Set up the process differently based on platform
            if platform.system() == "Windows":
                # On Windows, hide the console window completely
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(
                    command,
                    shell=False,  # Avoid shell interpretation
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # For non-Windows platforms
                process = subprocess.Popen(
                    command,
                    shell=False,  # Avoid shell interpretation
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

            # Add the process to our tracking collections
            self.active_processes.append(process)
            self.download_process_pids.add(process.pid)

            # Capture and emit each line of output from the process
            output_filename = None
            complete_output = ""

            # Read from process stdout
            while True:
                if self.is_shutting_down:
                    # Terminate the process if we're shutting down
                    process.terminate()
                    return False

                # Check if the process has exited
                if process.poll() is not None:
                    break

                try:
                    line = process.stdout.readline()
                    if not line:
                        # If no output but process still running, brief pause
                        time.sleep(0.1)
                        continue

                    line = line.strip()
                    if line:  # Ignore empty lines
                        complete_output += line + "\n"
                        self.download_log.emit(url, line)

                        # Check if the line contains information about the file destination
                        if "[download] Destination:" in line:
                            output_filename = line.split("Destination:")[1].strip()
                except Exception as e:
                    self.download_log.emit(url, f"Error reading output: {str(e)}")
                    break

            # For test compatibility - if we have a complete output but no filename was found
            # during the streaming process, try to extract it from the full output
            if not output_filename and process.stdout:
                try:
                    # Read any remaining output
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        complete_output += remaining_output
                    # Extract filename from the entire output
                    output_filename = self._extract_filename_from_output(complete_output)
                except Exception as e:
                    self.download_log.emit(url, f"Error processing final output: {str(e)}")

            # Check the return code
            returncode = process.poll()

            # Remove the process from our tracking collections
            if process in self.active_processes:
                self.active_processes.remove(process)
            self.download_process_pids.discard(process.pid)

            if returncode == 0:
                if not output_filename:
                    output_filename = "File downloaded"
                self.download_completed.emit(url, output_filename)
                return True
            else:
                self.download_error.emit(url, "Download error. Check the logs for more details.")
                return False

        except Exception as e:
            self.download_error.emit(url, str(e))
            return False

    def _extract_filename_from_output(self, output):
        """Extracts the filename from the yt-dlp output"""
        try:
            lines = output.split('\n')
            for line in lines:
                if "[download] Destination:" in line:
                    return line.split("Destination:")[1].strip()
            return "File downloaded"
        except:
            return "File downloaded"

    def set_output_dir(self, directory):
        """Sets the output directory for downloads"""
        if not self.is_shutting_down:
            self.output_dir = directory

    def is_yt_dlp_available(self):
        """Checks if yt-dlp is available for use"""
        return self.yt_dlp_path is not None and os.path.exists(self.yt_dlp_path)