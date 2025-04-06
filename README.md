# VideoDL

<div align="center">

![VideoDL Logo](resources/icons/icon.ico)

**A modern, user-friendly video downloader application for windows (and other platforms).**

</div>

## Features

- **Concurrent Downloads**: Configure the number of simultaneous downloads (1-10)
- **Clean User Interface**: Modern, intuitive UI with status updates and logs
- **Automatic Updates**: Built-in yt-dlp downloader ensures you always have the latest version
- **Visual Status Tracking**: Color-coded status indicators for each download
- **Detailed Logging**: View progress and debug information for each download

## Screenshots

![VideoDLScreenshot](https://github.com/user-attachments/assets/0dcf5f59-1921-4725-8763-db42671dfeed)

## Installation

### Windows

#### Option 1: Pre-built Executable
1. Go to the [Releases](https://github.com/randomname124290358349/videoDL/releases) page
2. Download the latest `VideoDL.exe` file
3. Run the executable - no installation required!

#### Option 2: Build from Source
1. Clone the repository
   ```
   git clone https://github.com/randomname124290358349/videoDL.git
   ```
2. Install requirements
   ```
   pip install -r requirements.txt
   ```
3. Run the application
   ```
   python main.py
   ```

### Other Platforms (Linux, macOS)

1. Clone the repository
   ```
   git clone https://github.com/randomname124290358349/videoDL.git
   ```
2. Install requirements
   ```
   pip install -r requirements.txt
   ```
3. Run the application
   ```
   python main.py
   ```

## Requirements

- Python 3.8 or higher
- PyQt6
- Internet connection for downloading yt-dlp and videos

## How to Use

1. Launch the application
2. Select an output directory using the "Browse" button
3. Paste video URLs (one per line) in the text area
4. Adjust the number of concurrent downloads if needed
5. Click "Start Downloads"
6. Watch the progress in the downloads area

## Supported Sites

VideoDL uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the actual downloading, so it supports all sites compatible with yt-dlp. This includes:

- YouTube
- Vimeo
- Twitter
- TikTok
- Facebook
- Instagram
- SoundCloud
- And hundreds more!

For the full list of supported sites, visit the [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Building

### Windows

The project includes a GitHub Actions workflow that automatically builds the Windows executable. You can also build it manually:

```
pyinstaller --name=VideoDL --onefile --windowed --add-data "resources;resources" --icon=resources/icons/icon.ico main.py
```

### Linux/macOS

```
pyinstaller --name=VideoDL --onefile --windowed --add-data "resources:resources" --icon=resources/icons/icon.ico main.py
```

## Technical Details

- **Programming Language**: Python
- **UI Framework**: PyQt6
- **Downloader Backend**: yt-dlp
- **Concurrency**: QThreadPool for multi-threaded downloads

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the powerful download engine
- [PyQt](https://riverbankcomputing.com/software/pyqt/) for the UI framework
