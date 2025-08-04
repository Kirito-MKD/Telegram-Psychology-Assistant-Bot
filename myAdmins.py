from telebot.async_telebot import AsyncTeleBot
import os


class MyAdmins():
    def __init__(self, logs: object, bot:AsyncTeleBot):
        self.logs = logs
        self.bot = bot
        self.active_admins = self._read_admins()

    def _read_admins(self) -> list:

        if os.path.exists("./admins/admins.txt"):
            with open("./admins/admins.txt", "r", encoding="utf-8") as file:
                admins = file.read().split(";")
        else:
            with open("./admins/admins.txt") as file:
                file.write("")
            admins = []

        return admins


    def register_admin(self, id: int):
        self.active_admins.append(str(id))

        if os.path.exists("./admins/admins.txt"):

            with open("./admins/admins.txt", "a", encoding="utf-8") as file:
                file.write(str(id)+";")

        else:
            self.logs.set_error_log("There's not admins.txt", "register_admin")
            self._read_admins()

    async def _send_mes(self,id, message_to_send:str):
        try:
            await self.bot.send_message(id , message_to_send)
        except Exception as err:
            self.logs.set_error_log(str(err) , "_send_mes")

    async def is_active_admin(self, id: int, mute_mode:bool=False) -> bool:
            if str(id) in self.active_admins:
                return True
            else:
                if not mute_mode:
                    await self._send_mes(id, "Вы не авторизовались введите /login")

            return False


    async def notify_active_admins(self, notification_message: str):

        for admin in self.active_admins:
            if admin:
                await self._send_mes(admin, notification_message)