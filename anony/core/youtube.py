import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch
from anony import logger
from anony.helpers import Track, utils

API_URL = "https://shrutibots.site"

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)"
        )

    def get_cookies(self):
        if not self.checked:
            if os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies missing, yt-dlp may fail")
            return None

        return random.choice(self.cookies)

    async def search(self, query: str, m_id: int, video=False):
        try:
            search = VideosSearch(query, limit=1)
            results = await search.next()
        except:
            return None

        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1]["url"].split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )

    async def playlist(self, limit, user, url, video):
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                tracks.append(
                    Track(
                        id=data.get("id"),
                        channel_name=data.get("channel", {}).get("name"),
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(data.get("duration")),
                        title=data.get("title")[:25],
                        thumbnail=data.get("thumbnails")[-1]["url"].split("?")[0],
                        url=data.get("link").split("&list=")[0],
                        user=user,
                        view_count="",
                        video=video,
                    )
                )
        except:
            pass

        return tracks

    async def api_download(self, video_id, video=False):
        try:
            async with aiohttp.ClientSession() as session:

                params = {"url": video_id, "type": "video" if video else "audio"}

                async with session.get(
                    f"{API_URL}/download",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:

                    if resp.status != 200:
                        return None

                    data = await resp.json()
                    token = data.get("download_token")

                    if not token:
                        return None

                    stream_url = f"{API_URL}/stream/{video_id}?type={'video' if video else 'audio'}"

                    filename = f"downloads/{video_id}.{'mp4' if video else 'webm'}"

                    async with session.get(
                        stream_url,
                        headers={"X-Download-Token": token},
                        timeout=aiohttp.ClientTimeout(total=300),
                    ) as file:

                        if file.status != 200:
                            return None

                        os.makedirs("downloads", exist_ok=True)

                        with open(filename, "wb") as f:
                            async for chunk in file.content.iter_chunked(16384):
                                f.write(chunk)

                    return filename

        except:
            return None

    async def ytdlp_download(self, video_id, video=False):

        url = self.base + video_id
        filename = f"downloads/{video_id}.{'mp4' if video else 'webm'}"

        cookie = self.get_cookies()

        opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "nocheckcertificate": True,
            "cookiefile": cookie,
        }

        if video:
            opts["format"] = "bestvideo+bestaudio"
        else:
            opts["format"] = "bestaudio"

        def run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    ydl.download([url])
                except:
                    return None
            return filename

        return await asyncio.to_thread(run)

    async def download(self, video_id, video=False):

        file = await self.api_download(video_id, video)

        if file:
            return file

        logger.warning("API failed, switching to yt-dlp")

        return await self.ytdlp_download(video_id, video)
