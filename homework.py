import logging
import os
import requests
import telegram
import time
from urllib.error import URLError
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
MESSAGES = {
    'env_error': 'Отсутствует обязательная переменная окружения',
    'no_new': 'В ответе нет новых статусов',
    'API_error': 'Ошибка при запросе к API',
    'API_unavailable': 'Эндпоинт недоступен',
    'not_JSON': 'Ответ возвращен не в формате JSON',
    'wrong_value': 'Ошибка в возвращаемой API информации',
    'status_change': 'Изменился статус проверки работы',
    'status_unknown': 'Неизвестный статус домашней работы',
    'message_sent': 'Сообщение успешно отправлено',
    'message_not_sent': 'Бот не смог отправить сообщение',
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    """Функция отпровляет сообщение пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(MESSAGES['message_sent'])
    except telegram.TelegramError:
        logging.error(MESSAGES['message_not_sent'])


def get_api_answer(current_timestamp):
    """Функция получает ответ от эндпоинта."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.RequestException:
        logging.error(MESSAGES['API_error'])
        raise URLError(MESSAGES['API_error'])
    if homework_statuses.status_code == HTTPStatus.OK:
        try:
            return homework_statuses.json()
        except ValueError:
            logging.error(MESSAGES['not_JSON'])
            raise ValueError(MESSAGES['not_JSON'])
    logging.error(MESSAGES['API_unavailable'])
    raise ResponseError(MESSAGES['API_unavailable'])


def check_response(response):
    """Функция проверяет ответ от эндпоинта."""
    if 'homeworks' in response and isinstance(response.get('homeworks'), list):
        return response.get('homeworks')
    logging.error(MESSAGES['wrong_value'])
    raise TypeError(MESSAGES['wrong_value'])


def parse_status(homework):
    """Функция возвращает обработанный ответ от эндпоинта."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'{MESSAGES["status_change"]} "{homework_name}". {verdict}'
    logging.error(MESSAGES['status_unknown'])
    raise KeyError(MESSAGES['status_unknown'])


def check_tokens():
    """Функция проверяет валидность токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Главная функция: отправляет и проверяет запрос API.
    В случае успеха посылает сообщение через бот.
    """
    if not check_tokens():
        logging.critical(MESSAGES['env_error'])
        raise TokenValidationError(MESSAGES['env_error'])

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(MESSAGES['no_new'])
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
