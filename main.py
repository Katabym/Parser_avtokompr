import json
import logging
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import argparse
import subprocess
import sys



# Настройка логирования
logging.basicConfig(
    filename='parser.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Файлы для хранения данных
OUTPUT_JSON = 'results.json'
HISTORY_FILE = 'processed_vins.txt'
VIN_FILE = 'vins.txt'
COOKIES_FILE = 'cookies.pkl'

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def load_cookies(driver):
    # Загрузка cookies из файла и добавление их в браузер.
    if not os.path.exists(COOKIES_FILE):
        logging.error(f"Файл cookies {COOKIES_FILE} не найден. Авторизация невозможна.")
        return False

    with open(COOKIES_FILE, 'rb') as f:
        cookies = pickle.load(f)

    # Установливаю cookies
    driver.get('https://avtokompromat.ru/')
    for cookie in cookies:
        driver.add_cookie(cookie)
    logging.info("Cookies успешно загружены в браузер.")
    return True

def load_processed_vins():
    # Загрузка списка обработанных VIN-кодов из файла
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_processed_vin(vin):
    # Сохранение обработанного VIN-кода в файл истории
    with open(HISTORY_FILE, 'a') as f:
        f.write(vin + '\n')

def load_vins():
    # Загрузка списка VIN-кодов из файла
    if not os.path.exists(VIN_FILE):
        logging.error(f"Файл {VIN_FILE} не найден.")
        return []
    with open(VIN_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_to_json(data):
    # Сохранение данных в JSON файл
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, 'r') as f:
            existing_data = json.load(f)
        existing_data.update(data)
        data = existing_data
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Данные сохранены в {OUTPUT_JSON}")

def parse_vin(driver, vin):
    # Парсинг данных для одного VIN-кода
    try:
        logging.info(f"Обрабатываем VIN: {vin}")
        # После авторизации страница перенаправляется  сюда
        driver.get('https://avtokompromat.ru/user/gosvin.php?pn=0')

        # Ожидание появления поля ввода VIN
        vin_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'id_param'))
        )
        vin_input.clear()
        vin_input.send_keys(vin)

        # Нажатие на кнопку поиска
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'id_knop_prov1'))
        )
        search_button.click()

        # Логируем текущий URL после нажатия кнопки поиска
        logging.info(f"Текущий URL после поиска: {driver.current_url}")

        # Ожидание появления блока info_cart, содержащего нужные данные
        info_block = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'info_cart') and contains(., 'Владельцы / Периоды владения транспортным средством')]"))
        )

        # Получаем все параграфы внутри блока
        paragraphs = info_block.find_elements(By.TAG_NAME, 'p')

        # Парсинг данных
        result = {}

        # Поиск количества записей в ПТС
        for p in paragraphs:
            if 'Количество записей в ПТС' in p.text:
                result['owners number'] = p.find_element(By.TAG_NAME, 'strong').text.split()[-1]

        # Парсинг периодов владения
        owner_count = 1
        for i, p in enumerate(paragraphs):
            if '-ая запись:' in p.text or '-я запись:' in p.text:
                period = paragraphs[i + 1].text  # Период владения
                result[f'period of possession by owner №{owner_count}'] = period
                owner_count += 1

        logging.info(f"Успешно обработан VIN: {vin}")
        return result

    except Exception as e:
        logging.error(f"Ошибка при обработке VIN {vin}: {str(e)}")
        return None

def main_parser(arg_VIN=None):
    driver = setup_driver()

    # Загружаем cookies для авторизации
    if not load_cookies(driver):
        logging.error("Не удалось загрузить cookies. Завершение работы.")
        driver.quit()
        return

    processed_vins = load_processed_vins()
    if arg_VIN == None:
        vins = load_vins()
    else:
        vins = arg_VIN



    if not vins:
        logging.error("Список VIN-кодов пуст.")
        driver.quit()
        return

    results = {}
    for vin in vins:
        if vin in processed_vins:
            logging.info(f"Пропускаем VIN {vin}, так как он уже обработан.")
            continue

        data = parse_vin(driver, vin)
        if data:
            results[vin] = data
            save_processed_vin(vin)

    if results:
        save_to_json(results)

    driver.quit()
    logging.info("Парсинг завершен.")


def main():
    atms = argparse.ArgumentParser(description='Парсер для VIN номеров')
    atms.add_argument('--cookies', action='store_true', help='Запускает скрипт для сбора cookies, если таковых нет')
    atms.add_argument('--VIN', type=str, nargs='+', help='Для ввода своего списка номеров')

    args = atms.parse_args()

    try:
        if args.cookies:
            # Запускаем grab_cookies.py
            subprocess.run([sys.executable, 'grab_cookies.py'])
        elif args.VIN:
            # Запуск парсера по введённому/введённым номерам
            print(f"Parametr: {args.VIN}")
            main_parser(args.VIN)
        else:
            # Запувк парсера по номерам из файла
            main_parser()

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()