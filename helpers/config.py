import configparser
import ujson
import os

is_dev = bool(os.getenv('dev', False))
bot_token = os.getenv("bot_token")
replicate_key = os.getenv("replicate_key")
weather_key = os.getenv("weather_key")
tts_key = os.getenv("tts_key")
assemblyai_key = os.getenv("assemblyai_key")
openai_key = os.getenv("openai_key")
gigachat_secret = os.getenv("gigachat_secret")
hugging_cookie = os.getenv("hugging_cookie")
web_url = os.getenv("web_url")
success_vid = os.getenv("success_vid")
admin_chat = int(os.getenv("admin_chat"))
together_token = None

mysql_server = os.getenv("mysql_server")
mysql_user = os.getenv("mysql_user")
mysql_password = os.getenv("mysql_pw")

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_BIRTHDAY_HOUR: int = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
random_ans: list[str] = ujson.loads(config["Settings"]['random_ans'])
calls: list[str] = ujson.loads(config["Settings"]['calls'])
calls_private: list[str] = ujson.loads(config["Settings"]['calls_private'])
ends: list[str] = ujson.loads(config["Settings"]['ends'])
