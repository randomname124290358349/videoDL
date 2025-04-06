import pytest
from PyQt6.QtWidgets import QApplication, QSizePolicy
import sys

# Import the module to test
from views.download_item import DownloadItemWidget

# Setup QApplication for tests
@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the tests"""
    app = QApplication(sys.argv)
    yield app
    app.quit()

# Fixture to create a download item widget for tests
@pytest.fixture
def download_widget(app):
    """Create a DownloadItemWidget instance for testing"""
    url = "https://example.com/video.mp4"
    widget = DownloadItemWidget(url)
    return widget

def test_initialization(download_widget):
    """Test widget initialization with correct properties"""
    assert download_widget.url == "https://example.com/video.mp4"
    assert download_widget.status == "Pending"
    assert download_widget.url_label.text() == "https://example.com/video.mp4"
    assert download_widget.status_label.text() == "Pending"
    
def test_long_url_truncation(app):
    """Test that long URLs are truncated in the display"""
    long_url = "https://example.com/very-long-video-url-that-should-be-truncated-in-the-display.mp4"
    widget = DownloadItemWidget(long_url)
    
    # The URL should be truncated in the display but maintained in the widget's property
    assert widget.url == long_url
    assert len(widget.url_label.text()) < len(long_url)
    assert widget.url_label.text().endswith("...")
    assert widget.url_label.toolTip() == long_url  # Tooltip should contain the full URL

def test_update_status_completed(download_widget):
    """Test status update to 'Completed'"""
    download_widget.update_status("Completed")
    
    assert download_widget.status == "Completed"
    assert download_widget.status_label.text() == "Completed"
    # Check if background color changes to green shade
    assert "background-color: #e8f5e9" in download_widget.styleSheet()
    assert "color: #2E7D32" in download_widget.status_label.styleSheet()

def test_update_status_in_progress(download_widget):
    """Test status update to 'In progress'"""
    download_widget.update_status("In progress")
    
    assert download_widget.status == "In progress"
    assert download_widget.status_label.text() == "In progress"
    # Check if background color changes to blue shade
    assert "background-color: #e3f2fd" in download_widget.styleSheet()
    assert "color: #1565C0" in download_widget.status_label.styleSheet()

def test_update_status_error(download_widget):
    """Test status update to 'Error'"""
    download_widget.update_status("Error")
    
    assert download_widget.status == "Error"
    assert download_widget.status_label.text() == "Error"
    # Check if background color changes to red shade
    assert "background-color: #ffebee" in download_widget.styleSheet()
    assert "color: #c62828" in download_widget.status_label.styleSheet()

def test_add_log(download_widget):
    """Test adding log messages"""
    # Initial log should be empty
    assert download_widget.log_area.toPlainText() == ""
    
    # Add a log message
    download_widget.add_log("Download started")
    assert "Download started" in download_widget.log_area.toPlainText()
    
    # Add another log message
    download_widget.add_log("Progress: 50%")
    
    log_text = download_widget.log_area.toPlainText()
    assert "Download started" in log_text
    assert "Progress: 50%" in log_text

def test_log_auto_scroll(download_widget, monkeypatch):
    """Test auto-scroll functionality when adding logs"""
    # Mock the scrollbar to track setValue calls
    scroll_value = [0]  # Use a list to be mutable inside the mock
    
    class MockScrollBar:
        def setValue(self, value):
            scroll_value[0] = value
            
        def maximum(self):
            return 100  # Just a dummy value
    
    mock_scrollbar = MockScrollBar()
    monkeypatch.setattr(download_widget.log_area, "verticalScrollBar", lambda: mock_scrollbar)
    
    # Add a log message
    download_widget.add_log("Test message")
    
    # Check if scrollbar was set to maximum
    assert scroll_value[0] == 100

def test_widget_size_policies(download_widget):
    """Test widget size policies are set correctly"""
    # Test main widget size policy
    assert download_widget.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert download_widget.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    
    # Test URL label size policy
    assert download_widget.url_label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    
    # Test status label size policy
    assert download_widget.status_label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Minimum
    
    # Test log area size policy
    assert download_widget.log_area.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert download_widget.log_area.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

def test_ui_appearance(download_widget):
    """Test UI element appearance and properties"""
    # Test log area properties
    assert download_widget.log_area.isReadOnly() == True
    assert download_widget.log_area.maximumHeight() == 200
    
    # Verify font settings
    assert "Consolas" in download_widget.log_area.font().family()
    assert "Segoe UI" in download_widget.url_label.font().family()
    
    # Check widget border radius in style
    assert "border-radius: 8px" in download_widget.styleSheet()
