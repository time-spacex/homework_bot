import os
import sys
import time
import logging
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import InvalidResponseStatusException, MissingTokenException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверки доступности необходимых переменных окружения."""
    error_message = 'Недоступна необходимая для работы переменная окружения: '
    env_data: dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens = [name for name, token in env_data.items() if not token]
    if missing_tokens:
        error_message += ', '.join(missing_tokens)
        logging.critical(error_message)
        raise MissingTokenException(error_message)


def send_message(bot, message):
    """Функция отправки сообщений в Telegram."""
    try:
        logging.debug('Начало отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Удачная отправка сообщения в Telegram: {message}')
    except telegram.TelegramError:
        logging.error('Сбой при отправке сообщения в Telegram.')


def get_api_answer(timestamp):
    """Функция возвращает ответ от API сервиса Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        logging.debug(
            'Начало запроса к API Практикум.Домашка, '
            f'ENDPOINT: {ENDPOINT}, parameters: {payload}'
        )
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        error_message = (
            f'Недоступность эндпоинта: {ENDPOINT}, '
            f'статус: {response.status_code}, '
            f'причина: {response.reason}'
        )
        if response.status_code != HTTPStatus.OK:
            raise InvalidResponseStatusException(error_message)
        logging.debug('Успешное завершение запроса к API Практикум.Домашка')
        return response.json()
    except requests.RequestException:
        raise ConnectionError(error_message)


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    logging.debug('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError(f'ответ от API не является словарем: {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if 'current_date' not in response:
        raise KeyError('Отсутствует ключ "current_date" в ответе API')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Тип данных в ключе "homeworks" в ответе API не является списком: '
            f'{type(response.get("homeworks"))}'
        )
    logging.debug('Успешное окончание проверки ответа API')


def parse_status(homework):
    """Функция проверки статуса сданной домашней работы."""
    logging.debug('Начало проверки статуса домашней работы')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_name:
        raise KeyError(
            'Отсутствует ключ с названием домашней работы "homework_name"'
        )
    if not homework_status:
        raise KeyError('Отсутствует ключ со статусом домашней работы "status"')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            'Ключ со статусом работы не соответствует документации: '
            f'{homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.debug('Успешное окончание проверки статуса домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework_status = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                homework = response.get('homeworks')[0]
                message = parse_status(homework)
                send_message(bot, message)
                homework_status = message
                timestamp = int(time.time())
            else:
                logging.debug('Отсутствие в ответе новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if homework_status != message:
                send_message(bot, message)
                homework_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.StreamHandler(sys.stdout)
    logging.basicConfig(
        level=logging.DEBUG,
        filename='output.log',
        format=(
            '%(asctime)s, '
            '%(levelname)s, '
            '%(funcName)s, '
            '%(lineno)d, '
            '%(message)s, '
            '%(name)s'
        ),
        encoding='utf-8'
    )
    main()
