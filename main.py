import logging
import yaml
import aiohttp
import re
import youtube_dl
from moviepy.editor import *
from telethon import TelegramClient, events

with open("login.yml", 'r') as f:
    config = yaml.safe_load(f)

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

client = TelegramClient(**config['telethon_settings']).start(bot_token=config['bot_token'])


async def youtube_search(search_query):
    async with aiohttp.ClientSession() as session:
        print('Getting videos')
        async with await session.get('https://www.youtube.com/results?search_query=' + search_query) as resp:
            # search_results = [[], []]
            print(resp.status)
            # print(await resp.text())
            urls = re.findall('\/watch\?v=(.{11})', await resp.text())
            search_results = list(dict.fromkeys(urls))
            return search_results


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
        urls = await youtube_search(event.text)
        ans = []
        for entry in urls:
            ans.append(builder.article(entry, text='https://www.youtube.com/watch?v=' + entry))
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
            print('Downloading music')
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
