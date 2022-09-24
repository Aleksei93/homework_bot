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
    """Отправка сообщения в Телегу."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешная отправка сообщения.')
    except Exception as error:
        raise SystemError(f'Не отправляются сообщения, {error}')


def get_api_answer(current_timestamp):
    """запрос статуса домашней работы."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except Exception as error:
        raise SystemError(f'Ошибка получения request, {error}')
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            logger.info('успешное получение Эндпоинта')
            homework = homework_statuses.json()
            if 'error' in homework:
                raise SystemError(f'Ошибка json, {homework["error"]}')
            elif 'code' in homework:
                raise SystemError(f'Ошибка json, {homework["code"]}')
            else:
                return homework
        elif homework_statuses.status_code == HTTPStatus.REQUEST_TIMEOUT:
            raise SystemError(f'Ошибка код {homework_statuses.status_code}')
        elif homework_statuses.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            raise SystemError(f'Ошибка код {homework_statuses.status_code}')
        # не понимаю зачем проверять отдельно 408 и 500, если всё попадёт в
        # else. не проходили тесты, пока не добавил
        else:
            raise SystemError(
                f'Недоступен Эндпоинт, код {homework_statuses.status_code}')


def check_response(response):
    """проверка ответа на корректность."""
    if type(response) == dict:
        response['current_date']
        # -------------------замечание------------------------------
        # если в ответе не окажется ключа 'homeworks', то упадём тут с ошибкой
        # -------------------ответ------------------------------
        # не упадёт с ошибкой, а выпадет в except функции main()
        # сделал осознано, чтобы не городить условия проверки из if-else
        # в задании обозначена необходимость проверки этих ключей
        homeworks = response['homeworks']
        if type(homeworks) == list:
            return homeworks
        else:
            raise SystemError('Тип ключа homeworks не list')
    else:
        raise TypeError('Ответ от Домашки не словарь')


def parse_status(homework):
    """Парсинг информации о домашке."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_name is not None and homework_status is not None:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return ('Изменился статус проверки '
                    + f'работы "{homework_name}". {verdict}')
        else:
            raise SystemError('неизвестный статус')
    else:
        raise KeyError('нет нужных ключей в словаре')


def check_tokens():
    """Проверка доступности необходимых токенов."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical('Ошибка импорта токенов Telegramm.')
        return False
    elif not PRACTICUM_TOKEN:
        raise SystemError('Ошибка импорта токенов Домашки.')
    else:
        return True


def main():
    """Бот для отслеживания статуса домашки на Яндекс.Домашка."""
    global old_message
    if not check_tokens():
        raise SystemExit('Я вышел')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME

    while True:
        try:
            if type(current_timestamp) is not int:
                raise SystemError('В функцию передана не дата')
            response = get_api_answer(current_timestamp)
            response = check_response(response)

            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status is not None:
                    send_message(bot, homework_status)
            else:
                logger.debug('нет новых статусов')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                old_message = message
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()