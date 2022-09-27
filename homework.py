import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import BadRequestError, ErorrAPI, WrongAnswerApiError

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
        raise ErorrAPI('Сообщение не отправлено !')


def get_api_answer(current_timestamp):
    """делает запрос к  эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        else:
            raise WrongAnswerApiError('Сервер практикума не доступен')
    except Exception as error:
        raise BadRequestError(f'Ошибка получения request, ошибка: {error}')


def check_response(response):
    """проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Тип  API не словарь')
    if 'homeworks' not in response:
        raise KeyError('Ключ  не содержит homeworks')
    if 'current_date' not in response:
        raise KeyError('Ключ  не содержит current_date')
    if not isinstance(response['homeworks'], list):
        raise Exception('Список отсуствует')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о  домашней работе статус."""
    if not homework:
        raise ErorrAPI('Словарь homeworks пуст')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует Ключ homework_name')
    if 'status' not in homework:
        raise KeyError('Отсуствует Ключ status')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'{homework_status} отсутствует в словаре verdicts')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_message = ''
    old_status = ''

    while True:
        try:
            if not isinstance(current_timestamp, int):
                raise ErorrAPI('формат current_timestamp не чило')
            response = get_api_answer(current_timestamp)
            response_time = response['current_date'] or int(time.time())
            response = check_response(response)

            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status != old_status:
                    old_status = homework_status
                    send_message(bot, homework_status)
            else:
                logger.info('нет новых статусов')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                old_message = message
        finally:
            current_timestamp = response_time
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
