import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import requests
from io import StringIO

# Import the module to test
from models.downloader import VideoDownloader


class TestVideoDownloader(unittest.TestCase):
    """Unit tests for the VideoDownloader class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create a test instance with a mock output directory
        self.test_output_dir = "/test/output/dir"

        # Create patches for the signals to monitor emissions
        self.patches = {
            "download_started": patch.object(VideoDownloader, "download_started"),
            "download_progress": patch.object(VideoDownloader, "download_progress"),
            "download_completed": patch.object(VideoDownloader, "download_completed"),
            "download_error": patch.object(VideoDownloader, "download_error"),
            "download_log": patch.object(VideoDownloader, "download_log"),
            "yt_dlp_status": patch.object(VideoDownloader, "yt_dlp_status")
        }

        # Start all patches and store the mocks
        self.mocks = {}
        for name, patcher in self.patches.items():
            self.mocks[name] = patcher.start()

        # Patch tempfile.mkdtemp to return a predictable path
        self.mock_temp_dir = "/tmp/fake_temp_dir"
        patcher_mkdtemp = patch("tempfile.mkdtemp", return_value=self.mock_temp_dir)
        self.mock_mkdtemp = patcher_mkdtemp.start()
        self.patches["mkdtemp"] = patcher_mkdtemp

        # Create the downloader instance after patching signals
        self.downloader = VideoDownloader(output_dir=self.test_output_dir)

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Stop all patches
        for patcher in self.patches.values():
            patcher.stop()

    def test_create_temp_dir(self):
        """Test the _create_temp_dir method"""
        # The method is called in __init__, so we just verify its effects
        self.assertEqual(self.downloader.temp_dir, self.mock_temp_dir)
        self.mocks["download_log"].emit.assert_called_once_with(
            "System", f"Creating temporary directory: {self.mock_temp_dir}")

    @patch("tempfile.mkdtemp")
    def test_create_temp_dir_with_exception(self, mock_mkdtemp):
        """Test the _create_temp_dir method when an exception occurs"""
        # Configure mocks
        mock_mkdtemp.side_effect = Exception("Test error")

        # Create a new instance to trigger the method with our configured mock
        downloader = VideoDownloader()

        # Verify the results
        self.mocks["download_log"].emit.assert_called_with(
            "System", "Error creating temporary directory: Test error")

    @patch("platform.system")
    @patch("requests.get")
    @patch("os.path.join")
    @patch("os.chmod")
    @patch("builtins.open", new_callable=mock_open)
    def test_initialize_yt_dlp_windows(self, mock_file, mock_chmod, mock_join, mock_get, mock_system):
        """Test the initialize_yt_dlp method on Windows"""
        # Configure mocks
        mock_system.return_value = "Windows"
        mock_join.return_value = os.path.join(self.mock_temp_dir, "yt-dlp.exe")

        # Mock the API response
        mock_response_latest = MagicMock()
        mock_response_latest.json.return_value = {
            "assets": [
                {"name": "yt-dlp.exe", "browser_download_url": "https://example.com/yt-dlp.exe"}
            ]
        }

        # Mock the download response
        mock_response_download = MagicMock()
        mock_response_download.iter_content.return_value = [b"fake_content"]

        # Configure the requests.get to return different responses for different URLs
        def get_side_effect(url, **kwargs):
            if "api.github.com" in url:
                return mock_response_latest
            else:
                return mock_response_download

        mock_get.side_effect = get_side_effect

        # Call the method
        result = self.downloader.initialize_yt_dlp()

        # Verify the results
        self.assertTrue(result)
        self.mocks["yt_dlp_status"].emit.assert_any_call("starting")
        self.mocks["yt_dlp_status"].emit.assert_any_call("downloading")
        self.mocks["yt_dlp_status"].emit.assert_any_call("ready")
        mock_file.assert_called_once_with(os.path.join(self.mock_temp_dir, "yt-dlp.exe"), 'wb')
        # On Windows, we should not call chmod
        mock_chmod.assert_not_called()

    @patch("platform.system")
    @patch("requests.get")
    @patch("os.path.join")
    @patch("os.chmod")
    @patch("builtins.open", new_callable=mock_open)
    def test_initialize_yt_dlp_unix(self, mock_file, mock_chmod, mock_join, mock_get, mock_system):
        """Test the initialize_yt_dlp method on Unix"""
        # Configure mocks
        mock_system.return_value = "Linux"
        mock_join.return_value = os.path.join(self.mock_temp_dir, "yt-dlp")

        # Mock the API response
        mock_response_latest = MagicMock()
        mock_response_latest.json.return_value = {
            "assets": [
                {"name": "yt-dlp", "browser_download_url": "https://example.com/yt-dlp"}
            ]
        }

        # Mock the download response
        mock_response_download = MagicMock()
        mock_response_download.iter_content.return_value = [b"fake_content"]

        # Configure the requests.get to return different responses for different URLs
        def get_side_effect(url, **kwargs):
            if "api.github.com" in url:
                return mock_response_latest
            else:
                return mock_response_download

        mock_get.side_effect = get_side_effect

        # Call the method
        result = self.downloader.initialize_yt_dlp()

        # Verify the results
        self.assertTrue(result)
        self.mocks["yt_dlp_status"].emit.assert_any_call("starting")
        self.mocks["yt_dlp_status"].emit.assert_any_call("downloading")
        self.mocks["yt_dlp_status"].emit.assert_any_call("ready")
        mock_file.assert_called_once_with(os.path.join(self.mock_temp_dir, "yt-dlp"), 'wb')
        # On Unix, we should call chmod
        mock_chmod.assert_called_once_with(os.path.join(self.mock_temp_dir, "yt-dlp"), 0o755)

    @patch("requests.get")
    def test_initialize_yt_dlp_api_error(self, mock_get):
        """Test the initialize_yt_dlp method when the API request fails"""
        # Configure mocks
        mock_get.side_effect = requests.exceptions.RequestException("Test error")

        # Call the method
        result = self.downloader.initialize_yt_dlp()

        # Verify the results
        self.assertFalse(result)
        self.mocks["yt_dlp_status"].emit.assert_any_call("starting")
        self.mocks["yt_dlp_status"].emit.assert_any_call("error")
        self.mocks["download_error"].emit.assert_called_with(
            "System",
            "Failed to initialize yt-dlp: Failed to get information about the latest version of yt-dlp: Test error")

    @patch("platform.system")
    @patch("requests.get")
    def test_initialize_yt_dlp_asset_not_found(self, mock_get, mock_system):
        """Test the initialize_yt_dlp method when the asset is not found"""
        # Configure mocks
        mock_system.return_value = "Windows"

        # Mock the API response with no matching asset
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {"name": "something_else", "browser_download_url": "https://example.com/something_else"}
            ]
        }
        mock_get.return_value = mock_response

        # Call the method
        result = self.downloader.initialize_yt_dlp()

        # Verify the results
        self.assertFalse(result)
        self.mocks["yt_dlp_status"].emit.assert_any_call("error")
        self.mocks["download_error"].emit.assert_called_with(
            "System", "Failed to initialize yt-dlp: Could not find the yt-dlp version for your platform")

    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_cleanup(self, mock_rmtree, mock_exists):
        """Test the cleanup method"""
        # Configure mocks
        mock_exists.return_value = True

        # Call the method
        self.downloader.cleanup()

        # Verify the results
        mock_exists.assert_called_once_with(self.mock_temp_dir)
        mock_rmtree.assert_called_once_with(self.mock_temp_dir)
        self.mocks["download_log"].emit.assert_called_with(
            "System", f"Temporary directory removed: {self.mock_temp_dir}")

    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_cleanup_with_exception(self, mock_rmtree, mock_exists):
        """Test the cleanup method when an exception occurs"""
        # Configure mocks
        mock_exists.return_value = True
        mock_rmtree.side_effect = Exception("Test error")

        # Call the method
        self.downloader.cleanup()

        # Verify the results
        self.mocks["download_log"].emit.assert_called_with(
            "System", "Error during cleanup: Test error")

    @patch("os.path.exists")
    @patch("subprocess.Popen")
    def test_download_video_success(self, mock_popen, mock_exists):
        """Test the download_video method with successful download"""
        # Configure mocks
        mock_exists.return_value = True
        self.downloader.yt_dlp_path = os.path.join(self.mock_temp_dir, "yt-dlp")

        # Mock Popen process
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Success return code
        mock_process.stdout = StringIO("[download] Destination: /test/output/dir/video.mp4\n")
        mock_popen.return_value = mock_process

        # Call the method
        url = "https://example.com/video"
        result = self.downloader.download_video(url)

        # Verify the results
        self.assertTrue(result)
        self.mocks["download_started"].emit.assert_called_once_with(url)
        self.mocks["download_completed"].emit.assert_called_once_with(
            url, "/test/output/dir/video.mp4")

    @patch("os.path.exists")
    def test_download_video_no_output_dir(self, mock_exists):
        """Test the download_video method with no output directory"""
        # Configure mocks
        mock_exists.return_value = True
        self.downloader.output_dir = ""  # Empty output directory

        # Call the method
        url = "https://example.com/video"
        result = self.downloader.download_video(url)

        # Verify the results
        self.assertFalse(result)
        self.mocks["download_started"].emit.assert_called_once_with(url)
        self.mocks["download_error"].emit.assert_called_once_with(
            url, "No output directory has been selected")

    @patch("os.path.exists")
    def test_download_video_no_yt_dlp(self, mock_exists):
        """Test the download_video method with no yt-dlp available"""
        # Configure mocks
        mock_exists.return_value = False
        self.downloader.yt_dlp_path = "/non/existent/path"

        # Call the method
        url = "https://example.com/video"
        result = self.downloader.download_video(url)

        # Verify the results
        self.assertFalse(result)
        self.mocks["download_started"].emit.assert_called_once_with(url)
        self.mocks["download_error"].emit.assert_called_once_with(
            url, "yt-dlp is not available")

    @patch("os.path.exists")
    @patch("subprocess.Popen")
    def test_download_video_process_error(self, mock_popen, mock_exists):
        """Test the download_video method with process error"""
        # Configure mocks
        mock_exists.return_value = True
        self.downloader.yt_dlp_path = os.path.join(self.mock_temp_dir, "yt-dlp")

        # Mock Popen process with error
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Error return code
        mock_process.stdout = StringIO("Some error output\n")
        mock_popen.return_value = mock_process

        # Call the method
        url = "https://example.com/video"
        result = self.downloader.download_video(url)

        # Verify the results
        self.assertFalse(result)
        self.mocks["download_started"].emit.assert_called_once_with(url)
        self.mocks["download_error"].emit.assert_called_once_with(
            url, "Download error. Check the logs for more details.")

    @patch("os.path.exists")
    @patch("subprocess.Popen")
    def test_download_video_exception(self, mock_popen, mock_exists):
        """Test the download_video method with an exception"""
        # Configure mocks
        mock_exists.return_value = True  # Make os.path.exists return True
        self.downloader.yt_dlp_path = os.path.join(self.mock_temp_dir, "yt-dlp")  # Set a valid path
        mock_popen.side_effect = Exception("Test error")

        # Call the method
        url = "https://example.com/video"
        result = self.downloader.download_video(url)

        # Verify the results
        self.assertFalse(result)
        self.mocks["download_started"].emit.assert_called_once_with(url)
        self.mocks["download_error"].emit.assert_called_once_with(
            url, "Test error")

    def test_extract_filename_from_output(self):
        """Test the _extract_filename_from_output method"""
        # Test with filename in output
        output = "Some output\n[download] Destination: /path/to/video.mp4\nMore output"
        filename = self.downloader._extract_filename_from_output(output)
        self.assertEqual(filename, "/path/to/video.mp4")

        # Test with no filename in output
        output = "Some output\nNo destination info\nMore output"
        filename = self.downloader._extract_filename_from_output(output)
        self.assertEqual(filename, "File downloaded")

        # Test with exception
        filename = self.downloader._extract_filename_from_output(None)  # Will cause an exception
        self.assertEqual(filename, "File downloaded")

    def test_set_output_dir(self):
        """Test the set_output_dir method"""
        new_dir = "/new/output/dir"
        self.downloader.set_output_dir(new_dir)
        self.assertEqual(self.downloader.output_dir, new_dir)

    @patch("os.path.exists")
    def test_is_yt_dlp_available_true(self, mock_exists):
        """Test the is_yt_dlp_available method when yt-dlp is available"""
        # Configure mocks
        mock_exists.return_value = True
        self.downloader.yt_dlp_path = "/path/to/yt-dlp"

        # Call the method
        result = self.downloader.is_yt_dlp_available()

        # Verify the results
        self.assertTrue(result)
        mock_exists.assert_called_once_with("/path/to/yt-dlp")

    @patch("os.path.exists")
    def test_is_yt_dlp_available_false_no_path(self, mock_exists):
        """Test the is_yt_dlp_available method when yt-dlp path is None"""
        # Configure mocks
        mock_exists.return_value = True
        self.downloader.yt_dlp_path = None

        # Call the method
        result = self.downloader.is_yt_dlp_available()

        # Verify the results
        self.assertFalse(result)
        mock_exists.assert_not_called()

    @patch("os.path.exists")
    def test_is_yt_dlp_available_false_not_exists(self, mock_exists):
        """Test the is_yt_dlp_available method when yt-dlp file doesn't exist"""
        # Configure mocks
        mock_exists.return_value = False
        self.downloader.yt_dlp_path = "/path/to/yt-dlp"

        # Call the method
        result = self.downloader.is_yt_dlp_available()

        # Verify the results
        self.assertFalse(result)
        mock_exists.assert_called_once_with("/path/to/yt-dlp")


if __name__ == "__main__":
    unittest.main()