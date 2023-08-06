import io
import logging

import aiohttp
import ffmpeg
import yaml
import base64
from mediafile import MediaFile, Image, ImageType
from pytube import YouTube, Playlist, exceptions
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument
import shazamio

with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['youtube_apikey']

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)

client = TelegramClient(**config['telethon_settings']).start(bot_token=config['bot_token'])

session = aiohttp.ClientSession()

shazam = shazamio.Shazam()

f.close()


def find_album_name(data:list) -> str:
    album = None
    for section in data:
        if 'metadata' in section.keys():
            for metadata in section['metadata']:
                if metadata['title'].lower() == 'album':
                    album = metadata['text']
    return album if album else 'No album'


async def download_and_prepare_picture(url: str) -> bytes:
    async with session.get(url) as resp:
        return await resp.content.read()


async def youtube_search(search_type, search_query, amount) -> list or None:
    search_query = search_query.strip()
    if not search_query:
        return
    async with session.get('https://www.googleapis.com/youtube/v3/search', params={'part': 'snippet',
                                                                                   'q': search_query,
                                                                                   'maxResult': amount,
                                                                                   'type': search_type,
                                                                                   'key': api_key}) as response:
        resp = await response.json()
        return resp['items']


async def generate_names(yt: YouTube):
    if yt.metadata.metadata and len(yt.metadata.metadata) == 1:
        return {'Artist': yt.metadata.metadata[0]['Artist'] if 'Artist' in yt.metadata.metadata[0] else yt.author,
                'Title': yt.metadata.metadata[0]['Song'] if 'Song' in yt.metadata.metadata[0] else yt.title,
                'Album': yt.metadata.metadata[0]['Album'] if 'Album' in yt.metadata.metadata[0] else '',
                'picture': await download_and_prepare_picture(yt.thumbnail_url)}
    else:
        return {'Artist': yt.author, 'Title': yt.title, 'Album': '', 'picture': await download_and_prepare_picture(yt.thumbnail_url)}


async def yt_download(event: events.newmessage.NewMessage.Event, yt: YouTube) -> None:
    video = io.BytesIO()
    type_ = None
    for stream in yt.streams:
        if stream.audio_codec == 'opus':
            type_ = stream.mime_type.replace('audio/', '')
            break
        else:
            type_ = 'mp4'
    mess_id = await event.reply(f'__Downloading {yt.title}__')
    yt.streams.get_audio_only(subtype=type_).stream_to_buffer(buffer=video)
    file = io.BytesIO(video.getvalue())
    process = (
        ffmpeg
            .input('pipe:')
            .output('pipe:', format='opus')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )
    out, err = process.communicate(input=file.read())
    out_file = io.BytesIO(out)
    track_data = await shazam.recognize_song(out)
    if len(track_data['matches']) > 1 or 'track' not in track_data.keys() or 'title' not in track_data['track'].keys() or 'subtitle' not in track_data['track'].keys():
        metas = await generate_names(yt)
    else:
        metas = {
            'Artist': track_data['track']['subtitle'],
            'Title': track_data['track']['title'],
            'Album': find_album_name(track_data['track']['sections']),
            'picture': await download_and_prepare_picture(track_data['track']['images']['coverart'])
        }
    track_file = MediaFile(out_file)
    cover = Image(data=metas['picture'], desc=u'album cover', type=ImageType.front)
    track_file.images = [cover]
    track_file.title = metas['Title']
    track_file.album = metas['Album']
    track_file.artist = metas['Artist']
    track_file.albumartist = metas['Artist']
    track_file.save()
    out_file = io.BytesIO(out_file.getvalue())
    out_file.name = f"{metas['Artist']} - {metas['Title']}.ogg"
    await client.edit_message(mess_id, f'__Uploading {yt.title}__')
    async with client.action(event.sender_id, 'file'):
        await event.reply(file=out_file)
        await client.delete_messages(event.sender_id, mess_id)


async def build_answer(switch: str, event: events.InlineQuery.Event):
    return [event.builder.article(title=result['snippet']['title'],
                                  description=f"Published by: {result['snippet']['channelTitle']}",
                                  thumb=InputWebDocument(
                                      url=result['snippet']['thumbnails']['default']['url'],
                                      size=0,
                                      mime_type='image/jpg',
                                      attributes=[]),
                                  text=f"https://www.youtube.com/playlist?list={result['id']['playlistId']}"
                                  if switch == '.p' else f"https://www.youtube.com/watch?v={result['id']['videoId']}")
            for result in
            await youtube_search(search_type='video' if switch == '.v' else 'playlist',
                                 search_query=event.text[2:] if not switch else event.text,
                                 amount=10)]


@client.on(events.InlineQuery())
async def inline_query(event):
    if not event.text or len(event.text) < 3:
        await event.answer(
            [event.builder.article('Wrong command', text='Usage: @YTmusicRipperBot <.p/.v> <video or playlist query>')])
        return
    else:
        if event.text.startswith('.p'):
            await event.answer(await build_answer('.p', event=event))
        elif event.text.startswith('.v'):
            await event.answer(await build_answer('.v', event=event))
        else:
            await event.answer(await build_answer('.v', event=event))


@client.on(events.NewMessage())
async def answer(event):
    if event.text == '/start':
        await event.reply('Usage: @YTmusicRipperBot <.p/.v> <video or playlist query>')
    elif event.text.startswith('@'):
        await event.respond("It's me 😂")
    elif 'https://www.youtube.com/' in event.text or 'https://youtu.be/' in event.text:
        if 'playlist?list=' not in event.text:
            try:
                yt = YouTube(event.text)
                await yt_download(event, yt)
            except exceptions.VideoUnavailable as e:
                logger.exception(msg=e)
                await event.reply('**Video is unavailable**')
        else:
            try:
                playlist = Playlist(event.text)
                for vid in playlist.videos:
                    await yt_download(event, vid)
            except Exception as e:
                await event.reply('**Playlist or video is unavailable**')
                print(e)


with client:
    print('Good morning!')
    client.run_until_disconnected()
