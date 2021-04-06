import io
import logging
import aiohttp
import ffmpeg
import yaml
from mutagen import oggvorbis
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
        return {'Artist': yt.metadata.metadata[0]['Artist'], 'Title': yt.metadata.metadata[0]['Song']}
        # return {'Artist': yt.metadata.metadata[0]['Artist'], 'Title': yt.metadata.metadata[0]['Song'],
                # 'Album': yt.metadata.metadata[0]['Album']}
    #TODO:Check if metadata contains Album
    else:
        return {'Artist': yt.author, 'Title': yt.title}
        # return {'Artist': yt.author, 'Title': yt.title, 'Album': ''}


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
            .output('pipe:', format='ogg')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )
    out, err = process.communicate(input=file.read())
    out_file = io.BytesIO(out)
    mutagen_file = oggvorbis.OggVorbis(out_file)
    metas = await generate_names(yt)
    mutagen_file['Artist'] = metas['Artist']
    mutagen_file['Title'] = metas['Title']
    # mutagen_file['Album'] = metas['Album']
    #TODO:Add some cover
    mutagen_file.save(out_file)
    out_file = io.BytesIO(out_file.getvalue())
    #TODO:Try to simplify BytesIO casting
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
            await youtube_search(search_type='video' if switch == '.v' else 'playlist', search_query=event.text[2:],
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
