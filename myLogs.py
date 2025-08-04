import datetime

class Mylogs():

    def _write_message(self, message, path):
        with open(path, "a+", encoding="utf-8") as file:
            file.write(message)

    def _get_time(self) -> str:
        utc_time = datetime.datetime.utcnow()
        tz_modifier = datetime.timedelta(hours=3)
        tz_time = utc_time + tz_modifier
        return tz_time.strftime("%Y-%m-%d %H:%M:%S")

    def clear_logs(self):
        with open(self.error_log_path , "w") as f:
            f.write(self._get_time() + " -- " + self.session + "\n")

        with open(self.sending_log_path , "w") as f:
            f.write(self._get_time() + " -- " + self.session + "\n")

    def __init__(self, session):
        self.session = session
        self.sending_log_path = "logs/sending_logs.txt"
        self.error_log_path = "logs/error_logs.txt"
        self.clear_logs()
        self.enable = True

    def set_sending_log(self, id, first_name:str):
        if self.enable:
            log = f"{self._get_time()} -- sending message to user {first_name}|{id}\n"
            self._write_message(log, self.sending_log_path)

    def set_error_log(self, err, block_code):
        if self.enable:
            log = f"{self._get_time() } -- error occured in {block_code}: {err}\n"
            self._write_message(log, self.error_log_path)

    def get_error_logs(self) -> "IO":
        doc = open(self.error_log_path, 'rb')
        return doc

    def get_sending_logs(self) -> "IO":
        doc = open(self.sending_log_path , 'rb')
        return doc

    def disable_logs(self):
        self.enable = False

    def enable_logs(self):
        self.enable = True