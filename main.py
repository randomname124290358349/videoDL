import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from models.downloader import VideoDownloader
from views.main_window import MainWindow


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and PyInstaller
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Handler for unhandled exceptions
def exception_hook(exctype, value, tb):
    """
    Captures unhandled exceptions to prevent the application from closing silently
    """
    traceback_str = ''.join(traceback.format_exception(exctype, value, tb))

    # Show a message to the user
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText("An unexpected error occurred")
    msg.setInformativeText(str(value))
    msg.setDetailedText(traceback_str)
    msg.setWindowTitle("Error")
    msg.exec()

    # Call the default handler to maintain normal error logging behavior
    sys.__excepthook__(exctype, value, tb)


def main():
    # Configure the hook for unhandled exceptions
    sys.excepthook = exception_hook

    # Initialize the application
    app = QApplication(sys.argv)
    try:
        icon_path = resource_path("resources/icons/icon.ico")
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    except Exception as e:
        print(f"Warning: Could not load icon: {str(e)}")

    app.setApplicationName("VideoDL")
    app.setStyle("Fusion")

    app.setStyleSheet("""
        QToolTip {
            border: 1px solid #8A2BE2;
            background-color: white;
            color: #333;
            padding: 5px;
            border-radius: 3px;
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }
    """)

    # Create the downloader
    downloader = VideoDownloader()
    app.aboutToQuit.connect(downloader.cleanup)

    # Create and display the main window
    window = MainWindow(downloader)
    window.show()

    # Execute the main application loop
    return app.exec()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)