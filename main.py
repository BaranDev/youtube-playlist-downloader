import yt_dlp
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from threading import Thread, Event
import time
import json
from datetime import datetime
import urllib.request
from PIL import Image, ImageTk
from io import BytesIO
import sys
import humanize

# ===== Configuration settings =====
# GUI settings
APP_TITLE = "YouTube Playlist Downloader"
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 800
PADDING = 10
YOUTUBE_RED = "#FF0000"
YOUTUBE_WHITE = "#FFFFFF"
YOUTUBE_DARK = "#000000"  # Changed to black
YOUTUBE_LIGHT_GRAY = "#F5F5F5"
YOUTUBE_GRAY = "#000000"  # Changed to black
BUTTON_TEXT_COLOR = "#000000"  # Text color for all buttons
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"
FONT_SIZE_SMALL = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_LARGE = 12
FONT_SIZE_TITLE = 14
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube")

# Text labels
LABEL_PLAYLIST_URL = "Playlist URL"
LABEL_OUTPUT_DIR = "Save to"
BUTTON_DOWNLOAD = "Download"
BUTTON_STOP = "Cancel"
BUTTON_PAUSE = "Pause"
BUTTON_RESUME = "Resume"
BUTTON_BROWSE = "Browse..."
STATUS_READY = "Ready to download"
STATUS_PREVIEWING = "Loading playlist details..."
STATUS_DOWNLOADING = "Downloading..."
STATUS_PAUSED = "Download paused"
STATUS_STOPPED = "Download stopped"
STATUS_COMPLETE = "Download completed!"
STATUS_ERROR = "Error: {}"
DEFAULT_STATUS = STATUS_READY

# Download options
FORMAT_OPTIONS = [
    (
        "Best Quality (Video + Audio)",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    ),
    (
        "HD 1080p",
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
    ),
    (
        "HD 720p",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    ),
    (
        "480p",
        "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
    ),
    (
        "360p",
        "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]",
    ),
    ("Audio Only (MP3)", "bestaudio[ext=m4a]/bestaudio"),
]
DEFAULT_OUTPUT_TEMPLATE = "%(playlist_index)s. %(title)s.%(ext)s"


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_thumbnail(url):
    """Download and create a thumbnail image from URL"""
    try:
        with urllib.request.urlopen(url) as response:
            img_data = response.read()
            img = Image.open(BytesIO(img_data))
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Error loading thumbnail: {e}")
        return None


def format_size(bytes_size):
    """Format bytes to human-readable size"""
    return humanize.naturalsize(bytes_size)


def format_time(seconds):
    """Format seconds to human-readable time"""
    if seconds < 60:
        return f"{seconds:.0f} sec"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hrs"


class DownloadManager:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self.active_downloads = {}
        self.history = []
        self.last_update_time = {}
        self.download_speeds = {}
        self.stop_events = {}
        self.pause_events = {}
        self.current_playlist_info = None

        # Create history file if it doesn't exist
        self.history_file = os.path.join(
            os.path.expanduser("~"), ".youtube_downloader_history.json"
        )
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_history(self):
        """Save download history to file"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    def get_playlist_info(self, playlist_url, callback=None):
        """Get playlist information without downloading"""
        if not playlist_url.strip():
            if callback:
                callback(None, "Please enter a valid URL")
            return

        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "dump_single_json": True,
            "skip_download": True,
            "force_generic_extractor": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(playlist_url, download=False)
                self.current_playlist_info = info
                if callback:
                    callback(info, None)
                return info
            except Exception as e:
                error_message = str(e)
                if callback:
                    callback(None, error_message)
                return None

    def download_playlist(
        self,
        playlist_url,
        output_dir,
        format_option,
        selected_indices=None,
        save_thumbnail=False,
    ):
        """Download playlist videos"""
        if not playlist_url.strip():
            if self.status_callback:
                self.status_callback(STATUS_ERROR.format("Please enter a valid URL"))
            return

        # Create a unique ID for this download
        download_id = f"{int(time.time())}"
        self.stop_events[download_id] = Event()
        self.pause_events[download_id] = Event()

        # Prepare for download metrics
        self.last_update_time[download_id] = time.time()
        self.download_speeds[download_id] = []

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Format selection
        format_str = next(
            (f for _, f in FORMAT_OPTIONS if f == format_option), FORMAT_OPTIONS[0][1]
        )

        # Setup postprocessors
        postprocessors = []
        if "Audio Only" in format_option:
            postprocessors.append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            )
        else:
            postprocessors.append(
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
            )

        # Add merge output format to prevent leftover files
        postprocessors.append(
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            }
        )

        # Download options
        ydl_opts = {
            "format": format_str,
            "outtmpl": os.path.join(output_dir, DEFAULT_OUTPUT_TEMPLATE),
            "ignoreerrors": True,
            "quiet": False,
            "postprocessors": postprocessors,
            "writethumbnail": save_thumbnail,
            "progress_hooks": [lambda d: self.update_progress(d, download_id)],
            "noplaylist": False,
            "continuedl": True,
            "merge_output_format": "mp4",  # Force merging to mp4 to prevent leftovers
            "keepvideo": False,  # Don't keep separate video files
        }

        # Add selected indices if specified
        if selected_indices and len(selected_indices) > 0:
            # Convert to playlist_items format: 1,2,5-7,10
            items = []
            for i in sorted(selected_indices):
                items.append(str(i + 1))  # 1-indexed in youtube-dl
            ydl_opts["playlist_items"] = ",".join(items)

        # Save to history
        history_entry = {
            "id": download_id,
            "url": playlist_url,
            "output_dir": output_dir,
            "format": format_option,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "started",
            "title": (
                self.current_playlist_info.get("title", "Unknown Playlist")
                if self.current_playlist_info
                else "Unknown Playlist"
            ),
            "videos_count": (
                len(self.current_playlist_info.get("entries", []))
                if self.current_playlist_info
                else 0
            ),
        }
        self.history.append(history_entry)
        self.save_history()

        # Start download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Update status
                if self.status_callback:
                    self.status_callback(
                        {"status": STATUS_DOWNLOADING, "download_id": download_id}
                    )

                # Download
                ydl.download([playlist_url])

                # Check if download was stopped or completed
                if self.stop_events[download_id].is_set():
                    if self.status_callback:
                        self.status_callback(
                            {"status": STATUS_STOPPED, "download_id": download_id}
                        )

                    # Update history
                    for entry in self.history:
                        if entry["id"] == download_id:
                            entry["status"] = "stopped"
                            break
                else:
                    if self.status_callback:
                        self.status_callback(
                            {"status": STATUS_COMPLETE, "download_id": download_id}
                        )

                    # Update history
                    for entry in self.history:
                        if entry["id"] == download_id:
                            entry["status"] = "completed"
                            break

                self.save_history()

            except Exception as e:
                error_message = str(e)
                if self.status_callback:
                    self.status_callback(
                        {
                            "status": STATUS_ERROR.format(error_message),
                            "download_id": download_id,
                        }
                    )

                # Update history
                for entry in self.history:
                    if entry["id"] == download_id:
                        entry["status"] = "error"
                        entry["error"] = error_message
                        break

                self.save_history()

            finally:
                # Clean up
                if download_id in self.stop_events:
                    del self.stop_events[download_id]
                if download_id in self.pause_events:
                    del self.pause_events[download_id]
                if download_id in self.last_update_time:
                    del self.last_update_time[download_id]
                if download_id in self.download_speeds:
                    del self.download_speeds[download_id]

    def update_progress(self, d, download_id):
        """Update progress information for a specific download"""
        if self.stop_events.get(download_id, Event()).is_set():
            # Download was stopped, raise an exception to break the download
            raise Exception("Download stopped by user")

        # Handle pausing
        while self.pause_events.get(download_id, Event()).is_set():
            if self.status_callback:
                self.status_callback(
                    {"status": STATUS_PAUSED, "download_id": download_id}
                )
            time.sleep(0.5)
            if self.stop_events.get(download_id, Event()).is_set():
                raise Exception("Download stopped by user")

        if d["status"] == "downloading":
            try:
                # Calculate speed
                current_time = time.time()
                time_diff = current_time - self.last_update_time.get(
                    download_id, current_time
                )
                if time_diff > 0:
                    # Get downloaded bytes
                    downloaded_bytes = d.get("downloaded_bytes", 0)
                    total_bytes = d.get("total_bytes", 0) or d.get(
                        "total_bytes_estimate", 0
                    )

                    # Calculate speed
                    speed = d.get("speed", 0)
                    if speed:
                        self.download_speeds[download_id] = self.download_speeds.get(
                            download_id, []
                        )[-9:] + [speed]

                    # Calculate average speed
                    avg_speed = sum(self.download_speeds.get(download_id, [1])) / len(
                        self.download_speeds.get(download_id, [1])
                    )

                    # Calculate ETA
                    eta = d.get("eta", 0)
                    eta_str = format_time(eta) if eta else "Unknown"

                    # Format speed
                    speed_str = (
                        format_size(avg_speed) + "/s" if avg_speed else "Unknown"
                    )

                    # Format progress
                    percent = d.get("_percent_str", "Unknown").strip()
                    filename = os.path.basename(d.get("filename", "Unknown"))

                    # Format size
                    downloaded_str = format_size(downloaded_bytes)
                    total_str = format_size(total_bytes) if total_bytes else "Unknown"

                    # Update status
                    if self.status_callback:
                        self.status_callback(
                            {
                                "status": "downloading",
                                "download_id": download_id,
                                "filename": filename,
                                "percent": percent,
                                "speed": speed_str,
                                "eta": eta_str,
                                "progress": d.get("downloaded_bytes", 0)
                                / (
                                    d.get("total_bytes", 1)
                                    or d.get("total_bytes_estimate", 1)
                                ),
                                "downloaded": downloaded_str,
                                "total": total_str,
                                "playlist_index": d.get("info_dict", {}).get(
                                    "playlist_index", 0
                                ),
                                "playlist_count": d.get("info_dict", {}).get(
                                    "n_entries", 0
                                ),
                            }
                        )

                    # Update last time
                    self.last_update_time[download_id] = current_time
            except:
                pass

        elif d["status"] == "finished":
            # Video download finished, now processing
            if self.status_callback:
                try:
                    filename = os.path.basename(d.get("filename", "Unknown"))
                    self.status_callback(
                        {
                            "status": "processing",
                            "download_id": download_id,
                            "filename": filename,
                            "playlist_index": d.get("info_dict", {}).get(
                                "playlist_index", 0
                            ),
                            "playlist_count": d.get("info_dict", {}).get(
                                "n_entries", 0
                            ),
                        }
                    )
                except:
                    pass

    def stop_download(self, download_id):
        """Stop a specific download"""
        if download_id in self.stop_events:
            self.stop_events[download_id].set()
            if download_id in self.pause_events:
                self.pause_events[download_id].clear()  # Unpause if paused
            return True
        return False

    def pause_download(self, download_id):
        """Pause a specific download"""
        if download_id in self.pause_events:
            self.pause_events[download_id].set()
            return True
        return False

    def resume_download(self, download_id):
        """Resume a specific download"""
        if download_id in self.pause_events:
            self.pause_events[download_id].clear()
            return True
        return False


class YouTubeFrame(ttk.Frame):
    """Custom frame with YouTube styling"""

    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop("bg", YOUTUBE_WHITE)
        super().__init__(parent, style="YouTube.TFrame", **kwargs)
        style = ttk.Style()
        style.configure("YouTube.TFrame", background=bg_color)


class YouTubeLabel(ttk.Label):
    """Custom label with YouTube styling"""

    def __init__(self, parent, **kwargs):
        font_size = kwargs.pop("font_size", FONT_SIZE_NORMAL)
        fg_color = kwargs.pop("fg", YOUTUBE_DARK)
        bg_color = kwargs.pop("bg", YOUTUBE_WHITE)
        font_weight = kwargs.pop("font_weight", "normal")
        super().__init__(parent, style="YouTube.TLabel", **kwargs)
        style = ttk.Style()
        style.configure(
            "YouTube.TLabel",
            font=(FONT_FAMILY, font_size, font_weight),
            foreground=fg_color,
            background=bg_color,
        )


class YouTubeButton(ttk.Button):
    """Custom button with YouTube styling"""

    def __init__(self, parent, **kwargs):
        button_type = kwargs.pop("button_type", "primary")
        super().__init__(parent, style=f"YouTube.{button_type}.TButton", **kwargs)
        style = ttk.Style()

        # Primary button (Red)
        style.configure(
            "YouTube.primary.TButton",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            foreground=YOUTUBE_WHITE,
            background=YOUTUBE_RED,
        )

        # Secondary button (Gray)
        style.configure(
            "YouTube.secondary.TButton",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_LIGHT_GRAY,
        )


class PlaylistDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)
        self.root.configure(bg=YOUTUBE_WHITE)

        # Download manager
        self.download_manager = DownloadManager(self.update_status)

        # Current download info
        self.active_download_id = None
        self.is_paused = False

        # Initialize variables
        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.format_var = tk.StringVar(value=FORMAT_OPTIONS[0][0])
        self.status_var = tk.StringVar(value=DEFAULT_STATUS)
        self.progress_var = tk.DoubleVar(value=0)
        self.save_thumbnail_var = tk.BooleanVar(value=False)
        self.playlist_info = None
        self.selected_videos = []

        # Set up styles
        self.setup_styles()

        # Set up UI
        self.setup_ui()

    def setup_styles(self):
        """Set up ttk styles"""
        style = ttk.Style()

        # Button styles
        style.configure("TButton", font=(FONT_FAMILY, FONT_SIZE_NORMAL), padding=6)

        # Primary button style (red with black text)
        style.configure(
            "Primary.TButton",
            foreground=BUTTON_TEXT_COLOR,
            background=YOUTUBE_RED,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        )
        style.map(
            "Primary.TButton",
            foreground=[("pressed", BUTTON_TEXT_COLOR), ("active", BUTTON_TEXT_COLOR)],
            background=[("pressed", "#CC0000"), ("active", "#DD0000")],
        )

        # Secondary button style (gray with black text)
        style.configure(
            "Secondary.TButton",
            foreground=BUTTON_TEXT_COLOR,
            background=YOUTUBE_LIGHT_GRAY,
        )
        style.map(
            "Secondary.TButton",
            foreground=[("pressed", BUTTON_TEXT_COLOR), ("active", BUTTON_TEXT_COLOR)],
            background=[("pressed", "#E0E0E0"), ("active", "#EBEBEB")],
        )

        # Danger button style (dark red with black text)
        style.configure(
            "Danger.TButton",
            foreground=BUTTON_TEXT_COLOR,
            background="#CC0000",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        )
        style.map(
            "Danger.TButton",
            foreground=[("pressed", BUTTON_TEXT_COLOR), ("active", BUTTON_TEXT_COLOR)],
            background=[("pressed", "#BB0000"), ("active", "#CC0000")],
        )

        # Entry style
        style.configure("TEntry", font=(FONT_FAMILY, FONT_SIZE_NORMAL), padding=8)

        # Label styles - all with black text
        style.configure(
            "TLabel",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_WHITE,
        )

        # Title label
        style.configure(
            "Title.TLabel",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_WHITE,
        )

        # Header label
        style.configure(
            "Header.TLabel",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_WHITE,
        )

        # Status label
        style.configure(
            "Status.TLabel",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_WHITE,
        )

        # Error label
        style.configure(
            "Error.TLabel",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            foreground=YOUTUBE_DARK,
            background=YOUTUBE_WHITE,
        )

        # Frame styles - all with white background, no borders
        style.configure("TFrame", background=YOUTUBE_WHITE)

        # Header frame
        style.configure("Header.TFrame", background=YOUTUBE_WHITE)

        # Content frame
        style.configure("Content.TFrame", background=YOUTUBE_WHITE)

        # Card frame - removed border/relief
        style.configure(
            "Card.TFrame", background=YOUTUBE_WHITE, relief="flat", borderwidth=0
        )

        # Progress bar
        style.configure("TProgressbar", thickness=8, background=YOUTUBE_RED)

        # Combobox
        style.configure("TCombobox", font=(FONT_FAMILY, FONT_SIZE_NORMAL), padding=8)

    def setup_ui(self):
        """Set up the application UI"""
        # Main container (with padding)
        self.main_container = ttk.Frame(self.root, style="TFrame", padding=PADDING)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(self.main_container, style="Header.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # App title
        title_label = ttk.Label(header_frame, text=APP_TITLE, style="Title.TLabel")
        title_label.pack(anchor=tk.W)

        # Input frame
        input_frame = ttk.Frame(self.main_container, style="Content.TFrame")
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # URL input
        url_label = ttk.Label(input_frame, text=LABEL_PLAYLIST_URL, style="TLabel")
        url_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.url_entry = ttk.Entry(input_frame, width=50, style="TEntry")
        self.url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        # URL preview button
        self.preview_button = ttk.Button(
            input_frame,
            text="Get Videos",
            style="Secondary.TButton",
            command=self.preview_playlist,
        )
        self.preview_button.grid(row=1, column=1, padx=5)

        # Output directory
        dir_label = ttk.Label(input_frame, text=LABEL_OUTPUT_DIR, style="TLabel")
        dir_label.grid(row=0, column=2, sticky=tk.W, pady=(0, 5), padx=(20, 0))

        dir_entry = ttk.Entry(
            input_frame, width=30, textvariable=self.output_dir, style="TEntry"
        )
        dir_entry.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(20, 10))

        # Browse button
        browse_button = ttk.Button(
            input_frame,
            text=BUTTON_BROWSE,
            style="Secondary.TButton",
            command=self.browse_directory,
        )
        browse_button.grid(row=1, column=3, padx=5)

        # Format selection
        format_label = ttk.Label(input_frame, text="Format:", style="TLabel")
        format_label.grid(row=2, column=0, sticky=tk.W, pady=(15, 5))

        format_menu = ttk.Combobox(
            input_frame,
            textvariable=self.format_var,
            values=[f[0] for f in FORMAT_OPTIONS],
            state="readonly",
            style="TCombobox",
        )
        format_menu.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        format_menu.current(0)

        # Configure grid
        input_frame.columnconfigure(0, weight=3)
        input_frame.columnconfigure(2, weight=2)

        # Create notebook for playlist info and download history
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Playlist info tab
        self.playlist_frame = ttk.Frame(
            self.notebook, style="Content.TFrame", padding=PADDING
        )
        self.notebook.add(self.playlist_frame, text="Playlist Details")

        # History tab
        self.history_frame = ttk.Frame(
            self.notebook, style="Content.TFrame", padding=PADDING
        )
        self.notebook.add(self.history_frame, text="Download History")

        # Setup playlist frame
        self.setup_playlist_frame()

        # Setup history frame
        self.setup_history_frame()

        # Bottom control frame
        control_frame = ttk.Frame(self.main_container, style="Content.TFrame")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Status display
        status_frame = ttk.Frame(control_frame, style="Content.TFrame")
        status_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 10))

        status_label = ttk.Label(status_frame, text="Status:", style="TLabel")
        status_label.pack(side=tk.LEFT)

        self.status_display = ttk.Label(
            status_frame, textvariable=self.status_var, style="Status.TLabel"
        )
        self.status_display.pack(side=tk.LEFT, padx=(5, 0))

        # Progress info
        self.progress_info = ttk.Label(status_frame, text="", style="Status.TLabel")
        self.progress_info.pack(side=tk.RIGHT)

        # Progress bar
        self.progress = ttk.Progressbar(
            control_frame,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_var,
            style="TProgressbar",
        )
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Button frame
        button_frame = ttk.Frame(control_frame, style="Content.TFrame")
        button_frame.pack(fill=tk.X)

        # Download button
        self.download_button = ttk.Button(
            button_frame,
            text=BUTTON_DOWNLOAD,
            style="Primary.TButton",
            command=self.start_download,
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))

        # Pause/Resume button
        self.pause_button = ttk.Button(
            button_frame,
            text=BUTTON_PAUSE,
            style="Secondary.TButton",
            command=self.toggle_pause,
            state=tk.DISABLED,
        )
        self.pause_button.pack(side=tk.LEFT, padx=(0, 10))

        # Stop button
        self.stop_button = ttk.Button(
            button_frame,
            text=BUTTON_STOP,
            style="Danger.TButton",
            command=self.stop_download,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT)

    def setup_playlist_frame(self):
        """Set up the playlist information frame"""
        # Empty state
        self.playlist_empty_label = ttk.Label(
            self.playlist_frame,
            text="Enter a YouTube playlist URL and click Get Videos to see details",
            style="Header.TLabel",
        )
        self.playlist_empty_label.pack(anchor=tk.CENTER, expand=True)

        # Playlist info container (hidden initially)
        self.playlist_info_container = ttk.Frame(
            self.playlist_frame, style="Content.TFrame"
        )

        # Playlist header
        playlist_header = ttk.Frame(
            self.playlist_info_container, style="Content.TFrame"
        )
        playlist_header.pack(fill=tk.X, pady=(0, 15))

        # Thumbnail placeholder
        self.thumbnail_label = ttk.Label(playlist_header, style="TLabel")
        self.thumbnail_label.pack(side=tk.LEFT, padx=(0, 15))

        # Playlist details
        playlist_details = ttk.Frame(playlist_header, style="Content.TFrame")
        playlist_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.playlist_title = ttk.Label(
            playlist_details, text="", style="Header.TLabel"
        )
        self.playlist_title.pack(anchor=tk.W)

        self.playlist_channel = ttk.Label(playlist_details, text="", style="TLabel")
        self.playlist_channel.pack(anchor=tk.W)

        self.playlist_count = ttk.Label(playlist_details, text="", style="TLabel")
        self.playlist_count.pack(anchor=tk.W)

        # Video selection tools
        selection_frame = ttk.Frame(
            self.playlist_info_container, style="Content.TFrame"
        )
        selection_frame.pack(fill=tk.X, pady=(0, 10))

        selection_label = ttk.Label(
            selection_frame, text="Video Selection:", style="TLabel"
        )
        selection_label.pack(side=tk.LEFT)

        select_all_btn = ttk.Button(
            selection_frame,
            text="Select All",
            style="Secondary.TButton",
            command=self.select_all_videos,
        )
        select_all_btn.pack(side=tk.LEFT, padx=(10, 5))

        select_none_btn = ttk.Button(
            selection_frame,
            text="Deselect All",
            style="Secondary.TButton",
            command=self.deselect_all_videos,
        )
        select_none_btn.pack(side=tk.LEFT)

        # Videos list
        videos_frame = ttk.Frame(self.playlist_info_container, style="Content.TFrame")
        videos_frame.pack(fill=tk.BOTH, expand=True)

        # Add a canvas for scrolling
        self.canvas = tk.Canvas(videos_frame, bg=YOUTUBE_WHITE, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(
            videos_frame, orient="vertical", command=self.canvas.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame inside the canvas for videos
        self.videos_container = ttk.Frame(self.canvas, style="Content.TFrame")
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.videos_container, anchor="nw"
        )

        # Configure scrolling region when videos are added
        self.videos_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Handle resizing
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Mouse wheel scrolling - bind to canvas
        self.bind_mousewheel_to_canvas()

    def setup_history_frame(self):
        """Set up the download history frame"""
        # Create a canvas for scrolling
        self.history_canvas = tk.Canvas(
            self.history_frame, bg=YOUTUBE_WHITE, highlightthickness=0
        )
        self.history_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar
        history_scrollbar = ttk.Scrollbar(
            self.history_frame, orient="vertical", command=self.history_canvas.yview
        )
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas
        self.history_canvas.configure(yscrollcommand=history_scrollbar.set)
        self.history_canvas.bind(
            "<Configure>",
            lambda e: self.history_canvas.configure(
                scrollregion=self.history_canvas.bbox("all")
            ),
        )

        # Create a frame inside the canvas for history items
        self.history_container = ttk.Frame(self.history_canvas, style="Content.TFrame")
        self.history_canvas.create_window(
            (0, 0),
            window=self.history_container,
            anchor="nw",
            width=self.history_canvas.winfo_width(),
        )

        # Handle resizing
        self.history_canvas.bind("<Configure>", self.on_history_canvas_configure)

        # Mouse wheel scrolling
        self.history_canvas.bind_all("<MouseWheel>", self.on_history_mousewheel)
        self.history_canvas.bind_all("<Button-4>", self.on_history_mousewheel)
        self.history_canvas.bind_all("<Button-5>", self.on_history_mousewheel)

        # Load history
        self.load_history()

    def load_history(self):
        """Load download history into the history tab"""
        # Clear existing history items
        for widget in self.history_container.winfo_children():
            widget.destroy()

        # Check if history is empty
        if not self.download_manager.history:
            empty_label = ttk.Label(
                self.history_container,
                text="No download history yet",
                style="Header.TLabel",
            )
            empty_label.pack(anchor=tk.CENTER, expand=True, pady=50)
            return

        # Add history items (most recent first)
        for i, item in enumerate(reversed(self.download_manager.history)):
            self.create_history_item(item, i)

    def create_history_item(self, item, index):
        """Create a history item card"""
        item_frame = ttk.Frame(self.history_container, style="Card.TFrame", padding=10)
        item_frame.pack(fill=tk.X, pady=(0, 10))

        # Title and date
        title_frame = ttk.Frame(item_frame, style="Content.TFrame")
        title_frame.pack(fill=tk.X)

        title = item.get("title", "Unknown Playlist")
        title_label = ttk.Label(title_frame, text=title, style="Header.TLabel")
        title_label.pack(side=tk.LEFT)

        date = item.get("date", "Unknown date")
        date_label = ttk.Label(title_frame, text=date, style="Status.TLabel")
        date_label.pack(side=tk.RIGHT)

        # Details
        details_frame = ttk.Frame(item_frame, style="Content.TFrame")
        details_frame.pack(fill=tk.X, pady=(5, 0))

        # URL
        url_label = ttk.Label(
            details_frame, text=f"URL: {item.get('url', 'Unknown')}", style="TLabel"
        )
        url_label.pack(anchor=tk.W)

        # Format
        format_label = ttk.Label(
            details_frame,
            text=f"Format: {item.get('format', 'Unknown')}",
            style="TLabel",
        )
        format_label.pack(anchor=tk.W)

        # Status with appropriate color
        status = item.get("status", "unknown")
        status_style = "Status.TLabel"
        if status == "completed":
            status_text = "Status: Completed"
        elif status == "error":
            status_text = f"Status: Error - {item.get('error', 'Unknown error')}"
            status_style = "Error.TLabel"
        elif status == "stopped":
            status_text = "Status: Stopped by user"
        else:
            status_text = f"Status: {status.capitalize()}"

        status_label = ttk.Label(details_frame, text=status_text, style=status_style)
        status_label.pack(anchor=tk.W)

        # Directory
        dir_label = ttk.Label(
            details_frame,
            text=f"Saved to: {item.get('output_dir', 'Unknown')}",
            style="TLabel",
        )
        dir_label.pack(anchor=tk.W)

        # Video count
        count_label = ttk.Label(
            details_frame, text=f"Videos: {item.get('videos_count', 0)}", style="TLabel"
        )
        count_label.pack(anchor=tk.W)

        # Action buttons
        button_frame = ttk.Frame(item_frame, style="Content.TFrame")
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Download again button
        redownload_button = ttk.Button(
            button_frame,
            text="Download Again",
            style="Primary.TButton",
            command=lambda i=item: self.redownload_item(i),
        )
        redownload_button.pack(side=tk.LEFT, padx=(0, 5))

        # Open folder button
        open_folder_button = ttk.Button(
            button_frame,
            text="Open Folder",
            style="Secondary.TButton",
            command=lambda d=item.get("output_dir"): self.open_folder(d),
        )
        open_folder_button.pack(side=tk.LEFT)

    def redownload_item(self, item):
        """Redownload a playlist from history"""
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, item.get("url", ""))

        # Set format
        format_str = item.get("format", FORMAT_OPTIONS[0][0])
        self.format_var.set(format_str)

        # Set output directory
        self.output_dir.set(item.get("output_dir", DEFAULT_OUTPUT_DIR))

        # Preview the playlist
        self.preview_playlist()

        # Switch to playlist tab
        self.notebook.select(0)

    def open_folder(self, directory):
        """Open the output directory in file explorer"""
        if os.path.exists(directory):
            if sys.platform == "win32":
                os.startfile(directory)
            elif sys.platform == "darwin":  # macOS
                os.system(f"open '{directory}'")
            else:  # Linux
                os.system(f"xdg-open '{directory}'")
        else:
            messagebox.showerror("Error", "Directory does not exist")

    def on_canvas_configure(self, event):
        """Handle canvas resize event"""
        # Update the width of the canvas window to fill the canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)

        # Make sure the full scrollregion is set
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_history_canvas_configure(self, event):
        """Handle history canvas resize event"""
        self.history_canvas.itemconfig(
            self.history_canvas.find_withtag("all")[0], width=event.width
        )

    def on_mousewheel(self, event):
        """This is kept for compatibility but no longer used directly"""
        # We now use bind_mousewheel_to_canvas() instead
        pass

    def on_history_mousewheel(self, event):
        """Handle mousewheel event for history scrolling"""
        if event.num == 4 or event.delta > 0:
            self.history_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.history_canvas.yview_scroll(1, "units")

    def preview_playlist(self):
        """Preview playlist information"""
        playlist_url = self.url_entry.get().strip()
        if not playlist_url:
            messagebox.showerror("Error", "Please enter a YouTube playlist URL")
            return

        # Update status
        self.status_var.set(STATUS_PREVIEWING)
        self.progress_var.set(0)
        self.progress_info.config(text="")

        # Disable UI during preview
        self.url_entry.config(state=tk.DISABLED)
        self.preview_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)

        # Start preview in a separate thread
        preview_thread = Thread(
            target=self.download_manager.get_playlist_info,
            args=(playlist_url, self.handle_playlist_info),
        )
        preview_thread.daemon = True
        preview_thread.start()

    def handle_playlist_info(self, info, error):
        """Handle playlist information result"""
        # Re-enable UI
        self.url_entry.config(state=tk.NORMAL)
        self.preview_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)

        if error:
            self.status_var.set(STATUS_ERROR.format(error))
            messagebox.showerror("Error", f"Could not load playlist: {error}")
            return

        if info:
            self.playlist_info = info
            self.display_playlist_info(info)
            self.status_var.set(STATUS_READY)

            # Switch to playlist tab
            self.notebook.select(0)
        else:
            self.status_var.set(
                STATUS_ERROR.format("Could not load playlist information")
            )

    def display_playlist_info(self, info):
        """Display playlist information"""
        # Hide empty state and show playlist info
        self.playlist_empty_label.pack_forget()
        self.playlist_info_container.pack(fill=tk.BOTH, expand=True)

        # Set playlist details
        title = info.get("title", "Unknown Playlist")
        self.playlist_title.config(text=title)

        channel = info.get("uploader", "Unknown Channel")
        self.playlist_channel.config(text=f"Channel: {channel}")

        entries = info.get("entries", [])
        count = len(entries)
        self.playlist_count.config(text=f"Videos: {count}")

        # Try to get and display thumbnail
        if "thumbnail" in info:
            thumbnail = get_thumbnail(info["thumbnail"])
            if thumbnail:
                self.thumbnail_label.config(image=thumbnail)
                self.thumbnail_label.image = thumbnail

        # Clear existing videos
        for widget in self.videos_container.winfo_children():
            widget.destroy()

        # Add videos
        self.selected_videos = []
        for i, video in enumerate(entries):
            self.add_video_item(video, i)

        # Make sure scrolling is properly bound to all new items
        self.bind_mousewheel_to_canvas()

        # Select all videos by default
        self.select_all_videos()

        # Update the scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bind_mousewheel_to_canvas(self):
        """Bind mousewheel events to the canvas and all its children"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

        def _bind_to_widget(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel_linux)
            widget.bind("<Button-5>", _on_mousewheel_linux)

            # Recursively bind to all children
            for child in widget.winfo_children():
                _bind_to_widget(child)

        # Bind to canvas and videos container
        _bind_to_widget(self.canvas)
        _bind_to_widget(self.videos_container)

    def add_video_item(self, video, index):
        """Add a video item to the videos list"""
        video_id = video.get("id", "")
        title = video.get("title", "Unknown Video")

        # Create a frame for the video item
        video_frame = ttk.Frame(self.videos_container, style="Card.TFrame", padding=5)
        video_frame.pack(fill=tk.X, pady=(0, 5))

        # Checkbox for selection
        var = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(
            video_frame,
            variable=var,
            command=lambda i=index, v=var: self.toggle_video_selection(i, v.get()),
        )
        checkbox.pack(side=tk.LEFT, padx=(0, 10))

        # Video index
        index_label = ttk.Label(video_frame, text=f"{index + 1}.", style="TLabel")
        index_label.pack(side=tk.LEFT, padx=(0, 10))

        # Video title
        title_label = ttk.Label(video_frame, text=title, style="TLabel")
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Store references
        video["_checkbox_var"] = var
        video["_index"] = index

        # Bind mouse wheel for scrolling on this item too
        self.bind_mousewheel_to_widget_and_children(video_frame)

    def bind_mousewheel_to_widget_and_children(self, widget):
        """Bind mousewheel events to a widget and all its children"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"  # Prevent event from propagating

        def _on_mousewheel_linux(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            return "break"  # Prevent event from propagating

        # Bind to this widget
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel_linux)
        widget.bind("<Button-5>", _on_mousewheel_linux)

        # Bind to all children
        for child in widget.winfo_children():
            self.bind_mousewheel_to_widget_and_children(child)

    def toggle_video_selection(self, index, selected):
        """Toggle a video's selection state"""
        if selected and index not in self.selected_videos:
            self.selected_videos.append(index)
        elif not selected and index in self.selected_videos:
            self.selected_videos.remove(index)

    def select_all_videos(self):
        """Select all videos in the playlist"""
        if not self.playlist_info:
            return

        entries = self.playlist_info.get("entries", [])
        self.selected_videos = list(range(len(entries)))

        # Update checkboxes
        for video in entries:
            if "_checkbox_var" in video:
                video["_checkbox_var"].set(True)

    def deselect_all_videos(self):
        """Deselect all videos in the playlist"""
        self.selected_videos = []

        # Update checkboxes
        if self.playlist_info:
            for video in self.playlist_info.get("entries", []):
                if "_checkbox_var" in video:
                    video["_checkbox_var"].set(False)

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)

    def start_download(self):
        """Start downloading the playlist"""
        playlist_url = self.url_entry.get().strip()
        output_dir = self.output_dir.get()
        format_option = next(
            (f[1] for f in FORMAT_OPTIONS if f[0] == self.format_var.get()),
            FORMAT_OPTIONS[0][1],
        )
        save_thumbnail = self.save_thumbnail_var.get()

        if not playlist_url:
            messagebox.showerror("Error", "Please enter a YouTube playlist URL")
            return

        if not self.playlist_info:
            # Try to preview first
            self.preview_playlist()
            return

        if not self.selected_videos:
            messagebox.showerror(
                "Error", "Please select at least one video to download"
            )
            return

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Update UI
        self.status_var.set(STATUS_DOWNLOADING)
        self.progress_var.set(0)
        self.progress_info.config(text="Starting download...")

        # Enable/disable buttons
        self.download_button.config(state=tk.DISABLED)
        self.preview_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL, text=BUTTON_PAUSE)
        self.stop_button.config(state=tk.NORMAL)

        # Reset pause state
        self.is_paused = False

        # Start download in a separate thread
        download_thread = Thread(
            target=self.download_manager.download_playlist,
            args=(
                playlist_url,
                output_dir,
                format_option,
                self.selected_videos,
                save_thumbnail,
            ),
        )
        download_thread.daemon = True
        download_thread.start()

    def update_status(self, status_info):
        """Update status information from download manager"""
        if isinstance(status_info, str):
            self.status_var.set(status_info)
            return

        if isinstance(status_info, dict):
            status = status_info.get("status", "")
            self.active_download_id = status_info.get(
                "download_id", self.active_download_id
            )

            if status == "downloading":
                # Update progress bar
                progress = status_info.get("progress", 0)
                self.progress_var.set(progress * 100)

                # Update status text
                filename = status_info.get("filename", "")
                percent = status_info.get("percent", "")
                speed = status_info.get("speed", "")
                eta = status_info.get("eta", "")

                status_text = f"Downloading {filename}"
                self.status_var.set(status_text)

                # Update progress info
                playlist_index = status_info.get("playlist_index", 0)
                playlist_count = status_info.get("playlist_count", 0)

                progress_text = f"Video {playlist_index}/{playlist_count} | {percent} | {speed} | ETA: {eta}"
                self.progress_info.config(text=progress_text)

            elif status == "processing":
                filename = status_info.get("filename", "")
                playlist_index = status_info.get("playlist_index", 0)
                playlist_count = status_info.get("playlist_count", 0)

                self.status_var.set(f"Processing {filename}")
                self.progress_info.config(
                    text=f"Video {playlist_index}/{playlist_count} | Converting video..."
                )

            elif status == STATUS_PAUSED:
                self.status_var.set(STATUS_PAUSED)

            elif status == STATUS_STOPPED:
                self.status_var.set(STATUS_STOPPED)
                self.download_completed()

            elif status == STATUS_COMPLETE:
                self.status_var.set(STATUS_COMPLETE)
                self.progress_var.set(100)
                self.progress_info.config(text="All videos downloaded successfully")
                self.download_completed()

            elif status.startswith(STATUS_ERROR.format("")):
                self.status_var.set(status)
                self.download_completed()

    def download_completed(self):
        """Handle completed download (success, error, or stopped)"""
        # Update UI
        self.download_button.config(state=tk.NORMAL)
        self.preview_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

        # Reset active download
        self.active_download_id = None
        self.is_paused = False

        # Reload history
        self.load_history()

    def toggle_pause(self):
        """Toggle pause/resume of current download"""
        if not self.active_download_id:
            return

        if self.is_paused:
            # Resume
            self.download_manager.resume_download(self.active_download_id)
            self.pause_button.config(text=BUTTON_PAUSE)
            self.is_paused = False
        else:
            # Pause
            self.download_manager.pause_download(self.active_download_id)
            self.pause_button.config(text=BUTTON_RESUME)
            self.is_paused = True

    def stop_download(self):
        """Stop current download"""
        if not self.active_download_id:
            return

        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Stop", "Are you sure you want to stop the download?"
        )
        if result:
            self.download_manager.stop_download(self.active_download_id)
            self.status_var.set(STATUS_STOPPED)


def main():
    root = tk.Tk()

    try:
        # Determine base path (handles both script & bundled exe)
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS  # Running as bundled app (exe)
        else:
            base_path = os.path.abspath(".")  # Running as script

        icon_ico_path = os.path.join(base_path, "docs/images/icon.ico")
        icon_png_path = os.path.join(base_path, "docs/images/icon.png")

        # Set Windows taskbar & window icon (.ico)
        if os.name == "nt" and os.path.exists(icon_ico_path):
            root.iconbitmap(icon_ico_path)

        # Set cross-platform window icon (.png)
        if os.path.exists(icon_png_path):
            icon_img = Image.open(icon_png_path)
            icon_photo = ImageTk.PhotoImage(icon_img)
            root.iconphoto(True, icon_photo)

    except Exception as e:
        print(f"Could not set application icon: {e}")

    app = PlaylistDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
