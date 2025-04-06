import unittest

# Import the module to test
from controllers.url_validator import is_valid_url, clean_url_list


class TestUrlValidator(unittest.TestCase):
    def test_is_valid_url_with_valid_urls(self):
        """Test that valid URLs are correctly validated."""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://example.com/path/to/resource",
            "http://example.com/path?query=string",
            "https://example.com/video.mp4",
            "http://localhost:8080",
            "http://127.0.0.1",
            "https://192.168.1.1:8080/resource",
            "http://sub.domain.example.com",
            "https://example.co.uk",
            "http://example-site.com",
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(is_valid_url(url), f"URL should be valid: {url}")

    def test_is_valid_url_with_invalid_urls(self):
        """Test that invalid URLs are correctly rejected."""
        invalid_urls = [
            "",  # Empty string
            "example.com",  # Missing protocol
            "www.example.com",  # Missing protocol
            "ftp://example.com",  # Wrong protocol
            "http:/example.com",  # Missing slash
            "http//example.com",  # Missing colon
            "http://",  # Missing domain
            "http://.com",  # Invalid domain
            "http://example..com",  # Double dot
            "http://example",  # Incomplete domain
            "javascript:alert('XSS')",  # JavaScript URL
            "file:///etc/passwd",  # File URL
            "http://user:pass@example.com",  # Authentication not supported
            "   http://example.com   ",  # Contains whitespace
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(is_valid_url(url), f"URL should be invalid: {url}")

    def test_clean_url_list_with_valid_string(self):
        """Test cleaning a string containing URLs."""
        url_string = """
        https://example.com/video1.mp4
        https://example.com/video2.mp4
        http://invalid
        https://example.org/file.mp4
        not a url
        """
        
        expected = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.org/file.mp4"
        ]
        
        result = clean_url_list(url_string)
        self.assertEqual(result, expected)

    def test_clean_url_list_with_list(self):
        """Test cleaning a list of URLs."""
        url_list = [
            "https://example.com/video1.mp4",
            "invalid url",
            "https://example.com/video2.mp4",
            "   ",  # Empty line with whitespace
            "http://localhost:8080"
        ]
        
        expected = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "http://localhost:8080"
        ]
        
        result = clean_url_list(url_list)
        self.assertEqual(result, expected)

    def test_clean_url_list_with_empty_input(self):
        """Test cleaning an empty input."""
        self.assertEqual(clean_url_list(""), [])
        self.assertEqual(clean_url_list([]), [])
        self.assertEqual(clean_url_list("\n\n   \n"), [])

    def test_clean_url_list_with_mixed_valid_invalid(self):
        """Test cleaning a mixed list of valid and invalid URLs."""
        url_string = """
        https://example.com/video1.mp4
        ftp://example.com/file.txt
        www.example.com
        https://example.org/resource
        http://192.168.1.1:8080
        """
        
        expected = [
            "https://example.com/video1.mp4",
            "https://example.org/resource",
            "http://192.168.1.1:8080"
        ]
        
        result = clean_url_list(url_string)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
