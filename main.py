import logging
import ffmpeg as ffmpeg
import yaml
import io
import aiohttp as aiohttp
from mutagen import oggopus
from pytube import YouTube, Playlist, exceptions
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument

with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['youtube_apikey']

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)
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
    process = (
        ffmpeg
            .input('pipe:')
            .output('pipe:', format='opus')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )
    out, err = process.communicate(input=file.read())
    out_file = io.BytesIO(out)
    mutagen_file = oggopus.OggOpus(fileobj=out_file)
    mutagen_file['artist'] = yt.author
    mutagen_file['title'] = f'!{yt.title}'
    mutagen_file.save(out_file)
    out_file = io.BytesIO(out_file.getvalue())
    out_file.name = f'{yt.title}.opus'
    await client.edit_message(mess_id, f'__Uploading {yt.title}__')
    await event.reply(file=out_file)
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


@client.on(events.NewMessage())
async def answer(event):
    if event.text == '/start':
        await event.reply('Siema ;)')
    elif event.text.startswith('@'):
        await event.respond("It's me 😂")
    elif 'https://www.youtube.com/' in event.text or 'https://youtu.be/' in event.text:
        if 'playlist?list=' not in event.text:
            try:
                yt = YouTube(event.text)
                await yt_download(event, yt)
            except exceptions.VideoUnavailable as e:
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
