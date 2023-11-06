<p align="center">
      <img src="https://ibb.org.ru/images/2023/11/06/SNIMOK-EKRANA-2023-11-06-145511.png" alt="Project Logo" width="300">
</p>

<p align="center">
   <img src="https://img.shields.io/badge/Language-python%203.11.4-blueviolet" alt="python version">
   <img src="https://img.shields.io/badge/API-aiogram%202.9.0-yellow" alt="aiogram version">
</p>

## About

A telegram bot that helps automate ordering and delivery from the Chinese POIZON marketplace through an intermediary. In the environment variables, you need to put the API token of the bot, the payment token, the name of your channel and the DB settings.

## Documentation

### Environment Variables:
- **-** **'BOT_TOKEN'** - API bot token.
- **-** **'PAYMENTS_TOKEN'** - payment token.
  
- **-** **'host'** - DB host.
- **-** **'port'** - DB port.
- **-** **'db_name'** - DB name.
- **-** **'user'** - DB username.
- **-** **'password'** - DB password.

- **-** **'channel_name'** - telegram channel name.
- **-** **'admin'** - link to the channel manager.

### Methods:
- **-** **'call_menu()'** **'def'** - the start menu called by the start command.
- **-** **'category_menu()'** **'def'** - menu of product categories.
- **-** **'order_reg_menu()'** **'def'** - menu for interaction with the order.
- **-** **'admin_menu()'** **'def'** - menu called by the admin command.
- **-** **'display_basket(user_id, chat_id, _bot, _cursor)'** **'async def'** - shopping cart display function.
- **-** **'cmd_start(message: types.Message, state: FSMContext)'** **'async def'** - handler of the start command.
- **-** **'cmd_admin(message: types.Message)'** **'async def'** - handler of the admin command.
- **-** **'cmd_basket(message: types.Message)'** **'async def'** - handler of the basket command. Calls the function display_basket.
- **-** **'callback(call, state: FSMContext)'** **'async def'** - button data handler.
- **-** **'delete_product(message: types.Message)'** **'async def'** - removing an item from the shopping cart.
- **-** **'successful_payment(message: types.Message)'** **'async def'** - payment processor.

## Developers

- [tsunamicxde](https://github.com/tsunamicxde)
  
