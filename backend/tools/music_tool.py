from yt_dlp import YoutubeDL
from typing import Optional, Dict, Any

YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch1:',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

def play_music(query: str) -> Optional[Dict[str, Any]]:
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=False)
            if not info or 'entries' not in info or not info['entries']:
                return None
            
            track = info['entries'][0]
            
            # Lấy ảnh thumbnail chất lượng cao nhất khả dụng
            thumbnail_url = track.get('thumbnail')
            thumbnails = track.get('thumbnails', [])
            if thumbnails:
                thumbnail_url = thumbnails[-1].get('url', thumbnail_url)

            return {
                "success": True,
                "title": track.get('title'),
                "stream_url": track.get('url'),          # Direct audio stream link
                "image_url": thumbnail_url,              # URL ảnh bìa / thumbnail
                "duration_seconds": track.get('duration'),
                "author": track.get('uploader')
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }