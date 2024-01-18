import os
import sys
import time
import logging

import requests
import telegram
from dotenv import load_dotenv

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

logging.basicConfig(
    level=logging.DEBUG,
    filename='output.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


class CustomException(Exception):
    """Класс для вызова кастомного исключения."""

    pass


def check_tokens():
    """Функция проверки доступности необходимых переменных окружения."""
    error_message = 'Недоступна необходимая для работы переменная окружения: '
    env_data: dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name, variable in env_data.items():
        if not variable:
            logger.critical(error_message + name)
            raise CustomException(
                error_message + name
            )


def send_message(bot, message):
    """Функция отправки сообщений в Telegram."""
    try:
        logger.debug('Удачная отправка сообщения в Telegram: ' + message)
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        error_message = 'Сбой при отправке сообщения в Telegram: '
        logger.error(error_message + str(error))
        raise CustomException(error_message + str(error))


def get_api_answer(timestamp):
    """Функция возвращает ответ от API сервиса Практикум.Домашка."""
    headers = {'Authorization': 'OAuth {}'.format(PRACTICUM_TOKEN)}
    payload = {'from_date': timestamp}
    error_message = 'Недоступность эндпоинта: ' + ENDPOINT
    try:
        response = requests.get(ENDPOINT, headers=headers, params=payload)
        if response.status_code != 200:
            logger.error(error_message)
            raise CustomException(error_message)
        return response.json()
    except Exception as error:
        logger.error(error_message + str(error))
        raise CustomException(error_message + str(error))


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    error_message = 'Отсутствуют ожидаемые ключи в ответе API'
    if (
        'homeworks' in response
        and isinstance(response, dict)
        and isinstance(response.get('homeworks'), list)
    ):
        return response
    else:
        logger.error(error_message)
        raise TypeError(error_message)


def parse_status(homework):
    """Функция проверки статуса сданной домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if (
        homework_status
        and (homework_status in HOMEWORK_VERDICTS)
        and homework_name
    ):
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        error_message = 'Неожиданный статус домашней работы в ответе API: '
        logger.error(error_message + homework_status)
        raise CustomException(error_message + homework_status)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homework_status = None
    while True:
        try:
            response = check_response(get_api_answer(timestamp))
            if response.get('homeworks'):
                homework = response.get('homeworks')[0]
                message = parse_status(homework)
                actual_status = homework.get('status')
                if actual_status != homework_status:
                    send_message(bot, message)
                    homework_status = actual_status
                else:
                    logger.debug('Отсутствие в ответе новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            raise Exception(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
