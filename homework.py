import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

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
    """Проверка токенов."""
    if (PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID) is None:
        raise logger.critical('Отсутствует одна из переменных окружения')


def send_message(bot, message):
    """Отправка сообщения в бот."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение доставлено успешно')
    except telegram.TelegramError as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')


def get_api_answer(timestamp):
    """Запрос API."""
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.exceptions.Timeout:
        raise KeyError('Вышло время ожидания запроса')
    except requests.exceptions.HTTPError:
        raise KeyError('Неверный URL-адрес')
    except requests.exceptions.RequestException:
        raise KeyError('Критическая ошибка')
    if homeworks.status_code == HTTPStatus.OK:
        try:
            return homeworks.json()
        except JSONDecodeError:
            print("Ответ API не преобразовался в JSON")
    logger.exception()


def check_response(response):
    """Проверка ответа API."""
    if 'homeworks' not in response:
        raise TypeError('Ключ "homeworks" отсутствует в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Список домашних работ пришёл не в виде списка')
    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' not in homework:
        raise ValueError('Ключ "homework_name" отсутствует в словаре homework')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise ValueError('Ключ "status" отсутствует в словаре homework')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError(
            'Ключ "homework_status" отсутствует в словаре HOMEWORK_VERDICTS')
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS[homework_status]
    if verdict is None:
        logging.exception()
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            try:
                homework = check_response(response)[0]
            except requests.exceptions.Timeout:
                raise KeyError('Список домашних работ пуст')
            message = parse_status(homework)
            if message != last_message:
                send_message(bot, message)
            else:
                logging.debug('Статус домашней работы не изменился')
            timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
