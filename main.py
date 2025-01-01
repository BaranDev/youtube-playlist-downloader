import yt_dlp
import os


def download_playlist(playlist_url, output_dir="downloads"):
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]",
        "outtmpl": f"{output_dir}/%(playlist_index)s - %(title)s.%(ext)s",
        "ignoreerrors": True,
        "quiet": False,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(playlist_url, download=True)
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    playlist_url = input("Enter YouTube playlist URL: ")
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    download_playlist(playlist_url)
