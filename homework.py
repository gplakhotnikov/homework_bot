import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import TokenValidationError, ResponseError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    """Функция отпровляет сообщение пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except telegram.TelegramError:
        logging.error('Бот не смог отправить сообщение')


def get_api_answer(current_timestamp):
    """Функция получает ответ от эндпоинта."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code == HTTPStatus.OK:
        return homework_statuses.json()
    else:
        logging.error('Эндпоинт недоступен')
        send_message(telegram.Bot(token=TELEGRAM_TOKEN), 'Эндпоинт недоступен')
        raise ResponseError('Эндпоинт недоступен')


def check_response(response):
    """Функция проверяет ответ от эндпоинта."""
    if 'homeworks' in response and isinstance(response.get('homeworks'), list):
        return response.get('homeworks')
    else:
        logging.error('Ошибка в возвращаемой API информации')
        send_message(telegram.Bot(token=TELEGRAM_TOKEN),
                     'Ошибка в возвращаемой API информации')
        raise TypeError('Ошибка в возвращаемой API информации')


def parse_status(homework):
    """Функция возвращает обработанный ответ от эндпоинта."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Неизвестный статус домашней работы')
        send_message(telegram.Bot(token=TELEGRAM_TOKEN),
                     'Неизвестный статус домашней работы')
        raise KeyError('Неизвестный статус домашней работы')


def check_tokens():
    """Функция проверяет валидность токенов."""
    if (PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
            or TELEGRAM_CHAT_ID is None):
        return False
    else:
        return True


def main():
    """Главная функция: отправляет и проверяет запрос API.
    В случае успеха посылает сообщение через бот.
    """
    api_error = False
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        raise TokenValidationError('Проверьте корректность токенов')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('В ответе нет новых статусов')
            for homework in homeworks:
                status = parse_status(homework)
                send_message(bot, status)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Ошибка при запросе к API: {error}'
            logging.error(message)
            if not api_error:
                send_message(bot, message)
                api_error = True
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
