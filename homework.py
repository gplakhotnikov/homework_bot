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
ENV_ERROR = 'Отсутствует обязательная переменная окружения'
NO_NEW = 'В ответе нет новых статусов'
API_ERROR = 'Ошибка при запросе к API'
API_UNAVAILABLE = 'Эндпоинт недоступен'
NOT_JSON = 'Ответ возвращен не в формате JSON'
WRONG_VALUE = 'Ошибка в возвращаемой API информации'
STATUS_CHANGE = 'Изменился статус проверки работы'
STATUS_UNKNOWN = 'Неизвестный статус домашней работы'
MESSAGE_SENT = 'Сообщение успешно отправлено'
MESSAGE_NOT_SENT = 'Бот не смог отправить сообщение'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    """Функция отпровляет сообщение пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(MESSAGE_SENT)
    except telegram.TelegramError:
        logging.error(MESSAGE_NOT_SENT)


def get_api_answer(current_timestamp):
    """Функция получает ответ от эндпоинта."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.RequestException:
        logging.error(API_ERROR)
        raise ResponseError(API_ERROR)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(API_UNAVAILABLE)
        raise ResponseError(API_UNAVAILABLE)
    try:
        return homework_statuses.json()
    except ValueError:
        logging.error(NOT_JSON)
        raise ValueError(NOT_JSON)


def check_response(response):
    """Функция проверяет ответ от эндпоинта."""
    if 'homeworks' in response and isinstance(response['homeworks'], list):
        return response.get('homeworks')
    logging.error(WRONG_VALUE)
    raise TypeError(WRONG_VALUE)


def parse_status(homework):
    """Функция возвращает обработанный ответ от эндпоинта."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'{STATUS_CHANGE} "{homework_name}". {verdict}'
    logging.error(STATUS_UNKNOWN)
    raise KeyError(STATUS_UNKNOWN)


def check_tokens():
    """Функция проверяет валидность токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Главная функция: отправляет и проверяет запрос API.
    В случае успеха посылает сообщение через бот.
    """
    if not check_tokens():
        logging.critical(ENV_ERROR)
        raise TokenValidationError(ENV_ERROR)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(NO_NEW)
            for homework in homeworks:
                status = parse_status(homework)
                send_message(bot, status)
            current_timestamp = int(time.time())
        except Exception as error:
            send_message(bot, str(error))
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
