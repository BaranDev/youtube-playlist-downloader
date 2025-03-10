<p align="center">
  <img src="docs/images/icon.png" alt="Youtube Playlist Downloader Logo" width="160"/>
</p>

# YouTube Playlist Downloader

A simple yet powerful Python application to download entire YouTube playlists in high quality MP4 format.

## Features

- Downloads complete YouTube playlists
- Extracts videos in high quality (best video + best audio)
- Automatically converts to MP4 format
- Numbers files according to playlist order
- Handles errors gracefully without stopping the entire process

## Requirements

- Python 3.6+
- yt-dlp
- FFmpeg (for video conversion)

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/barandev/youtube-playlist-downloader.git
    cd youtube-playlist-downloader
    ```

2. Install the required dependencies:
    ```bash
    pip install yt-dlp
    ```

3. Install FFmpeg:
    - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
    - **macOS**: `WIP`
    - **Linux**: `WIP`
  
## Usage

Run the script:
```bash
python main.py
```

When prompted, enter the URL of the YouTube playlist you want to download:
```
Enter YouTube playlist URL: https://www.youtube.com/playlist?list=PLexample123456
```

The videos will be downloaded to a `downloads` folder in the current directory, named according to their position in the playlist:
```
downloads/
  1 - First Video.mp4
  2 - Second Video.mp4
  ...
```

## Customization

You can modify the `download_playlist` function parameters to change:

- Output directory (default is "downloads")
- Video format
- Naming convention
- Other yt-dlp options

## How It Works

The application uses yt-dlp (a fork of youtube-dl) to:

1. Extract playlist metadata
2. Download each video in the highest available quality
3. Merge video and audio streams
4. Convert the result to MP4 format

## Limitations

- Requires a stable internet connection
- Download speed depends on your connection
- Some videos may be unavailable due to regional restrictions or privacy settings

## License

This project is released under the MIT License.

## Disclaimer !

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws when downloading content.