import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

handler = logging.StreamHandler(sys.stdout)

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
        raise logging.critical('Отсутствует одна из переменных окружения')


def send_message(bot, message):
    """Отправка сообщения в бот."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение доставлено успешно')
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')


def get_api_answer(timestamp):
    """Запрос API."""
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if homeworks.status_code == 200:
        return homeworks.json()
    requests.RequestException
    logging.exception()


def check_response(response):
    """Проверка API."""
    if 'homeworks' not in response:
        raise TypeError
    if not isinstance(response['homeworks'], list):
        raise TypeError
    response = response['homeworks']
    return response


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' not in homework:
        raise ValueError('Ключ "homework_name" отсутствует')
    homework_name = homework['homework_name']
    print(homework_name)
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError('Ключ "homework_status" отсутствует')
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
            homework = check_response(response)[0]
            message = parse_status(homework)
            if message != last_message:
                send_message(bot, message)
            else:
                logging.debug('Статус домашней работы не изменился')
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
