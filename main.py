import logging

from aiogram import Bot, Dispatcher, executor, types
from httpx import AsyncClient
import validators
import yaml

with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config['TELEGRAM_BOT_TOKEN'])
dp = Dispatcher(bot)
client = AsyncClient()


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply('Привет! Это бот для проверки новостей, '
                        'сделанный для хакатона MoscowCityHack командой NorthShine.\n'
                        'Вставьте ссылку на новость или текст новости. Поиск может занять некоторое время')


@dp.message_handler()
async def search(message: types.Message):
    if validators.url(message.text):
        response = await client.post(
            config['SEARCH_BY_URL'],
            data={'url': message.text},
            timeout=10000,
        )
        data = response.json()
        is_trusted_url = data['is_trusted_url']
        is_real_author = data['is_real_author']
        is_real_article = data['is_real_article']
        article_url = data['article_url']
        author = data['author']
        title = data['title']
        await message.answer(f'Это доверенный сайт: {is_trusted_url}\n'
                             f'Это реальный автор: {is_real_author}\n'
                             f'Это реально существующая статья: {is_real_article}\n'
                             f'Ссылка на статью: {article_url}\n'
                             f'Автор: {author}\n'
                             f'Заголовок: {title}')
    else:
        await message.answer('Поиск по тексту пока не реализован')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
