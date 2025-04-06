from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from PyQt6.QtCore import QRunnable, pyqtSlot


class DownloadTask(QRunnable):
    """Task for background download using QThreadPool"""

    def __init__(self, downloader, url):
        super().__init__()
        self.downloader = downloader
        self.url = url

    @pyqtSlot()
    def run(self):
        """Executes the download in a separate thread"""
        self.downloader.download_video(self.url)


class DownloadController(QObject):
    """Controller to manage multiple downloads"""

    # Signals
    download_queue_updated = pyqtSignal(list)
    all_downloads_completed = pyqtSignal()

    def __init__(self, downloader):
        super().__init__()
        self.downloader = downloader
        self.thread_pool = QThreadPool()
        self.download_queue = []
        self.current_downloads = set()

        # Configure maximum number of simultaneous downloads
        self.max_concurrent = 3
        self.thread_pool.setMaxThreadCount(self.max_concurrent)

        # Connect downloader signals
        self.downloader.download_completed.connect(self._on_download_completed)
        self.downloader.download_error.connect(self._on_download_error)

    def add_urls(self, urls):
        """Add URLs to the download queue"""

        for url in urls:
            if url not in self.download_queue and url not in self.current_downloads:
                self.download_queue.append(url)

        self.download_queue_updated.emit(self.download_queue)
        self._process_queue()

        return urls

    def _process_queue(self):
        """Process the download queue by starting new downloads as availability permits"""
        while (len(self.current_downloads) < self.max_concurrent and
               len(self.download_queue) > 0):
            url = self.download_queue.pop(0)
            self.current_downloads.add(url)

            # Create and start download task
            task = DownloadTask(self.downloader, url)
            self.thread_pool.start(task)

        self.download_queue_updated.emit(self.download_queue)

    def _on_download_completed(self, url, filename):
        """Handle download completed event"""
        if url in self.current_downloads:
            self.current_downloads.remove(url)
            self._process_queue()

        if len(self.current_downloads) == 0 and len(self.download_queue) == 0:
            self.all_downloads_completed.emit()

    def _on_download_error(self, url, error):
        """Handle download error event"""
        if url in self.current_downloads:
            self.current_downloads.remove(url)
            self._process_queue()

    def clear_queue(self):
        """Clear the download queue (does not affect downloads in progress)"""
        self.download_queue.clear()
        self.download_queue_updated.emit(self.download_queue)

    def set_max_concurrent(self, count):
        """Set the maximum number of simultaneous downloads"""
        self.max_concurrent = max(1, count)
        self.thread_pool.setMaxThreadCount(self.max_concurrent)