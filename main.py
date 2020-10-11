import logging
import yaml
import os
import googleapiclient.discovery
import re
import json
import youtube_dl
from moviepy.editor import *
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument

with open("login.yml", 'r') as f:
    config = yaml.safe_load(f)

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = config['youtube_apikey']

youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey=DEVELOPER_KEY)

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

client = TelegramClient(**config['telethon_settings']).start(bot_token=config['bot_token'])


async def youtube_search(search_query):
    request = youtube.search().list(
        part="snippet",
        maxResults=10,
        q=search_query
    )
    response = request.execute()
    result = json.dumps(response)
    result = json.loads(result)
    result = json.dumps(result["items"])
    result = json.loads(result)
    return result


def error():
    return "Error while searching videos"


@client.on(events.InlineQuery)
async def inline_query(event):
    builder = event.builder
    if not event.text or len(event.text) < 3:
        ans = builder.article('Wrong command', text='Usage: @YTmusicRipperBot <music/video> <YT url/YT video name>')
        await event.answer([ans])
        return
    else:
        results = await youtube_search(event.text)
        ans = []
        for entry in results:
            id = json.dumps(entry['id'])
            id = json.loads(id)
            snippet = json.dumps(entry['snippet'])
            snippet = json.loads(snippet)
            thumb = json.dumps(snippet['thumbnails'])
            thumb = json.loads(thumb)
            thumb = json.dumps(thumb['high'])
            thumb = json.loads(thumb)
            ans.append(builder.article(snippet['title'], description=snippet['channelTitle'],
                                       thumb=InputWebDocument(url=thumb['url'], size=0, mime_type="image/jpeg", attributes=[], ),
                                       text='https://www.youtube.com/watch?v=' + id['videoId']))
        await event.answer(ans)


@client.on(events.NewMessage)
async def answer(event):
    if event.text.startswith("@"):
        await event.respond('It\'s me 😂')
    if re.match('https:\/\/www.youtube.com\/watch\?v=(.{11})', event.text):
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'keepvideo': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("{}".format(event.text))
            title = ydl.prepare_filename(info)
            mp4_file = r''+title
            mp3_file = r''+title+'.mp3'
            videoclip = VideoFileClip(mp4_file)
            audioclip = videoclip.audio
            audioclip.write_audiofile(mp3_file)
            videoclip.close()
            os.remove(title)
        await event.reply(file=mp3_file)
        os.remove(title+'.mp3')


with client:
    print('Good morning!')
    client.run_until_disconnected()
