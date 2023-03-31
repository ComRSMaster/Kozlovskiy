import configparser
import json
import os

is_dev = bool(os.getenv('dev', False))
bot_token = os.getenv("Kozlovskiy_token")
replicate_key = os.getenv("replicate_key")
weather_key = os.getenv("weather_key")
tts_key = os.getenv("tts_key")
web_url = os.getenv("web_url")

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
admin_chat = json.loads(config["Settings"]['admin_chat'])
success_vid = json.loads(config["Settings"]['success_vid_DEV' if is_dev else 'success_vid'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
