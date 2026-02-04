# Pinterest Downloader

A Python application for downloading Pinterest content with a graphical user interface (GUI). This tool allows you to easily download pins, videos, and images from Pinterest with support for batch processing and local storage management.

## Features

- **GUI Interface**: User-friendly Tkinter-based graphical interface
- **Media Downloading**: Download both images and videos from Pinterest pins
- **Database Management**: SQLite database to track downloaded pins and their metadata
- **Batch Processing**: Download multiple pins efficiently
- **Local Storage**: Organize and manage downloaded media files
- **Async Support**: Asynchronous downloading for improved performance
- **Browser Automation**: Selenium-based web scraping with Chrome WebDriver support

## Project Structure

```
├── pinterest_gui.py       # Main GUI application
├── code_download.py       # Media downloading logic
├── pinterest_db.py        # Database management
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Requirements

- Python 3.7+
- Chrome browser (for Selenium automation)
- Dependencies listed in `requirements.txt`

## Installation

1. Clone or download this project:
```bash
cd "Pinterest Downloader"
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. The application will automatically manage ChromeDriver for Selenium automation.

## Usage

Run the main GUI application:

```bash
python pinterest_gui.py
```

### Main Components

- **pinterest_gui.py**: The main application window with download management interface
- **code_download.py**: Handles the actual media extraction and downloading from Pinterest URLs
- **pinterest_db.py**: Manages SQLite database for storing pin information and file locations

## Dependencies

- Django - Web framework components
- djangorestframework - REST API support
- crawl4ai - Advanced web crawling capabilities
- playwright - Browser automation
- beautifulsoup4 - HTML parsing
- requests - HTTP requests
- selenium - Web browser automation
- webdriver-manager - Automatic ChromeDriver management

## Features Overview

### Downloading
- Extract media URLs from Pinterest pins
- Support for both images and videos
- Async/await for non-blocking operations
- Automatic fallback media extraction

### Database
- Track downloaded pins with metadata
- Store file paths and pin information
- Update and query pin records

### GUI
- Download URL input
- File save location selection
- Progress tracking
- Download history management

## License

This project is provided as-is for personal use.

## Notes

- Ensure you have permission to download content from Pinterest
- The application respects Pinterest's terms of service
- Large batch downloads may take time depending on internet speed
