import time

from urllib.parse import parse_qs
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from toollib.logger import Logger


class XpressEngine(object):
    logger = Logger("xe_crawler")

    LOGIN_PAGE = '/index.php?act=dispMemberLoginForm'
    MY_PAGE = '/index.php?act=dispMemberInfo'
    OWN_DOCUMENTS = '/index.php?act=dispMemberOwnDocument'
    OWN_COMMENTS = '/index.php?act=dispMemberOwnComment'

    def __init__(self, url=None, user_id=None, password=None, headless=False):
        self.logger.debug("xe_crawler instance created")
        if url is None:
            self.logger.error("웹사이트 주소가 올바르지 않습니다.")
            # exit(1)
        if user_id is None:
            self.logger.error("계정명이 올바르지 않습니다.")
            # exit(1)
        if password is None:
            self.logger.error("패스워드가 올바르지 않습니다.")
            # exit(1)
        self.url = url
        self.user_id = user_id
        self.password = password
        self.isHeadless = headless
        self.browser = None

    def load_browser(self, executable_path):
        options = webdriver.ChromeOptions()
        if self.isHeadless:
            options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument('lang=ko_KR')
        self.browser = webdriver.Chrome(executable_path, chrome_options=options)
        pass

    def load_xe(self):
        self.browser.get(self.url)
        self.browser.implicitly_wait(3)
        pass

    # 로그인 처리
    def login(self):
        self.browser.get(self.url + self.LOGIN_PAGE)
        self.browser.find_element_by_xpath('//*[@id="uid"]').send_keys(self.user_id)
        self.browser.find_element_by_xpath('//*[@id="upw"]').send_keys(self.password)
        # 로그인
        self.browser.find_element_by_xpath('//*[@id="commonLogin"]/fieldset/span[2]/input').click()
        if WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="header_login"]/span[2]/a'))):
            self.logger.info("로그인 성공")
        else:
            self.logger.error("로그인에 실패했습니다.")
            exit(1)
        time.sleep(1)

    def load_mypage(self):
        self.browser.get(self.url + self.MY_PAGE)
        pass

    def load_my_documents(self, page=1):
        self.browser.get(self.url + self.OWN_DOCUMENTS + '&page=' + str(page))
        self.browser.implicitly_wait(3)
        pass

    def load_my_documents_html(self, page=1):
        self.load_my_documents(page)
        html = self.browser.execute_script(
            'return window.document.getElementsByClassName("colTable")[0].innerHTML'
        )
        return BeautifulSoup(html, 'html.parser')

    def load_my_comments(self, page=1):
        self.browser.get(self.url + self.OWN_COMMENTS + '&page=' + str(page))
        self.browser.implicitly_wait(3)

    def load_my_comments_html(self, page=1):
        self.load_my_comments(page)
        html = self.browser.execute_script(
            'return window.document.getElementsByClassName("colTable")[0].innerHTML'
        )
        return BeautifulSoup(html, 'html.parser')

    def quit(self):
        if self.browser:
            self.browser.quit()
        pass

    def __del__(self):
        self.quit()