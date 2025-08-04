import soundfile as sf   #   pip install pysoundfile
import os
import assemblyai as aai


class AudioReader():
    def __init__(self, logs:object):
        self.api = self._read_api()
        self.logs = logs

    def _read_api(self)->str:

        if os.path.exists("./audio_api.txt"):
            with open("./audio_api.txt", "r", encoding="utf-8") as file:
                api = file.read()
        else:
            self.logs.set_error_log("There's not file with audio api")

            with open("./audio_api.txt", "w", encoding="utf-8") as file:
                file.write("")

            api = ""

        return api

    def set_api(self, new_api: str) -> bool:
        """Return false when can't write api in file"""
        self.api = new_api

        try:
            with open("./audio_api.txt", "w", encoding="utf-8") as file:
                file.write(new_api)

        except Exception as err:
            self.logs.set_error_log(str(err), "set_api")
            return False

        return True

    async def convert_ogg_to_wav(self, file_name: str) -> bool:

        try:
            data , samplerate = sf.read(f"./voices/{file_name}")
            sf.write(f"./voices/{file_name.replace('.ogg' , '.wav')}" , data , samplerate)
        except Exception as err:
            print(err)
            self.logs.set_error_log(str(err) , "convert ogg to wav")
            return False

        try:
            os.remove(f"./voices/{file_name}")
        except Exception as err:
            self.logs.set_error_log(str(err) , "NOT CRITICAL. can't delete file " + file_name)

        return True

    async def convert_audio_to_text(self, file_name: str) -> str:

        if not self.api:
            self.logs.set_error_log("audio api is empty", "convert_audio")
            return ""

        if not os.path.exists(f"./voices/{file_name}"):
            self.logs.set_error_log("file does not exists" , "convert audio to text")
            return ""

        if not await self.convert_ogg_to_wav(file_name):
            return ""

        file_name = file_name.replace('.ogg' , '.wav')

        try:
            aai.settings.api_key = self.api
            config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.nano , language_code="ru")
            transcriber = aai.Transcriber(config=config)
        except Exception as err:
            print(err)
            self.logs.set_error_log(str(err) , "connection to server aai")
            return ""

        try:
            transcript = transcriber.transcribe(f"./voices/{file_name}")
            result = transcript.text
        except Exception as err:
            print(err)
            self.logs.set_error_log(str(err) , "getting file from aai")
            return ""

        if os.path.exists(f"./voices/{file_name}"):
            try:
                os.remove(f"./voices/{file_name}")
            except Exception as err:
                print(err)
                self.logs.set_error_log(str(err) , "cant delete audio file")

        return result



