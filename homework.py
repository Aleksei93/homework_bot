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
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
    '': 'статус для работы не назначен'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info('Бот отправил сообщение')
    except telegram.error.TelegramError(message):
        logger.error('Сообщение не отправлено !')
        raise Exception('Сообщение не отправлено !')


def get_api_answer(current_timestamp):
    """делает запрос к  эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logging.exception('Запрос от сервера не получен.')
        raise ErorrAPI('Запрос от сервера не получен.')
    if response.status_code != HTTPStatus.OK:
        raise ErorrAPI('Сервер практикума не доступен')
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logging.error('Тип  API не словарь')
        raise ErorrAPI('Тип  API не словарь')
    if 'homeworks' not in response:
        logging.error('Ответ API не содержит homeworks')
        raise KeyError('Ключ не содержит homeworks')
    if 'current_date' not in response:
        logging.error('Ответ API не содержит current_date')
        raise KeyError('Ключ не содержит current_date')
    if type(response['homeworks']) is not list:
        logging.error('Получен неправильный тип')
        raise Exception('Список отсуствует')
    return response['homeworks'][0]


def parse_status(homework):
    """Извлекает из информации о  домашней работе статус."""
    try:
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception:
        logging.exception('Неисзвестный статус.')
        raise KeyError('Неисзвестный статус ')

    return f'Изменился статус проверки работы. {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key, value in tokens.items():
        if value is None:
            logger.critical(f'Отсутствует переменная окружения {key}.')
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_message = ''
    errors = True

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message != prev_message:
                prev_message = message
                send_message(bot, message)
                current_timestamp = response['current_date']
            else:
                current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            send_message(bot, 'Сбой в работе программы')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
