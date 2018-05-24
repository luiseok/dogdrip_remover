import wget
import zipfile
import platform
import os
import stat
import time
from pathlib import Path
from toollib.logger import Logger
from crawler.xe import XpressEngine
from config import config


class DogdripRemover(object):
    logger = Logger("DogdripRemover")
    # Installing Requirements
    CHROME_DRIVER_URL = dict(Linux='https://chromedriver.storage.googleapis.com/2.38/chromedriver_linux64.zip',
                             Darwin='https://chromedriver.storage.googleapis.com/2.38/chromedriver_mac64.zip',
                             Windows='https://chromedriver.storage.googleapis.com/2.38/chromedriver_win32.zip')
    WEBSITE_URL = 'http://dogdrip.net'

    def __init__(self, arch=platform.system()):
        self.logger.debug("DogdripRemover instance created")
        self.driverPath = None
        try:
            if not Path('./chromedriver.zip').is_file():
                # 1. Chromedriver 설치
                self.logger.info("크롬 드라이버를 다운로드합니다.")
                self.logger.debug("OS: %s", str(arch))
                self.logger.debug("URL: %s", str(self.CHROME_DRIVER_URL.get(arch)))
                wget.download(self.CHROME_DRIVER_URL.get(arch), './chromedriver.zip')
                self.logger.debug("크롬드라이버 다운로드 성공. 압축 해제")

            chromedriver = zipfile.ZipFile('./chromedriver.zip')
            chromedriver.extractall('./')
            self.driverPath = os.path.realpath(chromedriver.namelist()[0])
            self.logger.debug("압축해제 완료. chromedriver 위치: %s", self.driverPath)
            chromedriver.close()

            st = os.stat(self.driverPath)
            os.chmod(self.driverPath, st.st_mode | stat.S_IEXEC)
            self.logger.debug("크롬 드라이버 권한 변경 완료 +x")

        except Exception as e:
            self.logger.error("크롬 드라이버 다운로드에 실패했습니다.")
            self.logger.exception(e)
            exit(1)
