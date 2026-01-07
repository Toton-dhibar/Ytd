from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import glob
import shutil
import re
import time
import json
import mimetypes

app = Flask(__name__)

# Store download progress and file information
download_progress = {}

# Configure cookies folder
COOKIES_FOLDER = 'cookies'
app.config['COOKIES_FOLDER'] = COOKIES_FOLDER

# Create cookies directory
os.makedirs(COOKIES_FOLDER, exist_ok=True)

# Create downloads directory
DOWNLOADS_DIR = 'downloads'
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def get_platform_from_url(url):
    """Detect which platform the URL is from"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'facebook.com' in url:
        return 'facebook'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'terabox.com' in url or 'teraboxapp.com' in url or 'nephobox.com' in url:
        return 'terabox'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'vimeo.com' in url:
        return 'vimeo'
    elif 'dailymotion.com' in url:
        return 'dailymotion'
    else:
        return 'all'

def get_cookie_file_for_url(url):
    """Get the appropriate cookie file for the given URL"""
    platform = get_platform_from_url(url)
    
    # Check if platform-specific cookie file exists
    platform_cookie = os.path.join(COOKIES_FOLDER, f"{platform}.txt")
    if os.path.exists(platform_cookie):
        return f"{platform}.txt"
    
    # Fall back to all.txt if it exists
    all_cookie = os.path.join(COOKIES_FOLDER, "all.txt")
    if os.path.exists(all_cookie):
        return "all.txt"
    
    # No cookie file available
    return None

class ProgressHook:
    def __init__(self, download_id):
        self.download_id = download_id
    
    def hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', 'N/A')
            download_progress[self.download_id] = {
                'status': 'downloading',
                'percent': percent,
                'speed': speed
            }
        elif d['status'] == 'finished':
            download_progress[self.download_id] = {
                'status': 'processing',
                'message': 'Download completed, processing file...'
            }

def sanitize_filename(filename, max_length=100):
    """Sanitize filename and limit its length more aggressively"""
    if not filename:
        return "video"
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove emojis and special characters (keep basic alphanumeric, spaces, hyphens, underscores)
    filename = re.sub(r'[^\w\s\-_\.]', '', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Trim leading/trailing spaces
    filename = filename.strip()
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # If filename is still too long, truncate it
    if len(filename) > max_length:
        # Keep extension if present
        name, ext = os.path.splitext(filename)
        # Truncate the name part
        truncated_name = name[:max_length - len(ext)]
        filename = truncated_name + ext
    
    return filename

def get_safe_filename(title, format_type, format_ext, max_length=150):
    """Generate a safe filename with proper extension"""
    if not title:
        title = "video"
    
    # Basic sanitization
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_title = re.sub(r'[^\w\s\-_\.]', '', safe_title)
    safe_title = safe_title.replace(' ', '_')[:100]
    
    # Set proper extension based on format type and requested format
    if format_type == 'audio':
        if format_ext in ['mp3', 'flac', 'm4a', 'wav', 'ogg', 'aac', 'wma', 'opus']:
            extension = format_ext
        else:
            extension = 'm4a'  # Default audio format
    else:
        if format_ext in ['mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', '3gp']:
            extension = format_ext
        else:
            extension = 'mp4'  # Default video format
    
    filename = f"{safe_title}.{extension}"
    
    # Final length check
    if len(filename) > max_length:
        name_part = safe_title[:max_length - len(extension) - 1]
        filename = f"{name_part}.{extension}"
    
    return filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_formats', methods=['POST'])
def get_formats():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get appropriate cookie file for this URL
        cookies_file = get_cookie_file_for_url(url)
        platform = get_platform_from_url(url)
        if platform == 'terabox' and not cookies_file:
            return jsonify({'error': 'TeraBox downloads require a valid cookies file (cookies/terabox.txt)'}), 400
        
        # Configure yt-dlp options for format extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
        }
        
        # Add cookies if available
        if cookies_file:
            cookies_path = os.path.join(app.config['COOKIES_FOLDER'], cookies_file)
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
        
        if platform == 'terabox':
            ydl_opts['http_headers']['Referer'] = url
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract info without downloading
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return jsonify({'error': 'Could not extract video information'}), 400
                
                # Organize formats
                video_formats = []
                audio_formats = []
                
                if 'formats' in info:
                    for fmt in info['formats']:
                        # Skip formats without proper IDs
                        if not fmt.get('format_id'):
                            continue
                        
                        format_info = {
                            'format_id': fmt['format_id'],
                            'ext': fmt.get('ext', ''),
                            'filesize_approx': fmt.get('filesize_approx') or fmt.get('filesize'),
                            'format_note': fmt.get('format_note', ''),
                            'quality': fmt.get('quality', 0)
                        }
                        
                        # Check if it's a video format (has video codec and height)
                        if fmt.get('vcodec') != 'none' and fmt.get('height'):
                            format_info.update({
                                'height': fmt.get('height'),
                                'width': fmt.get('width'),
                                'fps': fmt.get('fps'),
                                'vcodec': fmt.get('vcodec'),
                                'acodec': fmt.get('acodec', 'none')
                            })
                            video_formats.append(format_info)
                        
                        # Check if it's an audio format (has audio codec but no video)
                        elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            format_info.update({
                                'acodec': fmt.get('acodec'),
                                'abr': fmt.get('abr'),  # Audio bitrate
                                'asr': fmt.get('asr')   # Audio sample rate
                            })
                            audio_formats.append(format_info)
                
                # Sort video formats by quality (height) descending
                video_formats.sort(key=lambda x: (x.get('height', 0), x.get('fps', 0)), reverse=True)
                
                # Sort audio formats by bitrate descending
                audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                
                # If no separate audio formats found, create some basic options
                if not audio_formats and video_formats:
                    audio_formats = [
                        {
                            'format_id': 'bestaudio',
                            'ext': 'best',
                            'format_note': 'Best Available Audio',
                            'abr': None,
                            'acodec': 'best'
                        }
                    ]
                
                return jsonify({
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'video_formats': video_formats[:30],  # Limit to top 30 formats
                    'audio_formats': audio_formats[:15],  # Limit to top 15 formats
                    'thumbnail': info.get('thumbnail'),
                    'view_count': info.get('view_count'),
                    'description': info.get('description', '')[:500] if info.get('description') else ''
                })
                
            except yt_dlp.utils.ExtractorError as e:
                error_msg = str(e)
                if "Private video" in error_msg:
                    error_msg = "This video is private. Try using a cookies file to access it."
                elif "Video unavailable" in error_msg:
                    error_msg = "This video is unavailable or has been removed."
                elif "Sign in to confirm your age" in error_msg:
                    error_msg = "Age-restricted content. Please use a cookies file from a logged-in session."
                return jsonify({'error': f'Extraction failed: {error_msg}'}), 400
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        url = data.get('url')
        format_type = data.get('format_type')  # 'video' or 'audio'
        format_id = data.get('format_id')  # The specific format ID selected by user
        output_format = data.get('output_format', 'mp4')  # Final output format
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not format_id:
            return jsonify({'error': 'Format ID is required'}), 400
        
        # Get appropriate cookie file for this URL
        cookies_file = get_cookie_file_for_url(url)
        platform = get_platform_from_url(url)
        if platform == 'terabox' and not cookies_file:
            return jsonify({'error': 'TeraBox downloads need an uploaded cookies file (cookies/terabox.txt)'}), 400
        print(f"Using cookie file: {cookies_file} for URL: {url}")
        
        download_id = str(uuid.uuid4())
        
        # Start download in background
        thread = threading.Thread(
            target=perform_download,
            args=(download_id, url, format_type, format_id, output_format, cookies_file)
        )
        thread.start()
        
        return jsonify({
            'download_id': download_id,
            'message': 'Download started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def perform_download(download_id, url, format_type, format_id, output_format, cookies_file):
    # Use a shorter temp directory
    temp_dir = tempfile.mkdtemp(dir='/tmp')
    try:
        platform = get_platform_from_url(url)
        # Use simple filename pattern for download to avoid long paths
        simple_pattern = os.path.join(temp_dir, f'dl_{download_id[:8]}.%(ext)s')
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': simple_pattern,
            'progress_hooks': [ProgressHook(download_id).hook],
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'merge_output_format': output_format,
            'prefer_ffmpeg': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'extractor_retries': 3,
            'retries': 3,
        }
        
        # Add cookies if available
        if cookies_file:
            cookies_path = os.path.join(app.config['COOKIES_FOLDER'], cookies_file)
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
                print(f"Using cookies from: {cookies_path}")
        
        if platform == 'terabox':
            ydl_opts['http_headers']['Referer'] = url
        
        # Set the format based on user selection
        if format_type == 'audio':
            if format_id == 'bestaudio':
                ydl_opts['format'] = 'bestaudio/best'
            else:
                ydl_opts['format'] = format_id
            
            # Set up audio post-processing
            postprocessors = []
            if output_format in ['mp3', 'flac', 'm4a', 'wav', 'ogg', 'aac', 'wma', 'opus']:
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': output_format,
                    'preferredquality': '192',
                })
            
            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors
                
        else:  # video
            # For video downloads, ensure we get both video and audio
            if format_id in ['best', 'worst']:
                ydl_opts['format'] = format_id
            else:
                if output_format == 'mp4':
                    preferred_video = f"{format_id}[ext=mp4][vcodec^=avc1]/bestvideo[ext=mp4][vcodec^=avc1]"
                    preferred_audio = "bestaudio[ext=m4a]/bestaudio"
                    ydl_opts['format'] = f"{preferred_video}+{preferred_audio}/best[ext=mp4]/best"
                else:
                    ydl_opts['format'] = f'{format_id}+bestaudio/best[ext={output_format}]/{format_id}/best'
            
            # Set up video post-processing for format conversion
            postprocessors = []
            
            if output_format in ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', '3gp']:
                postprocessors.append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': output_format,
                })
            
            # Always add metadata and ensure proper encoding for compatibility
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            })
            
            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors
            
            ffmpeg_args = ['-movflags', '+faststart']
            if output_format == 'mp4':
                ffmpeg_args.extend(['-c:v', 'libx264', '-profile:v', 'high', '-level', '4.0', '-c:a', 'aac', '-b:a', '192k', '-ac', '2'])
            ydl_opts['postprocessor_args'] = {'FFmpegVideoConvertor': ffmpeg_args}
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # First, try to extract info to validate the URL
                info = ydl.extract_info(url, download=False)
                if not info:
                    download_progress[download_id] = {
                        'status': 'error',
                        'error': 'Could not extract video information'
                    }
                    return
                
                # Get the title for filename
                title = info.get('title', 'video')
                safe_filename = get_safe_filename(title, format_type, output_format)
                
                # Now perform the actual download
                result = ydl.extract_info(url, download=True)
                
                if result:
                    # Wait a moment for any post-processing to complete
                    time.sleep(2)
                    
                    # Find the downloaded file
                    files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
                    if files:
                        # Sort by modification time to get the latest file
                        files.sort(key=lambda x: os.path.getmtime(os.path.join(temp_dir, x)), reverse=True)
                        downloaded_file = files[0]
                        original_file_path = os.path.join(temp_dir, downloaded_file)
                        final_file_path = os.path.join(temp_dir, safe_filename)
                        
                        # Rename to the proper filename
                        if os.path.exists(original_file_path):
                            try:
                                if original_file_path != final_file_path:
                                    os.rename(original_file_path, final_file_path)
                            except OSError:
                                # If rename fails, just use the original file
                                final_file_path = original_file_path
                                safe_filename = downloaded_file
                            
                            # Verify the file exists and is accessible
                            if os.path.exists(final_file_path) and os.path.getsize(final_file_path) > 0:
                                target_path = os.path.join(DOWNLOADS_DIR, safe_filename)
                                if os.path.exists(target_path):
                                    name, ext = os.path.splitext(safe_filename)
                                    target_path = os.path.join(DOWNLOADS_DIR, f"{name}_{download_id[:6]}{ext}")
                                    safe_filename = os.path.basename(target_path)
                                moved = False
                                try:
                                    shutil.move(final_file_path, target_path)
                                    final_file_path = target_path
                                    moved = True
                                except Exception:
                                    final_file_path = final_file_path

                                if moved and temp_dir and os.path.exists(temp_dir):
                                    shutil.rmtree(temp_dir, ignore_errors=True)
                                    temp_dir = None

                                download_progress[download_id] = {
                                    'status': 'finished',
                                    'filename': safe_filename,
                                    'file_path': final_file_path,
                                    'temp_dir': temp_dir,
                                    'format_id': format_id,
                                    'completed_at': time.time()
                                }
                            else:
                                download_progress[download_id] = {
                                    'status': 'error',
                                    'error': 'File was created but is empty or inaccessible'
                                }
                        else:
                            download_progress[download_id] = {
                                'status': 'error',
                                'error': 'Download completed but file not found'
                            }
                    else:
                        download_progress[download_id] = {
                            'status': 'error',
                            'error': 'Download completed but no files found'
                        }
                
            except yt_dlp.utils.ExtractorError as e:
                error_msg = str(e)
                if "Private video" in error_msg:
                    error_msg = "This video is private. Try using a cookies file to access it."
                elif "Video unavailable" in error_msg:
                    error_msg = "This video is unavailable or has been removed."
                elif "Sign in to confirm your age" in error_msg:
                    error_msg = "Age-restricted content. Please use a cookies file from a logged-in session."
                elif "format is not available" in error_msg.lower():
                    error_msg = f"Requested format is not available for this video."
                download_progress[download_id] = {
                    'status': 'error',
                    'error': f'Extraction failed: {error_msg}'
                }
                shutil.rmtree(temp_dir, ignore_errors=True)
                
            except Exception as e:
                error_msg = str(e)
                download_progress[download_id] = {
                    'status': 'error',
                    'error': f'Download error: {error_msg}'
                }
                shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        download_progress[download_id] = {
            'status': 'error',
            'error': str(e)
        }
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/progress/<download_id>')
def get_progress(download_id):
    progress = download_progress.get(download_id, {'status': 'not_found'})
    return jsonify(progress)

@app.route('/download_file/<download_id>')
def download_file(download_id):
    try:
        progress = download_progress.get(download_id)
        
        if not progress or progress['status'] != 'finished':
            return jsonify({'error': 'File not ready for download'}), 404
        
        file_path = progress.get('file_path')
        temp_dir = progress.get('temp_dir')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Verify file is not empty
        if os.path.getsize(file_path) == 0:
            return jsonify({'error': 'File is empty'}), 404
        
        # Get filename for download
        filename = progress.get('filename', 'download')
        
        # Create response
        response = send_file(
            file_path, 
            as_attachment=True,
            download_name=filename
        )
        
        # Clean up the temporary directory after sending the file
        @response.call_on_close
        def cleanup():
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                if download_id in download_progress:
                    download_progress[download_id]['temp_dir'] = None
            except:
                pass
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/play_file/<download_id>')
def play_file(download_id):
    try:
        progress = download_progress.get(download_id)
        
        if not progress or progress.get('status') != 'finished':
            return jsonify({'error': 'File not ready for playback'}), 404
        
        file_path = progress.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        return send_file(
            file_path,
            as_attachment=False,
            download_name=progress.get('filename', os.path.basename(file_path)),
            mimetype=mime_type,
            conditional=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cleanup function to remove old temporary files
def cleanup_old_files():
    """Clean up old files from progress tracking"""
    while True:
        time.sleep(3600)  # Run every hour
        try:
            current_time = time.time()
            to_remove = []
            
            for download_id, progress in download_progress.items():
                # Remove entries older than 24 hours
                if progress.get('status') == 'finished':
                    file_path = progress.get('file_path')
                    if file_path and os.path.exists(file_path):
                        file_age = current_time - os.path.getctime(file_path)
                        if file_age > 86400:  # 24 hours
                            to_remove.append(download_id)
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                            temp_dir = progress.get('temp_dir')
                            if temp_dir and os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir, ignore_errors=True)
            
            for download_id in to_remove:
                if download_id in download_progress:
                    del download_progress[download_id]
                    
        except Exception as e:
            print(f"Cleanup error: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    # Print available cookie files
    print("Available cookie files:")
    for file_path in glob.glob(os.path.join(COOKIES_FOLDER, '*.txt')):
        filename = os.path.basename(file_path)
        print(f"  - {filename}")
    
    app.run(debug=True, host='0.0.0.0', port=5003)
