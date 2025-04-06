import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl
import sys
from unittest.mock import MagicMock, patch

# Import the modules to test
from views.main_window import MainWindow, DownloadTask, YtDlpInitTask


# Setup QApplication for tests
@pytest.fixture(scope="session")
def app():
    """Create a QApplication instance for the tests"""
    app = QApplication(sys.argv)
    yield app
    app.quit()


# Fixture for mock downloader
@pytest.fixture
def mock_downloader():
    """Create a mock downloader instance with signals"""
    downloader = MagicMock()

    # Create mock signals
    downloader.download_started = MagicMock()
    downloader.download_started.connect = MagicMock()
    downloader.download_completed = MagicMock()
    downloader.download_completed.connect = MagicMock()
    downloader.download_error = MagicMock()
    downloader.download_error.connect = MagicMock()
    downloader.download_log = MagicMock()
    downloader.download_log.connect = MagicMock()
    downloader.yt_dlp_status = MagicMock()
    downloader.yt_dlp_status.connect = MagicMock()

    # Set up emit functions
    downloader.download_started.emit = MagicMock()
    downloader.download_completed.emit = MagicMock()
    downloader.download_error.emit = MagicMock()
    downloader.download_log.emit = MagicMock()
    downloader.yt_dlp_status.emit = MagicMock()

    return downloader


# Fixture for clean_url_list mock
@pytest.fixture
def mock_clean_url_list(monkeypatch):
    """Create a mock for clean_url_list function"""
    mock = MagicMock()
    monkeypatch.setattr('views.main_window.clean_url_list', mock)
    return mock


# Fixture for main window
@pytest.fixture
def main_window(app, mock_downloader):
    """Create a MainWindow instance for testing"""
    window = MainWindow(mock_downloader)
    yield window
    window.close()


def test_initialization(main_window, mock_downloader):
    """Test window initialization with correct properties"""
    assert main_window.downloader == mock_downloader
    assert isinstance(main_window.download_widgets, dict)
    assert main_window.yt_dlp_ready is False
    assert len(main_window.download_queue) == 0
    assert len(main_window.current_downloads) == 0
    assert main_window.download_button.isEnabled() is False
    assert main_window.windowTitle() == "VideoDL"
    assert main_window.thread_pool.maxThreadCount() == 3


def test_set_max_concurrent(main_window):
    """Test setting maximum concurrent downloads"""
    test_value = 5
    main_window.concurrent_spin.setValue(test_value)
    assert main_window.thread_pool.maxThreadCount() == test_value


@patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory')
def test_browse_output_directory(mock_dialog, main_window, mock_downloader):
    """Test browsing for output directory"""
    # Set up mock to return a test directory
    test_dir = "/test/directory"
    mock_dialog.return_value = test_dir

    # Call the method
    main_window.browse_output_directory()

    # Check if directory was set correctly
    assert main_window.output_dir.text() == test_dir
    mock_downloader.set_output_dir.assert_called_with(test_dir)

    # Test with canceled dialog
    mock_dialog.return_value = ""
    main_window.browse_output_directory()
    # Should still have the previous value
    assert main_window.output_dir.text() == test_dir


def test_start_downloads_no_urls(main_window, monkeypatch):
    """Test start_downloads with no URLs provided"""
    # Mock the statusBar
    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Ensure URL input is empty
    main_window.url_input.setPlainText("")

    # Set yt_dlp_ready to true
    main_window.yt_dlp_ready = True

    # Call the method
    main_window.start_downloads()

    # Check statusBar message
    status_bar.showMessage.assert_called_with("No links provided")


@patch('PyQt6.QtWidgets.QMessageBox.warning')
def test_start_downloads_no_output_dir(mock_warning, main_window, monkeypatch):
    """Test start_downloads with URLs but no output directory"""
    # Mock the statusBar
    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Set yt_dlp_ready to true
    main_window.yt_dlp_ready = True

    # Set URL input but empty output directory
    main_window.url_input.setPlainText("https://example.com/video")
    main_window.output_dir.setText("")

    # Call the method
    main_window.start_downloads()

    # Check if warning was shown
    mock_warning.assert_called_once()
    status_bar.showMessage.assert_called_with("Please select an output directory")


def test_start_downloads_valid_urls(mock_clean_url_list, main_window, monkeypatch):
    """Test start_downloads with valid URLs and output directory"""
    # Mock process_queue and statusBar
    process_queue_mock = MagicMock()
    monkeypatch.setattr(main_window, '_process_queue', process_queue_mock)

    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Set yt_dlp_ready to true and output directory
    main_window.yt_dlp_ready = True
    main_window.output_dir.setText("/test/output")

    # Set up mock for clean_url_list
    test_urls = ["https://example.com/video1", "https://example.com/video2"]
    mock_clean_url_list.return_value = test_urls

    # Set URL input
    main_window.url_input.setPlainText("https://example.com/video1\nhttps://example.com/video2")

    # Call the method
    main_window.start_downloads()

    # Verify downloader output dir was set
    main_window.downloader.set_output_dir.assert_called_with("/test/output")

    # Check if widgets were created for each URL
    assert len(main_window.download_widgets) == 2
    assert all(url in main_window.download_widgets for url in test_urls)

    # Check if process_queue was called and URL input was cleared
    process_queue_mock.assert_called_once()
    assert main_window.url_input.toPlainText() == ""

    # Check status message
    status_bar.showMessage.assert_called_with(f"Added {len(test_urls)} links to download")


@patch('views.main_window.DownloadTask')
def test_process_queue(mock_download_task, main_window, monkeypatch):
    """Test _process_queue method"""
    # Mock thread_pool.start
    thread_pool_start = MagicMock()
    monkeypatch.setattr(main_window.thread_pool, 'start', thread_pool_start)

    # Set max thread count
    main_window.thread_pool.setMaxThreadCount(2)

    # Set up download queue
    test_urls = ["https://example.com/video1", "https://example.com/video2", "https://example.com/video3"]
    main_window.download_queue = test_urls.copy()

    # Call the method
    main_window._process_queue()

    # Check if correct number of tasks were started
    assert thread_pool_start.call_count == 2

    # Check if current_downloads was updated
    assert len(main_window.current_downloads) == 2
    assert "https://example.com/video1" in main_window.current_downloads
    assert "https://example.com/video2" in main_window.current_downloads

    # Check if queue was updated
    assert main_window.download_queue == ["https://example.com/video3"]


def test_on_download_started(main_window, monkeypatch):
    """Test on_download_started method"""
    # Create a mock widget and status bar
    mock_widget = MagicMock()
    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Add mock widget to download_widgets
    test_url = "https://example.com/video"
    main_window.download_widgets[test_url] = mock_widget

    # Call the method
    main_window.on_download_started(test_url)

    # Check if widget status was updated
    mock_widget.update_status.assert_called_with("In progress")
    status_bar.showMessage.assert_called_with(f"Starting download: {test_url}")


def test_on_download_completed(main_window, monkeypatch):
    """Test on_download_completed method"""
    # Create a mock widget and status bar
    mock_widget = MagicMock()
    status_bar = MagicMock()
    process_queue_mock = MagicMock()

    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)
    monkeypatch.setattr(main_window, '_process_queue', process_queue_mock)

    # Add mock widget to download_widgets and URL to current_downloads
    test_url = "https://example.com/video"
    test_filename = "video.mp4"
    main_window.download_widgets[test_url] = mock_widget
    main_window.current_downloads.add(test_url)

    # Add a dummy URL to prevent "All downloads completed" message
    main_window.download_queue = ["https://example.com/another_video"]

    # Call the method
    main_window.on_download_completed(test_url, test_filename)

    # Check if widget status was updated
    mock_widget.update_status.assert_called_with("Completed")
    mock_widget.add_log.assert_called_with(f"Download completed: {test_filename}")

    # Check if URL was removed from current_downloads and queue was processed
    assert test_url not in main_window.current_downloads
    process_queue_mock.assert_called_once()

    # Check status message
    status_bar.showMessage.assert_called_with(f"Download completed: {test_filename}")


def test_on_download_error(main_window, monkeypatch):
    """Test on_download_error method"""
    # Create a mock widget and status bar
    mock_widget = MagicMock()
    status_bar = MagicMock()
    process_queue_mock = MagicMock()

    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)
    monkeypatch.setattr(main_window, '_process_queue', process_queue_mock)

    # Add mock widget to download_widgets and URL to current_downloads
    test_url = "https://example.com/video"
    test_error = "Download failed"
    main_window.download_widgets[test_url] = mock_widget
    main_window.current_downloads.add(test_url)

    # Call the method
    main_window.on_download_error(test_url, test_error)

    # Check if widget status was updated
    mock_widget.update_status.assert_called_with("Error")
    mock_widget.add_log.assert_called_with(f"Error: {test_error}")

    # Check if URL was removed from current_downloads and queue was processed
    assert test_url not in main_window.current_downloads
    process_queue_mock.assert_called_once()

    # Check status message
    status_bar.showMessage.assert_called_with(f"Download error: {test_url}")


def test_on_download_log(main_window):
    """Test on_download_log method"""
    # Create a mock widget
    mock_widget = MagicMock()

    # Add mock widget to download_widgets
    test_url = "https://example.com/video"
    test_message = "Downloading... 50%"
    main_window.download_widgets[test_url] = mock_widget

    # Call the method
    main_window.on_download_log(test_url, test_message)

    # Check if log was added
    mock_widget.add_log.assert_called_with(test_message)


@patch('PyQt6.QtGui.QDesktopServices.openUrl')
def test_open_github(mock_open_url, main_window):
    """Test open_github method"""
    # Call the method
    main_window.open_github()

    # Check if URL was opened
    expected_url = QUrl("https://github.com/randomname124290358349/videoDL")
    mock_open_url.assert_called_with(expected_url)


def test_on_yt_dlp_status(main_window, monkeypatch):
    """Test on_yt_dlp_status method for different statuses"""
    # Mock the statusBar
    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Test "starting" status
    main_window.on_yt_dlp_status("starting")
    assert main_window.ytdlp_status_label.text() == "Initializing yt-dlp..."
    status_bar.showMessage.assert_called_with("Initializing yt-dlp...")

    # Test "downloading" status
    main_window.on_yt_dlp_status("downloading")
    assert main_window.ytdlp_status_label.text() == "Downloading yt-dlp..."
    status_bar.showMessage.assert_called_with("Downloading yt-dlp...")

    # Test "ready" status
    main_window.on_yt_dlp_status("ready")
    assert main_window.ytdlp_status_label.text() == "yt-dlp ready!"
    assert main_window.ytdlp_progress.maximum() == 100
    assert main_window.ytdlp_progress.value() == 100
    assert main_window.ytdlp_status_widget.isVisible() is False
    assert main_window.download_button.isEnabled() is True
    assert main_window.yt_dlp_ready is True
    status_bar.showMessage.assert_called_with("Ready to start downloads")

    # Test "error" status
    main_window.on_yt_dlp_status("error")
    assert main_window.ytdlp_status_label.text() == "Error downloading yt-dlp!"
    assert main_window.ytdlp_progress.maximum() == 100
    assert main_window.ytdlp_progress.value() == 0
    status_bar.showMessage.assert_called_with("Error downloading yt-dlp. Check your connection.")


def test_download_task():
    """Test DownloadTask class"""
    mock_downloader = MagicMock()
    mock_window = MagicMock()
    test_url = "https://example.com/video"

    # Create task
    task = DownloadTask(mock_downloader, test_url, mock_window)

    # Check initialization
    assert task.downloader == mock_downloader
    assert task.url == test_url
    assert task.window == mock_window
    assert task._parent_refs == [mock_downloader, mock_window]

    # Test run method
    mock_downloader.download_video = MagicMock()
    task.run()
    mock_downloader.download_video.assert_called_with(test_url)

    # Test run method with exception
    mock_downloader.download_video = MagicMock(side_effect=Exception("Test error"))
    mock_downloader.download_error = MagicMock()
    task.run()
    mock_downloader.download_error.emit.assert_called_with(test_url, "Test error")


def test_yt_dlp_init_task():
    """Test YtDlpInitTask class"""
    mock_downloader = MagicMock()
    mock_window = MagicMock()

    # Create task
    task = YtDlpInitTask(mock_downloader, mock_window)

    # Check initialization
    assert task.downloader == mock_downloader
    assert task.window == mock_window

    # Test run method
    mock_downloader.initialize_yt_dlp = MagicMock()
    task.run()
    mock_downloader.initialize_yt_dlp.assert_called_once()

    # Test run method with exception
    mock_downloader.initialize_yt_dlp = MagicMock(side_effect=Exception("Test error"))
    mock_downloader.yt_dlp_status = MagicMock()
    task.run()
    mock_downloader.yt_dlp_status.emit.assert_called_with("error")


def test_initialize_yt_dlp(main_window, monkeypatch):
    """Test initialize_yt_dlp method"""
    # Mock thread_pool.start and statusBar
    thread_pool_start = MagicMock()
    monkeypatch.setattr(main_window.thread_pool, 'start', thread_pool_start)

    status_bar = MagicMock()
    monkeypatch.setattr(main_window, 'statusBar', lambda: status_bar)

    # Call the method
    main_window.initialize_yt_dlp()

    # Check if task was started
    thread_pool_start.assert_called_once()
    status_bar.showMessage.assert_called_with("Downloading yt-dlp...")


@patch('PyQt6.QtWidgets.QMessageBox.warning')
def test_start_downloads_yt_dlp_not_ready(mock_warning, main_window):
    """Test start_downloads when yt_dlp is not ready"""
    # Set yt_dlp_ready to false
    main_window.yt_dlp_ready = False

    # Call the method
    main_window.start_downloads()

    # Check if warning was shown
    mock_warning.assert_called_once()