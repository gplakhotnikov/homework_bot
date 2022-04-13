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
        logging.info(MESSAGES.get('message_sent'))
    except telegram.TelegramError:
        logging.error(MESSAGES.get('message_not_sent'))


def get_api_answer(current_timestamp):
    """Функция получает ответ от эндпоинта."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.RequestException:
        logging.error(MESSAGES.get("API_error"))
        raise URLError(MESSAGES.get("API_error"))
    if homework_statuses.status_code == HTTPStatus.OK:
        try:
            return homework_statuses.json()
        except ValueError:
            logging.error(MESSAGES.get('not_JSON'))
            raise ValueError(MESSAGES.get('not_JSON'))
    logging.error(MESSAGES.get('API_unavailable'))
    raise ResponseError(MESSAGES.get('API_unavailable'))


def check_response(response):
    """Функция проверяет ответ от эндпоинта."""
    if 'homeworks' in response and isinstance(response.get('homeworks'), list):
        return response.get('homeworks')
    logging.error(MESSAGES.get('wrong_value'))
    raise TypeError(MESSAGES.get('wrong_value'))


def parse_status(homework):
    """Функция возвращает обработанный ответ от эндпоинта."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'{MESSAGES.get("status_change")} "{homework_name}". {verdict}'
    logging.error(MESSAGES.get('status_unknown'))
    raise KeyError(MESSAGES.get('status_unknown'))


def check_tokens():
    """Функция проверяет валидность токенов."""
    if any([PRACTICUM_TOKEN is None,
            TELEGRAM_TOKEN is None,
            TELEGRAM_CHAT_ID is None]):
        return False
    else:
        return True


def main():  # noqa: C901
    """Главная функция: отправляет и проверяет запрос API.
    В случае успеха посылает сообщение через бот.
    """
    error_messages_sent = {
        'API_error': False,
        'other_API_error': False,
        'not_JSON': False,
        'API_unavailable': False,
        'wrong_value': False,
        'status_unknown': False,
    }

    if not check_tokens():
        logging.critical(MESSAGES.get('env_error'))
        raise TokenValidationError(MESSAGES.get('env_error'))

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(MESSAGES.get('no_new'))
            for homework in homeworks:
                status = parse_status(homework)
                send_message(bot, status)
            current_timestamp = int(time.time())
        except URLError:
            if not error_messages_sent.get('API_error'):
                send_message(bot, MESSAGES.get('API_error'))
                error_messages_sent['API_error'] = True
        except ValueError:
            if not error_messages_sent.get('not_JSON'):
                send_message(bot, MESSAGES.get('not_JSON'))
                error_messages_sent['not_JSON'] = True
        except ResponseError:
            if not error_messages_sent.get('API_unavailable'):
                send_message(bot, MESSAGES.get('API_unavailable'))
                error_messages_sent['API_unavailable'] = True
        except TypeError:
            if not error_messages_sent.get('wrong_value'):
                send_message(bot, MESSAGES.get('wrong_value'))
                error_messages_sent['wrong_value'] = True
        except KeyError:
            if not error_messages_sent.get('status_unknown'):
                send_message(bot, MESSAGES.get('status_unknown'))
                error_messages_sent['status_unknown'] = True
        except Exception as error:
            message = f'{MESSAGES.get("API_error")} : {error}'
            logging.error(message)
            if not error_messages_sent.get('other_api_error'):
                send_message(bot, message)
                error_messages_sent['other_api_error'] = True
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
