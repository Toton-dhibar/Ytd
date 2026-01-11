# Universal Video Downloader 🎥

A powerful Flask-based web application for downloading videos and audio from multiple platforms including YouTube, Facebook, Instagram, and many more.

## Features ✨

### Video Download Options
- **Formats**: MP4, MKV, MPEG
- **Resolutions**: 4K (2160p), 2K (1440p), 1080p, 720p, 480p, 360p
- **High-quality downloads with format conversion**

### Audio Download Options
- **Formats**: MP3, FLAC, M4A
- **High-quality audio extraction**

### Supported Platforms
- 🎥 YouTube
- 📘 Facebook
- 📷 Instagram
- 📦 TeraBox (with cookies)
- 🐦 Twitter
- 📺 Vimeo
- 🎵 SoundCloud
- 📱 TikTok
- 🎬 Dailymotion
- And many more (powered by yt-dlp)

### Advanced Features
- **Cookies Support**: Upload cookies.txt for private/age-restricted content
- **Inline Playback**: Play completed downloads directly in the browser
- **Progress Tracking**: Real-time download progress with speed monitoring
- **Download Management**: View and download previously saved files
- **Responsive Design**: Works perfectly on desktop and mobile devices

## Installation 🚀

### Prerequisites
- Python 3.7 or higher
- FFmpeg (for video/audio conversion)

### Ubuntu 22.04 Setup

1. **Update system and install dependencies:**
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv ffmpeg -y
```

2. **Clone the repository:**
```bash
git clone https://github.com/Toton-dhibar/YT.git
cd YT
```

3. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

4. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

5. **Create downloads directory:**
```bash
mkdir downloads
```

## Usage 🎯

### Starting the Server

1. **Activate virtual environment** (if not already activated):
```bash
source venv/bin/activate
```

2. **Run the Flask application:**
```bash
python app.py
```

3. **Access the application:**
   - Open your browser and go to `http://your-server-ip:5000`
   - For local testing: `http://localhost:5000`

### Using Cookies (Optional)

For downloading private or age-restricted content:

1. Export cookies from your browser using a browser extension (like "Get cookies.txt")
2. Save the cookies as `cookies.txt`
3. Upload the file through the web interface when downloading

### Production Deployment

For production on your 1GB VPS:

1. **Install and configure supervisor for process management:**
```bash
sudo apt install supervisor -y
```

2. **Create supervisor configuration:**
```bash
sudo nano /etc/supervisor/conf.d/yt-downloader.conf
```

Add the following content:
```ini
[program:yt-downloader]
command=/path/to/YT/venv/bin/python /path/to/YT/app.py
directory=/path/to/YT
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/yt-downloader.err.log
stdout_logfile=/var/log/yt-downloader.out.log
```

3. **Start the service:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start yt-downloader
```

## API Endpoints 🔌

### POST /download
Start a download job
```json
{
    "url": "https://www.youtube.com/watch?v=example",
    "format_type": "video",
    "quality": "1080p",
    "format": "mp4",
    "cookies_file": "optional_cookies.txt"
}
```

### GET /progress/{download_id}
Get download progress
```json
{
    "status": "downloading",
    "percent": "45%",
    "speed": "2.5MB/s"
}
```

### GET /downloads
List all downloaded files

### GET /download_file/{filename}
Download a specific file

## Project Structure 📁

```
YT/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore           # Git ignore rules
├── templates/
│   └── index.html       # Main web interface
├── static/
│   ├── css/
│   │   └── style.css    # Application styles
│   └── js/
│       └── script.js    # Frontend JavaScript
└── downloads/           # Downloaded files storage
```

## Resource Requirements 💾

- **RAM**: Minimum 512MB, Recommended 1GB
- **Storage**: Depends on downloads, recommend 10GB+ free space
- **CPU**: Single core sufficient for moderate usage
- **Network**: Good internet connection for downloads

## Troubleshooting 🔧

### Common Issues

1. **FFmpeg not found**: Install FFmpeg using `sudo apt install ffmpeg`
2. **Permission denied**: Check file permissions and ownership
3. **Port already in use**: Change the port in `app.py` or kill the process using the port
4. **Download fails**: Check if the video URL is valid and accessible

### Facebook/Instagram video tips

- These platforms often serve DASH/HLS streams where video and audio are separate; if you pick a video-only format you will only get video (and no sound). The app now prefers AVC/H.264 video + AAC audio and always merges them into an MP4 with `+faststart` so the `moov` atom stays at the beginning.
- When the only available video codec is AV1/VP9, the downloader re-encodes to H.264/AAC for broad device support (Android gallery, WhatsApp/Telegram share, VLC).
- If you need a manual fix or want to post-process an existing file, run:  
  ```bash
  ffmpeg -i input.mp4 -c:v libx264 -preset medium -profile:v high -level 4.0 -pix_fmt yuv420p -c:a aac -b:a 192k -ac 2 -movflags +faststart output.mp4
  ```
- Best practices: prefer MP4 containers, keep a cookies file for private reels, and let yt-dlp pick `bestvideo+bestaudio` with AVC/AAC when available. If a manifest lists only fragmented MP4, always remux/re-encode with the command above to ensure metadata and duration are correct.

### Performance Optimization

For better performance on limited resources:
- Monitor disk space regularly
- Clean old downloads periodically
- Consider setting download limits in yt-dlp options

## Security Notes 🔒

- The application runs on all interfaces (0.0.0.0) by default
- Consider using a reverse proxy (nginx/apache) in production
- Regularly update yt-dlp for latest site support
- Be cautious with cookies files containing sensitive data

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License 📄

This project is open source and available under the [MIT License](LICENSE).

## Support 💬

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Ensure yt-dlp supports your target website
