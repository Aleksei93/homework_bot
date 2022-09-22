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


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError(message):
        logger.error('Сообщение не отправлено !')


def get_api_answer(current_timestamp):
    """делает запрос к  эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logging.exception('Запрос от сервера не получен.')
    if response.status_code != HTTPStatus.OK:
        raise ErorrAPI('Сервер практикума не доступен')
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    if type(response) is not dict:
        logging.error('Тип  API не словарь')
        raise TypeError('Тип  API не словарь')
    if 'homeworks' not in response:
        logging.error('Ответ API не содержит homeworks')
        raise KeyError('Ключа не содержит homeworks')
    if type(response['homeworks']) is not list:
        logging.error('Получен неправильный тип')
        raise Exception('Список отсуствует')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о  домашней работе статус."""
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        raise KeyError('API не имеет ключ "homework_name" ')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception:
        logging.exception('Неисзвестный статус.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    variables = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for variable in variables:

        if not variable:
            logger.critical(
                f' Переменной {variable} не найдено. Бот приостанолен.')
            return False

    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_upd_time = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_list = check_response(response)
            for homework in hw_list:
                upd_time = homework.get('date_updated')

                if upd_time != prev_upd_time:
                    prev_upd_time = upd_time
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = int(time.time())

        except Exception:
            logging.exception('Сбой в работе программы')
            message = 'Сбой в работе программы'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
