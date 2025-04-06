import unittest
from unittest.mock import Mock
from PyQt6.QtCore import QThreadPool

# Import the class to test
from controllers.download_controller import DownloadController, DownloadTask


class TestDownloadController(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock downloader
        self.mock_downloader = Mock()
        self.mock_downloader.download_completed = Mock()
        self.mock_downloader.download_error = Mock()
        
        # Create the controller with the mock downloader
        self.controller = DownloadController(self.mock_downloader)
        
        # Sample URLs for testing
        self.sample_urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video3.mp4",
            "https://example.com/video4.mp4",
            "https://example.com/video5.mp4"
        ]

    def test_initialization(self):
        """Test the controller initializes with the correct default values."""
        self.assertEqual(self.controller.max_concurrent, 3)
        self.assertEqual(len(self.controller.download_queue), 0)
        self.assertEqual(len(self.controller.current_downloads), 0)
        self.assertIsInstance(self.controller.thread_pool, QThreadPool)
        self.assertEqual(self.controller.thread_pool.maxThreadCount(), 3)

    def test_add_urls(self):
        """Test adding URLs to the download queue."""
        # Mock _process_queue to prevent it from actually processing URLs
        self.controller._process_queue = Mock()
        
        # Set up a signal capture for download_queue_updated
        signal_received = []
        self.controller.download_queue_updated.connect(lambda queue: signal_received.append(queue))
        
        # Add URLs to the queue
        added_urls = self.controller.add_urls(self.sample_urls[:2])
        
        # Verify the URLs were added to the queue
        self.assertEqual(added_urls, self.sample_urls[:2])
        self.assertEqual(self.controller.download_queue, self.sample_urls[:2])
        
        # Verify the signal was emitted
        self.assertEqual(len(signal_received), 1)
        self.assertEqual(signal_received[0], self.sample_urls[:2])
        
        # Verify _process_queue was called
        self.controller._process_queue.assert_called_once()

    def test_add_duplicate_urls(self):
        """Test adding duplicate URLs to the queue."""
        # Mock _process_queue to prevent it from actually processing URLs
        self.controller._process_queue = Mock()
        
        # Add the same URL twice
        self.controller.add_urls([self.sample_urls[0]])
        self.controller.add_urls([self.sample_urls[0]])
        
        # Verify the URL was only added once
        self.assertEqual(len(self.controller.download_queue), 1)
        
        # Add a URL that's already in current_downloads
        self.controller.current_downloads.add(self.sample_urls[1])
        self.controller.add_urls([self.sample_urls[1]])
        
        # Verify it wasn't added to the queue
        self.assertNotIn(self.sample_urls[1], self.controller.download_queue)

    def test_process_queue(self):
        """Test processing the download queue."""
        # Add URLs to the queue
        self.controller.download_queue = self.sample_urls[:5].copy()
        
        # Mock the thread_pool.start method
        self.controller.thread_pool.start = Mock()
        
        # Set up signal capture
        signal_received = []
        self.controller.download_queue_updated.connect(lambda queue: signal_received.append(queue))
        
        # Process the queue
        self.controller._process_queue()
        
        # Verify the correct number of downloads were started (max_concurrent = 3)
        self.assertEqual(len(self.controller.current_downloads), 3)
        self.assertEqual(len(self.controller.download_queue), 2)
        
        # Verify thread_pool.start was called 3 times
        self.assertEqual(self.controller.thread_pool.start.call_count, 3)
        
        # Verify the signal was emitted with the updated queue
        self.assertEqual(len(signal_received), 1)
        self.assertEqual(signal_received[0], self.sample_urls[3:5])

    def test_on_download_completed(self):
        """Test handling download completion."""
        # Set up the controller with current downloads
        url = self.sample_urls[0]
        self.controller.current_downloads.add(url)
        
        # Add more URLs to the queue
        self.controller.download_queue = self.sample_urls[1:3].copy()
        
        # Mock _process_queue
        self.controller._process_queue = Mock()
        
        # Mock all_downloads_completed signal
        self.controller.all_downloads_completed = Mock()
        
        # Simulate download completion
        self.controller._on_download_completed(url, "downloaded_video.mp4")
        
        # Verify the URL was removed from current_downloads
        self.assertNotIn(url, self.controller.current_downloads)
        
        # Verify _process_queue was called
        self.controller._process_queue.assert_called_once()
        
        # Verify all_downloads_completed was not emitted (queue not empty)
        self.controller.all_downloads_completed.emit.assert_not_called()
        
        # Clear the queue and current downloads
        self.controller.download_queue.clear()
        self.controller.current_downloads.clear()
        
        # Reset the mock
        self.controller._process_queue.reset_mock()
        
        # Simulate download completion with empty queue
        self.controller._on_download_completed(url, "downloaded_video.mp4")
        
        # Verify all_downloads_completed was emitted
        self.controller.all_downloads_completed.emit.assert_called_once()

    def test_on_download_error(self):
        """Test handling download errors."""
        # Set up the controller with current downloads
        url = self.sample_urls[0]
        self.controller.current_downloads.add(url)
        
        # Mock _process_queue
        self.controller._process_queue = Mock()
        
        # Simulate download error
        self.controller._on_download_error(url, "Connection error")
        
        # Verify the URL was removed from current_downloads
        self.assertNotIn(url, self.controller.current_downloads)
        
        # Verify _process_queue was called
        self.controller._process_queue.assert_called_once()

    def test_clear_queue(self):
        """Test clearing the download queue."""
        # Add URLs to the queue
        self.controller.download_queue = self.sample_urls[:3].copy()
        
        # Set up signal capture
        signal_received = []
        self.controller.download_queue_updated.connect(lambda queue: signal_received.append(queue))
        
        # Clear the queue
        self.controller.clear_queue()
        
        # Verify the queue is empty
        self.assertEqual(len(self.controller.download_queue), 0)
        
        # Verify the signal was emitted with an empty queue
        self.assertEqual(len(signal_received), 1)
        self.assertEqual(signal_received[0], [])

    def test_set_max_concurrent(self):
        """Test setting the maximum number of concurrent downloads."""
        # Set max_concurrent to a new value
        self.controller.set_max_concurrent(5)
        
        # Verify max_concurrent was updated
        self.assertEqual(self.controller.max_concurrent, 5)
        self.assertEqual(self.controller.thread_pool.maxThreadCount(), 5)
        
        # Test with a value less than 1
        self.controller.set_max_concurrent(0)
        
        # Verify min value of 1 is enforced
        self.assertEqual(self.controller.max_concurrent, 1)
        self.assertEqual(self.controller.thread_pool.maxThreadCount(), 1)

    def test_download_task(self):
        """Test the DownloadTask class."""
        # Create a DownloadTask
        url = self.sample_urls[0]
        task = DownloadTask(self.mock_downloader, url)
        
        # Run the task
        task.run()
        
        # Verify the downloader's download_video method was called with the correct URL
        self.mock_downloader.download_video.assert_called_once_with(url)


if __name__ == '__main__':
    unittest.main()
