import logging
import yaml
import googleapiclient.discovery
import re
import requests
import json
import youtube_dl
from moviepy.editor import *
from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture
from mutagen.id3 import ID3, APIC
from mutagen import id3
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
    if search_query == '' or search_query == ' ':
        return
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
            ids = json.dumps(entry['id'])
            ids = json.loads(ids)
            if ids['kind'] != 'youtube#channel':
                snippet = json.dumps(entry['snippet'])
                snippet = json.loads(snippet)
                thumb = json.dumps(snippet['thumbnails'])
                thumb = json.loads(thumb)
                thumb = json.dumps(thumb['high'])
                thumb = json.loads(thumb)
                ans.append(await builder.article(snippet['title'], description=snippet['channelTitle'],
                                                 thumb=InputWebDocument(url=thumb['url'], size=0, mime_type="image/jpeg",
                                                                        attributes=[], ),
                                                 text='https://www.youtube.com/watch?v=' + ids['videoId']))
        await event.answer(ans)


@client.on(events.NewMessage)
async def answer(event):
    if event.text == '/start':
        await event.reply('Siema mały kurwiu ;)')
    if event.text.startswith('@'):
        await event.respond('It\'s me 😂')
    if re.match('https://www.youtube.com/watch\?v=(.{11})', event.text):
        messId = await event.reply("Downloading mp4")
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'keepvideo': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("{}".format(event.text))
            title = ydl.prepare_filename(info)
            await client.edit_message(messId, 'Converting to mp3')
            mp4_file = r'' + title
            mp3_file = r'' + title + '.mp3'
            videoclip = VideoFileClip(mp4_file)
            audioclip = videoclip.audio
            audioclip.write_audiofile(mp3_file)
            request = youtube.search().list(
                part="snippet",
                maxResults=1,
                q=info['id']
            )
            response = request.execute()
            result = json.dumps(response)
            result = json.loads(result)
            result = json.dumps(result["items"])
            result = json.loads(result)
            for entry in result:
                snippet = json.dumps(entry['snippet'])
                snippet = json.loads(snippet)
                thumb = json.dumps(snippet['thumbnails'])
                thumb = json.loads(thumb)
                thumb = json.dumps(thumb['high'])
                thumb = json.loads(thumb)
            audio = EasyID3(title + '.mp3')
            audio['title'] = '!' + snippet['title']
            audio['artist'] = snippet['channelTitle']
            audio.save()
            audio = ID3(title + '.mp3')
            pic = Picture()
            pic.type = id3.PictureType.COVER_FRONT
            pic.width = 640
            pic.height = 640
            pic.mime = 'image/jpeg'
            r = requests.get(thumb['url'], stream=True)
            r.raw.decode_content = True
            pic.data = r.raw.read()

            audio['APIC'] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3, desc=u'Cover',
                data=pic.data
            )
            audio.save()
            videoclip.close()
            os.remove(title)
            await client.edit_message(messId, 'Uploading...')
            await event.reply(file=mp3_file)
            await client.edit_message(messId, 'Here is your mp3 ⬇️')
        os.remove(title + '.mp3')


with client:
    print('Good morning!')
    client.run_until_disconnected()
