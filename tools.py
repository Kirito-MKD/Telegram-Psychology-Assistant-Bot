from telebot import types
import datetime
import json
import os
from fuzzywuzzy import fuzz
from random import randint


buttons_admins = [
    "Статистика",
    "Очистить статистику",
   "Изменить/активировать юзер аккаунт",
    "Добавить карту к игре",
    "Удалить карту к игре",
    "Мои карточки",
    "Добавить новое ключ-слово",
    "Удалить ключ-слово",
    "Мои слова-ключи",
    "Изменить промт",
    "Изменить задержку для пользователей",
    "Добавить пользователя в черный список",
    "Удалить пользователя из черного списка",
    "Показать пользователей в черном списке",
    "Проверить работу бота",
    "Изменить api для обработки голоса",
    "Очистить историю",
]


def create_user_menu(messages: list) -> "types.ReplyKeyboardMarkup":
    """Создает клавиатуру (которая располагается под полем ввода сообщений пользователя) с кнопками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)  # создания клавиатуры для ответов

    for text in messages:
        button = types.KeyboardButton(text)
        keyboard.add(button)

    return keyboard


def get_time(str_mode: bool = True) -> str or datetime.datetime:
    utc_time = datetime.datetime.utcnow()
    tz_modifier = datetime.timedelta(hours=3)
    tz_time = utc_time + tz_modifier
    if str_mode:
        return tz_time.strftime("%Y-%m-%d %H:%M:%S")

    return tz_time
def read_file(file_name: str) -> dict:

    try:
        with open(file_name, "r", encoding="utf-8") as file:
            with open(file_name) as file:
                data = json.load(file)

            return data
    except Exception as _:
        return {}


def save_file(file_name: str, data:dict) -> bool:
    try:
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file)

    except Exception as err:
        return False

    return True

def get_wordkeys() -> list:
    key_words = []

    if not os.path.exists("./keywords_files/files_info.json"):
        with open("./keywords_files/files_info.json", "w") as file:
            json.dump({} , file)
        return []

    for key in read_file("./keywords_files/files_info.json"):
        key_words.append(key)

    return key_words


def get_full_user_from_db(database, logs) -> list["date", "first_name", "nickname", "phone"]:
    """user[0]-date user[1]-first_name user[2]-username user[3]-phone user[4]-type(sub/unsub)"""
    users = []

    try:
        for user in database.get_all("statistic"):
            users.append([user[0], user[1], user[2], user[3]])
    except Exception as err:
        logs.set_error_log(str(err) , "get statistic from db")

    return users


def reset_full(database, logs):
    try:
        database.delete_all("statistic")
    except Exception as err:
        logs.set_error_log(str(err) , "reset statistic")


def add_to_statistic(database, date, first_name, nickname, phone, type, id, logs=""):
    database.delete_id(id , "statistic")

    try:
        database.add_new_items([date , first_name, nickname, phone, type, id,] , "date, first_name, user_name, phone,type, id", "statistic")
    except Exception as err:
        if logs:
            logs.set_error_log(str(err) , "add user to Db")
        return False

    return True

def check_key_word(event) -> bool:
    info = read_file("./keywords_files/files_info.json")

    for key in info.keys():

        if fuzz.ratio(event.message.text.lower(), key) >= 75:
            return True

    else:
        return False


def is_blacklist(id: int, database) -> bool:
    res = database.get_certain(f"id={id}", "black_list")

    if res:
        return True

    return False

def get_user(user) -> ["name", "user_name", "phone"]:
    return [
        user.first_name if user.first_name else "",
        user.username if user.username else "",
        user.phone if user.phone else "",]


def decode(code: str) -> str:
    alphabet_numbers = {
        'a': '0' ,
        'b': '1' ,
        'c': '2' ,
        'd': '3' ,
        'e': '4' ,
        'f': '5' ,
        'g': '6' ,
        'h': '7' ,
        'i': '8' ,
        'j': '9'
    }
    new_code = ""
    for letter in code:
        new_code += alphabet_numbers[letter]

    return new_code


def generate_delay(start:int, end: int) -> int:
    return randint(min([start, end]), max([start, end]))