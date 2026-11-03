"""
네이버 공식 검색 API로 뉴스 기사를 수집하는 PyQt6 GUI 앱
'원문에서 본문 추출'을 켜면 언론사 원문 페이지의 본문도 BeautifulSoup4로 추출 (robots.txt가 허용하는 경우만)

필요 패키지:
    pip install requests beautifulsoup4 PyQt6 openpyxl

API 키 발급: https://developers.naver.com/apps 에서 '검색' API로 애플리케이션 등록
키는 앱 화면에 입력하며 파일로 저장하지 않음. 환경변수 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET이 있으면 자동으로 채움

실행:
    python naver_news_crawler.py
"""

import csv
import html
import os
import sys
import time
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

API_URL = "https://openapi.naver.com/v1/search/news.json"
API_MAX_DISPLAY = 100  # 한 번에 요청할 수 있는 최대 건수
API_MAX_START = 1000   # start 파라미터 최댓값

USER_AGENT = "naver-news-crawler/1.0"

BODY_COLUMN = 3

# 엑셀 시트 구성: (기사 키, 머리글, 열 너비)
EXCEL_COLUMNS = [
    ("title", "제목", 50),
    ("press", "언론사", 20),
    ("date", "날짜", 20),
    ("url", "링크", 40),
    ("description", "요약", 60),
    ("body", "본문", 80),
]
EXCEL_MAX_CELL_CHARS = 32767  # 엑셀 셀 하나에 들어가는 최대 글자 수
EXCEL_MAX_LINK_CHARS = 2000   # 이보다 긴 링크는 엑셀이 파일 오류로 처리할 수 있음


def clean_html(text):
    """API 응답의 <b> 태그와 &quot; 같은 HTML 엔티티를 제거"""
    return BeautifulSoup(text, "html.parser").get_text()


def format_date(pub_date):
    """'Mon, 03 Nov 2026 13:52:07 +0900' -> '2026-11-03 13:52:07'"""
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return pub_date


def search_news(query, client_id, client_secret, max_articles=10, sort="sim"):
    """검색 API를 호출해 기사 목록을 요청 단위로 yield. sort - sim: 관련도순, date: 최신순"""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    count = 0
    start = 1

    while count < max_articles and start <= API_MAX_START:
        params = {
            "query": query,
            "display": min(API_MAX_DISPLAY, max_articles - count),
            "start": start,
            "sort": sort,
        }
        resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"API 오류 {resp.status_code}: {resp.text[:200]}")

        items = resp.json().get("items", [])
        if not items:
            break

        batch = []
        for item in items:
            url = item.get("originallink") or item["link"]
            batch.append({
                "title": clean_html(item["title"]),
                "press": urlparse(url).netloc,
                "date": format_date(item.get("pubDate")),
                "url": url,
                "description": clean_html(item.get("description", "")),
                "body": "",
            })

        count += len(items)
        start += len(items)
        yield batch
        time.sleep(0.2)


def robots_allows(url, cache):
    """해당 사이트의 robots.txt가 수집을 허용하는지 확인. 확인할 수 없으면 허용하지 않은 것으로 처리"""
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    if root not in cache:
        parser = RobotFileParser()
        try:
            resp = requests.get(f"{root}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=10)
        except requests.RequestException:
            cache[root] = None
        else:
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
                cache[root] = parser
            elif 400 <= resp.status_code < 500:
                cache[root] = "allow_all"  # robots.txt가 없는 사이트
            else:
                cache[root] = None

    rules = cache[root]
    if rules is None:
        return False
    if rules == "allow_all":
        return True
    return rules.can_fetch(USER_AGENT, url)


def extract_body(url):
    """언론사 원문 페이지 본문 추출 (사이트마다 구조가 달라 일반적인 추출만 수행)"""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    resp.raise_for_status()
    # bytes를 넘겨 EUC-KR 언론사 페이지도 meta charset 기준으로 디코딩
    soup = BeautifulSoup(resp.content, "html.parser")
    container = soup.find("article") or soup.body
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")] if container else []
    return "\n".join(p for p in paragraphs if len(p) > 20)


def iter_bodies(articles):
    """기사별로 (행 번호, 본문, 로그 메시지)를 yield. 가져오지 못한 기사의 본문은 빈 문자열"""
    robots_cache = {}
    total = len(articles)
    for row, article in enumerate(articles):
        url = article["url"]
        prefix = f"[{row + 1}/{total}]"
        try:
            if not robots_allows(url, robots_cache):
                yield row, "", f"{prefix} robots.txt로 건너뜀: {url}"
                continue
            body = extract_body(url)
        except requests.RequestException as e:
            yield row, "", f"{prefix} 실패: {url} ({e})"
        else:
            yield row, body, f"{prefix} 본문 {len(body)}자: {article['title'][:40]}"
            time.sleep(1)  # 서버 부담 줄이기


def save_csv(rows, filename):
    # utf-8-sig: 엑셀에서 한글이 깨지지 않도록
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "press", "date", "url", "description", "body"])
        writer.writeheader()
        writer.writerows(rows)


def save_excel(rows, filename):
    """기사 목록을 .xlsx로 저장하고, 셀 글자 수 제한으로 잘린 칸의 수를 반환"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "뉴스"

    for column, (_, header, width) in enumerate(EXCEL_COLUMNS, 1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = Font(bold=True)
        sheet.column_dimensions[cell.column_letter].width = width

    truncated = 0
    for row, article in enumerate(rows, 2):
        for column, (key, _, _) in enumerate(EXCEL_COLUMNS, 1):
            value = ILLEGAL_CHARACTERS_RE.sub("", article[key])
            if len(value) > EXCEL_MAX_CELL_CHARS:
                value = value[:EXCEL_MAX_CELL_CHARS]
                truncated += 1
            cell = sheet.cell(row=row, column=column, value=value)
            # '='로 시작하는 기사 제목 등이 수식으로 실행되지 않도록 문자열로 고정
            cell.data_type = "s"
            if key == "url" and value.startswith(("http://", "https://")) and len(value) <= EXCEL_MAX_LINK_CHARS:
                cell.hyperlink = value
                cell.style = "Hyperlink"

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(filename)
    return truncated


class CrawlWorker(QThread):
    """네트워크 작업이 화면을 멈추지 않도록 별도 스레드에서 실행"""

    articles_found = pyqtSignal(list)
    body_ready = pyqtSignal(int, str)
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, query, client_id, client_secret, max_articles, sort, fetch_body, parent=None):
        super().__init__(parent)
        self.query = query
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_articles = max_articles
        self.sort = sort
        self.fetch_body = fetch_body

    def run(self):
        # QThread 안에서 처리되지 않은 예외는 앱 전체를 종료시키므로 여기서 모두 받음
        try:
            self.crawl()
        except Exception as e:
            self.failed.emit(str(e))

    def crawl(self):
        articles = []
        batches = search_news(self.query, self.client_id, self.client_secret, self.max_articles, self.sort)
        for batch in batches:
            articles.extend(batch)
            self.articles_found.emit([dict(a) for a in batch])
            self.log.emit(f"[API] 누적 {len(articles)}건")
            if self.isInterruptionRequested():
                self.log.emit("중지했습니다.")
                return

        if not articles:
            self.log.emit("검색 결과가 없습니다.")
            return

        if self.fetch_body:
            self.progress.emit(0, len(articles))
            for row, body, message in iter_bodies(articles):
                self.body_ready.emit(row, body)
                self.progress.emit(row + 1, len(articles))
                self.log.emit(message)
                if self.isInterruptionRequested():
                    self.log.emit("중지했습니다.")
                    return

        self.log.emit(f"완료: {len(articles)}건")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 수집기")
        self.resize(1100, 760)
        self.articles = []
        self.worker = None
        self.build_ui()

    def build_ui(self):
        self.query_edit = QLineEdit("반도체")
        self.query_edit.setPlaceholderText("검색어")
        self.query_edit.returnPressed.connect(self.start_search)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, API_MAX_START + API_MAX_DISPLAY - 1)
        self.max_spin.setValue(10)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("관련도순", "sim")
        self.sort_combo.addItem("최신순", "date")

        self.body_check = QCheckBox("원문에서 본문 추출")
        self.body_check.setToolTip("robots.txt가 허용하는 언론사 페이지에서만 가져옵니다.")

        self.search_button = QPushButton("검색")
        self.search_button.clicked.connect(self.start_search)
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_search)
        self.save_button = QPushButton("CSV 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_results_csv)
        self.excel_button = QPushButton("엑셀 저장")
        self.excel_button.setEnabled(False)
        self.excel_button.clicked.connect(self.save_results_excel)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("검색어"))
        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(QLabel("최대 건수"))
        search_row.addWidget(self.max_spin)
        search_row.addWidget(self.sort_combo)
        search_row.addWidget(self.body_check)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.stop_button)
        search_row.addWidget(self.save_button)
        search_row.addWidget(self.excel_button)

        self.id_edit = QLineEdit(os.environ.get("NAVER_CLIENT_ID", ""))
        self.secret_edit = QLineEdit(os.environ.get("NAVER_CLIENT_SECRET", ""))
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_help = QLabel('<a href="https://developers.naver.com/apps">API 키 발급받기</a> · 입력한 키는 저장되지 않습니다.')
        key_help.setOpenExternalLinks(True)

        key_form = QFormLayout()
        key_form.addRow("Client ID", self.id_edit)
        key_form.addRow("Client Secret", self.secret_edit)
        key_form.addRow(key_help)
        key_group = QGroupBox("네이버 API 키")
        key_group.setLayout(key_form)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["제목", "언론사", "날짜", "본문"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_selected)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        self.detail.setPlaceholderText("목록에서 기사를 선택하면 내용이 표시됩니다.")

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setSizes([320, 280])

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(90)

        layout = QVBoxLayout()
        layout.addLayout(search_row)
        layout.addWidget(key_group)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_view)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def start_search(self):
        if self.worker is not None:
            return

        query = self.query_edit.text().strip()
        client_id = self.id_edit.text().strip()
        client_secret = self.secret_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "입력 확인", "검색어를 입력하세요.")
            return
        if not client_id or not client_secret:
            QMessageBox.warning(self, "입력 확인", "네이버 API 키(Client ID, Client Secret)를 입력하세요.")
            return

        self.articles = []
        self.table.setRowCount(0)
        self.detail.clear()
        self.log_view.clear()
        self.progress_bar.setVisible(False)
        self.save_button.setEnabled(False)
        self.excel_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_view.appendPlainText(f"검색어: {query}")

        self.worker = CrawlWorker(
            query,
            client_id,
            client_secret,
            self.max_spin.value(),
            self.sort_combo.currentData(),
            self.body_check.isChecked(),
            self,
        )
        self.worker.articles_found.connect(self.add_articles)
        self.worker.body_ready.connect(self.set_body)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.log_view.appendPlainText)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.search_finished)
        self.worker.start()

    def stop_search(self):
        if self.worker is not None:
            self.worker.requestInterruption()
            self.stop_button.setEnabled(False)
            self.log_view.appendPlainText("진행 중인 요청이 끝나면 중지합니다.")

    def add_articles(self, batch):
        for article in batch:
            row = len(self.articles)
            self.articles.append(article)
            self.table.insertRow(row)
            values = [article["title"], article["press"], article["date"], "-"]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        if self.table.currentRow() < 0 and self.articles:
            self.table.selectRow(0)

    def set_body(self, row, body):
        self.articles[row]["body"] = body
        self.table.item(row, BODY_COLUMN).setText(f"{len(body)}자" if body else "-")
        if self.table.currentRow() == row:
            self.show_selected()

    def update_progress(self, value, total):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(value)

    def show_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        article = self.articles[row]
        # 기사 내용은 외부에서 온 데이터이므로 HTML로 해석되지 않게 이스케이프
        title, press, date, url, description, body = (
            html.escape(article[key]) for key in ("title", "press", "date", "url", "description", "body")
        )
        parts = [
            f"<h3>{title}</h3>",
            f"<p>{press} · {date}<br><a href=\"{url}\">{url}</a></p>",
            f"<p><b>요약</b><br>{description}</p>",
        ]
        if body:
            parts.append("<p><b>본문</b><br>" + body.replace("\n", "<br>") + "</p>")
        self.detail.setHtml("".join(parts))

    def show_error(self, message):
        self.log_view.appendPlainText(f"오류: {message}")
        QMessageBox.critical(self, "오류", message)

    def search_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(bool(self.articles))
        self.excel_button.setEnabled(bool(self.articles))

    def save_results_csv(self):
        self.save_results("CSV 저장", "naver_news.csv", "CSV 파일 (*.csv)", save_csv)

    def save_results_excel(self):
        self.save_results("엑셀 저장", "naver_news.xlsx", "엑셀 파일 (*.xlsx)", save_excel)

    def save_results(self, caption, default_name, file_filter, writer):
        filename, _ = QFileDialog.getSaveFileName(self, caption, default_name, file_filter)
        if not filename:
            return
        try:
            truncated = writer(self.articles, filename)
        except OSError as e:
            # 엑셀에서 같은 파일을 열어 둔 경우에도 여기로 옴 (PermissionError)
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n파일이 다른 프로그램에서 열려 있으면 닫고 다시 시도하세요.")
            return
        self.log_view.appendPlainText(f"저장 완료: {filename} ({len(self.articles)}건)")
        if truncated:
            self.log_view.appendPlainText(f"주의: 엑셀 셀 글자 수 제한으로 {truncated}개 칸의 내용이 잘렸습니다.")

    def closeEvent(self, event):
        # 실행 중인 스레드를 정리하지 않고 종료하면 앱이 비정상 종료됨
        if self.worker is not None:
            self.worker.requestInterruption()
            self.hide()
            self.worker.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
