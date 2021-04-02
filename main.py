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
from pytube import YouTube, Playlist, exceptions
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument

with open('login.yml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['youtube_apikey']

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

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


async def yt_download(event: events.newmessage.NewMessage.Event, yt: YouTube) -> None:
    video = io.BytesIO()
    type_ = None
    for stream in yt.streams:
        if stream.audio_codec == 'opus':
            type_ = stream.mime_type.replace('audio/', '')
            break
        else:
            pass
    mess_id = await event.reply(f'__Downloading {yt.title}__')
    yt.streams.get_audio_only(subtype=type_).stream_to_buffer(buffer=video)
    file = io.BytesIO(video.getvalue())
    file.name = f'{yt.title}.{type_}'
    await client.edit_message(mess_id, f'__Uploading {yt.title}__')
    await event.reply(file=file)
    await client.delete_messages(event.sender_id, mess_id)


@client.on(events.InlineQuery())
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


@client.on(events.NewMessage())
async def answer(event):
    if event.text == '/start':
        await event.reply('Siema mały kurwiu ;)')
    elif event.text.startswith('@'):
        await event.respond("It's me 😂")
    elif 'https://www.youtube.com/' in event.text or 'https://youtu.be/' in event.text:
        if 'playlist?list=' not in event.text:
            try:
                yt = YouTube(event.text)
                await yt_download(event, yt)
                # video = io.BytesIO()
                # print('Downloading')
                # stream = yt.streams.first()
                # type_ = None
                # for stream in yt.streams:
                #     if stream.audio_codec == 'opus':
                #         type_ = stream.mime_type.replace('audio/', '')
                #         break
                #     else:
                #         pass
                # messId = await event.reply(f'__Downloading {yt.title}__')
                # yt.streams.get_audio_only(subtype=type_).stream_to_buffer(buffer=video)
                # file = io.BytesIO(video.getvalue())
                # file.name = f'{yt.title}.{type_}'
                # await client.edit_message(messId, f'__Uploading {yt.title}__')
                # await event.reply(file=file)
                # await client.delete_messages(event.sender_id, messId)
            except exceptions.VideoUnavailable as e:
                await event.reply('**Video is unavailable**')
        else:
            try:
                playlist = Playlist(event.text)
                for vid in playlist.videos:
                    await yt_download(event, vid)
            except Exception as e:
                print(e)
                # messId = await event.reply("Downloading mp4")
                # video = io.BytesIO()
                # print('Downloading')
                # vid.streams.get_audio_only().stream_to_buffer(buffer=video)
                # file = io.BytesIO(video.getvalue())
                # file.name = f'{vid.title}.mp4'
                # print('Uploading')
                # await client.send_file(event.sender.id, file=file)


with client:
    print('Good morning!')
    client.run_until_disconnected()
