#!/usr/bin/env python
from ast import literal_eval
import json
import aiohttp

class MyDeepSeek():
    def __init__(self, logs, database:object, table_n: str, model:str, api_key:str):
        self.api = api_key
        self.model = model
        self.logs = logs
        self.database = database
        self.table_name = table_n
        self.path_prompt = "./prompt/" + "prompt.txt"
        self.prompt = []
        self._read_prompt()
    async def get_answer(self, id: int, text:str="") -> str:

        is_dialog = False
        message_history = []

        if self._check_dialog(id):
            is_dialog = True
            message_history = self._get_history(id)

            if not message_history:
                return ""

        message_history.append({"role": "user" , "content":text})

        # send to mistral
        headers = {
            "Authorization": f"Bearer {self.api}" ,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model ,
            "messages": self.prompt + message_history ,
            "stream": False,
            "temperature": 0.7
        }

        json_data = json.dumps(data)
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post("https://openrouter.ai/api/v1/chat/completions",headers=headers, data=json_data)
                if response.status != 200:
                    print("Ошибка API:" , response.status)
                    self.logs.set_error_log("Error api", "get response")
                    return "200"
                answer = await response.json()
                agent_message = answer["choices"][0]["message"]["content"]


        except Exception as err:
            self.logs.set_error_log(str(err) , "get answer from deepseek\n" + str(agent_message))
            return "404"

            # Перенос строки после завершения потока

        if not agent_message:
            self.logs.set_error_log("Не удалось получить ответ от нейросети", "get answer from deepseek")
            return "404"

        message_history.append({"role": "assistant" , "content": agent_message})

        if is_dialog:
            self._update_history(message_history, id)
        else:
            self._add_new_user(message_history, id)

        return agent_message

    def _get_history(self, id) -> list:
        try:
            history = self.database.get_certain(f"id={id}",self.table_name)
            history = literal_eval(history[0][1])
            return history
        except Exception as err:
            self.logs.set_error_log(str(err) , "get history DB")
            return []
    def _process_content(self, content: str) -> str:
        return content.replace('<think>' , '').replace('</think>' , '')


    def _read_prompt(self) -> bool:

        try:
            with open(self.path_prompt, encoding="utf-8") as f:
                our_instruction = f.read()
        except Exception as err:
            self.logs.set_error_log(str(err), "Cant read a promt")
            return False

        self.prompt.clear()
        self.prompt = [{"role": "system", "content": our_instruction}]
        return True

    def set_prompt(self) -> bool:
        return self._read_prompt()

    def _check_dialog(self, id: int) -> bool:
        try:
            return self.database.check_value(f"id={id}", self.table_name)
        except Exception as err:
            self.logs.set_error_log(str(err) , "check value DB")

    def _update_history(self, his: list, id: int):
        his = str(his)
        try:
            self.database.update_value("history", his, "id", str(id), self.table_name)
        except Exception as err:
            self.logs.set_error_log(str(err) , "update chat history")

        activity = int(self.database.get_certain(f"id={id}" , self.table_name)[0][-1]) + 1

        try:
            self.database.update_value("active" , activity , "id" , str(id) , self.table_name)
        except Exception as err:
            self.logs.set_error_log(str(err) , "update chat history")

    def _add_new_user(self, history: list, id: int):
        history = str(history)

        try:
            self.database.add_new_items([id, history, 1], "id, history, active", self.table_name)
        except Exception as err:
            self.logs.set_error_log(str(err) , "update chat history")
