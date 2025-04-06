import subprocess
import os
import tempfile
import shutil
import requests
import platform
from PyQt6.QtCore import QObject, pyqtSignal


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

        # Create temporary directory without downloading yt-dlp
        self._create_temp_dir()

    def _create_temp_dir(self):
        """Creates only the temporary directory without downloading yt-dlp"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="videodl_")
            self.download_log.emit("System", f"Creating temporary directory: {self.temp_dir}")
        except Exception as e:
            self.download_log.emit("System", f"Error creating temporary directory: {str(e)}")

    def initialize_yt_dlp(self):
        """Initializes yt-dlp, downloading the latest version"""
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
            try:
                response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=30)
                response.raise_for_status()  # Check for HTTP response errors
                latest_release = response.json()
            except requests.exceptions.RequestException as e:
                self.download_log.emit("System", f"Request error: {str(e)}")
                raise Exception(f"Failed to get information about the latest version of yt-dlp: {str(e)}")

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
                raise Exception("Could not find the yt-dlp version for your platform")

            # Download the file
            self.download_log.emit("System", f"Downloading from: {download_url}")
            try:
                response = requests.get(download_url, stream=True, timeout=60)
                response.raise_for_status()  # Check for HTTP response errors

                with open(self.yt_dlp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            except requests.exceptions.RequestException as e:
                self.download_log.emit("System", f"Error downloading the file: {str(e)}")
                raise Exception(f"Failed to download the yt-dlp file: {str(e)}")
            except IOError as e:
                self.download_log.emit("System", f"Error saving the file: {str(e)}")
                raise Exception(f"Failed to save the yt-dlp file: {str(e)}")

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

    def cleanup(self):
        """Cleans up temporary resources when the program is terminated"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.download_log.emit("System", f"Temporary directory removed: {self.temp_dir}")
        except Exception as e:
            self.download_log.emit("System", f"Error during cleanup: {str(e)}")

    def download_video(self, url):
        """Function to download video from a specific URL"""
        try:
            self.download_started.emit(url)

            if not self.output_dir:
                self.download_error.emit(url, "No output directory has been selected")
                return False

            if not self.yt_dlp_path or not os.path.exists(self.yt_dlp_path):
                self.download_error.emit(url, "yt-dlp is not available")
                return False

            # Build the command as a list of arguments instead of a string
            command = [
                self.yt_dlp_path,  # Use the path to the downloaded executable
                '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b',
                '-o', f'{self.output_dir}/%(title)s.%(ext)s',
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

            # Capture and emit each line of output from the process
            output_filename = None

            # More robust method to read output line by line
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                line = line.strip()
                if line:  # Ignore empty lines
                    self.download_log.emit(url, line)

                    # Check if the line contains information about the file destination
                    if "[download] Destination:" in line:
                        output_filename = line.split("Destination:")[1].strip()

            # Check the return code
            returncode = process.poll()

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
        self.output_dir = directory

    def is_yt_dlp_available(self):
        """Checks if yt-dlp is available for use"""
        return self.yt_dlp_path is not None and os.path.exists(self.yt_dlp_path)