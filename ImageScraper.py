import os
import requests
import time
import random
import threading
import hashlib
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ImageScraper:
    def __init__(self, app, tags, download_folder="Default/default_download", max_images=10,
                 user_agents_file="Default/chrome.txt", credentials_file="Default/credentials.txt"):
        self.app = app
        self.tags = tags
        self.download_folder = download_folder
        self.max_images = max_images
        self.user_agents = self.load_file(user_agents_file)
        self.credentials = self.load_file(credentials_file)
        self.downloaded_hashes = set()

    def load_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return file.read().splitlines()
        except FileNotFoundError:
            print(f"File {file_path} not found.")
            return []

    def check_chromedriver(self):
        try:
            options = Options()
            options.add_argument("--headless")
            webdriver.Chrome(options=options)
        except WebDriverException as e:
            print(f"Error: {e}")
            print("Chrome core browser needed for proper work.")
            print("Install Chrome browser and download chromedriver, please.")
            print("Then add chromedriver path to system PATH.")
            print("You can download it here: https://sites.google.com/chromium.org/driver/")
            return False
        return True

    def start_download(self):
        if not self.check_chromedriver():
            return

        download_thread = threading.Thread(target=self.download_images)
        download_thread.start()

    def download_images(self, stop_flag=False):
        def get_high_quality_url(low_quality_url):
            return low_quality_url.replace("/236x/", "/originals/")

        def scroll_to_top_and_open_first_pin(browser):

            browser.execute_script("window.scrollTo(0, 0);")
            time.sleep(3)

            first_pin = browser.find_element(By.CLASS_NAME, 'hCL')
            if first_pin:
                first_pin.click()
                time.sleep(3)

        def download_image(url, save_path, extension):
            try:
                response = requests.get(url, headers={'User-Agent': self.get_random_user_agent()}, stream=True)

                if response.content:
                    if 'Content-Length' in response.headers and int(response.headers['Content-Length']) >= 246:
                        if is_valid_image_size(response):
                            with open(f"{save_path}.{extension}", 'wb') as file:
                                file.write(response.content)
                            return True

            except Exception as e:
                print(f"Failed to load an image: {str(e)}")

            return False

        def is_valid_image_size(response):
            try:
                image = Image.open(BytesIO(response.content))
                width, _ = image.size

                if image.format.lower() in {"jpeg", "png", "gif"}:
                    return width >= 230  #####----
            except Exception as e:
                print(f"Failed to get image size: {str(e)}")

            return False

        def scroll_and_load_images():
            last_height = browser.execute_script(
                "return Math.max( document.body.scrollHeight, document.body.offsetHeight, "
                "document.documentElement.clientHeight, "
                "document.documentElement.scrollHeight, document.documentElement.offsetHeight );")

            for _ in range(3):  # repeat 3 times
                try:
                    element_present = EC.presence_of_element_located((By.CLASS_NAME, 'hCL'))
                    WebDriverWait(browser, 10).until(element_present)

                    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)

                    new_height = browser.execute_script(
                        "return Math.max( document.body.scrollHeight, document.body.offsetHeight,"
                        " document.documentElement.clientHeight, document.documentElement.scrollHeight,"
                        " document.documentElement.offsetHeight );")

                    if new_height == last_height:
                        # scroll-check
                        break

                    last_height = new_height

                    image_elements = browser.find_elements(By.CLASS_NAME, 'hCL')
                    if image_elements:
                        return image_elements

                except Exception as e:
                    print(f"Failed to load images: {str(e)}")
                    time.sleep(10)

            print("Failed to load images after all tries.")
            return []

        def login_to_pinterest():
            login_url = "https://www.pinterest.com/login/"
            browser.get(login_url)
            time.sleep(3)

            username, password = self.credentials[:2]

            email_input = browser.find_element(By.ID, 'email')
            email_input.send_keys(username)

            password_input = browser.find_element(By.ID, 'password')
            password_input.send_keys(password)

            password_input.send_keys(Keys.RETURN)

            time.sleep(5)

            self.app.insert_log(f"Trying to log in with credentials: {username}")

            if "login" not in browser.current_url.lower():
                self.app.insert_log("Log in successful.")
            else:
                self.app.insert_log("Log in failed.")

        try:
            tags = self.tags.get()
            tag_query = '%20'.join(tags.split())
            pinterest_url = f"https://www.pinterest.com/search/pins/?q={tag_query}&rs=typed"
            self.app.insert_log(f"Request sent: {pinterest_url}")

            options = Options()
            options.headless = True
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--headless")
            options.add_argument(f"user-agent={self.get_random_user_agent()}")
            options.add_argument("--window-size=1920,1080")

            with webdriver.Chrome(options=options) as browser:
                login_to_pinterest()

                browser.get(pinterest_url)
                time.sleep(3)

                total_images = self.max_images
                images_downloaded = 0

                while images_downloaded < self.max_images:
                    try:
                        if not scroll_and_load_images():
                            scroll_to_top_and_open_first_pin(browser)
                            self.app.clear_log()
                            self.app.insert_log(f"No images left turning page.")
                            self.app.insert_log(f"Images loaded: {images_downloaded}")
                            continue

                        image_elements = scroll_and_load_images()

                        for i, img_element in enumerate(image_elements):
                            if  images_downloaded >= self.max_images or self.app.stop_flag:
                                self.app.clear_log()
                                self.app.insert_log(f"Loading completed")
                                self.app.progressbar["value"] = 0
                                break

                            low_quality_url = img_element.get_attribute('src')
                            high_quality_url = get_high_quality_url(low_quality_url)

                            image_name = f"image_{images_downloaded + 1}"
                            extension = high_quality_url.split('.')[-1]  # pansions

                            save_path = os.path.join(self.download_folder, image_name)

                            image_hash = self.calculate_image_hash(high_quality_url)

                            if image_hash in self.downloaded_hashes:
                                print(f"Image with hash {image_hash} already downloaded. Passing.")
                                continue

                            debug_log = f"Current object url: {high_quality_url}"
                            self.app.insert_log(debug_log)

                            if download_image(high_quality_url, save_path, extension):
                                images_downloaded += 1
                                self.downloaded_hashes.add(image_hash)

                                progress_value = (images_downloaded * 100) / self.max_images
                                self.app.progressbar["value"] = progress_value
                                self.app.master.update_idletasks()

                        time.sleep(3)

                    except Exception as e:
                        print(f"Image processing failure: {str(e)}")

        except Exception as e:
            self.app.insert_log(f"Tag processing failure: {str(e)}")

    def calculate_image_hash(self, url):
        response = requests.get(url)
        image_data = response.content
        image_hash = hashlib.md5(image_data).hexdigest()
        return image_hash

    def get_random_user_agent(self):
        if self.user_agents:
            return random.choice(self.user_agents)
        else:
            print("User Agents list empty.")
            return ""