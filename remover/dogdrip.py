import wget
import zipfile
import platform
import os
import stat
import time
import sqlite3
import re

from urllib.parse import parse_qs
from urllib.parse import urlparse
from pathlib import Path
from toollib.logger import Logger

from crawler.xe import XpressEngine
from config import config


class DogdripRemover(object):
    dogdripBrowser: XpressEngine
    logger = Logger("DogdripRemover")
    # Installing Requirements
    CHROME_DRIVER_URL = dict(Linux='https://chromedriver.storage.googleapis.com/2.38/chromedriver_linux64.zip',
                             Darwin='https://chromedriver.storage.googleapis.com/2.38/chromedriver_mac64.zip',
                             Windows='https://chromedriver.storage.googleapis.com/2.38/chromedriver_win32.zip')
    WEBSITE_URL = 'http://dogdrip.net'
    conn = None
    cur = None

    def __init__(self, arch=platform.system()):
        self.logger.debug("DogdripRemover instance created")
        self.driverPath = None
        self.conn = sqlite3.connect("my_dogdrip.db")
        self.cur = self.conn.cursor()
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
            else:
                chromedriver = zipfile.ZipFile('./chromedriver.zip')
            self.driverPath = os.path.realpath(chromedriver.namelist()[0])
            self.logger.debug("압축해제 완료. chromedriver 위치: %s", self.driverPath)
            chromedriver.close()

            # Chromedriver 실행권한 부여
            if not arch == "Windows":
                st = os.stat(self.driverPath)
                os.chmod(self.driverPath, st.st_mode | stat.S_IEXEC)
                self.logger.debug("크롬 드라이버 권한 변경 완료 +x")
            self.db_initialize()

        except sqlite3.Error as e:
            self.logger.error("데이터베이스 초기화에 실패했습니다.")
            self.logger.exception(e)
            exit(1)
        except Exception as e:
            self.logger.error("크롬 드라이버 다운로드에 실패했습니다.")
            self.logger.exception(e)
            exit(1)

        self.dogdripBrowser = XpressEngine(url=self.WEBSITE_URL,
                                           user_id=config.get('user_id'),
                                           password=config.get('password'),
                                           headless=False)

    def db_initialize(self):
        """
            데이터베이스 초기화
            데이터베이스에서는 본인이 작성할 댓글과 게시물을 임시로 저장하고,
            조건 처리에 대한 모든 질의를 http request를 통해 하는것보다 빠른 처리성능을 꾀하고자 sqlite3를 사용한다.
        """
        # 문서
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS documents (document_srl TEXT PRIMARY KEY, href TEXT NOT NULL, title TEXT, content TEXT, view_count INT, comment_count INT, vote_up INT, vote_down INT, created_at TEXT,  target_board TEXT, is_deleted INTEGER DEFAULT 0)")
        """
            CREATE TABLE IF NOT EXISTS documents (
                document_srl TEXT PRIMARY KEY, - 게시물 고유번호
                href TEXT NOT NULL,            - 게시물 고유주소
                title TEXT,                    - 게시물 제목
                content TEXT,                  - 게시물 내용
                view_count INT,                - 조회 수
                comment_count INT,             - 댓글 수 
                vote_up INT,                   - 개드립
                vote_down INT,                 - 붐업
                created_at TEXT,               - 작성시간
                target_board TEXT,             - 게시판 이름
                is_deleted INTEGER DEFAULT 0   - 삭제여부
            )
        """
        self.conn.execute("CREATE INDEX IF NOT EXISTS d_target_board_idx ON documents(`target_board`)")
        self.conn.commit()
        # 댓글
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS comments (comment_srl TEXT PRIMARY KEY, target_srl  TEXT, content TEXT, created_at TEXT, target_board TEXT, has_child INTEGER DEFAULT 0)")
        """
            CREATE TABLE IF NOT EXISTS comments (
                comment_srl TEXT PRIMARY KEY,  - 댓글 고유번호
                target_srl  TEXT,              - 댓글이 작성된 원래 문서의 고유번호
                content TEXT,                  - 댓글 내용
                created_at TEXT,               - 작성 시간
                target_board TEXT,             - 게시판 이름
                has_child INTEGER DEFAULT 0    - 대댓글 여부
            )
        """
        self.conn.execute("CREATE INDEX IF NOT EXISTS c_target_board_idx ON comments(`target_board`)")
        self.conn.commit()

    def login(self):
        self.dogdripBrowser.load_browser(self.driverPath)
        self.dogdripBrowser.login()
        pass

    def fetch_comment_list(self):
        html = self.dogdripBrowser.load_my_comments_html()
        current_page, total_page = self.get_pagination_info(html.find('caption').get_text())
        self.logger.info("총 %s페이지의 댓글이 있습니다.", total_page)
        for page in range(int(current_page), int(total_page) + 1):
            self.logger.info("총 %s페이지 중 %s페이지의 댓글들을 수집하고있습니다.", str(page))
            html = self.dogdripBrowser.load_my_comments_html(page)
            html_comment_list = html.find_all('tr')
            comments = self.parse_comment(html_comment_list)
            self.insert_comments(comments);

    def parse_comment(self, html_comment_list):
        comments = []

        if html_comment_list:
            for comment_list in html_comment_list:
                # 마이페이지에서 수집할 수 있는 댓글 정보 저장
                content = comment_list.find("td", {"class": "wide"})
                if content:
                    comment = content.find("a")
                    if comment:
                        target_srl = urlparse(comment['href']).path
                        while os.path.dirname(target_srl) != '/':
                            target_srl = os.path.dirname(target_srl)
                        target_srl = target_srl.replace('/', '')
                        comment_srl = comment['href'].split("#")[1].split("_")[1]
                        created_at = comment_list.find("td", {"class": "nowrap"}).get_text()
                        self.logger.debug("원본 게시물 번호: %s, 댓글 고유번호: %s, 댓글내용: %s, 작성시간: %s", target_srl, comment_srl,
                                          comment.get_text(), created_at)
                        if not comment.get_text() == "[삭제 되었습니다]":
                            comments.append((comment_srl, target_srl, comment.get_text(), created_at))
            return comments
        else:
            return None

    def insert_comments(self, comments):
        insert_into_comments = "INSERT INTO comments(comment_srl, target_srl, content, created_at) VALUES (?,?,?,datetime(?)) "
        self.cur.executemany(insert_into_comments, comments)
        self.conn.commit();

    @classmethod
    def get_pagination_info(cls, text):
        pattern = re.compile(r'\b[0-9]*.\/.[0-9]*')
        pagination = pattern.findall(text)
        return pagination[0].split('/')

    def __del__(self):
        self.logger.debug("DogdripRemover 인스턴스가 종료되었습니다.")
        try:
            self.dogdripBrowser.quit()
        except Exception as e:
            self.logger.exception(str(e))
            pass
