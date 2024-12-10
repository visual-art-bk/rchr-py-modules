import traceback
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from contextlib import contextmanager
from app.core.utils.Logger import Logger

MAX_REQUEST = 10


class SeniumScraper:

    logger = Logger(
        name="SeniumScraper", log_file="SeniumScraper.log"
    ).get_logger()

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.target_link = None

    def goto(self, url):
        self.target_link = url
        self.driver.get(url)
        self.driver.maximize_window()

    def search_keyword_in_form(self, keyword, by, expression):
        if not keyword:
            raise ValueError("ValueError - 검색에 사용되는 키워드 입력은 필수")

        SeniumScraper._validate_selenium_input(
            by=by, expression=expression, context="검색"
        )

        try:
            search_box = self.find_element(
                by=by,
                expression=expression,
                element_description="검색창 폼",
            )
            if not search_box:
                self.logger(f"{expression} 에 해당하는 검색창 폼 엘리멘트 없음")
                return False

            search_box.send_keys(keyword)
            search_box.submit()
            return True
        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context="검색창 폼 엘리멘트", exception=e
            )
            return False

    def find_element(
        self,
        by,
        expression="정의되지않음",
        element_description="정의되지않은-엘레멘트",
        timeout=10,
    ):
        SeniumScraper._validate_selenium_input(
            by=by, expression=expression, context="검색"
        )

        try:

            element = WebDriverWait(self.driver, timeout=timeout).until(
                EC.presence_of_element_located((by, expression))
            )

            if not element:
                self.logger.info(f"{expression} 에 해당되는 엘리멘트 없음")
                return None

            return element

        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context=element_description, exception=e
            )

            return None

    def find_all_element(
        self,
        by,
        expression="정의되지않음",
        element_description="multiple element정의되지않은-엘레멘트들",
        timeout=10,
    ):
        SeniumScraper._validate_selenium_input(
            by=by, expression=expression, context="검색"
        )

        try:

            elements = WebDriverWait(self.driver, timeout=timeout).until(
                EC.presence_of_all_elements_located((by, expression))
            )

            if not elements:
                self.logger.info(f"{expression} 에 해당되는 엘리멘트들 없음")
                return None

            return elements

        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context=element_description, exception=e
            )

            return None

    def find_element_in_parent(
        self,
        parent,
        by,
        expression="정의되지않음",
        element_description="multiple element정의되지않은-엘레멘트들",
        timeout=10,
    ):
        try:
            children = WebDriverWait(parent, timeout=timeout).until(
                EC.presence_of_element_located((by, expression))
            )

            return children

        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context=element_description, exception=e
            )

            return None

    @contextmanager
    def switch_to_iframe(self, timeout=10):
        """
        주어진 iframe으로 전환하고, 작업 완료 후 기본 컨텍스트로 복귀하는 함수.
        :param iframe_locator: iframe을 찾기 위한 Selenium By locator (예: (By.ID, "iframe-id"))
        :param timeout: iframe 탐색 대기 시간 (기본값: 10초)
        """
        element_description = "iframe"
        expression = "iframe"

        try:

            iframe = self.find_element(
                by=By.CSS_SELECTOR,
                element_description=element_description,
                expression=expression,
            )

            if not iframe:
                return False

            self.driver.switch_to.frame(iframe)

            self.logger.info(f"iframe 전환 성공")

            yield

        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context=element_description, exception=e
            )

        finally:
            if iframe:

                self.driver.switch_to.default_content()
                self.logger.info("iframe에서 복귀")
                return True
            return False

    def scroll_with_more_btn(
        self, by, expression, max_scroll_attempts=10, timeout=10, sleep_for_loading=1
    ):
        element_description = "더보기버튼"

        more_btn = None
        try:

            more_btn = self.find_element(
                by=by,
                element_description=element_description,
                expression=expression,
                timeout=timeout,
            )

            if not more_btn:
                self.logger.info(
                    f"By: {by}, Exp: {expression}에 해당하는 더보기버튼없음"
                )
                return False
        except Exception as e:
            SeniumScraper.handle_exception(
                expression=expression, context=element_description, exception=e
            )

        scroll_attempts = 0
        while scroll_attempts < max_scroll_attempts:
            self.scroll_page_to_end(sleep=sleep_for_loading)

            more_btn.click()

            self.scroll_page_to_end(sleep=sleep_for_loading)

            scroll_attempts += 1
        return True

    def scroll_page_to_end(self, sleep=0.5, max_attempts=10):
        """
        웹 페이지가 끝까지 로드될 때까지 스크롤하는 메서드.
        - sleep: 각 스크롤 후 대기 시간 (초)
        - max_attempts: 스크롤 시도 횟수 제한
        """
        attempts = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while attempts < max_attempts:
            # 페이지 끝까지 스크롤
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(sleep)

            # 스크롤 후 페이지 높이 확인
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # 페이지 높이가 더 이상 증가하지 않으면 종료
            if new_height == last_height:
                break

            # 업데이트된 높이 저장 및 시도 횟수 증가
            last_height = new_height
            attempts += 1

        if attempts == max_attempts:
            self.logger.info(
                f"최대 스크롤 시도에 도달하여 중지 총 시도 횟수: {attempts}"
            )

    @staticmethod
    def _validate_selenium_input(by, expression, context="검색"):
        if not by:
            raise ValueError(
                f"ValueError - {context}에 사용되는 'by'는 필수\n"
                f" 예: By.CSS_SELECTOR"
            )
        if not expression:
            raise ValueError(
                f"ValueError - {context}에 사용되는 'expression'은 필수\n"
                f" 예: input[@name='query']"
            )

    @staticmethod
    def handle_exception(context, expression, exception):
        """
        공통 예외 처리 함수.
        :param context: 현재 실행 중인 컨텍스트 설명 (예: "엘리먼트 찾기")
        :param expression: 처리 중이던 Selenium의 표현식
        :param exception: 발생한 예외 객체
        """
        if isinstance(exception, TimeoutException):
            SeniumScraper.logger.exception(
                f"TimeoutException: {context}에서 '{expression}' 처리 중 시간초과\n"
                f"Msg: {exception}"
            )
        elif isinstance(exception, NoSuchElementException):
            SeniumScraper.logger.exception(
                f"NoSuchElementException: {context}에서 '{expression}' 처리 중 엘리먼트 없음\n"
                f"Msg: {exception}"
            )
        else:
            SeniumScraper.logger.exception(
                f"Exception: {context}에서 '{expression}' 처리 중 예외 발생\n"
                f"Msg: {exception}"
            )
