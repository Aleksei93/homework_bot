import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from exceptions import ErorrAPI

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


current_timestamp = 0
timestamp = 0
params = {'from_date': timestamp}
response = requests.get(ENDPOINT, headers=HEADERS, params=params).json()
spisok_dz = response['homeworks'][0]['status']
print (spisok_dz )

verdict = HOMEWORK_STATUSES[spisok_dz]

message = f'Статус последнего задания {verdict}'

bot = telegram.Bot(token=TELEGRAM_TOKEN)
bot.send_message(TELEGRAM_CHAT_ID, text=message)
