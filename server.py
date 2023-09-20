import logging
import psycopg2

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types.message import ContentType
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from config import host, port, db_name, user, password, BOT_TOKEN, channel_name
from exchange_rate import last_price

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())

conn = psycopg2.connect(
    host=host,
    port=port,
    dbname=db_name,
    user=user,
    password=password
)
cursor = conn.cursor()

with open('create_users_table.sql', 'r') as sql_config:
    create_table_query = sql_config.read()

cursor.execute(create_table_query)

conn.commit()


all_types = {
    "shoes": 2000,
    "wear": 2000,
    "accessories": 1000,
    "bags": 1000,
    "suitcases": 3000,
    "health": 1000,
    "watch": 5000,
    "sport": 1000,
    "technics": 5000
}


def call_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    order_reg = types.InlineKeyboardButton("Оформление заказа 🛍", callback_data="order_reg")
    calc_the_cost = types.InlineKeyboardButton("Рассчитать стоимость 💹", callback_data="calc_the_cost")
    tracking = types.InlineKeyboardButton("Отслеживание 🔎", callback_data="tracking")
    reviews = types.InlineKeyboardButton("Отзывы ✨", callback_data="reviews")
    chat = types.InlineKeyboardButton("Наш чат ☁️", callback_data="chat")
    question = types.InlineKeyboardButton("У меня вопрос ❓️", callback_data="question")
    markup.add(order_reg, calc_the_cost, tracking, reviews, chat, question)
    return markup


@dp.message_handler(commands=['start', 'help'])
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.chat.id

    keyboard = call_menu()
    await message.reply("Я - бот канала по доставке POIZON, помогаю быстро посчитать цену и заказать"
                        "почти любой товар из Китая в розницу.", reply_markup=keyboard)

    async with state.proxy() as data:
        data['current_step'] = 1

    try:
        insert_query = '''
                INSERT INTO users (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO UPDATE
                SET user_id = EXCLUDED.user_id
                RETURNING user_id;
            '''

        cursor.execute(insert_query, (user_id,))
        conn.commit()
    except psycopg2.Error as ex:
        conn.rollback()
        await message.reply("Что-то пошло не так")
        print(ex)


@dp.callback_query_handler(lambda callback_query: True)
async def callback(call, state: FSMContext):
    user_id = call.message.chat.id
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if call.data == "order_reg":
        pass
    elif call.data == "calc_the_cost":
        async with state.proxy() as data:
            data['current_step'] = 2

        markup = types.InlineKeyboardMarkup(row_width=1)
        shoes = types.InlineKeyboardButton("Обувь 👟", callback_data="shoes")
        wear = types.InlineKeyboardButton("Одежда 👕", callback_data="wear")
        accessories = types.InlineKeyboardButton("Аксессуары 🧣", callback_data="accessories")
        bags = types.InlineKeyboardButton("Сумки и рюкзаки 🎒", callback_data="bags")
        suitcases = types.InlineKeyboardButton("Чемоданы 🧳", callback_data="suitcases")
        health = types.InlineKeyboardButton("Красота и здоровье 💄️", callback_data="health")
        watch = types.InlineKeyboardButton("Часы ⌚️", callback_data="watch")
        sport = types.InlineKeyboardButton("Спорт 🏀", callback_data="sport")
        technics = types.InlineKeyboardButton("Техника 💻", callback_data="technics")
        unknown = types.InlineKeyboardButton("Не могу найти нужную категорию", callback_data="question")
        markup.add(shoes, wear, accessories, bags, suitcases, health, watch, sport, technics, unknown)
        await bot.send_message(call.message.chat.id, "Укажите категорию товара", reply_markup=markup)
    elif call.data in all_types.keys():
        async with state.proxy() as data:
            data['current_step'] = 3
            data['type'] = call.data
        await bot.send_message(call.message.chat.id, "Введите стоимость в юанях для расчёта стоимости: ")


@dp.message_handler(lambda message: message.text)
async def handle_text(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)

        async with state.proxy() as data:
            user_type = data.get('type')
            if data['current_step'] == 3:
                amount = (last_price * price) + all_types[user_type]
                await message.reply(f"Курс: {last_price}\n"
                                    f"Сумма вместе с доставкой и страховкой: {amount}")

    except ValueError:
        await message.reply(f"Введите стоимость в числовом формате")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
