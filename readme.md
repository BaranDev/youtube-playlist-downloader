# YouTube Playlist Downloader

This repository contains a simple Python script to download YouTube playlists using `yt-dlp`. The script downloads the best video and audio quality available and saves them in the specified output directory.

## Requirements

- Python 3.x
- `yt-dlp`

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/barandev/youtube_playlist_downloader.git
    cd youtube_playlist_downloader
    ```

2. Install the required Python packages:
    ```sh
    pip install yt-dlp
    ```

## Usage

1. Run the script:
    ```sh
    python main.py
    ```

2. Enter the YouTube playlist URL when prompted.

The downloaded videos will be saved in the `downloads` directory by default.

## Options

- You can change the output directory by modifying the `output_dir` parameter in the `download_playlist` function.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for providing the downloading functionality.

## Additional Requirements

- `ffmpeg` is required for post-processing. You can install it using one of the following methods:

    - Release essentials:
        ```sh
        choco install ffmpeg
        winget install "FFmpeg (Essentials Build)"
        ```

    - Release full:
        ```sh
        choco install ffmpeg-full
        scoop install ffmpeg
        winget install ffmpeg
        ```

    - Release full shared:
        ```sh
        scoop install ffmpeg-shared
        winget install "FFmpeg (Shared)"
        ```

    - Git master:
        ```sh
        scoop install ffmpeg-gyan-nightly
        ```
