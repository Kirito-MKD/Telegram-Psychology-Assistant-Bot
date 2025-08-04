from telebot.async_telebot import AsyncTeleBot
import telebot
from telebot import types

from telethon import TelegramClient
from telethon import events
import shutil

import asyncio

from database import connection_table
from myDeepSeek import MyDeepSeek
from myLogs import Mylogs
from audioConvert import AudioReader
from tools import create_user_menu, buttons_admins, read_file, save_file,\
    get_wordkeys, get_time, get_full_user_from_db, reset_full, add_to_statistic,\
    check_key_word, get_user, is_blacklist, generate_delay, decode

from myAdmins import MyAdmins
from exel import Exel

import os

API_bot = "Your Api"
bot = AsyncTeleBot(API_bot)
me = "me"
database_name = "chat_history.db"
database = connection_table(database_name) # history of interaction with user in role of game
assistant_table_name = "assistant_history" # history of interaction with user in role of assistant
logs = Mylogs("AI bot")

Audio = AudioReader(logs)

Admins = MyAdmins(logs, bot)

ai_api_key = "AI api" # ai api
model = "deepseek/deepseek-chat:free" # model for assistant
assistant_ai = MyDeepSeek(logs, database, assistant_table_name, model, ai_api_key) # assitant


user_time_data = []
time_message = ""
user_login = ""
user_password = ""
session_name = "Current-session" # name to logs and file of user bot session


bool_get_login = False
bool_get_password = False
@bot.message_handler(commands=["start"])
async def start(message):
    await bot.send_message(message.chat.id, "Я ваш помощник по вашему каналу, чтобы начать введите /login")

"""Authorisation"""
@bot.message_handler(commands=["login"])
async def login(message):
    if await Admins.is_active_admin(message.from_user.id, mute_mode=True):
        markup = create_user_menu(buttons_admins)
        await bot.send_message(message.chat.id, "Вы уже прошли авторизацию", reply_markup=markup)
        return None

    global bool_get_login
    bool_get_login = True

    await bot.send_message(message.chat.id, "Введите логин:")

@bot.message_handler(func=lambda message: message.text and bool_get_login)
async def get_login(message):
    global bool_get_login , bool_get_password

    if message.text != user_login:
        bool_get_login = False
        await bot.send_message(message.chat.id, "Неверный логин!\nПопробуйте еще раз!\n/login")
        return None

    bool_get_login = False
    bool_get_password = True

    await bot.send_message(message.chat.id, "Введите пароль")

@bot.message_handler(func=lambda message: message.text and bool_get_password)
async def get_password(message):
    global bool_get_password

    if message.text != user_password:
        await bot.send_message(message.chat.id, "Неверный пароль!\nПопробуйте еще раз.\n /login")
        bool_get_password = False
        return None

    bool_get_password = False
    Admins.register_admin(message.from_user.id)
    markup = create_user_menu(buttons_admins)
    await bot.send_message(message.chat.id, "Вы успешно авторизовались", reply_markup=markup)


"""User bot activation"""


time_user_data = []
flag = False
bool_get_user_bot_data = False
bool_get_code = False
my_thread = False
app = None
sCode = None
bot_subscribers = 0
bot_unsubscribers = 0
active_bot = False
unsub_sending = True

start_delay = 1
end_delay = 4


live_order = []
messages_from_users = {}

@bot.message_handler(func=lambda message: message.text == buttons_admins[2])
async def user_bot(message):

    if not await Admins.is_active_admin(message.from_user.id):
        return None

    if not os.path.exists(session_name+".session"):
        markup = telebot.types.InlineKeyboardMarkup().add(
            *[
                types.InlineKeyboardButton(text="Отмена" , callback_data="cancel") ,
                types.InlineKeyboardButton(text="Добавить" , callback_data="add_bot")
            ]
        )
        await bot.send_message(message.chat.id, "У вас нет активого бота. Хотите добавить?", reply_markup=markup)

    elif not app and os.path.exists(session_name+".session"):
        markup = telebot.types.InlineKeyboardMarkup().add(
            *[
                types.InlineKeyboardButton(text="Отмена" , callback_data="cancel") ,
                types.InlineKeyboardButton(text="Изменить" , callback_data="add_bot_o")
            ]
        )
        markup.add(types.InlineKeyboardButton(text="Активировать" , callback_data="activate"))
        await bot.send_message(message.chat.id , "Имеется неактивный бот." , reply_markup=markup)
    else:
        markup = telebot.types.InlineKeyboardMarkup().add(
            *[
                types.InlineKeyboardButton(text="Отмена" , callback_data="cancel") ,
                types.InlineKeyboardButton(text="Изменить" , callback_data="add_bot_o")
            ]
        )
        markup.add(types.InlineKeyboardButton(text="Выключить" , callback_data="disable"))
        await bot.send_message(message.chat.id , "У вас есть активный бот. Изменить его?" , reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "disable")
async def disable_user_bot(call):
    global app
    await bot.send_message(call.message.chat.id, "Отключаем бота...")

    if app:
        global active_bot, flag
        active_bot = False
        flag=False

        try:
            await app.disconnect()
        except Exception as err:
            logs.set_error_log(str(err), "disable user bot")

    await asyncio.sleep(10)
    app = None
    await bot.send_message(call.message.chat.id , "Бот отключен")


@bot.callback_query_handler(func=lambda call: call.data == "activate")
async def active_bot(call):
    global bool_get_user_bot_data
    bool_get_user_bot_data = False
    await get_code(call.message, True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_bot"))
async def add_bot(call):
    global bool_get_user_bot_data, app
    bool_get_user_bot_data = True

    if call.data[-1] == "o":

        global flag, flag_session, active_bot
        flag = False
        active_bot = False

        await bot.send_message(call.message.chat.id, "Подождите 10 секунд\nОтключаем старого бота")
        await asyncio.sleep(10)

        if app:
            try:
                await app.disconnect()
            except Exception as err:
                pass

        try:
            if os.path.exists(session_name+".session"):
                os.remove(session_name+".session")
        except Exception as err:
            logs.set_error_log(str(err), "delete session")

    time_user_data.clear()
    await bot.send_message(call.message.chat.id , "Введите данные юзер бота как:" \
                                                  "\n<u>api_id;api_hash;телефон </u>\n" \
                                                  "Формат телефона <i>+79225551234</i>" , parse_mode="HTML")

@bot.message_handler(func=lambda message: bool_get_user_bot_data)
async def get_data_user_bot(message):
    try:
        api_id, api_hash,phone = message.text.split(";")
        time_user_data.extend([api_id, api_hash, phone])
    except Exception as err:
        logs.set_error_log("Not critical " + str(err), "get_data_from_user")
        await bot.send_message(message.chat.id, "Неккоректный ввод")
        return None

    global bool_get_user_bot_data , app , bool_get_code, sCode, flag
    bool_get_user_bot_data = False
    app = None
    try:
        app = TelegramClient(session=session_name , api_id=api_id , api_hash=api_hash)
        await app.connect()
        await app.send_code_request(phone)
    except Exception as err:
        pass
        if str(err) == "database is locked":

            if app:

                # todo !!!
                try:
                    asyncio.get_event_loop().stop()
                except Exception as err1:
                    logs.set_error_log(str(err1), "get_data_from_user_bot:1")

                try:
                    await app.disconnect()
                except Exception as err2:
                    logs.set_error_log(str(err2), "get_data_from_user_bot:2")
        await bot.send_message(message.chat.id, "Ошибка\nпопробуйте еще раз")
        flag = False
        return None

    bool_get_code = True
    await bot.send_message(message.chat.id, "Введите код, отправленный на аккаунт юзер бота.\n"
                                            " Зашифруйте код согасно схеме:\n"
                                            "0 - a\n"
                                            "1 - b\n"
                                            "2 - c\n"
                                            "3 - d\n"
                                            "4 - e\n"
                                            "5 - f\n"
                                            "6 - g\n"
                                            "7 - h\n"
                                            "8 - i\n"
                                            "9 - j")

@bot.message_handler(func=lambda message: bool_get_code)
async def get_code(message=None, active_mode = False, message_mode=True):
    global app, sCode, my_thread, flag, bool_get_code
    bool_get_code = False


    try:
        if active_mode and not flag:
            data = read_file("user-bot.json")
            api_id = data["api_id"]
            api_hash = data["api_hash"]
            phone = data["phone"]
            user_time_data.clear()
            user_time_data.extend([api_id, api_hash, phone])
            app = TelegramClient(session_name, api_hash=api_hash, api_id=api_id)
            await app.connect()
            await app.start()
        elif flag:
            await bot.send_message(message.chat.id , "Бот уже активирован\n")
            return None
        else:

            if message_mode:
                code = decode(str(message.text))

                api_id , api_hash , phone = time_user_data
                await app.sign_in(phone, code)
                data = {
                    "api_id": api_id ,
                    "api_hash": api_hash ,
                    "phone": phone
                }
                save_file("user-bot.json" , data)

    except Exception as err:
        if str(err) == "database is locked":
            logs.set_error_log("Not critical" + str(err), "get_code")
            await bot.send_message(message.chat.id , "Бот уже активирован\n")
            return None

        elif str(err) == "The confirmation code has expired (caused by SignInRequest)":
            try:
                app = TelegramClient(session_name, api_hash=api_hash, api_id=api_id)
                await app.start()
            except:
                logs.set_error_log("The confirmation code has expired (caused by SignInRequest)", "get_code_except")
        else:
            await bot.send_message(message.chat.id , "Ошибка\n" + str(err))
            await app.disconnect()
            logs.set_error_log(str(err) , "get_code")
            app = None
            return None

    global active_bot

    if message_mode:
        await bot.send_message(message.chat.id, "Готово")
    else:
        await Admins.notify_active_admins("Юзер-бот был перезапущен.Ошибка произошла на сервере\n")

    flag = True
    active_bot = True
    if (active_bot and app) and app.is_connected():

        @app.on(events.NewMessage(func=lambda event: check_key_word(event)))
        async def keywords(event):
            global end_delay, start_delay
            message = event.message
            try:
                user = await event.get_sender()
                name , nickname , phone = get_user(user)
                id = user.id
            except Exception as err:
                name = ""
                nickname = ""
                phone = ""
                logs.set_error_log(str(err) , "get user")
                id = message.peer_id.user_id

            if is_blacklist(id , database):
                return None

            await asyncio.sleep(end_delay * 60 , start_delay * 60)
            key_words = read_file("./keywords_files/files_info.json")
            await app.send_read_acknowledge(id, message)

            if message.text.lower() in key_words.keys():
                path = key_words[message.text.lower()]
                await app.send_read_acknowledge(id , message)
                await app.send_file(id , file=path)
                logs.set_sending_log(id , name)

                add_to_statistic(database , get_time() ,
                                 name, nickname, phone,
                                 "Слово ключ " + message.text , id)

                return None

        @app.on(events.NewMessage(func=lambda event: not check_key_word(event) and event.is_private))
        async def consultant(event):
            message = event.message
            print("Message")

            try:
                user = await event.get_sender()

                if user.bot:
                    return None

                name , nickname , phone = get_user(user)
                id = user.id
            except Exception as err:
                name = ""
                nickname = ""
                phone = ""
                try:
                    id = message.peer_id.user_id
                except Exception as err:
                    id =-1
                    logs.set_error_log(str(err), "can't get user")
                    return None
                logs.set_error_log(str(err) , "get user")

            if id < 0:
                return None

            if is_blacklist(id, database):
                return None

            """Convert voice"""
            if event.message.voice: # answering on voice

                try:

                    if os.path.exists(f"./voices/{id}.ogg"):
                        os.remove(f"./voices/{id}.ogg")

                    path = await event.message.download_media(file=f"./voices/{id}")
                    file_name = path.split("/")[-1]
                    shutil.move(path, path.replace(".oga", ".ogg"))
                    file_name = file_name.replace(".oga", ".ogg")
                except Exception as err:
                    logs.set_error_log(str(err), "download media from user " + name)
                    await app.send_message(id, "Извините, я не смогла вас понять\n"
                                                            "Не могли бы вы, пожалуйста, написать мне")
                    return None

                try:
                    text = await Audio.convert_audio_to_text(file_name)
                    message.text = text
                except Exception as err:
                    logs.set_error_log(str(err), "audio error convert")
                    await app.send_message(id, "Извините, я не смогла вас понять. Не могли бы вы, пожалуйста, написать мне")
                    return None

                if not text:
                    await app.send_message(id ,
                                           "Извините, я не смогла вас понять. Не могли бы вы, пожалуйста, написать мне")
                    return None
            """End convert voice"""

            if not message.text:
                return None

            read_only_acnowelge = False
            if id in messages_from_users.keys():
                if messages_from_users[id]:
                    read_only_acnowelge = True

                messages_from_users[id] += "\n" + message.text
            else:
                messages_from_users[id] = message.text

            try:
                activity = database.get_certain(f"id={id}" , assistant_table_name)
            except Exception as err:
                logs.set_error_log(str(err), "cant get activity")
                activity = []

            if activity:
                activity = int(activity[0][-1])
            else:
                activity = 0

            if activity > 6:
                print("Message")
                await asyncio.sleep(generate_delay(start_delay*60, end_delay*60))
            else:
                print(f"message{activity}")
                await asyncio.sleep(60)

            if read_only_acnowelge:
                try:
                    await app.send_read_acknowledge(id, message)
                except Exception as err:
                    logs.set_error_log(str(err) , "can't mark as read message user " + name)
                return None

            try:
                message_from_user = messages_from_users[id].replace("DEL", "")
                messages_from_users[id] = ""
            except Exception as err:
                logs.set_error_log(str(err), "cant clear message history")
                return None

            if message_from_user:
                answer = await assistant_ai.get_answer(id , message_from_user)
            else:
                return None

            if not answer:
                for _ in range(4):

                    answer = await assistant_ai.get_answer(id, message_from_user)

                    if answer:
                        break

            if not answer:
                logs.set_error_log("Empty answer from mistral", 'get answer from ai in main.py')
                return None

            if answer == "200":
                logs.set_error_log("AI server error" , 'get answer from ai in main.py')
                await Admins.notify_active_admins("Ошибка связанная с сервером. Скорее всего кончились средства на вашем аккаунте")

                return None

            if answer == "404":
                answer = await assistant_ai.get_answer(id , message_from_user)

                for _ in range(5):
                    answer = await assistant_ai.get_answer(id , message_from_user)
                    await asyncio.sleep(15)

                    if answer and answer != "404":
                        break

                if answer == "404":
                    logs.set_error_log("can't get message from ai", "in 404 get code")
                    await Admins.notify_active_admins(f"Не удалось получить ответ от нейросети для пользователя: {name}\n"
                                               f"Нейросеть прислала пустой ответ")
                    return None

            try:
                await app.send_read_acknowledge(id , message)
            except Exception as err:
                logs.set_error_log(str(err), "can't mark as read message user " + name)
                return None

            live_order.append([id,answer, name, nickname, phone])


        if (active_bot and app) and app.is_connected():

            while app and app.is_connected():

                for user in live_order:
                    id , answer , name , nickname , phone = user

                    cards_name = read_file("./photo_cards/files_info.json")
                    is_photo = False
                    cards = []
                    for card_name in cards_name.keys():

                        if answer.find(f"~~{card_name}~~") != -1:
                            answer = answer.replace(f"~~{card_name}~~" , "")
                            answer = answer.replace("\\n", "\n")
                            is_photo = True
                            cards.append(card_name)

                    try:
                        app.parse_mode = "markdown"
                        async with app.action(id , 'typing'):
                            await asyncio.sleep(generate_delay(10 , 30))
                        await app.send_message(id, answer.replace("<|end_of_sentence|>", ""))

                        add_to_statistic(database , get_time() ,
                                         name , nickname , phone ,
                                         "Консультант" , id)

                        logs.set_sending_log(id , name)

                    except Exception as err:
                        logs.set_error_log(str(err), "sending message")

                    if is_photo:
                        try:
                            for card in cards:
                                await app.send_file(id , file=cards_name[card])
                        except Exception as err:
                            logs.set_error_log(str(err), f"Не удалось отправить карточку пользователю {id}")

                            await Admins.notify_active_admins(f"Не удалось отправить карточку пользователю {id}")

                    live_order.remove(user)
                    await asyncio.sleep(25)

                await asyncio.sleep(5)


"""Cards logic"""

bool_get_card_name = False
bool_get_photo_card = False
bool_get_card_name_to_del = False
card_name = ""

@bot.message_handler(func=lambda message: message.text == buttons_admins[3])
async def cards(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None
    global bool_get_card_name
    bool_get_card_name = True
    await bot.send_message(message.chat.id, "Введите название для вашей фото карточки.\n"
                                            "Укажите название файла с <u>расширением!</u>\n"
                                            "Пример: <i>mycard.png</i>",parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text and bool_get_card_name)
async def get_card_name(message):
    global bool_get_card_name, card_name, bool_get_photo_card
    bool_get_photo_card = True
    bool_get_card_name = False
    card_name = message.text.lower()
    await bot.send_message(message.chat.id, "Теперь отправьте фото карточки")

@bot.message_handler(content_types=["photo"])
async def get_card_photo(message):
    global bool_get_photo_card, card_name

    if not bool_get_photo_card:
        return None

    bool_get_photo_card = False

    try:
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        path = "./photo_cards/" + card_name
        with open(path, 'wb') as new_file:
            new_file.write(downloaded_file)

        info = read_file("./photo_cards/files_info.json")

        if card_name not in info.keys():
            info[card_name.lower()] = path
            save_file("./photo_cards/files_info.json", info)
        else:
            await bot.send_message(message.chat.id, f"У вас уже есть файл с таким названием <u>{card_name}</u>",
                                   parse_mode="HTML")
            return None
    except Exception as err:
        logs.set_error_log(str(err), "get card photo")
        await bot.send_message(message.chat.id , "Не удалось скачать отправленный файл\nПопробуйте еще раз")
        return None

    await bot.send_message(message.chat.id, f"Карточка с названием <u>{card_name}</u> добавлена",
                           parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == buttons_admins[4])
async def delete_card(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    info = read_file("./photo_cards/files_info.json")

    if len(info.keys()) > 0:
        await bot.send_message(message.chat.id , "У вас есть следующие карточки")

        for name in info.keys():
            await bot.send_message(message.chat.id , name)

        global bool_get_card_name_to_del
        bool_get_card_name_to_del = True
        await bot.send_message(message.chat.id , "Введите название карточки для удаления")

    else:
        await bot.send_message(message.chat.id , "У вас нет карточек")


@bot.message_handler(func=lambda message: message.text and bool_get_card_name_to_del)
async def complete_delete(message):
    info = read_file("./photo_cards/files_info.json")
    global bool_get_card_name_to_del
    bool_get_card_name_to_del = False

    if message.text.lower() not in info.keys():
        await bot.send_message(message.chat.id, "У вас нет карточки с таким названием")
        return None

    if os.path.exists(info[message.text.lower()]):

        try:
            os.remove(info[message.text.lower()])
        except Exception as err:
            logs.set_error_log(str(err), "complete_delete")
            await bot.send_message(message.chat.id, f"Не удалось удалить карточку с именем <u>{message.text}</u>",
                                   parse_mode="HTML")
            return None

    del info[message.text.lower()]
    save_file("./photo_cards/files_info.json" , info)
    await bot.send_message(message.chat.id , f"Карточка с именем <u>{message.text}</u> удалена",
                           parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == buttons_admins[5])
async def show_cards(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    markup = telebot.types.InlineKeyboardMarkup().add(
        *[
            types.InlineKeyboardButton(text="Фотографии с именами" , callback_data="photo_cards") ,
            types.InlineKeyboardButton(text="Только имена" , callback_data="name_cards")
        ]
    )
    await bot.send_message(message.chat.id, "Как вы хотите получить свои фотографии", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "photo_cards")
async def send_photo_cards(call):
    info = read_file("./photo_cards/files_info.json")

    if len(info.keys()) > 0:
        await bot.send_message(call.message.chat.id , "У вас есть следующие карточки")

        for name in info.keys():

            try:
                await bot.send_photo(call.message.chat.id, open(info[name], "rb"), caption=name)
            except Exception as err:
                logs.set_error_log(str(err), "send photo cards")
                await bot.send_message(call.message.chat.id , f"Не удалось отправить карточку с именем {name}")

        await bot.send_message(call.message.chat.id , "Готово")
    else:
        await bot.send_message(call.message.chat.id , "У вас нет карточек")

@bot.callback_query_handler(func=lambda call: call.data == "name_cards")
async def send_name_cards(call):
    info = read_file("./photo_cards/files_info.json")

    if len(info.keys()) > 0:
        await bot.send_message(call.message.chat.id, "У вас есть следующие карточки")
        for name in info.keys():
            await bot.send_message(call.message.chat.id, name)
        await bot.send_message(call.message.chat.id, "Готово")
    else:
        await bot.send_message(call.message.chat.id , "У вас нет карточек")

"""Key words logic and change prompt"""
word_key = ""
get_word_key = False
get_word_key_to_del = False
get_prompt = False
@bot.message_handler(func=lambda message: message.text == buttons_admins[6])
async def keyword(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    global get_word_key
    get_word_key = True
    await bot.send_message(message.chat.id, "Введите слово-ключ")
@bot.message_handler(func=lambda message: get_word_key)
async def add_keyword(message):
    global word_key
    word_key = message.text
    await bot.send_message(message.chat.id, f"Ваше слово-ключ: <u>{word_key}</u>\nОтправьте теперь файл",
                           parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == buttons_admins[9])
async def change_prompt(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    global get_prompt
    get_prompt = True
    await bot.send_message(message.chat.id, "Хорошо, отправьте промт в формате <u>.txt</u>", parse_mode="HTML")
@bot.message_handler(content_types=['document'])
async def download_document(message):
    global get_word_key , word_key, get_prompt

    if get_word_key:


        get_word_key = False

        try:
            file_info = await bot.get_file(message.document.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            path = "./keywords_files/" + message.document.file_name
            with open(path, 'wb') as new_file:
                new_file.write(downloaded_file)

            info = read_file("./keywords_files/files_info.json")

            if message.document.file_name not in info.keys():
                info[word_key.lower()] = path
                save_file("./keywords_files/files_info.json", info)
            else:
                await bot.send_message(message.chat.id, f"У вас уже есть файл под словом-ключем {word_key}")
                return None

        except Exception as err:
            logs.set_error_log(err, "Can't download key word document")
            await bot.send_message(message.chat.id, "Не удалось скачать отправленый файл\nПопробуйте еще раз")
            return None

        await bot.send_message(message.chat.id, f"Файл с словом ключом <u>{word_key}</u> успешно добавлен",
                               parse_mode="HTML")
    elif get_prompt:
        get_prompt = False

        try:
            file_info = await bot.get_file(message.document.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            path = "./prompt/" + "prompt.txt"

            with open(path , 'wb') as new_file:
                new_file.write(downloaded_file)

        except Exception as err:
            logs.set_error_log(err , "Can't download prompt document")
            await bot.send_message(message.chat.id , "Не удалось скачать отправленый файл\nПопробуйте еще раз")
            return None

        for i in range(3):

            if assistant_ai.set_prompt():
                break

            await bot.send_message(message.chat.id, "Не удалось обновить промт пробуем еще раз")
            await asyncio.sleep(5)

            if i == 2:
                logs.set_error_log("Не удалось обновить промт" , "update promt")
                await bot.send_message(message.chat.id , "Не удалось обновить промт, попробуйте еще раз")
                return None

        await bot.send_message(message.chat.id, "Промт успешно изменен")

@bot.message_handler(func=lambda message: message.text == buttons_admins[7])
async def get_keyword_to_del(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    global get_word_key_to_del

    keys = get_wordkeys()

    await bot.send_message(message.chat.id , "У вас следующие ключи-слова: ")
    for key in keys:
        await bot.send_message(message.chat.id , key)

    get_word_key_to_del = True
    await bot.send_message(message.chat.id, "Введите ключ, который хотите удалить")


@bot.message_handler(func=lambda message: get_word_key_to_del)
async def delete_key(message):
    info = read_file("./keywords_files/files_info.json")
    global get_word_key_to_del
    get_word_key_to_del = False

    if message.text.lower() not in info.keys():
        await bot.send_message(message.chat.id, "У вас нет такого слова-ключа")
        return None

    file_path = info[message.text.lower()]

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as err:
            logs.set_error_log(str(err), "delete_key")
            await bot.send_message(message.chat.id, f"Не удалось удалить ключевое слово {message.text}\nПопробуйте еще раз")
            return None

    del info[message.text.lower()]
    save_file("./keywords_files/files_info.json", info)

    await bot.send_message(message.chat.id, f"Слово-ключ <u>{message.text}</u> было удалено", parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == buttons_admins[8])
async def show_keyword(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    markup = telebot.types.InlineKeyboardMarkup().add(
        *[
            types.InlineKeyboardButton(text="Файлы с именами" , callback_data="files_keyword") ,
            types.InlineKeyboardButton(text="Только имена" , callback_data="name_keyword") #TODO
        ]
    )
    await bot.send_message(message.chat.id , "Как вы хотите получить свои ключи?" , reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "files_keyword")
async def send_files_keywords(call):
    message = call.message

    info = read_file("./keywords_files/files_info.json")
    await bot.send_message(message.chat.id , "У вас следующие ключи-слова: ")
    for key in info.keys():
        await bot.send_message(message.chat.id , f"Ключ: <i>{key}</i>", parse_mode="HTML")
        try:
            await bot.send_document(message.chat.id , open(info[key], 'rb'))
        except Exception as err:
            logs.set_error_log(str(err), "send files of keywords")
            await bot.send_message(message.chat.id, f"Не удалось отправить файл, связанный с ключом: {key}")

    await bot.send_message(message.chat.id, "Готово")


@bot.callback_query_handler(func=lambda call: call.data == "name_keyword")
async def send_names_keywords(call):
    message = call.message

    keys = get_wordkeys()
    await bot.send_message(message.chat.id , "У вас следующие ключи-слова: ")
    for key in keys:
        await bot.send_message(message.chat.id , key)
    await bot.send_message(message.chat.id , "Готово")

@bot.message_handler(func=lambda message: message.text ==buttons_admins[-1])
async def clear_history(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    database.delete_all(assistant_table_name)
    await bot.send_message(message.chat.id, "Готово")



"""Statistic"""
@bot.message_handler(func=lambda message: message.text == buttons_admins[0])
async def get_full_statistic(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2).add(
        *[
            types.InlineKeyboardButton(text="Exel", callback_data="post_exel"),
            types.InlineKeyboardButton(text="Сообщение" , callback_data="post_message"),
            types.InlineKeyboardButton(text="Обнулить статистику" , callback_data="reset_full") ,
        ]
    )

    markup.add(types.InlineKeyboardButton(text="Отмена" , callback_data="cancel"))

    await bot.send_message(message.chat.id, "Выбирите exel, если хотите получить exel таблицу\n"
                                            "Выберите сообщение, если хотите получить статистику в боте.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "post_message")
async def get_full_statistic_in_message(call):
    users = get_full_user_from_db(database, logs)
    answer = "Последняя дата взаимодействия|имя пользователя|ник в тг|телефон\n\n"

    for user in users:
        answer += user[0] + " " + user[1] + " " + user[2] + " " + user[3] + "\n\n"
    if not users:
        await bot.send_message(call.message.chat.id, "Нет взаимодействий")
        return None

    await bot.send_message(call.message.chat.id, answer)

@bot.callback_query_handler(func=lambda call: call.data == "post_exel")
async def get_full_statistic_exel(call):
    users = get_full_user_from_db(database, logs)
    file = Exel().build(users)
    await bot.send_message(call.message.chat.id, "Вот ваша статистика")
    doc = open(file, 'rb')
    await bot.send_document(call.message.chat.id, document=doc)


@bot.message_handler(func=lambda message: message.text == buttons_admins[1])
async def clear_full_statistic(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    try:
        reset_full(database, logs)
        await bot.send_message(message.chat.id , "Готово")
    except Exception as err:
        logs.set_error_log(str(err), "reset_full_statistic")
        await bot.send_message(message.chat.id , "Произошла ошибка во время очистки.\nСмотрите логи для подробностей")
@bot.callback_query_handler(func=lambda call: call.data == "reset_full")
async def reset_full_statistic(call):
    message = call.message

    if not await Admins.is_active_admin(message.from_user.id):
        return None

    try:
        reset_full(database, logs)
        await bot.send_message(message.chat.id , "Готово")
    except Exception as err:
        logs.set_error_log(str(err), "reset_full_statistic")
        await bot.send_message(message.chat.id , "Произошла ошибка во время очистки.\nСмотрите логи для подробностей")

"""Delay"""

get_delay = False
@bot.message_handler(func=lambda message: message.text == buttons_admins[10])
async def change_delay(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None

    global get_delay
    get_delay = True
    await bot.send_message(message.chat.id, f"У вас была задержка {start_delay}-{end_delay} минут\n"
                                            f"Введите новую задержку в формате диапазона:\n"
                                            f"<u>начало-конец</u>",parse_mode="HTML")

@bot.message_handler(func=lambda message: get_delay)
async def set_delay(message):
    global start_delay, end_delay, get_delay
    get_delay = False

    if len(message.text.split("-")) != 2:
        await bot.send_message(message.chat.id, "Не верный формат диапазона\n"
                                                "Корректный формат:\n"
                                                "<u>начало-конец</u>"
                                                "\nПопробуйте еще раз",parse_mode="HTML")
        return False

    start, end = message.text.split("-")
    if start.isdigit() and end.isdigit():
        start_delay = int(start)
        end_delay = int(end)
        await bot.send_message(message.chat.id, "Интервал был изменен")
    else:
        await bot.send_message(message.chat.id , "Вы ввели нечисловое значение или вы вели дробное значение.\n"
                                                 "Значение интервала должно быть целочисленным\n"
                                                 "Попробуйте еще раз" , parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == buttons_admins[14])
async def check_work(message):
    if app:
        try:
            await app.send_message(me, "Привет от бота.\nБот работает")
            await bot.send_message(message.chat.id , "Вам должно прийти сообщение от юзера бота")
        except:
            await bot.send_message(message.chat.id, "Юзер бот не активирован или не работает")
    else:
        await bot.send_message(message.chat.id, "Юзер бот не активирован или не работает")


"""Voice api"""
get_api = False

@bot.message_handler(func=lambda message: message.text == buttons_admins[15])
async def change_api(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None
    global get_api
    get_api = True
    await bot.send_message(message.chat.id, "Введите новое API для обработки голоса:")

@bot.message_handler(func=lambda message: message.text and get_api)
async def set_new_api(message):
    global get_api
    get_api = False

    if Audio.set_api(message.text):
        await bot.send_message(message.chat.id, "Готово")
    else:
        await bot.send_message(message.chat.id, "Не удалось сохранить новый API ключ в файл\n"
                                                "В случае перезагрузки сервера новый API будет утерян\n"
                                                "Попробуйте еще раз\n")


"""BlackList"""
bool_get_blackuser = False
bool_get_black_lista_user_to_del = False
bool_change_nickname = False
admin_message = None # сообщение админа
blackuser_id = 0
black_username = ""
@bot.message_handler(func=lambda message: message.text == buttons_admins[11])
async def black_list(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None
    global bool_get_blackuser, admin_message
    bool_get_blackuser = True
    admin_message = message
    await bot.send_message(message.chat.id, "Перешлите сообщение от пользователя, "
                                            "которого хотите добавить в черный список")


@bot.message_handler(func=lambda message: bool_get_blackuser)
async def add_to_black_list(message):
    global bool_get_blackuser, admin_message, blackuser_id, black_username
    bool_get_blackuser = False

    if is_blacklist(blackuser_id, database):
        await bot.send_message(message.chat.id, "Вы уже добавили этого пользователя в черный список")
        return None

    if message.forward_from.id:
        blackuser_id = message.forward_from.id
        if message.forward_from.username and not database.check_value(f"nickname='{message.text.lower()}'", "black_list"):
            black_username = message.forward_from.username
            markup = telebot.types.InlineKeyboardMarkup().add(
                *[
                    types.InlineKeyboardButton(text="Изменить никнейм" , callback_data="change_nick") ,
                    types.InlineKeyboardButton(text="Сохранить" , callback_data="save_nick")
                ]
            )
            await bot.send_message(message.chat.id, f"У пользователя ник {black_username}", reply_markup=markup)
        else:
            global bool_change_nickname
            bool_change_nickname = True
            await bot.send_message(admin_message.chat.id , "Не удалось получить никнейм пользователя\n"
                                                           "Введите никнейм, под которым выхотите добвить пользователя"
                                                           "в черный список")
    else:
        await bot.send_message(admin_message.chat.id, "Не удалось извлечь id пользователя.\n"
                                                      "Пользователь не добавлен в черный список")


@bot.callback_query_handler(func=lambda call: call.data == "save_nick")
async def confrim_adding_to_black_list(call):
    global blackuser_id, black_username

    if not blackuser_id and black_username:
        return None
    message = call.message
    try:
        database.add_new_items([blackuser_id, black_username.lower()], "id, nickname", "black_list")
        await bot.send_message(message.chat.id, "Пользователь добавлен в черный список")
        blackuser_id = 0
        black_username = ""
    except Exception as err:
        logs.set_error_log(str(err), "get_nick_name")
        await bot.send_message(message.chat.id , "Ошибка\n"
                                                 "Пользователь не добавлен в черный список")

@bot.callback_query_handler(func=lambda call: call.data == "change_nick")
async def change_nick(call):
    global bool_change_nickname, admin_message
    bool_change_nickname = True
    admin_message = None
    await bot.send_message(call.message.chat.id , "Введите никнейм, под которым выхотите добвить пользователя"
                                                   "в черный список")

@bot.message_handler(func=lambda message: message and bool_change_nickname)
async def get_nick_name(message):
    global bool_change_nickname, admin_message, blackuser_id
    bool_change_nickname = False
    admin_message = None

    if database.check_value(f"nickname='{message.text.lower()}'", "black_list"):

        await bot.send_message(message.chat.id, "Пользователь с таким ником уже есть в черном списке\n"
                                                "Начните сначала")
        return None

    if not blackuser_id:
        return None

    try:
        database.add_new_items([blackuser_id, message.text.lower()], "id, nickname", "black_list")
        await bot.send_message(message.chat.id, "Пользователь добавлен в черный список")
        blackuser_id = 0
    except Exception as err:
        logs.set_error_log(str(err), "get_nick_name")
        await bot.send_message(message.chat.id , "Ошибка\n"
                                                 "Пользователь не добавлен в черный список")

@bot.message_handler(func=lambda message: message.text == buttons_admins[12])
async def del_blackuser(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None
    global bool_get_black_lista_user_to_del
    bool_get_black_lista_user_to_del = True
    await bot.send_message(message.chat.id, "Введите ник пользователя, которого хотите удалить:")

@bot.message_handler(func=lambda message: message.text and bool_get_black_lista_user_to_del)
async def complete_del(message):
    global bool_get_black_lista_user_to_del
    bool_get_black_lista_user_to_del = False

    try:
        if not database.check_value(f"nickname='{message.text.lower()}'", "black_list"):
            await bot.send_message(message.chat.id , "Пользователь с таким ником не найден")
            return None
        database.delete_nickname(message.text.lower(), "black_list")
        await bot.send_message(message.chat.id, f"Пользователь с ником <u>{message.text}</u> был удален из черного списка", parse_mode="HTML")
    except Exception as err:
        logs.set_error_log(str(err), "complete_del")
        await bot.send_message(message.chat.id, "Пользователь с таким ником не найден!")


@bot.message_handler(func=lambda message: message.text == buttons_admins[13])
async def show_black_list(message):
    if not await Admins.is_active_admin(message.from_user.id):
        return None
    blacklist = database.get_all("black_list")

    if blacklist:
        for user in blacklist:
            await bot.send_message(message.chat.id, f"{user[-1]}")
        await bot.send_message(message.chat.id, "Готов")
    else:
        await bot.send_message(message.chat.id, "Список пуст")


"""logs"""
@bot.message_handler(commands=["logs"])
async def set_logs(message):
    await bot.send_document(message.chat.id, logs.get_error_logs())
    await bot.send_document(message.chat.id, logs.get_sending_logs())


@bot.message_handler(commands=["disable_logs"])
async def disable_logs(message):
    logs.disable_logs()
    await bot.send_message(message.chat.id, "Логи отключены")


@bot.message_handler(commands=["enable_logs"])
async def enable_logs(message):
    logs.enable_logs()
    await bot.send_message(message.chat.id , "Логи включены")


@bot.message_handler(commands=["clear_logs"])
async def clear_logs(message):
    logs.clear_logs()
    await bot.send_message(message.chat.id , "Логи очищены")


"""Start"""
async def start_bot():

    if os.path.exists("./Current-session.session") and os.path.exists("./user-bot.json"):
        await asyncio.gather(bot.polling(request_timeout=90) , get_code(None, True, False))
    else:
        await bot.polling(request_timeout=90)


asyncio.run(start_bot())
