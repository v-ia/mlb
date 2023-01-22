from abc import ABC, abstractmethod
import view
import data
import asyncpg
import aiohttp
import aiofiles
from data import File
import soundfile
import cv2
import os


class UserHandler(ABC):
    @abstractmethod
    async def respond(self, request: object, update: data.Update, connection: asyncpg.connection.Connection):
        pass


class HandlerFactory(ABC):
    @abstractmethod
    def create_user_handler(self) -> UserHandler:
        pass


class UserHelp(UserHandler):
    async def respond(self, request: object, update: data.Update, connection: asyncpg.connection.Connection):
        pass


class HelpFactory(HandlerFactory):
    def create_user_handler(self) -> UserHelp:
        return UserHelp()


class UserStart(UserHandler):
    async def respond(self, request: object, update: data.Update, connection: asyncpg.connection.Connection):
        text = 'Добро пожаловать! :) Ожидаю Ваши голосовые сообщения'
        data_to_send = data.Text(text)
        response = view.SendMessage(request.app['config'], update.user.chat_id, data_to_send)
        await response.send()


class StartFactory(HandlerFactory):
    def create_user_handler(self) -> UserStart:
        return UserStart()


# Сохранение аудиосообщений, преобразование в формат wav
class UserVoice(UserHandler):
    async def respond(self, request: object, update: data.Update, connection: asyncpg.connection.Connection):
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{request.app['config'].get('Bot', 'bot_token')}/getFile?file_id=" \
                  f"{update.data.value_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    json_update = resp.read()
                    file = File(file_id=json_update['message']['file'][-1]['file_id'],
                                value_id=json_update['message'].get('file_path'))
            url = f"https://api.telegram.org/file/bot{request.app['config'].get('Bot', 'bot_token')}/{file.value_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f'/ogg/{update.user.chat_id}/{update.data.value_id}.ogg', mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    audiodata, samplerate = soundfile.read(f'/ogg/{update.user.chat_id}/{update.data.value_id}.ogg')
                    soundfile.write(f'/wav/{update.user.chat_id}/{update.data.value_id}.wav', audiodata, 16000)


class VoiceFactory(HandlerFactory):
    def create_user_handler(self) -> UserVoice:
        return UserVoice()


# Определяет есть ли лицо на отправляемых фотографиях или нет, сохраняет только те, где оно есть
class UserPhoto(UserHandler):
    async def respond(self, request: object, update: data.Update, connection: asyncpg.connection.Connection):
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{request.app['config'].get('Bot', 'bot_token')}/getFile?file_id=" \
                  f"{update.data.value_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    json_update = resp.read()
                    file = File(file_id=json_update['message']['file'][-1]['file_id'],
                                value_id=json_update['message'].get('file_path'))
            url = f"https://api.telegram.org/file/bot{request.app['config'].get('Bot', 'bot_token')}/{file.value_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    image = resp.read()
                    mime = image.mime()
                    if mime == 'image/jpeg':
                        extension = '.jpg'
                    elif mime == 'image/png':
                        extension = '.png'
                    elif mime == 'image/gif':
                        extension = '.gif'
                    else:
                        extension = ''
                        image_path = f'/images/{update.user.chat_id}/{update.data.value_id}{extension}'
                    f = await aiofiles.open(image_path, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    img = cv2.imread(image_path)
                    face_rec = cv2.CascadeClassifier('faces.xml')
                    face_res = face_rec.detectMultiScale(img, scaleFactor=2, minNeighbors=1)
                    if not face_res:
                        os.remove(image_path)


class PhotoFactory(HandlerFactory):
    def create_user_handler(self) -> UserPhoto:
        return UserPhoto()
