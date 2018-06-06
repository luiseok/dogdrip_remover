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
    DELETE_COMMENT = '/index.php?act=dispBoardDeleteComment&document_srl='
    DELETE_DOCUMENT = '/index.php?act=dispBoardDelete&document_srl='
    CSRL = '&comment_srl='

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
        self.insert_processing_overlay()
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


    def insert_processing_overlay(self):
        self.browser.execute_script("""
        var style = document.createElement('style');
        style.type='text/css';
        style.innerHTML="#text{position:absolute;top:50%;left:50%;font-size:50px;color:#fff;transform:translate(-50%,-50%);-ms-transform:translate(-50%,-50%)} .dogdrip-remover-overlay{z-index:1;position:fixed;width:100%;height:100%;left:0;top:0;background-color:rgba(0,0,0,0.4);overflow-x:hidden;}.loader,.loader:after,.loader:before{top:20%;border-radius:50%;width:2.5em;height:2.5em;-webkit-animation:load7 1.8s infinite ease-in-out;animation:load7 1.8s infinite ease-in-out}.loader{color:#fff;font-size:10px;margin:80px auto;position:relative;text-indent:-9999em;-webkit-transform:translateZ(0);-ms-transform:translateZ(0);transform:translateZ(0);-webkit-animation-delay:-.16s;animation-delay:-.16s}.loader:after,.loader:before{content:'';position:absolute;top:0}.loader:before{left:-3.5em;-webkit-animation-delay:-.32s;animation-delay:-.32s}.loader:after{left:3.5em}@-webkit-keyframes load7{0%,100%,80%{box-shadow:0 2.5em 0 -1.3em}40%{box-shadow:0 2.5em 0 0}}@keyframes load7{0%,100%,80%{box-shadow:0 2.5em 0 -1.3em}40%{box-shadow:0 2.5em 0 0}}";
        document.head.appendChild(style);
        var div = document.createElement('div');
        div.className='dogdrip-remover-overlay';
        document.body.appendChild(div);
        var loader = document.createElement('div');
        loader.className='loader';
        document.getElementsByClassName('dogdrip-remover-overlay')[0].appendChild(loader);
        var text = document.createElement('div');
        text.id='text';
        text.textContent='현재 [개드립 리무버] 작업중입니다! 창을 닫으면 프로그램이 종료되니 닫지마세요';
        document.getElementsByClassName('dogdrip-remover-overlay')[0].appendChild(text);
        """)

    def load_mypage(self):
        self.browser.get(self.url + self.MY_PAGE)
        pass

    def load_my_documents(self, page=1):
        self.browser.get(self.url + self.OWN_DOCUMENTS + '&page=' + str(page))
        self.insert_processing_overlay()
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
        self.insert_processing_overlay()
        self.browser.implicitly_wait(3)

    def load_my_comments_html(self, page=1):
        self.load_my_comments(page)
        html = self.browser.execute_script(
            'return window.document.getElementsByClassName("colTable")[0].innerHTML'
        )
        return BeautifulSoup(html, 'html.parser')

    def click_by_xpath(self, element):
        self.browser.find_element_by_xpath(element).click()

    def delete_comment(self, comment):
        try:
            self.browser.get(self.url + self.DELETE_COMMENT + comment[1] + self.CSRL + comment[0])
            self.click_by_xpath('//*[@id="content"]/div[1]/div/form/div/span/input')
            self.insert_processing_overlay()
            WebDriverWait(self.browser, 2).until(EC.alert_is_present(), 'Timed out waiting for PA creation')
            alert = self.browser.switch_to.alert
            alert.accept()
            # self.browser.implicitly_wait(10)
        except TimeoutException as e:
            self.logger.debug("alert not found")
        except Exception as e:
            self.logger.error(e)
            pass

        try:
            if WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'articleNum'))):
                return True
        except TimeoutException as e:
            self.logger.debug("could not find article list")
            return False

    def delete_document(self, document):
        try:
            self.browser.get(self.url + self.DELETE_DOCUMENT + document[0] )
            self.click_by_xpath('//*[@id="content"]/div[1]/div/form/div/span/input')
            self.insert_processing_overlay()
            WebDriverWait(self.browser, 2).until(EC.alert_is_present(), 'Timed out waiting for PA creation')
            alert = self.browser.switch_to.alert
            alert.accept()
            # self.browser.implicitly_wait(10)
        except TimeoutException as e:
            self.logger.debug("alert not found")
        except Exception as e:
            self.logger.error(e)

        try:
            WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'articleNum')))
            return True
        except TimeoutException as e:
            self.logger.debug("could not find article list")
            return False

    def quit(self):
        if self.browser:
            self.browser.quit()
        pass

    def __del__(self):
        self.quit()