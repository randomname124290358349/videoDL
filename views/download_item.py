from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DownloadItemWidget(QWidget):
    """Widget that represents a download item in the interface"""

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.status = "Pending"

        # Main layout configuration
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Top layout for URL and status
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Video URL (truncated if too long)
        display_url = url
        if len(display_url) > 50:
            display_url = display_url[:47] + "..."

        self.url_label = QLabel(display_url)
        self.url_label.setToolTip(url)
        self.url_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.url_label.setStyleSheet("color: #333;")
        self.url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Download status
        self.status_label = QLabel(self.status)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        top_layout.addWidget(self.url_label, 3)
        top_layout.addWidget(self.status_label, 1)

        main_layout.addLayout(top_layout)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(200)
        self.log_area.setFont(QFont("Consolas", 12))
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.log_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.log_area)

        # Basic widget style
        self.setStyleSheet("""
            background-color: #f5f5f5; 
            border-radius: 8px; 
            margin: 4px;
            border: 1px solid #e0e0e0;
        """)

        # Set size policy for the widget
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def update_status(self, status):
        """Updates the download status"""
        self.status = status
        self.status_label.setText(status)

        if status == "Completed":
            self.setStyleSheet("""
                background-color: #e8f5e9; 
                border-radius: 8px; 
                margin: 4px;
                border: 1px solid #a5d6a7;
            """)
            self.status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        elif status == "In progress":
            self.setStyleSheet("""
                background-color: #e3f2fd; 
                border-radius: 8px; 
                margin: 4px;
                border: 1px solid #90caf9;
            """)
            self.status_label.setStyleSheet("color: #1565C0; font-weight: bold;")
        elif status == "Error":
            self.setStyleSheet("""
                background-color: #ffebee; 
                border-radius: 8px; 
                margin: 4px;
                border: 1px solid #ef9a9a;
            """)
            self.status_label.setStyleSheet("color: #c62828; font-weight: bold;")

    def add_log(self, message):
        """Adds a message to the log"""
        self.log_area.append(message)
        # Auto-scroll to the bottom
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())