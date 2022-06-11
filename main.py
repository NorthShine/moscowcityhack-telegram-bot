import logging

from aiogram import Bot, Dispatcher, executor, types, filters
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton
from httpx import AsyncClient
import validators
import yaml

with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config['TELEGRAM_BOT_TOKEN'])
dp = Dispatcher(bot)
client = AsyncClient()

author_keyboard = ReplyKeyboardMarkup()
author_keyboard.add(KeyboardButton('/author Я не знаю автора текста'))
title_keyboard = ReplyKeyboardMarkup()
title_keyboard.add(KeyboardButton('/title Я не знаю заголовок статьи'))


class TextRequest(StatesGroup):
    text = State()
    author = State()
    title = State()


def collect_data(data):
    is_trusted_url = data.get('is_trusted_url')
    is_real_author = data.get('is_real_author')
    is_real_article = data.get('is_real_article')
    articles_urls = str(data.get('found_articles', "Ссылка на статью не найдена"))
    found_authors = str(data.get('found_authors', "Автор не найден"))
    found_titles = str(data.get('found_titles', 'Заголовок не найден'))

    return f'Это доверенный сайт: {is_trusted_url}\n' \
           f'Это реальный автор: {is_real_author}\n' \
           f'Это реально существующая статья: {is_real_article}\n' \
           f'Найденные ссылки: {articles_urls}\n' \
           f'Найденные авторы: {found_authors}\n' \
           f'Найденные заголовки: {found_titles}'


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply('Привет! Это бот для проверки новостей, '
                        'сделанный для хакатона MoscowCityHack командой NorthShine.\n'
                        'Вставьте ссылку на новость после /url или текст новости после /text. '
                        'Поиск может занять некоторое время')


@dp.message_handler(filters.Text(contains='/url'))
async def search_by_url(message: types.Message):
    if validators.url(message.text):
        await message.answer('Подтверждение может занять некоторое время')
        response = await client.post(
            config['SEARCH_BY_URL'],
            json={'url': message.text},
            timeout=10000,
        )
        data = response.json()['data']

        if data.get('is_article') is False:
            await message.answer('Внимание: похоже вы указали ссылку не на статью, результаты могут быть некорректны')

        await message.answer(collect_data(data))
    else:
        await message.answer('Ошибка: вы ввели некорректную ссылку')


@dp.message_handler(filters.Text(contains='/text'), state=TextRequest.text)
async def search_by_text(message: types.Message):
    await TextRequest.text.set()
    await message.answer('Напишите имя автора текста после /author', reply_markup=author_keyboard)


@dp.message_handler(filters.Text(contains='/author'), state=TextRequest.author)
async def process_author(message: types.Message, state: FSMContext):
    if message.text == '/author Я не знаю автора текста':
        await state.update_data(author='')
    else:
        await state.update_data(author=message.text)
    await TextRequest.next()
    await message.answer('Напишите заголовок статьи после /title', reply_markup=title_keyboard)


@dp.message_handler(filters.Text(contains='/title'), state=TextRequest.title)
async def process_title(message: types.Message, state: FSMContext):
    if message.text == '/title Я не знаю заголовок статьи':
        await state.update_data(title='')
    else:
        await state.update_data(title=message.text)
    await state.finish()
    await message.answer('Подтверждение может занять некоторое время')

    async with state.proxy() as data:
        text = data['text']
        author = data['author']
        title = data['title']

    response = await client.post(
        config['SEARCH_BY_TEXT'],
        json={
            'text': text,
            'author': author,
            'title': title,
        },
        timeout=10000,
    )
    data = response.json()['data']
    await message.answer(collect_data(data))


@dp.message_handler()
async def default(message: types.Message):
    await message.answer('Нет такой команды. Список доступных команд можно узнать с помощью /help')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
