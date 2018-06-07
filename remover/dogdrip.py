from multiprocessing.pool import ThreadPool as Pool

import requests
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
import urllib.request
from pathlib import Path
from toollib.logger import Logger
from bs4 import BeautifulSoup

from crawler.xe import XpressEngine
from config import config


def millis():
    return int(round(time.time() * 1000))


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

    # 생성자
    # 크롬드라이버 설치, 데이터베이스 초기화 작업, Selenium 객체 생성
    def __init__(self, arch=platform.system()):
        self.logger.debug("DogdripRemover instance created")
        self.driverPath = None
        self.conn = None
        self.cur = None
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
                self.logger.debug("크롬 드라이버 실행 권한 변경 완료")
            # SQLite3 초기화
            if not Path('./my_dogdrip.db').is_file(): #데이터베이스 없는 경우
                self.conn = sqlite3.connect("my_dogdrip.db")
                self.cur = self.conn.cursor()
                self.db_initialize()
            else:
                self.conn = sqlite3.connect("my_dogdrip.db")
                self.cur = self.conn.cursor()

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
        self.logger.info("SQLite3 초기화중...")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_srl TEXT PRIMARY KEY,  /* 게시물 고유번호 */
                href TEXT NOT NULL,             /* 게시물 고유주소 */
                title TEXT,                     /* 게시물 제목 */
                content TEXT,                   /* 게시물 내용 */
                view_count INT,                 /* 조회 수 */
                comment_count INT,              /* 댓글 수 */
                vote_up INT,                    /* 개드립 */
                vote_down INT,                  /* 붐업 */
                created_at TEXT,                /* 작성시간 */
                target_board TEXT,              /* 게시판 이름 */
                is_deleted INTEGER DEFAULT 0    /* 삭제여부 */
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS d_target_board_idx ON documents(`target_board`)")
        self.conn.commit()
        # 댓글
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_srl TEXT PRIMARY KEY,  /* 댓글 고유번호 */
                target_srl  TEXT,              /* 댓글이 작성된 원래 문서의 고유번호 */
                href TEXT NOT NULL,            /* 고유 주소 */
                content TEXT,                  /* 댓글 내용 */
                created_at TEXT,               /* 작성 시간 */
                target_board TEXT,             /* 게시판 이름 */
                has_child INTEGER DEFAULT 0,    /* 대댓글 여부 */
                is_deleted INTEGER DEFAULT 0    /* 삭제여부 */
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS c_target_board_idx ON comments(`target_board`)")
        self.conn.commit()
        self.logger.info("SQLite3 초기화 완료!")

    # SQLite3 에 댓글 정보 삽입
    def insert_comments(self, comments):
        insert_into_comments = "INSERT OR REPLACE INTO comments(comment_srl, target_srl, href, content, created_at) " \
                               "VALUES (?,?,?,?,datetime(?)) "
        self.cur.executemany(insert_into_comments, comments)
        self.conn.commit()

    # SQLite3 에 문서 정보 삽입
    def insert_documents(self, documents):
        insert_into_documents = "INSERT OR REPLACE INTO documents(document_srl, href, title, comment_count, " \
                                "view_count, vote_up, created_at) VALUES (?,?,?,?,?,?,date(?)) "
        self.cur.executemany(insert_into_documents, documents)
        self.conn.commit()

    def login(self):
        self.dogdripBrowser.load_browser(self.driverPath)
        return self.dogdripBrowser.login()

    def comments_find_all(self):
        with self.conn:
            self.cur.execute("SELECT * FROM COMMENTS")
            comments = self.cur.fetchall()
            return comments

    def comments_find_not_deleted(self):
        with self.conn:
            self.cur.execute("SELECT * FROM comments")
            comments = self.cur.fetchall()
            return comments

    def update_document_detail(self, results):
        self.logger.debug("게시물에 상세정보를 추가합니다.")
        updatesql = "UPDATE documents SET target_board=?, content=? WHERE document_srl=?"
        new_infos = []
        for result in results:
            if result:
                document_srl = result[0][0]
                target_board = result[1]
                content = result[2]
                new_infos.append((target_board, content, document_srl))
            else:
                pass
        self.cur.executemany(updatesql, new_infos)
        self.conn.commit()

    def update_comment_detail(self, results):
        self.logger.debug("댓글에 상세정보를 추가합니다.(소속 게사판, 대댓글여부)")
        updatesql = "UPDATE comments SET target_board=?, has_child=? WHERE comment_srl=?"
        new_infos = []
        for result in results:
            if result:
                comment_srl = result[0][0]
                target_board = result[1]
                has_child = result[2]
                new_infos.append((target_board, has_child, comment_srl))
        self.cur.executemany(updatesql, new_infos)
        self.conn.commit()

    def update_is_deleted(self, doc, type='comment'):
        self.logger.debug("삭제여부를 변경합니다.")
        self.logger.debug(doc)
        if type == 'comment':
            updatesql = "UPDATE comments SET is_deleted='1' WHERE comment_srl=?"
            self.cur.execute(updatesql, [doc[0]])
        elif type == 'document':
            updatesql = "UPDATE documents SET is_deleted='1' WHERE document_srl=?"
            self.cur.execute(updatesql, [doc[0]])
        pass

    # 게시물 목록으로부터 게시물 기초 정보 수집
    # 게시물 번호, 제목, 주소, 조회수, 추천수, 작성시각
    def fetch_document_list(self):
        self.logger.info("작성한 게시물 목록을 불러오고 있습니다...")
        html = self.dogdripBrowser.load_my_documents_html()
        current_page, total_page = self.get_pagination_info(html.find('caption').get_text())
        self.logger.info("총 %s페이지의 문서가 있습니다.", total_page)
        for page in range(int(current_page), int(total_page) + 1):
            self.logger.info("%s페이지 중 %s페이지를 수집하고있습니다.", str(total_page), str(page))
            html = self.dogdripBrowser.load_my_documents_html(page)
            html_document_list = html.find_all('tr')
            documents = self.parse_document(html_document_list)
            self.insert_documents(documents)

    # 문서 정보 파싱
    def parse_document(self, html_document_list):
        documents = []
        pattern = re.compile(r'\s\[\d*.\]$')
        if html_document_list:
            for document_list in html_document_list:
                # 마이페이지에서 수집할 수 있는 문서 정보 저장
                content = document_list.find("td", {"class": "wide"})
                if content:
                    document = content.find("a")
                    if document:
                        href = document['href']
                        document_srl = urlparse(href).path
                        while os.path.dirname(document_srl) != '/':
                            document_srl = os.path.dirname(document_srl)
                        document_srl = document_srl.replace('/', '')
                        comment_count = pattern.findall(content.get_text().strip())
                        if comment_count:
                            comment_count = comment_count[0].replace('[', '').replace(']', '').strip()
                        else:
                            comment_count = "0"
                        title = document.get_text()
                        view_count = document.findNext()
                        vote_up = view_count.findNext()
                        created_at = vote_up.findNext().get_text()
                        self.logger.debug("원본 게시물 번호: %s, 게시물 주소: %s, 제목: %s, 댓글 수: %s, 조회 수: %s, 개드립 수: %s, 작성일: %s",
                                          document_srl, href, title, comment_count, view_count.get_text(),
                                          vote_up.get_text(), created_at)

                        documents.append((document_srl, href, title, comment_count, view_count.get_text(),
                                          vote_up.get_text(), created_at))
            return documents
        else:
            return None

    # 댓글 목록으로부터 게시물 기초 정보 수집
    # 댓글내용, 댓글번호, 원게시물 번호, 댓글주소, 작성시각
    def fetch_comment_list(self):
        self.logger.info("작성한 댓글 목록을 불러오고 있습니다...")
        html = self.dogdripBrowser.load_my_comments_html()
        current_page, total_page = self.get_pagination_info(html.find('caption').get_text())
        self.logger.info("총 %s페이지의 댓글이 있습니다.", total_page)
        for page in range(int(current_page), int(total_page) + 1):
            self.logger.info("총 %s페이지 중 %s페이지를 수집하고있습니다.", str(total_page), str(page))
            html = self.dogdripBrowser.load_my_comments_html(page)
            html_comment_list = html.find_all('tr')
            comments = self.parse_comment(html_comment_list)
            self.insert_comments(comments)

    # 댓글 정보 파싱
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
                        self.logger.debug("원본 게시물 번호: %s, 댓글 고유번호: %s, 작성시간: %s", target_srl, comment_srl,
                                          created_at.strip().replace('\n', ' '))
                        if not comment.get_text() == "[삭제 되었습니다]":
                            comments.append((comment_srl, target_srl, comment['href'], comment.get_text(), created_at))
            return comments
        else:
            return None

    @classmethod
    def get_pagination_info(cls, text):
        pattern = re.compile(r'\b[0-9]*.\/.[0-9]*')
        pagination = pattern.findall(text)
        return pagination[0].split('/')

    # 댓글 상세 정보 수집
    # 대댓글 여부, 문서가 소속된 게시판 정보
    def add_comment_detail_job(self, comments):
        pool = Pool(processes=config.get('process_concurrency'))
        results = pool.imap_unordered(self.request_comment_info, comments)
        self.update_comment_detail(results)

    # 웹 요청 - 댓글 상세정보 수집
    def request_comment_info(self, comment):
        start_time = millis()
        with requests.get(comment[2]) as res:
            if res.status_code == 200:
                self.logger.debug("댓글 로드완료. 시간: %sms, url: %s", str(millis() - start_time), comment[2])
                page = res.text
                page = BeautifulSoup(page, 'html.parser')
                # 게시판 주소 찾기
                # board_name = page.find_all("li", {"class": "category"})[-1].find("a")["href"].replace("/", "")
                board_title = page.find_all("div", {"class": "boardHeaderBorder"})
                board_name = ''
                if board_title:
                    board_name = urlparse(board_title[0].find("a")["href"]).path.replace('/', '')
                # 대댓글 찾기
                has_child = "1" if page.find_all("div", {"parent_srl": comment[0]}) else "0"
                return comment, board_name, has_child

    def collect_comment_details(self):
        comments = self.comments_find_all()
        self.add_comment_detail_job(comments)

    def add_document_detail_job(self, documents):
        pool = Pool(processes=config.get('process_concurrency'))
        results = pool.imap_unordered(self.request_document_info, documents)
        self.update_document_detail(results)

    def request_document_info(self, document):
        start_time = millis()
        with requests.get(document[1]) as res:
            if res.status_code == 200:
                self.logger.debug("페이지 로드완료. 시간: %sms, url: %s", str(millis() - start_time), document[1])
                page = res.text
                page = BeautifulSoup(page, 'html.parser')
                # 게시판 주소 찾기
                board_title = page.find_all("div", {"class": "boardHeaderBorder"})
                board_name = ''
                if board_title:
                    board_name = urlparse(board_title[0].find("a")["href"]).path.replace('/', '')
                content = page.find_all("div", {"class": "xe_content"})
                if content:
                    content = content[0].get_text().strip()
                if board_name == '':
                    self.logger.debug("게시물 파싱 불가. 직접 삭제 요망. 주소: %s",  document[1])
                    return None
                if not content:
                    self.logger.debug("게시물 파싱 불가. 직접 삭제 요망. 주소: %s", document[1])
                    return None

                return document, board_name, content

    def collect_document_details(self):
        documents = self.documents_find_all()
        self.add_document_detail_job(documents)

    def documents_find_all(self):
        with self.conn:
            self.cur.execute("SELECT * FROM documents")
            documents = self.cur.fetchall()
            return documents

    def delete_all_documents_job(self):
        documents = self.documents_find_all()
        # pool = Pool(processes=config.get('process_concurrency'))
        # results = pool.imap_unordered(self.request_comment_info, documents)
        for document in documents:
            if self.delete_selenium_document(document):
                self.update_is_deleted(document, type="document")
                pass

    def delete_selenium_document(self, document):
        self.logger.debug(document)
        return self.dogdripBrowser.delete_document(document)

    def delete_all_comments_job(self):
        comments = self.comments_find_not_deleted()
        # pool = Pool(processes=config.get('process_concurrency'))
        # results = pool.imap_unordered(self.delete_selenium_comments, comments)
        for comment in comments:
            if self.delete_selenium_comment(comment):
                self.update_is_deleted(comment, type="comment")
                pass

    def delete_selenium_comment(self, comment):
        if not comment[5] == 'temp':
            self.logger.debug(comment)
            return self.dogdripBrowser.delete_comment(comment)

    def __del__(self):
        self.logger.debug("DogdripRemover 인스턴스가 종료되었습니다.")
        try:
            self.dogdripBrowser.quit()
            self.cur.close()
            self.conn.close()
        except Exception as e:
            self.logger.exception(str(e))
            pass
