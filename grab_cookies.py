import pickle
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException

logging.basicConfig(
    filename='selenium.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

COOKIES_FILE = 'cookies.pkl'

def save_cookies(driver, path):
    # Сохранение cookies в файл
    try:
        with open(path, 'wb') as file:
            pickle.dump(driver.get_cookies(), file)
        logging.info(f"Cookies успешно сохранены в файл {path}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении cookies: {str(e)}")

def load_cookies(driver, path):
    # Загрузка cookies из файла
    try:
        if os.path.exists(path):
            with open(path, 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            logging.info(f"Cookies успешно загружены из файла {path}")
        else:
            logging.warning(f"Файл cookies {path} не найден")
    except Exception as e:
        logging.error(f"Ошибка при загрузке cookies: {str(e)}")

def setup_driver_with_cookies():
    try:
        chrome_options = Options()
        # Выключил чтобы можно было совершить авторизацию
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Обход обнаружения Selenium
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        logging.info("Инициализация WebDriver...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.info("WebDriver успешно инициализирован")

        # Открываю сайт
        logging.info("Открытие сайта https://avtokompromat.ru/...")
        driver.get('https://avtokompromat.ru/user/logpass.php')
        logging.info("Сайт успешно открыт")

        # Если cookies уже сохранены, загружаю их
        if os.path.exists(COOKIES_FILE):
            load_cookies(driver, COOKIES_FILE)
            logging.info("Перезагрузка страницы для применения cookies...")
            driver.get('https://avtokompromat.ru/')  # Перезагружаем страницу для применения cookies
        else:
            # Если cookies нет, нужно вручную авторизоваться
            logging.info("Cookies не найдены, требуется ручная авторизация")
            print("Пожалуйста, авторизуйтесь вручную в открывшемся окне браузера, затем нажмите Enter в консоли для сохранения cookies...")
            input("Нажмите Enter после авторизации...")
            save_cookies(driver, COOKIES_FILE)

        return driver

    except WebDriverException as e:
        logging.error(f"Ошибка WebDriver: {str(e)}")
        raise
    except TimeoutException as e:
        logging.error(f"Тайм-аут при загрузке страницы: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {str(e)}")
        raise

def main():
    try:
        driver = setup_driver_with_cookies()
        logging.info("WebDriver настроен и готов к работе")
        print("Браузер открыт. Вы можете продолжить работу с сайтом.")
        input("Нажмите Enter для завершения работы программы...")
        driver.quit()
        logging.info("WebDriver успешно закрыт")
    except Exception as e:
        logging.error(f"Ошибка в main: {str(e)}")
        raise

if __name__ == "__main__":
    main()