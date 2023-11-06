import logging
import psycopg2
import json
import re

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types.message import ContentType
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from config import host, port, db_name, user, password, BOT_TOKEN, channel_name, PAYMENTS_TOKEN, admin_name
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

with open('create_orders_table.sql', 'r') as sql_config:
    create_table_query = sql_config.read()

cursor.execute(create_table_query)

conn.commit()

with open('create_paid_orders_table.sql', 'r') as sql_config:
    create_table_query = sql_config.read()

cursor.execute(create_table_query)

conn.commit()


all_types = {
    "Обувь": 2000,
    "Одежда": 2000,
    "Аксессуары": 1000,
    "Сумки": 1000,
    "Чемоданы": 3000,
    "Красота и здоровье": 1000,
    "Часы": 5000,
    "Спорт": 1000,
    "Техника": 5000
}

all_status_types = {
    1: "Новый заказ ещё не оформлен",
    2: "Ваш заказ на рассмотрении менеджером",
    3: "Ваш заказ отклонён",
    4: "Ваш заказ подтверждён и ожидает оплаты"
}


def call_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    order_reg = types.InlineKeyboardButton("Оформление заказа 🛍", callback_data="order_reg")
    calc_the_cost = types.InlineKeyboardButton("Рассчитать стоимость 💹", callback_data="calc_the_cost")
    tracking = types.InlineKeyboardButton("Отслеживание 🔎", callback_data="tracking")
    reviews = types.InlineKeyboardButton("Отзывы ✨", callback_data="reviews")
    chat = types.InlineKeyboardButton("Наш чат ☁️", callback_data="chat")
    question = types.InlineKeyboardButton("У меня вопрос ❓️", callback_data="question")
    basket = types.InlineKeyboardButton("Корзина 🛒", callback_data="basket")
    status = types.InlineKeyboardButton("Статус заказа 🔎", callback_data="status")
    markup.add(order_reg, calc_the_cost, tracking, reviews, chat, question, basket, status)
    return markup


def category_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    shoes = types.InlineKeyboardButton("Обувь 👟", callback_data="Обувь")
    wear = types.InlineKeyboardButton("Одежда 👕", callback_data="Одежда")
    accessories = types.InlineKeyboardButton("Аксессуары 🧣", callback_data="Аксессуары")
    bags = types.InlineKeyboardButton("Сумки и рюкзаки 🎒", callback_data="Сумки")
    suitcases = types.InlineKeyboardButton("Чемоданы 🧳", callback_data="Чемоданы")
    health = types.InlineKeyboardButton("Красота и здоровье 💄️", callback_data="Красота и здоровье")
    watch = types.InlineKeyboardButton("Часы ⌚️", callback_data="Часы")
    sport = types.InlineKeyboardButton("Спорт 🏀", callback_data="Спорт")
    technics = types.InlineKeyboardButton("Техника 💻", callback_data="Техника")
    unknown = types.InlineKeyboardButton("Не могу найти нужную категорию", callback_data="question")
    markup.add(shoes, wear, accessories, bags, suitcases, health, watch, sport, technics, unknown)
    return markup


def order_reg_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    append_product_button = types.InlineKeyboardButton("Добавить товар в корзину 🛍", callback_data="append_product_button")
    basket = types.InlineKeyboardButton("Корзина 🛒", callback_data="basket")
    arrange_order_button = types.InlineKeyboardButton("Оформить заказ", callback_data="arrange_order_button")
    markup.add(append_product_button, basket, arrange_order_button)
    return markup


def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    order_list = types.InlineKeyboardButton("Посмотреть неоплаченные заказы", callback_data="order_list")
    order_payment_list = types.InlineKeyboardButton("Посмотреть оплаченные заказы", callback_data="order_payment_list")
    markup.add(order_list, order_payment_list)
    return markup


async def display_basket(user_id, chat_id, _bot, _cursor):
    try:
        cursor.execute("SELECT \"order\", cost FROM users WHERE user_id = %s;", (user_id,))
        row = _cursor.fetchone()
        current_orders = row[0]
        current_cost = row[1]

        if current_cost > 0:
            order_text = "Ваш заказ:\n"
            for current_order in current_orders:
                order_text += f"Товар №{current_orders.index(current_order)}: "
                for key, value in current_order.items():
                    order_text += f"\n{key} - {value}\n"
                order_text += f"\nУдалить товар №{current_orders.index(current_order)} - /del{current_orders.index(current_order)}\n\n"

            order_text += f"\n\nОбщая стоимость: {current_cost}"

            markup = types.InlineKeyboardMarkup(row_width=1)
            arrange_order_button = types.InlineKeyboardButton("Оформить заказ", callback_data="arrange_order_button")
            markup.add(arrange_order_button)
            await _bot.send_message(chat_id, order_text, reply_markup=markup)
        else:
            await _bot.send_message(chat_id, "Ваш заказ пуст")
    except psycopg2.Error:
        await _bot.send_message(chat_id, "Что-то пошло не так")


@dp.message_handler(commands=['start', 'help'])
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.chat.id

    user_url = f'tg://openmessage?user_id={user_id}'

    keyboard = call_menu()
    await message.reply("Я - бот канала по доставке POIZON, помогаю быстро посчитать цену и заказать"
                        "почти любой товар из Китая в розницу.", reply_markup=keyboard)

    async with state.proxy() as data:
        data['current_step'] = 1

    try:
        insert_query = '''
                INSERT INTO users (user_id, user_url)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET user_id = EXCLUDED.user_id, user_url = EXCLUDED.user_url
                RETURNING user_id;
            '''

        cursor.execute(insert_query, (user_id, user_url))
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        await message.reply("Что-то пошло не так")

    try:
        insert_query = '''
            INSERT INTO orders (order_name)
            VALUES (%s)
            ON CONFLICT (order_name) DO NOTHING
            RETURNING order_name;
        '''

        cursor.execute(insert_query, (user_url, ))
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        await message.reply("Что-то пошло не так")


@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    user_id = message.chat.id
    is_user_admin = False
    try:
        cursor.execute("SELECT is_user_admin FROM users WHERE user_id = %s;", (user_id,))
        is_user_admin = cursor.fetchone()[0]
    except (psycopg2.Error, TypeError):
        await message.reply("Что-то пошло не так")
    if is_user_admin:
        keyboard = admin_menu()
        await message.reply("Посмотреть все заказы: ", reply_markup=keyboard)


@dp.message_handler(commands=['basket'])
async def cmd_basket(message: types.Message):
    user_id = message.chat.id
    await bot.send_message(message.chat.id, "Корзина: ")
    await display_basket(user_id, message.chat.id, bot, cursor)


@dp.callback_query_handler(lambda callback_query: True)
async def callback(call, state: FSMContext):
    user_id = call.message.chat.id
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if call.data == "basket":
        await bot.send_message(call.message.chat.id, "Корзина: ")
        await display_basket(user_id, call.message.chat.id, bot, cursor)
    elif call.data == "order_reg" or call.data == "append_product_button":
        is_order_accepted = True
        try:
            cursor.execute("SELECT is_order_accepted FROM users WHERE user_id = %s;", (user_id,))
            is_order_accepted = cursor.fetchone()[0]
        except psycopg2.Error:
            conn.rollback()
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")

        if is_order_accepted:
            async with state.proxy() as data:
                data['current_step'] = 4
            photo = open('url_instruction.jpg', 'rb')
            await bot.send_message(call.message.chat.id, "Вставьте ссылку на товар: ")
            await bot.send_photo(call.message.chat.id, photo)

        else:
            await bot.send_message(call.message.chat.id, "Ваш заказ на рассмотрении менеджером! "
                                                         "Дождитесь, пока его одобрят")

    elif call.data == "calc_the_cost":
        async with state.proxy() as data:
            data['current_step'] = 2

        keyboard = category_menu()
        await bot.send_message(call.message.chat.id, "Укажите категорию товара", reply_markup=keyboard)
    elif call.data == "arrange_order_button":
        await bot.send_message(call.message.chat.id, "Укажите адрес: Город, Улица, Дом, Квартира, Почтовый индекс: ")
        async with state.proxy() as data:
            data['current_step'] = 8
    elif call.data in all_types.keys():
        async with state.proxy() as data:
            if data['current_step'] == 2:
                data['current_step'] = 3
                data['type'] = call.data
                await bot.send_message(call.message.chat.id, "Введите стоимость в юанях для расчёта стоимости: ")
            elif data['current_step'] == 5:
                data['category'] = str(call.data)
                data['current_step'] = 6

                photo = open('cost_instruction.jpg', 'rb')
                await bot.send_photo(call.message.chat.id, photo)

                await bot.send_message(call.message.chat.id, "Укажите цену товара в ЮАНЯХ (¥)\n"

                                                             "❗️Указывайте верную стоимость товара, иначе заказ будет отменён. Цена может меняться в зависимости от размера и цвета. ОЧЕНЬ ВАЖНО!\n"
                        
                                                             "❗️По волнистой линии '≈' НЕ ВЫКУПАЕМ!\n"
                        
                                                             "❗️ВНИМАНИЕ! Выбирайте цену которая ЗАЧЕРКНУТА. Система отображает скидки для первых покупателей. У нас нет этих скидок.")

    elif call.data == "status":
        order_status = -1
        try:
            cursor.execute("SELECT status FROM users WHERE user_id = %s;", (user_id,))
            order_status = int(cursor.fetchone()[0])
            await bot.send_message(call.message.chat.id, all_status_types[order_status])
        except (psycopg2.Error, TypeError, ValueError):
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
        if order_status == 4:
            try:
                cursor.execute("SELECT order_id FROM users WHERE user_id = %s;", (user_id,))
                order_id = int(cursor.fetchone()[0])
                cursor.execute("SELECT \"order\", cost FROM orders WHERE id = %s;", (order_id,))
                rows = cursor.fetchone()
                current_orders = rows[0]
                current_cost = rows[1]

                if current_cost > 0:
                    order_text = "Ваш заказ:\n"
                    for current_order in current_orders:
                        order_text += f"Товар №{current_orders.index(current_order)}: "
                        for key, value in current_order.items():
                            order_text += f"\n{key} - {value}\n"

                    order_text += f"\n\nОбщая стоимость: {current_cost}"

                    markup = types.InlineKeyboardMarkup(row_width=1)
                    payment_button = types.InlineKeyboardButton("Оплатить корзину 💵",
                                                                callback_data="payment_button")
                    cancel_payment_button = types.InlineKeyboardButton("Отменить заказ",
                                                                       callback_data="cancel_payment_button")
                    markup.add(payment_button, cancel_payment_button)
                    await bot.send_message(call.message.chat.id, "Вы хотите оплатить корзину? ",
                                           reply_markup=markup)
                else:
                    await bot.send_message(call.message.chat.id, "Ваш заказ пуст")
            except psycopg2.Error:
                await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif call.data == "order_list":
        try:
            cursor.execute("SELECT id, order_name, \"order\", cost, address, full_order_name FROM orders WHERE order_status = 1;")
            rows = cursor.fetchall()

            if rows:
                order_groups = {}
                for row in rows:
                    order_id, order_name, current_orders, current_cost, current_address, current_full_order_name = row
                    if order_name not in order_groups:
                        order_groups[order_name] = {
                            "order_id": order_id,
                            "orders": [],
                            "cost": current_cost,
                            "current_address": current_address,
                            "current_full_order_name": current_full_order_name
                        }
                    order_groups[order_name]["orders"].append(current_orders)

                for order_name, group in order_groups.items():
                    order_text = f"Заказ №{group['order_id']}\nОт '{order_name}':\n"
                    for current_order in group['orders']:
                        for index, order in enumerate(current_order):
                            order_text += f"\nТовар №{index}:\n"
                            for key, value in order.items():
                                order_text += f"{key} - {value}\n"
                    order_text += f"\n\nАдрес: {group['current_address']}"
                    order_text += f"\n\nФИО: {group['current_full_order_name']}"
                    order_text += f"\n\nОбщая стоимость: {group['cost']}"

                    markup = types.InlineKeyboardMarkup(row_width=1)
                    accept_order_button = types.InlineKeyboardButton("Подтвердить заказ ✅",
                                                                     callback_data=f"accept_order_{group['order_id']}_button")
                    cancel_order_button = types.InlineKeyboardButton("Отклонить заказ ❌",
                                                                     callback_data=f"cancel_order_{group['order_id']}_button")
                    markup.add(accept_order_button, cancel_order_button)

                    await bot.send_message(call.message.chat.id, order_text, reply_markup=markup)
            else:
                await bot.send_message(call.message.chat.id, "Новых заказов пока нет")
        except psycopg2.Error:
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif call.data == "order_payment_list":
        try:
            cursor.execute("SELECT id, order_name, \"order\", cost, address, full_order_name FROM paid_orders;")
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    order_id, order_name, current_orders, current_cost, current_address, current_full_order_name = row

                    order_text = f"Заказ №{order_id}\nОт '{order_name}':\n"

                    for index, order in enumerate(current_orders):
                        order_text += f"\nТовар №{index}:\n"
                        if isinstance(order, dict):
                            for key, value in order.items():
                                order_text += f"{key} - {value}\n"
                        else:
                            order_text += f"Не удалось разобрать товар\n"

                    order_text += f"\n\nАдрес: {current_address}"
                    order_text += f"\n\nФИО: {current_full_order_name}"

                    order_text += f"\n\nОбщая стоимость: {current_cost}\n\nЗаказ оплачен ✅"

                    await bot.send_message(call.message.chat.id, order_text)
            else:
                await bot.send_message(call.message.chat.id, "Оплаченных заказов пока нет")

        except psycopg2.Error:
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif re.search(r'accept_order_\d+_button', str(call.data)):
        try:
            user_id_match = re.search(r'accept_order_(.*?)_button', call.data)
            order_id = int(user_id_match.group(1))

            update_query = f'''
                                UPDATE users
                                SET 
                                    status = 4
                                WHERE order_id = %s;
                            '''
            cursor.execute(update_query, (order_id,))
            conn.commit()

            update_query = f'''
                                UPDATE orders
                                SET 
                                    order_status = 2
                                WHERE id = %s;
                            '''
            cursor.execute(update_query, (order_id,))
            conn.commit()

            await bot.send_message(call.message.chat.id, f"Вы успешно одобрили заказ №{order_id} ✅")
        except (psycopg2.Error, ValueError):
            conn.rollback()
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif re.search(r'cancel_order_\d+_button', str(call.data)):
        try:
            user_id_match = re.search(r'cancel_order_(.*?)_button', call.data)
            order_id = int(user_id_match.group(1))

            update_query = f'''
                            UPDATE users
                            SET 
                                status = 3,
                                is_order_accepted = DEFAULT
                            WHERE order_id = %s;
                        '''
            cursor.execute(update_query, (order_id,))
            conn.commit()

            cursor.execute("DELETE FROM orders WHERE id = %s;", (order_id,))

            await bot.send_message(call.message.chat.id, f"Вы успешно отклонили заказ №{order_id}")
        except (psycopg2.Error, ValueError):
            conn.rollback()
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif call.data == "payment_button":
        try:
            cursor.execute("SELECT order_id FROM users WHERE user_id = %s;", (user_id,))
            order_id = cursor.fetchone()[0]

            cursor.execute("SELECT cost FROM orders WHERE id = %s;", (order_id,))
            current_cost = cursor.fetchone()[0]

            price = types.LabeledPrice(label="Стоимость заказа", amount=current_cost * 100)

            await bot.send_invoice(call.message.chat.id,
                                   title="Оформление заказа",
                                   description="Оплата стоимости заказа",
                                   provider_token=PAYMENTS_TOKEN,
                                   currency="rub",
                                   is_flexible=False,
                                   prices=[price],
                                   start_parameter="order_pay",
                                   payload="order-payload")
        except psycopg2.Error:
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")
    elif call.data == "cancel_payment_button":
        order_id = -1
        try:
            cursor.execute("SELECT order_id FROM users WHERE user_id = %s;", (user_id,))
            order_id = cursor.fetchone()[0]
        except psycopg2.Error:
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")

        try:
            cursor.execute("DELETE FROM orders WHERE id = %s;", (order_id,))

            conn.commit()

            update_query = '''
                                UPDATE users
                                SET 
                                    "order" = DEFAULT,
                                    status = 1,
                                    is_order_accepted = DEFAULT
                                WHERE user_id = %s;
                           '''

            cursor.execute(update_query, (user_id,))
            conn.commit()

            await bot.send_message(call.message.chat.id, "Вы успешно отменили заказ")

        except psycopg2.Error:
            conn.rollback()
            await bot.send_message(call.message.chat.id, "Что-то пошло не так")

    elif call.data in ["tracking", "reviews", "chat", "question"]:
        await bot.send_message(call.message.chat.id, f"По любому вопросу вы можете обратиться к менеджеру\n{admin_name}\n"
                                                     f"или заглянуть в наш канал\n{channel_name}")


@dp.message_handler(lambda message: re.match(r'/del\d+', message.text))
async def delete_product(message: types.Message):
    user_id = message.chat.id
    try:
        try:
            index = int(message.text[4:])

            cursor.execute("SELECT \"order\" FROM users WHERE user_id = %s;", (user_id,))
            order = cursor.fetchone()[0]

            if 0 <= index < len(order):
                deleted_product_list = order.pop(index)
                new_data = json.dumps(order)
                try:
                    cursor.execute("UPDATE users SET \"order\" = %s WHERE user_id = %s;", (new_data, user_id))
                    conn.commit()

                    await message.reply(f"Вы успешно удалили товар из заказа.")
                    update_query = '''
                                        UPDATE users
                                        SET
                                            cost = cost - %s
                                        WHERE user_id = %s;
                                   '''

                    cursor.execute(update_query, (list(deleted_product_list.values())[0], user_id))
                    conn.commit()
                except psycopg2.Error:
                    conn.rollback()
                    await message.reply("Что-то пошло не так")
                keyboard = call_menu()
                deleted_product_list.clear()
                await message.reply("Выберите интересующую вас категорию в меню:\n",
                                    reply_markup=keyboard)
            else:
                await message.reply("Указанный индекс недопустим.")

        except psycopg2.Error:
            await message.reply("Что-то пошло не так")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате /del<индекс> для удаления товара из заказа.")


@dp.message_handler(lambda message: message.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.chat.id
    async with state.proxy() as data:
        if data['current_step'] == 3:
            try:
                price = float(message.text)
                user_type = data.get('type')
                amount = (last_price * price) + all_types[user_type]
                await message.reply(f"Курс: {last_price}\n"
                                    f"Сумма вместе с доставкой и страховкой: {amount}")
            except ValueError:
                await message.reply("Введите стоимость в числовом формате ❗")
        elif data['current_step'] == 4:
            try:
                data['url'] = str(message.text)

                keyboard = category_menu()
                await message.reply("Укажите категорию товара.\n"

                                    "❗️Необходимо выбрать верную категорию, в противном случае заказ будет отменён.\n"

                                    "❗️Если есть сомнения, вы всегда можете задать вопрос @your_channel_name", reply_markup=keyboard)

                data['current_step'] = 5
            except ValueError:
                keyboard = call_menu()
                await message.reply("Некорректная ссылка ❗", reply_markup=keyboard)
        elif data['current_step'] == 6:
            try:
                price = float(message.text)
                data['cost'] = int((last_price * price) + all_types[str(data['category'])])

                await message.reply("Укажите размер: ")
                data['current_step'] = 7
            except ValueError:
                await message.reply("Введите стоимость в числовом формате ❗")
        elif data['current_step'] == 7:
            data['size'] = str(message.text)

            await message.reply("👌")
            await message.reply("Товар успешно добавлен ✅")
            keyboard = order_reg_menu()
            await message.reply("Выберите опцию: ", reply_markup=keyboard)

            try:
                update_query = '''
                                                UPDATE users
                                                SET 
                                                    "order" = "order" || %s::jsonb,
                                                    cost = cost + %s
                                                WHERE user_id = %s;
                                           '''

                cursor.execute(update_query, (json.dumps({'Ссылка': data['url'], 'Цена': data['cost'],
                                                          'Категория': data['category'], 'Размер': data['size']}),
                                              data['cost'], user_id))
                conn.commit()

                data['current_step'] = 1
            except psycopg2.Error:
                conn.rollback()
                await bot.send_message(message.chat.id, "Что-то пошло не так")
        elif data['current_step'] == 8:
            try:
                data['address'] = str(message.text)
                await message.reply("Укажите своё ФИО: ")
                data['current_step'] = 9
            except ValueError:
                await message.reply("Введённый текст некорректен")
        elif data['current_step'] == 9:
            try:
                data['name'] = str(message.text)
                cursor.execute("SELECT \"order\", cost, user_url FROM users WHERE user_id = %s;", (user_id,))
                row = cursor.fetchone()
                current_order = json.dumps(row[0])
                current_cost = row[1]
                current_url = row[2]

                update_query = '''
                                    UPDATE orders
                                    SET 
                                        order_name = %s,
                                        "order" = "order" || %s::jsonb,
                                        cost = %s,
                                        order_status = 1,
                                        address = %s,
                                        full_order_name = %s;
                               '''
                cursor.execute(update_query, (current_url, current_order, current_cost, data['address'], data['name']))
                conn.commit()

                cursor.execute("SELECT id FROM orders WHERE order_name = %s", (current_url,))
                order_id = cursor.fetchone()[0]

                update_query = '''
                                    UPDATE users
                                    SET 
                                        "order" = DEFAULT,
                                        cost = DEFAULT,
                                        is_order_accepted = FALSE,
                                        status = 2,
                                        order_id = %s
                                    WHERE user_id = %s;
                               '''

                cursor.execute(update_query, (order_id, user_id,))
                conn.commit()

                await bot.send_message(message.chat.id, "Ваш заказ отправлен на проверку менеджеру ✅")
                data['current_step'] = 1
            except (psycopg2.Error, ValueError):
                conn.rollback()
                await bot.send_message(message.chat.id, "Что-то пошло не так")
        else:
            await message.reply("Введённый текст некорректен")


@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    user_id = message.chat.id
    order_id = -1
    await bot.send_message(message.chat.id,
                           f"Платёж на сумму {message.successful_payment.total_amount // 100}"
                           f" {message.successful_payment.currency} прошёл успешно ✅")

    try:
        cursor.execute("SELECT order_id FROM users WHERE user_id = %s;", (user_id,))
        order_id = cursor.fetchone()[0]
    except psycopg2.Error:
        await bot.send_message(message.chat.id, "Что-то пошло не так")

    try:
        cursor.execute("SELECT order_name, \"order\", cost, address, full_order_name FROM orders WHERE id = %s;",
                       (order_id, ))
        rows = cursor.fetchone()
        current_order_name = rows[0]
        current_order = json.dumps(rows[1])
        current_cost = rows[2]
        current_address = rows[3]
        current_full_order_name = rows[4]

        cursor.execute("DELETE FROM orders WHERE id = %s;", (order_id,))

        insert_query = '''
                        INSERT INTO paid_orders (order_name, "order", cost, address, full_order_name)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *;
                    '''

        cursor.execute(insert_query, (current_order_name, current_order, current_cost, current_address, current_full_order_name))
        conn.commit()

        update_query = '''
                                                        UPDATE users
                                                        SET 
                                                            status = 1,
                                                            is_order_accepted = DEFAULT
                                                        WHERE user_id = %s;
                                                   '''

        cursor.execute(update_query, (user_id,))
        conn.commit()

    except psycopg2.Error:
        conn.rollback()
        await bot.send_message(message.chat.id, "Что-то пошло не так")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
