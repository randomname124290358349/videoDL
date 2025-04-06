from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QFileDialog,
                             QScrollArea, QSpinBox, QLineEdit, QMessageBox,
                             QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSlot, QTimer, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

from views.download_item import DownloadItemWidget
from controllers.url_validator import clean_url_list
import os


class DownloadTask(QRunnable):
    """Task for background download using QThreadPool"""

    def __init__(self, downloader, url, window):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.window = window
        # Set auto-delete to True to clean up the task after completion
        self.setAutoDelete(True)

        # Store a reference to parent objects to prevent them from being
        # garbage collected while this task is running
        self._parent_refs = [downloader, window]

    @pyqtSlot()
    def run(self):
        """Runs the download in a separate thread"""
        try:
            self.downloader.download_video(self.url)
        except Exception as e:
            # Handle exceptions that might occur during download
            print(f"Error in download task: {str(e)}")
            # Try to emit the error signal if possible
            try:
                self.downloader.download_error.emit(self.url, str(e))
            except Exception:
                # If even that fails, at least log it
                print(f"Could not emit error signal for {self.url}: {str(e)}")


class YtDlpInitTask(QRunnable):
    """Task for initializing yt-dlp in background"""

    def __init__(self, downloader, window):
        super().__init__()
        self.downloader = downloader
        self.window = window  # Reference to the main window to keep the task alive

    @pyqtSlot()
    def run(self):
        """Runs the download of yt-dlp in a separate thread"""
        try:
            self.downloader.initialize_yt_dlp()
        except Exception as e:
            # Capture any unhandled exception to prevent application shutdown
            print(f"Error initializing yt-dlp: {str(e)}")
            # Emit error signal
            self.downloader.yt_dlp_status.emit("error")


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, downloader):
        super().__init__()

        self.downloader = downloader
        self.download_widgets = {}  # To track download widgets
        self.yt_dlp_ready = False

        # Configure thread pool for parallel downloads
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)  # Maximum of 3 simultaneous downloads

        # Tracking active downloads
        self.download_queue = []
        self.current_downloads = set()

        # Window settings
        self.setWindowTitle("VideoDL")
        self.setMinimumSize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title with GitHub button
        title_area = QHBoxLayout()
        title_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_area.setSpacing(15)

        title_label = QLabel("VideoDL")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #8A2BE2; margin-bottom: 5px;")
        title_area.addWidget(title_label)

        # GitHub button with text instead of emoji
        self.github_button = QPushButton("GitHub")
        self.github_button.setToolTip("Visit GitHub repository")
        self.github_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.github_button.setFixedSize(80, 32)
        self.github_button.setStyleSheet("""
            QPushButton {
                background-color: #6A0DAD;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8A2BE2;
            }
        """)
        self.github_button.clicked.connect(self.open_github)
        title_area.addWidget(self.github_button)

        main_layout.addLayout(title_area)

        # Description
        description = QLabel("Enter video links to download (one per line).\n"
                             "Supports all formats compatible with yt-dlp including YouTube, Vimeo, Twitter, TikTok and "
                             "many more.\n"
                             "For the full list of supported sites, visit: https://github.com/yt-dlp/yt-dlp")
        description.setFont(QFont("Segoe UI", 12))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("color: #6a6a6a; margin-bottom: 10px;")
        main_layout.addWidget(description)

        # URL input area
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Paste your links here...")
        self.url_input.setMaximumHeight(120)
        self.url_input.setFont(QFont("Segoe UI", 11))
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.url_input)

        # Download controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Output directory
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(8)
        dir_label = QLabel("Save to:")
        dir_label.setFont(QFont("Segoe UI", 11))
        dir_layout.addWidget(dir_label)

        self.output_dir = QLineEdit("")
        self.output_dir.setFont(QFont("Segoe UI", 11))
        self.output_dir.setPlaceholderText("Select a directory to save videos...")
        self.output_dir.setReadOnly(True)
        self.output_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dir_layout.addWidget(self.output_dir, 1)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFont(QFont("Segoe UI", 11))
        self.browse_button.clicked.connect(self.browse_output_directory)
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        dir_layout.addWidget(self.browse_button)

        # Concurrent downloads
        concurrent_layout = QHBoxLayout()
        concurrent_layout.setSpacing(8)
        concurrent_label = QLabel("Concurrent downloads:")
        concurrent_label.setFont(QFont("Segoe UI", 11))
        concurrent_layout.addWidget(concurrent_label)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(3)
        self.concurrent_spin.setFont(QFont("Segoe UI", 11))
        self.concurrent_spin.valueChanged.connect(self.set_max_concurrent)
        # Fix for QSpinBox buttons
        self.concurrent_spin.setFixedWidth(80)
        self.concurrent_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        concurrent_layout.addWidget(self.concurrent_spin)

        # Add layouts to controls
        controls_layout.addLayout(dir_layout, 3)
        controls_layout.addLayout(concurrent_layout, 1)

        main_layout.addLayout(controls_layout)

        # Download button
        self.download_button = QPushButton("Start Downloads")
        self.download_button.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.download_button.setMinimumHeight(45)
        self.download_button.clicked.connect(self.start_downloads)
        self.download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_button.setEnabled(False)  # Disabled until yt-dlp is ready
        main_layout.addWidget(self.download_button)

        # yt-dlp status area (new)
        self.ytdlp_status_widget = QWidget()
        self.ytdlp_status_layout = QHBoxLayout(self.ytdlp_status_widget)
        self.ytdlp_status_layout.setSpacing(10)

        self.ytdlp_status_label = QLabel("Initializing yt-dlp...")
        self.ytdlp_status_label.setFont(QFont("Segoe UI", 11))
        self.ytdlp_status_layout.addWidget(self.ytdlp_status_label)

        self.ytdlp_progress = QProgressBar()
        self.ytdlp_progress.setMinimum(0)
        self.ytdlp_progress.setMaximum(0)  # Indeterminate
        self.ytdlp_progress.setTextVisible(False)
        self.ytdlp_status_layout.addWidget(self.ytdlp_progress)

        main_layout.addWidget(self.ytdlp_status_widget)

        # Downloads list area
        downloads_label = QLabel("Downloads")
        downloads_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        downloads_label.setStyleSheet("color: #6A0DAD; margin-top: 10px;")
        main_layout.addWidget(downloads_label)

        # Scrollable area for downloads
        self.downloads_area = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_area)
        self.downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        self.downloads_layout.setSpacing(8)

        # Scroll for downloads area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.downloads_area)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(scroll, 1)

        # Status bar
        self.statusBar().showMessage("Initializing...")
        self.statusBar().setFont(QFont("Segoe UI", 10))
        self.statusBar().setStyleSheet("background-color: #f0f0f0; color: #555;")

        # Connect downloader signals
        self.downloader.download_started.connect(self.on_download_started)
        self.downloader.download_completed.connect(self.on_download_completed)
        self.downloader.download_error.connect(self.on_download_error)
        self.downloader.download_log.connect(self.on_download_log)
        self.downloader.yt_dlp_status.connect(self.on_yt_dlp_status)

        # Apply modern style
        self.apply_styles()

        # Start yt-dlp download after the interface is displayed
        QTimer.singleShot(500, self.initialize_yt_dlp)

    def initialize_yt_dlp(self):
        """Starts yt-dlp download in the background"""
        self.statusBar().showMessage("Downloading yt-dlp...")
        # Pass window reference to the task
        task = YtDlpInitTask(self.downloader, self)
        # Increase task priority
        task.setAutoDelete(True)  # Ensure object is removed after completion
        self.thread_pool.start(task)

    def on_yt_dlp_status(self, status):
        """Handles yt-dlp status updates"""
        if status == "starting":
            self.ytdlp_status_label.setText("Initializing yt-dlp...")
            self.statusBar().showMessage("Initializing yt-dlp...")
        elif status == "downloading":
            self.ytdlp_status_label.setText("Downloading yt-dlp...")
            self.statusBar().showMessage("Downloading yt-dlp...")
        elif status == "ready":
            self.ytdlp_status_label.setText("yt-dlp ready!")
            self.ytdlp_progress.setMaximum(100)
            self.ytdlp_progress.setValue(100)
            self.ytdlp_status_widget.setVisible(False)  # Hide container widget
            self.download_button.setEnabled(True)
            self.yt_dlp_ready = True
            self.statusBar().showMessage("Ready to start downloads")
        elif status == "error":
            self.ytdlp_status_label.setText("Error downloading yt-dlp!")
            self.ytdlp_progress.setMaximum(100)
            self.ytdlp_progress.setValue(0)
            self.statusBar().showMessage("Error downloading yt-dlp. Check your connection.")

    def apply_styles(self):
        """Define the interface style for a modern, purple look"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F8F8FE;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QLabel {
                color: #333;
            }
            QTextEdit, QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                color: #333;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
            }
            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #8A2BE2;
            }
            QPushButton {
                background-color: #8A2BE2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A0DAD;
            }
            QPushButton:disabled {
                background-color: #B19CD9;
                color: rgba(255, 255, 255, 0.7);
            }
            QScrollArea {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background-color: white;
            }
            QSpinBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                color: #333;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
                min-height: 25px;
            }
            QSpinBox:focus {
                border: 1px solid #8A2BE2;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                height: 20px;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #e0e0e0;
            }
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
                background-color: #d0d0d0;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F0F0F0;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #B19CD9;
                min-height: 30px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #8A2BE2;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                height: 0px;
                width: 0px;
            }
            QStatusBar {
                background-color: #F0F0F0;
                color: #555;
                font-size: 10pt;
            }
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #8A2BE2;
                border-radius: 3px;
            }
        """)

    def browse_output_directory(self):
        """Opens dialog to select output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select directory to save videos",
            self.output_dir.text() or os.path.expanduser("~")
        )

        if directory:
            self.output_dir.setText(directory)
            self.downloader.set_output_dir(directory)

    def set_max_concurrent(self, value):
        """Sets the maximum number of concurrent downloads"""
        self.thread_pool.setMaxThreadCount(value)

    def start_downloads(self):
        """Starts the download process with the provided URLs"""
        # Check if yt-dlp is ready
        if not self.yt_dlp_ready:
            QMessageBox.warning(self, "yt-dlp is not ready",
                                "Wait for yt-dlp download to complete before starting downloads.")
            return

        # Get URLs from text field
        urls_text = self.url_input.toPlainText().strip()

        if not urls_text:
            self.statusBar().showMessage("No links provided")
            return

        # Check if output directory was selected
        output_dir = self.output_dir.text()
        if not output_dir:
            QMessageBox.warning(self, "Directory not selected",
                                "Please select a directory to save the videos before starting downloads.")
            self.statusBar().showMessage("Please select an output directory")
            return

        # Set output directory
        self.downloader.set_output_dir(output_dir)

        # Process URLs
        urls = clean_url_list(urls_text)

        if urls:
            # Add URLs to queue
            for url in urls:
                if url not in self.download_widgets and url not in self.current_downloads:
                    self.download_queue.append(url)

                    # Create widget for download
                    widget = DownloadItemWidget(url)
                    self.downloads_layout.addWidget(widget)
                    self.download_widgets[url] = widget

            # Process queue
            self._process_queue()

            self.url_input.clear()
            self.statusBar().showMessage(f"Added {len(urls)} links to download")
        else:
            self.statusBar().showMessage("No valid links found")

    def _process_queue(self):
        """Processes the download queue starting new downloads as available"""
        max_concurrent = self.thread_pool.maxThreadCount()

        while (len(self.current_downloads) < max_concurrent and
               len(self.download_queue) > 0):
            url = self.download_queue.pop(0)
            self.current_downloads.add(url)

            # Create and start download task
            task = DownloadTask(self.downloader, url, self)
            self.thread_pool.start(task)

    def on_download_started(self, url):
        """Handles download start event"""
        if url in self.download_widgets:
            self.download_widgets[url].update_status("In progress")
            self.statusBar().showMessage(f"Starting download: {url}")

    def on_download_completed(self, url, filename):
        """Handles download completion event"""
        if url in self.download_widgets:
            self.download_widgets[url].update_status("Completed")
            self.download_widgets[url].add_log(f"Download completed: {filename}")
            self.statusBar().showMessage(f"Download completed: {filename}")

        if url in self.current_downloads:
            self.current_downloads.remove(url)
            self._process_queue()

        if len(self.current_downloads) == 0 and len(self.download_queue) == 0:
            self.statusBar().showMessage("All downloads have been completed")

    def on_download_error(self, url, error):
        """Handles download error event"""
        if url in self.download_widgets:
            self.download_widgets[url].update_status("Error")
            self.download_widgets[url].add_log(f"Error: {error}")
            self.statusBar().showMessage(f"Download error: {url}")

        if url in self.current_downloads:
            self.current_downloads.remove(url)
            self._process_queue()

    def on_download_log(self, url, message):
        """Handles download log event"""
        if url in self.download_widgets:
            self.download_widgets[url].add_log(message)

    def open_github(self):
        """Opens the GitHub repository URL"""
        QDesktopServices.openUrl(QUrl("https://github.com/randomname124290358349/videoDL"))

    def resizeEvent(self, event):
        """Handles window resize events"""
        super().resizeEvent(event)
        # Force layout update when the window is resized
        self.downloads_area.updateGeometry()