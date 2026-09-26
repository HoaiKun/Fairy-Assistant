import asyncio
from typing import Any, Dict, Optional
from yt_dlp import YoutubeDL

YDL_OPTS = {
    # Ưu tiên m4a/aac hoặc opus tương thích mượt mà nhất với Web Audio API
    'format': 'bestaudio[acodec=opus]/bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch1:',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
}


def _extract_track_sync(query: str) -> Optional[Dict[str, Any]]:
    with YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
        if not info:
            return None

        track = info['entries'][0] if 'entries' in info and info['entries'] else info
        if not track:
            return None

        thumbnails = track.get('thumbnails') or []
        thumbnail_url = thumbnails[-1].get('url') if thumbnails else track.get('thumbnail')

        return {
            "id": track.get('id'),
            "title": track.get('title'),
            "stream_url": track.get('url'),  # Direct audio stream URL từ Google CDN
            "image_url": thumbnail_url,
            "duration_seconds": track.get('duration'),
            "author": track.get('uploader') or track.get('channel'),
            "webpage_url": track.get('webpage_url') or track.get('original_url'),
        }


async def manage_playback(
    action: str,
    query: str = "",
    value: Optional[float] = None,
    playlist_name: str = ""
) -> Dict[str, Any]:
    """
    Tool điều khiển âm nhạc & trình phát cho Fairy.
    action: 'play', 'add_queue', 'pause', 'resume', 'next', 'prev', 
            'set_volume', 'set_speed', 'toggle_favorite', 'save_playlist'
    """
    action = action.lower().strip()

    try:
        # Nhóm 1: Các action cần bóc tách link từ YouTube
        if action in ["play", "add_queue"]:
            if not query.strip():
                return {
                    "type": "function_playback",
                    "success": False,
                    "error": "Thiếu tên bài hát hoặc URL cần phát."
                }

            track_data = await asyncio.to_thread(_extract_track_sync, query)
            if not track_data or not track_data.get("stream_url"):
                return {
                    "type": "function_playback",
                    "success": False,
                    "error": f"Không tìm thấy tài nguyên âm thanh cho: '{query}'"
                }

            return {
                "type": "function_playback",
                "success": True,
                "action": action,
                "track": track_data
            }

        # Nhóm 2: Các action điều khiển trạng thái (chuyển thẳng payload xuống client)
        valid_actions = {
            "pause", "resume", "next", "prev", 
            "set_volume", "set_speed", "toggle_favorite", "save_playlist"
        }
        if action in valid_actions:
            return {
                "type": "function_playback",
                "success": True,
                "action": action,
                "value": value,
                "playlist_name": playlist_name
            }

        return {
            "type": "function_playback",
            "success": False,
            "error": f"Hành động '{action}' không được hỗ trợ."
        }

    except Exception as e:
        return {
            "type": "function_playback",
            "success": False,
            "error": str(e)
        }