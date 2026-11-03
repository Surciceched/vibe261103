"""
네이버페이 증권 미국 주식 페이지에서 나스닥 종목을 시가총액순으로 수집하는 PyQt6 GUI 앱
'항목 더보기' 버튼을 눌러 다음 페이지를 불러옴. 표 데이터는 브라우저에서 JavaScript로 채워지므로 Selenium으로 렌더링한 뒤 BeautifulSoup4로 파싱

주의: stock.naver.com의 robots.txt는 일반 수집기의 접근을 허용하지 않음 (User-agent: * / Disallow: /)
개인 학습 용도로 가끔만 실행하고, 반복 수집이나 데이터 재배포 전에는 네이버 이용약관을 확인할 것

필요 패키지:
    pip install beautifulsoup4 selenium PyQt6

실행 (Chrome 필요):
    python naver_nasdaq_crawler.py
"""

import contextlib
import csv
import re
import sys
import time

from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from selenium import webdriver
from selenium.webdriver.common.by import By

# 첫 화면(/market/stock/usa)의 표는 일부 종목만 보여주므로 '전체 종목보기' 목록을 사용. 시가총액순
URL = "https://stock.naver.com/market/stock/usa/stocklist/marketValue?stockExchange=NSQ"
OUTPUT_FILE = "nasdaq_stocks.csv"
MAX_ITEMS = 200
MAX_ITEMS_LIMIT = 5000  # 입력할 수 있는 최대 건수

LOAD_MORE_BUTTON = 'button[data-nlogs="rank.stklistmore"]'
# 클래스 이름 끝의 해시는 사이트 배포 때 바뀔 수 있어 앞부분만 비교
END_OF_LIST = '[class*="end-of-list"][class*="is-visible"]'

# 화면에는 보이지 않고 스크린리더용으로만 들어 있는 문구
HIDDEN_TEXTS = ("관심종목에 추가", "가격이 업데이트되었습니다")

WAIT_SECONDS = 15

NAME_HEADER = "종목명"
UNITS = {"만": 10**4, "억": 10**8, "조": 10**12}
RANK_PREFIX = re.compile(r"\d+\s+")                     # '1 애플 AAPL'의 순위
CHANGE_RATE = re.compile(r"\(([+-]?[\d,.]+)%\)")        # '하락 6.31 (-1.83%)'의 등락률
NUMBER = re.compile(r"\$?\s*(-?[\d,]+(?:\.\d+)?)\s*(만|억|조)?\s*주?")  # '$ 219.01 억', '64,757,691 주'

PRICE_HEADER = "현재가"
CHANGE_HEADER = "전일대비"
LEFT_ALIGNED_HEADERS = (NAME_HEADER, "업종")  # 나머지 열은 숫자라 오른쪽 정렬
CHANGE_WORDS = {"상승": "▲", "하락": "▼"}

UP_COLOR = "#FF4D4F"    # 상승
DOWN_COLOR = "#4D94FF"  # 하락

STYLE_SHEET = """
QMainWindow, QWidget#central { background: #000000; }
QWidget { color: #E6E6EA; font-family: "Malgun Gothic", "Segoe UI", sans-serif; font-size: 13px; }
QMessageBox { background: #141418; }

QLabel#title { font-size: 22px; font-weight: 700; color: #FFFFFF; }
QLabel#subtitle { color: #7E7F8A; }
QLabel#fieldLabel { color: #9A9BA6; }
QLabel#summaryTotal { color: #FFFFFF; font-weight: 600; }

QPushButton {
    background: #1B1B21; border: 1px solid #2E2E36; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #26262E; }
QPushButton:pressed { background: #111115; }
QPushButton:disabled { color: #55565F; background: #101013; border-color: #1C1C21; }
QPushButton#primary { background: #FFFFFF; color: #000000; border-color: #FFFFFF; }
QPushButton#primary:hover { background: #DCDCE2; border-color: #DCDCE2; }
QPushButton#primary:disabled { background: #2A2A30; color: #6C6D76; border-color: #2A2A30; }

QSpinBox {
    background: #141418; border: 1px solid #2E2E36; border-radius: 8px;
    padding: 7px 10px; min-width: 60px;
}
QSpinBox:focus { border-color: #6C6D76; }
QSpinBox:disabled { color: #55565F; }

QTableWidget {
    background: #0A0A0D; border: 1px solid #202026; border-radius: 10px;
    outline: 0; selection-background-color: #1E2028;
}
QTableWidget::item { padding: 0 12px; border-bottom: 1px solid #17171C; }
QTableWidget::item:hover { background: #14141A; }
QTableWidget::item:selected { background: #1E2028; }
QHeaderView { background: transparent; }
QHeaderView::section {
    background: #0A0A0D; color: #8A8B96; font-weight: 600; border: none;
    border-bottom: 1px solid #2E2E36; padding: 10px 12px;
}
QHeaderView::section:hover { color: #FFFFFF; }
QHeaderView::up-arrow, QHeaderView::down-arrow { image: none; width: 0; height: 0; }
QTableCornerButton::section { background: #0A0A0D; border: none; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background: #33333B; border-radius: 3px; min-height: 30px; min-width: 30px; }
QScrollBar::handle:hover { background: #4A4A54; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QProgressBar { background: #1B1B21; border: none; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: #FFFFFF; border-radius: 2px; }

QPlainTextEdit {
    background: #0A0A0D; border: 1px solid #202026; border-radius: 10px;
    padding: 6px; color: #8A8B96; font-size: 12px;
}
"""


def sort_key(header, text):
    """셀 글자를 정렬 기준으로 변환. 숫자는 값으로, 나머지는 글자로 비교하고 숫자가 글자보다 앞에 옴"""
    if header == NAME_HEADER:
        return 1, 0, RANK_PREFIX.sub("", text, count=1).casefold()
    rate = CHANGE_RATE.search(text)
    if rate:
        return 0, float(rate.group(1).replace(",", "")), ""
    number = NUMBER.fullmatch(text)
    if number:
        return 0, float(number.group(1).replace(",", "")) * UNITS.get(number.group(2), 1), ""
    return 1, 0, text.casefold()


def change_direction(change_text):
    """전일대비 글자의 등락률 부호를 반환. 상승 1, 하락 -1, 보합이거나 알 수 없으면 0"""
    rate = CHANGE_RATE.search(change_text)
    if not rate:
        return 0
    value = float(rate.group(1).replace(",", ""))
    return (value > 0) - (value < 0)


def display_text(header, text):
    """'하락 6.31 (-1.83%)' -> '▼ 6.31 (-1.83%)'. 화면 표시에만 쓰고 CSV에는 원래 글자를 저장"""
    if header == CHANGE_HEADER:
        for word, arrow in CHANGE_WORDS.items():
            if text.startswith(word):
                return arrow + text[len(word):]
    return text


def clean_cell(td):
    """'$ 338.32 가격이 업데이트되었습니다' -> '$ 338.32'"""
    text = td.get_text(" ", strip=True)
    for hidden in HIDDEN_TEXTS:
        text = text.replace(hidden, "")
    return text.strip()


def parse_table(page_html):
    """페이지 HTML에서 (머리글 목록, 행 목록)을 추출. 행은 머리글을 키로 하는 dict"""
    soup = BeautifulSoup(page_html, "html.parser")
    caption = soup.find("caption", string=lambda text: text and "주식 테이블" in text)
    if caption is None:
        return [], []
    table = caption.find_parent("table")

    headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [clean_cell(td) for td in tr.find_all("td")]
        # 로딩 중에 표시되는 빈 행은 제외
        if len(cells) == len(headers) and any(cells):
            rows.append(dict(zip(headers, cells)))
    return headers, rows


def wait_for_rows(driver, min_count=1):
    """행이 min_count개 이상 채워지고 개수가 안정될 때까지 대기
    시세가 실시간으로 바뀌므로 내용이 아니라 행 개수로 판단"""
    deadline = time.monotonic() + WAIT_SECONDS
    last_count = None
    while time.monotonic() < deadline:
        headers, rows = parse_table(driver.page_source)
        if len(rows) >= min_count and len(rows) == last_count:
            return headers, rows
        last_count = len(rows)
        time.sleep(0.5)
    raise RuntimeError(f"{WAIT_SECONDS}초 안에 표를 읽지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")


def find_load_more(driver):
    """'항목 더보기' 버튼을 반환. 목록이 끝났거나 버튼이 나타나지 않으면 None"""
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        buttons = driver.find_elements(By.CSS_SELECTOR, LOAD_MORE_BUTTON)
        if buttons:
            return buttons[0]
        if driver.find_elements(By.CSS_SELECTOR, END_OF_LIST):
            return None
        time.sleep(0.5)
    return None


def fetch_nasdaq(max_items=MAX_ITEMS):
    """나스닥 목록을 열어 '항목 더보기'를 눌러가며 페이지마다 (머리글 목록, 누적 행 목록)을 yield"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(URL)
        headers, rows = wait_for_rows(driver)
        yield headers, rows[:max_items]
        while len(rows) < max_items:
            button = find_load_more(driver)
            if button is None:
                break
            # 화면 상단에 고정된 요소에 가려져도 클릭되도록 JavaScript로 실행
            driver.execute_script("arguments[0].click();", button)
            headers, rows = wait_for_rows(driver, min_count=len(rows) + 1)
            yield headers, rows[:max_items]
            time.sleep(1)  # 서버 부담 줄이기
    finally:
        driver.quit()


def save_csv(headers, rows, filename):
    # utf-8-sig: 엑셀에서 한글이 깨지지 않도록
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class SortableItem(QTableWidgetItem):
    """'$ 1,000.00'이 '$ 9.00'보다 앞에 오지 않도록 글자 대신 sort_key로 비교"""

    def __init__(self, header, text):
        super().__init__(display_text(header, text))
        self.key = sort_key(header, text)

    def __lt__(self, other):
        return self.key < other.key


class KeepColorDelegate(QStyledItemDelegate):
    """선택된 행에서도 상승/하락 글자색이 유지되도록 함"""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        brush = index.data(Qt.ItemDataRole.ForegroundRole)
        if brush is not None:
            option.palette.setBrush(QPalette.ColorRole.HighlightedText, brush)


class CrawlWorker(QThread):
    """브라우저 작업이 화면을 멈추지 않도록 별도 스레드에서 실행"""

    page_loaded = pyqtSignal(list, list)
    log = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, max_items, parent=None):
        super().__init__(parent)
        self.max_items = max_items

    def run(self):
        # QThread 안에서 처리되지 않은 예외는 앱 전체를 종료시키므로 여기서 모두 받음
        try:
            self.crawl()
        except Exception as e:
            self.failed.emit(str(e))

    def crawl(self):
        rows = []
        # 중간에 멈춰도 브라우저가 바로 종료되도록 제너레이터를 닫음
        with contextlib.closing(fetch_nasdaq(self.max_items)) as pages:
            for headers, rows in pages:
                self.page_loaded.emit(headers, rows)
                self.log.emit(f"누적 {len(rows)}건")
                if self.isInterruptionRequested():
                    self.log.emit("중지했습니다.")
                    return

        self.log.emit(f"완료: {len(rows)}건")
        if len(rows) < self.max_items:
            self.log.emit(f"주의: 목표 {self.max_items}건보다 적습니다. 목록이 끝났거나 '항목 더보기' 버튼을 찾지 못했습니다.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("나스닥 종목 수집기")
        self.resize(1120, 760)
        self.setStyleSheet(STYLE_SHEET)
        self.headers = []
        self.rows = []
        self.worker = None
        self.build_ui()

    def build_ui(self):
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, MAX_ITEMS_LIMIT)
        self.max_spin.setValue(MAX_ITEMS)
        self.max_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self.start_button = QPushButton("수집")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_crawl)
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_crawl)
        self.save_button = QPushButton("CSV 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_results)

        title = QLabel("나스닥 종목")
        title.setObjectName("title")
        subtitle = QLabel("시가총액순 · 네이버페이 증권")
        subtitle.setObjectName("subtitle")
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        max_label = QLabel("최대 건수")
        max_label.setObjectName("fieldLabel")

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        control_row.addLayout(title_column)
        control_row.addStretch(1)
        control_row.addWidget(max_label)
        control_row.addWidget(self.max_spin)
        control_row.addSpacing(8)
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(self.save_button)

        self.total_label = QLabel()
        self.total_label.setObjectName("summaryTotal")
        self.up_label = QLabel()
        self.up_label.setStyleSheet(f"color: {UP_COLOR}; font-weight: 600;")
        self.down_label = QLabel()
        self.down_label.setStyleSheet(f"color: {DOWN_COLOR}; font-weight: 600;")
        self.update_summary()

        summary_row = QHBoxLayout()
        summary_row.setSpacing(16)
        summary_row.addWidget(self.total_label)
        summary_row.addWidget(self.up_label)
        summary_row.addWidget(self.down_label)
        summary_row.addStretch(1)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setItemDelegate(KeepColorDelegate(self.table))
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.update_header_labels)
        self.reset_sort()

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(84)
        self.log_view.setPlaceholderText("수집 버튼을 누르면 진행 상황이 여기에 표시됩니다.")

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(control_row)
        layout.addLayout(summary_row)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_view)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)

    def reset_sort(self):
        # 기본값은 첫 번째 열 기준이라, 머리글을 누르기 전에는 사이트 순서(시가총액순)를 유지하도록 해제
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    def update_header_labels(self, section, order):
        # 스타일시트를 쓰면 기본 정렬 화살표가 이미지 없이는 그려지지 않아 머리글 글자에 직접 표시
        arrow = " ▲" if order == Qt.SortOrder.AscendingOrder else " ▼"
        for column, name in enumerate(self.headers):
            self.table.horizontalHeaderItem(column).setText(name + arrow if column == section else name)

    def update_summary(self):
        directions = [change_direction(stock.get(CHANGE_HEADER, "")) for stock in self.rows]
        self.total_label.setText(f"전체 {len(self.rows)}")
        self.up_label.setText(f"▲ 상승 {directions.count(1)}")
        self.down_label.setText(f"▼ 하락 {directions.count(-1)}")

    def start_crawl(self):
        if self.worker is not None:
            return

        self.headers = []
        self.rows = []
        self.reset_sort()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.update_summary()
        self.log_view.clear()
        self.progress_bar.setRange(0, self.max_spin.value())
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.max_spin.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.log_view.appendPlainText("브라우저를 실행해 페이지를 불러옵니다.")

        self.worker = CrawlWorker(self.max_spin.value(), self)
        self.worker.page_loaded.connect(self.show_rows)
        self.worker.log.connect(self.log_view.appendPlainText)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.crawl_finished)
        self.worker.start()

    def stop_crawl(self):
        if self.worker is not None:
            self.worker.requestInterruption()
            self.stop_button.setEnabled(False)
            self.log_view.appendPlainText("진행 중인 요청이 끝나면 중지합니다.")

    def show_rows(self, headers, rows):
        self.headers = headers
        self.rows = rows
        if self.table.columnCount() != len(headers):
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for column, key in enumerate(headers):
                self.table.horizontalHeaderItem(column).setTextAlignment(self.cell_alignment(key))

        # 정렬이 켜져 있으면 셀을 넣는 도중에 행 순서가 바뀌어 값이 섞이므로, 채운 뒤 다시 켬
        self.table.setSortingEnabled(False)
        # 시세가 페이지마다 바뀌므로 이미 표시한 행도 새 값으로 갱신
        self.table.setRowCount(len(rows))
        for row, stock in enumerate(rows):
            color = {1: QColor(UP_COLOR), -1: QColor(DOWN_COLOR)}.get(change_direction(stock.get(CHANGE_HEADER, "")))
            for column, key in enumerate(headers):
                item = SortableItem(key, stock[key])
                item.setTextAlignment(self.cell_alignment(key))
                if color is not None and key in (PRICE_HEADER, CHANGE_HEADER):
                    item.setForeground(color)
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)
        self.update_summary()
        self.progress_bar.setValue(len(rows))

    @staticmethod
    def cell_alignment(header):
        horizontal = Qt.AlignmentFlag.AlignLeft if header in LEFT_ALIGNED_HEADERS else Qt.AlignmentFlag.AlignRight
        return horizontal | Qt.AlignmentFlag.AlignVCenter

    def show_error(self, message):
        self.log_view.appendPlainText(f"오류: {message}")
        QMessageBox.critical(self, "오류", message)

    def crawl_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.max_spin.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(bool(self.rows))
        self.progress_bar.setVisible(False)

    def save_results(self):
        filename, _ = QFileDialog.getSaveFileName(self, "CSV 저장", OUTPUT_FILE, "CSV 파일 (*.csv)")
        if not filename:
            return
        try:
            save_csv(self.headers, self.rows, filename)
        except OSError as e:
            # 엑셀에서 같은 파일을 열어 둔 경우에도 여기로 옴 (PermissionError)
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n파일이 다른 프로그램에서 열려 있으면 닫고 다시 시도하세요.")
            return
        self.log_view.appendPlainText(f"저장 완료: {filename} ({len(self.rows)}건)")

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
