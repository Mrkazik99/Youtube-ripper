import logging
import yaml
import io
import aiohttp as aiohttp
import urllib
import re
import requests
import json
import youtube_dl
from moviepy.editor import *
from mutagen.easyid3 import EasyID3
from mutagen.flac import Picture
from mutagen.id3 import ID3, APIC
from mutagen import id3
import ffmpeg
from mutagen.mp3 import MP3
from pytube import YouTube
from pytube import Playlist
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument

with open('login.yml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['youtube_apikey']

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

client = TelegramClient(**config['telethon_settings']).start(bot_token=config['bot_token'])

session = aiohttp.ClientSession()

f.close()


async def youtube_search(type, search_query, amount):
    search_query = search_query.strip()
    if not search_query:
        return
    async with session.get('https://www.googleapis.com/youtube/v3/search', params={'part': 'snippet',
                                                                                   'q': search_query,
                                                                                   'maxResult': amount,
                                                                                   'type': type,
                                                                                   'key': api_key}) as response:
        resp = await response.json()
        return resp['items']


@client.on(events.InlineQuery)
async def inline_query(event):
    builder = event.builder
    if not event.text or len(event.text) < 3:
        ans = builder.article('Wrong command', text='Usage: @YTmusicRipperBot <.p/.v> <video or playlist query>')
        await event.answer([ans])
        return
    else:
        if event.text.startswith('.p'):
            results = await youtube_search(type='playlist', search_query=event.text[2:], amount=10)
            await event.answer([event.builder.article(title=item['snippet']['title'],
                                                      description=f"Published by: {item['snippet']['channelTitle']}",
                                                      thumb=InputWebDocument(
                                                          url=item['snippet']['thumbnails']['default']['url'],
                                                          size=0,
                                                          mime_type='image/jpg',
                                                          attributes=[]),
                                                      text=f"https://www.youtube.com/playlist?list={item['id']['playlistId']}")
                                for item in results])
        elif event.text.startswith('.v'):
            results = await youtube_search(type='video', search_query=event.text[2:], amount=10)
            await event.answer([event.builder.article(title=item['snippet']['title'],
                                                      description=f"Published by: {item['snippet']['channelTitle']}",
                                                      thumb=InputWebDocument(
                                                          url=item['snippet']['thumbnails']['default']['url'],
                                                          size=0, mime_type='image/jpeg', attributes=[]),
                                                      text=f"https://www.youtube.com/watch?v={item['id']['videoId']}")
                                for item in results])
        else:
            results = await youtube_search(type='video', search_query=event.text, amount=10)
            await event.answer([event.builder.article(title=item['snippet']['title'],
                                                      description=f"Published by: {item['snippet']['channelTitle']}",
                                                      thumb=InputWebDocument(
                                                          url=item['snippet']['thumbnails']['default']['url'],
                                                          size=0, mime_type='image/jpeg', attributes=[]),
                                                      text=f"https://www.youtube.com/watch?v={item['id']['videoId']}")
                                for item in results])

    # ans = []
    # if not results:
    #     ans.append(await builder.article('No videos found for this query.', text='Empty result'))
    # else:
    #     for entry in results:
    #         if entry['id']['kind'] == 'youtube#video':
    #             ans.append(
    #                 await builder.article(entry['snippet']['title'], description=entry['snippet']['channelTitle'],
    #                                       thumb=InputWebDocument(url=entry['snippet']['thumbnails']['high']['url'],
    #                                                              size=0,
    #                                                              mime_type="image/jpeg",
    #                                                              attributes=[], ),
    #                                       text='https://www.youtube.com/watch?v=' + entry['id']['videoId']))
    # await event.answer(ans)


@client.on(events.NewMessage)
async def answer(event):
    if event.text == '/start':
        await event.reply('Siema mały kurwiu ;)')
    if event.text.startswith('@'):
        await event.respond("It's me 😂")
    if 'https://www.youtube.com/' in event.text or 'https://youtu.be/' in event.text:
        if 'playlist?list=' not in event.text:
            messId = await event.reply("Downloading mp4")
            video = io.BytesIO()
            yt = YouTube(event.text)
            print('Downloading')
            stream = yt.streams.first()
            stream.stream_to_buffer(buffer=video)
            print('Converting')
            file = io.BytesIO(video.getvalue())
            file.name = f'{yt.title}.mp4'
            print('Uploading')
            await client.send_file(event.sender.id, file=file)
        else:
            playlist = Playlist(event.text)
            for vid in playlist.videos:
                messId = await event.reply("Downloading mp4")
                video = io.BytesIO()
                print('Downloading')
                vid.streams.first().stream_to_buffer(buffer=video)
                file = io.BytesIO(video.getvalue())
                file.name = f'{vid.title}.mp4'
                print('Uploading')
                await client.send_file(event.sender.id, file=file)

    # ydl_opts = {
    #     'format': 'best[ext=mp4]',
    #     'keepvideo': True
    # }
    # with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    #     info = ydl.extract_info("{}".format(event.text))
    #     title = ydl.prepare_filename(info)
    #     await client.edit_message(messId, 'Converting to mp3')
    #     mp4_file = r'' + title
    #     mp3_file = r'' + title + '.mp3'
    #     videoclip = VideoFileClip(mp4_file)
    #     audioclip = videoclip.audio
    #     audioclip.write_audiofile(mp3_file)
    #     request = youtube.search().list(
    #         part="snippet",
    #         maxResults=1,
    #         q=info['id']
    #     )
    #     response = request.execute()
    #     result = json.dumps(response)
    #     result = json.loads(result)
    #     result = json.dumps(result["items"])
    #     result = json.loads(result)
    #     for entry in result:
    #         snippet = json.dumps(entry['snippet'])
    #         snippet = json.loads(snippet)
    #         thumb = json.dumps(snippet['thumbnails'])
    #         thumb = json.loads(thumb)
    #         thumb = json.dumps(thumb['high'])
    #         thumb = json.loads(thumb)
    #     audio = EasyID3(title + '.mp3')
    #     audio['title'] = '!' + snippet['title']
    #     audio['artist'] = snippet['channelTitle']
    #     audio.save()
    #     audio = ID3(title + '.mp3')
    #     pic = Picture()
    #     pic.type = id3.PictureType.COVER_FRONT
    #     pic.width = 640
    #     pic.height = 640
    #     pic.mime = 'image/jpeg'
    #     r = requests.get(thumb['url'], stream=True)
    #     r.raw.decode_content = True
    #     pic.data = r.raw.read()
    #
    #     audio['APIC'] = APIC(
    #         encoding=3,
    #         mime='image/jpeg',
    #         type=3, desc=u'Cover',
    #         data=pic.data
    #     )
    #     audio.save()
    #     videoclip.close()
    #     os.remove(title)
    #     await client.edit_message(messId, 'Uploading...')
    #     await event.reply(file=mp3_file)
    #     await client.edit_message(messId, 'Here is your mp3 ⬇️')
    # os.remove(title + '.mp3')


with client:
    print('Good morning!')
    client.run_until_disconnected()
