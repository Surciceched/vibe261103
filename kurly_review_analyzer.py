"""
마켓컬리 상품 후기를 수집해 Pandas로 긍정/부정을 분석하고 matplotlib 파이차트로 보여주는 PyQt6 GUI 앱
상품 페이지가 후기를 불러올 때 쓰는 JSON API를 페이지 단위로 호출하므로 브라우저가 필요 없음

감성 분류는 별점이 없는 컬리 후기의 특성상 글자를 보고 판단함. 키워드/문구 규칙 기반이라 추정치이며,
반어법이나 규칙에 없는 표현은 틀릴 수 있으므로 표의 '근거' 열로 판단 이유를 확인할 수 있게 함

주의: 개인 학습 용도로 가끔만 실행하고, 반복 수집이나 데이터 재배포 전에는 컬리 이용약관을 확인할 것
작성자 이름은 수집하지 않음

필요 패키지:
    pip install requests pandas matplotlib PyQt6

실행:
    python kurly_review_analyzer.py
"""

import re
import sys
import time
from collections import Counter

import matplotlib

matplotlib.use("QtAgg")

import pandas as pd
import requests
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
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
    QVBoxLayout,
    QWidget,
)

DEFAULT_URL = "https://www.kurly.com/goods/1000572062?collectionCode=2611-blackweek-home-01"
REVIEWS_API = "https://api.kurly.com/product-review/v4/contents-products/{product_id}/reviews"
COUNT_API = "https://api.kurly.com/product-review/v1/contents-products/{product_id}/count"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Referer": "https://www.kurly.com/",
}
PRODUCT_ID = re.compile(r"/goods/(\d+)")
MAX_ITEMS = 300
MAX_ITEMS_LIMIT = 2000  # 입력할 수 있는 최대 건수
PAGE_SIZE = 50
REQUEST_DELAY = 0.5     # 서버 부담 줄이기
TIMEOUT = 15
SORT_TYPES = {"최신순": "RECENTLY", "추천순": "RECOMMEND"}
OUTPUT_FILE = "kurly_reviews.csv"

POSITIVE = "긍정"
NEGATIVE = "부정"
NEUTRAL = "중립"
LABELS = (POSITIVE, NEUTRAL, NEGATIVE)
NEGATIVE_WEIGHT = 1.5   # 후기는 칭찬으로 시작하는 경우가 많아 불만 표현이 하나라도 있으면 더 크게 반영

# 의견이 아닌 문구. 다른 규칙이 잘못 세지 않도록 가장 먼저 지움 (후기 좋아서 구매, 맛있었음 좋겠네요)
IGNORED = re.compile(
    r"(후기|리뷰|평점|평이|평)[가-힣]{0,6}?(좋아|좋고|좋길|좋은|많아|믿고|보고)"
    r"|[가-힣]*(으면|았음|었음|였음)좋겠[가-힣]*"
    r"|(맛있|좋)을(것|거|듯|까)[가-힣]*|맛있겠[가-힣]*|맛있기를[가-힣]*|잘먹을게[가-힣]*"
    r"|(맛있어|간편해|좋아)보[가-힣]*"
)
# 부정 표현을 부정해 칭찬이 되는 문구. '짜', '질기' 같은 부정어보다 먼저 찾음
NEGATED_NEGATIVE = re.compile(
    r"(안|덜)(짜|짠|달|질기|질긴|비린|비려|느끼)|(짜|달|질기|비리|느끼하|싱겁|번거롭|귀찮|비싸)(지|진|지도|지는)(않|안)"
    r"|별로안(짜|달|질|비)|(잡내|누린내|비린내|냄새)[가-힣]?(없|안나|하나도)|냄새나지않"
    r"|(불만|아쉬운점|아쉬울게|후회|실망|부족함|부족)[가-힣.]{0,2}(없|안|하지않)"
    r"|(귀찮|번거|힘들|피곤)[가-힣]{0,2}(때|날)|손색없"
)
NEGATIVE_WORDS = re.compile(
    r"맛없|맛이없|노맛|불호|흐물|작은양|(안|못)맛있|(맛있|좋)(지|진)[가-힣]?(않|못)|안좋|별로|그저그|그냥그|그닥|그다지"
    r"|실망|후회|최악|비추|불만|아쉬|번거|귀찮|힘드|힘들|헷갈|비싸|비쌈"
    r"|재구매[가-힣]{0,4}?(안|없|않|못|글쎄|고민)|다시는|안살|안사|안시킬"
    r"|(한번|1번|한개)[가-힣]{0,6}(로|걸로)만족"
    r"|(?<!진)(?<!가)(?<!공)(?<!꽉)짜(요|네|다|서|고|더|게|군|니)|짠맛|싱거|싱겁"
    r"|(너무|많이|엄청)달|단맛이강|(?<!배)달아(요|서)|느끼해|느끼하|느끼함"
    r"|질기|질겨|질겼|질김|비린|비려|잡내|누린내|냄새나|냉동내"
    r"|물러|무른|(?<!이)상한|상했|썩었|썩은|곰팡|적은편|양이적|양이작|부족"
    r"|얼었다녹|터져|터졌|파손|찢어|샜|배송이?늦|늦게(왔|도착|배송)"
    r"|예전같지|예전만|맛이변|맛이달라|예전그맛이(\.|…|$)"
)
POSITIVE_WORDS = re.compile(
    r"맛있|맛잇|맛나|맛났|맛납|맛남|존맛|꿀맛|짱맛|맛좋|맛도좋|맛은좋|맛이좋|맛도괜|맛집|맛은있|맛도있|마싯|먹을만"
    r"|좋|조아|괜찮|됀찮|굿|굳|👍|최고|짱|추천|강추|만족|감사|훌륭|완벽|대박"
    r"|재구매|재재구매|또구매|또주문|또샀|또시|또사|또먹|쟁여|쟁겨|쟁이|필수템|선호|자주|종종|항상|믿고먹"
    r"|간편|편하|편리|편해|든든|푸짐|알차|넉넉|부드럽|부드러|부들|보들|신선|잘먹|잘드|뚝딱|밥도둑"
    r"|마음에들|맘에들|잘어울|시원|보증수표|깔끔|빠른배송|배송도?빨"
)


def parse_product_id(url):
    """'https://www.kurly.com/goods/1000572062?...' -> '1000572062'"""
    match = PRODUCT_ID.search(url)
    if match is None:
        raise ValueError("주소에서 상품 번호를 찾지 못했습니다. kurly.com/goods/... 형식의 주소를 입력해 주세요.")
    return match.group(1)


def fetch_review_count(session, product_id):
    response = session.get(COUNT_API.format(product_id=product_id), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["data"]["count"]


def fetch_reviews(product_id, max_items=MAX_ITEMS, sort_type="RECENTLY"):
    """후기를 커서 방식으로 넘겨가며 페이지마다 (누적 후기 목록, 상품의 전체 후기 수)를 yield"""
    session = requests.Session()
    session.headers.update(HEADERS)
    total = fetch_review_count(session, product_id)
    params = {"sortType": sort_type, "size": PAGE_SIZE, "onlyImage": "false"}
    reviews = {}
    while len(reviews) < max_items:
        response = session.get(REVIEWS_API.format(product_id=product_id), params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()["data"]
        for review in data["reviews"]:
            # 내용 없는 후기는 분석할 수 없고, 페이지가 겹쳐도 번호가 같으면 한 번만 저장
            if review["contents"].strip() and len(reviews) < max_items:
                reviews[review["no"]] = {
                    "번호": review["no"],
                    "작성일": review["registeredAt"][:10],
                    "내용": review["contents"].strip(),
                    "좋아요": review["likeCount"],
                }
        yield list(reviews.values()), total
        after = (data.get("nextCursor") or {}).get("after")
        if not after:
            break
        params["after"] = after
        time.sleep(REQUEST_DELAY)


def classify(text):
    """후기 한 건을 (감성, 점수, 긍정 근거 목록, 부정 근거 목록)으로 분류"""
    # '맛 있어요', '아주맛있어요'처럼 띄어쓰기가 제각각이라 공백을 없애고 비교
    remaining = re.sub(r"\s+", "", text)
    remaining = IGNORED.sub(" ", remaining)

    positive = []
    negative = []
    # 앞에서 찾은 문구를 지워 '안 짜서'를 '짜서'로 다시 세는 일을 막음
    for pattern, found in ((NEGATED_NEGATIVE, positive), (NEGATIVE_WORDS, negative), (POSITIVE_WORDS, positive)):
        found.extend(match.group(0) for match in pattern.finditer(remaining))
        remaining = pattern.sub(" ", remaining)

    score = len(positive) - NEGATIVE_WEIGHT * len(negative)
    label = POSITIVE if score > 0 else NEGATIVE if score < 0 else NEUTRAL
    return label, score, positive, negative


def analyze(reviews):
    """후기 목록을 감성 분류 결과가 붙은 DataFrame으로 변환"""
    df = pd.DataFrame(reviews, columns=["번호", "작성일", "내용", "좋아요"])
    results = df["내용"].map(classify)
    df["감성"] = results.str[0]
    df["점수"] = results.str[1]
    df["긍정근거"] = results.str[2].str.join(", ")
    df["부정근거"] = results.str[3].str.join(", ")
    df["글자수"] = df["내용"].str.len()
    return df


def summarize(df):
    """감성별 건수, 비율, 평균 글자 수, 평균 좋아요 표. 건수가 0인 감성도 행을 유지"""
    summary = df.groupby("감성").agg(건수=("번호", "size"), 평균글자수=("글자수", "mean"), 평균좋아요=("좋아요", "mean"))
    summary = summary.reindex(list(LABELS)).fillna(0)
    summary["건수"] = summary["건수"].astype(int)
    summary["비율"] = summary["건수"] / max(len(df), 1) * 100
    return summary


def top_keywords(df, column, count=5):
    """'맛있, 좋' 형식의 근거 열에서 자주 나온 표현을 반환"""
    words = Counter()
    for value in df[column]:
        words.update(word for word in value.split(", ") if word)
    return words.most_common(count)


# 차트 색: 긍정/부정은 파랑/빨강 양극, 중립은 회색. dataviz validate_palette.js로 어두운 배경 대비 검증
CHART_BACKGROUND = "#0A0A0D"
LABEL_COLORS = {POSITIVE: "#3D87EE", NEUTRAL: "#8A8B96", NEGATIVE: "#E8413F"}
TEXT_COLOR = "#E6E6EA"
MUTED_TEXT_COLOR = "#9A9BA6"
FONT_FAMILY = "Malgun Gothic"
ALL_FILTER = "전체"
EMPTY_CHART_TEXT = "수집을 시작하면 여기에 결과가 표시됩니다"

STYLE_SHEET = """
QMainWindow, QWidget#central { background: #000000; }
QWidget { color: #E6E6EA; font-family: "Malgun Gothic", "Segoe UI", sans-serif; font-size: 13px; }
QMessageBox { background: #141418; }

QLabel#title { font-size: 22px; font-weight: 700; color: #FFFFFF; }
QLabel#subtitle { color: #7E7F8A; }
QLabel#fieldLabel { color: #9A9BA6; }
QLabel#summaryTotal { color: #FFFFFF; font-weight: 600; }
QLabel#keywords { color: #9A9BA6; font-size: 12px; }

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

QSpinBox, QLineEdit, QComboBox {
    background: #141418; border: 1px solid #2E2E36; border-radius: 8px;
    padding: 7px 10px; min-width: 60px;
}
QSpinBox:focus, QLineEdit:focus, QComboBox:focus { border-color: #6C6D76; }
QSpinBox:disabled, QLineEdit:disabled, QComboBox:disabled { color: #55565F; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #141418; border: 1px solid #2E2E36; outline: 0; selection-background-color: #26262E;
}

QTableWidget {
    background: #0A0A0D; border: 1px solid #202026; border-radius: 10px;
    outline: 0; selection-background-color: #1E2028;
}
QTableWidget::item { padding: 0 12px; border-bottom: 1px solid #17171C; }
QTableWidget::item:hover { background: #14141A; }
QTableWidget::item:selected { background: #1E2028; color: #FFFFFF; }
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

QSplitter::handle { background: transparent; }

QProgressBar { background: #1B1B21; border: none; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: #FFFFFF; border-radius: 2px; }

QPlainTextEdit {
    background: #0A0A0D; border: 1px solid #202026; border-radius: 10px;
    padding: 6px; color: #8A8B96; font-size: 12px;
}
"""


def label_icon(label):
    """감성을 글자와 함께 색 점으로도 표시. 표의 글자는 읽기 쉽도록 기본 색을 유지"""
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(LABEL_COLORS[label]))
    painter.drawEllipse(0, 0, 10, 10)
    painter.end()
    return QIcon(pixmap)


class SentimentPie(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(5, 5), facecolor=CHART_BACKGROUND, layout="constrained")
        super().__init__(self.figure)
        self.setParent(parent)
        self.draw_summary(None)

    def draw_summary(self, summary):
        self.figure.clear()
        ax = self.figure.add_subplot()
        ax.set_facecolor(CHART_BACKGROUND)
        total = 0 if summary is None else int(summary["건수"].sum())
        if total == 0:
            ax.axis("off")
            ax.text(0.5, 0.5, EMPTY_CHART_TEXT, ha="center", va="center", color=MUTED_TEXT_COLOR,
                    fontfamily=FONT_FAMILY, fontsize=11, transform=ax.transAxes)
            self.draw_idle()
            return

        shown = summary[summary["건수"] > 0]
        labels = [f"{name}\n{row['건수']:.0f}건 ({row['비율']:.1f}%)" for name, row in shown.iterrows()]
        # 작은 조각들이 오른쪽에 모여 글자가 겹치지 않도록, 가장 큰 긍정 조각의 시작 각도를 정함
        ax.pie(
            shown["건수"],
            labels=labels,
            colors=[LABEL_COLORS[name] for name in shown.index],
            startangle=30,
            labeldistance=1.14,
            wedgeprops={"edgecolor": CHART_BACKGROUND, "linewidth": 2},
            textprops={"color": TEXT_COLOR, "fontfamily": FONT_FAMILY, "fontsize": 10},
        )
        ax.set_title(f"후기 {total}건의 긍정/부정 비율", color=TEXT_COLOR, fontfamily=FONT_FAMILY,
                     fontsize=13, fontweight="bold", pad=18)
        handles = [Line2D([], [], marker="o", linestyle="", markersize=8, color=LABEL_COLORS[name], label=name)
                   for name in LABELS]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=False,
                  labelcolor=MUTED_TEXT_COLOR, prop={"family": FONT_FAMILY, "size": 10})
        self.draw_idle()


class CrawlWorker(QThread):
    """네트워크 작업이 화면을 멈추지 않도록 별도 스레드에서 실행"""

    page_loaded = pyqtSignal(list, int)
    log = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, product_id, max_items, sort_type, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.max_items = max_items
        self.sort_type = sort_type

    def run(self):
        # QThread 안에서 처리되지 않은 예외는 앱 전체를 종료시키므로 여기서 모두 받음
        try:
            self.crawl()
        except requests.RequestException as e:
            self.failed.emit(f"후기를 불러오지 못했습니다: {e}")
        except (KeyError, TypeError, ValueError) as e:
            self.failed.emit(f"응답 형식이 예상과 다릅니다. API가 바뀌었을 수 있습니다: {e!r}")

    def crawl(self):
        reviews = []
        for reviews, total in fetch_reviews(self.product_id, self.max_items, self.sort_type):
            self.page_loaded.emit(reviews, total)
            self.log.emit(f"누적 {len(reviews)}건 / 상품 전체 후기 {total:,}건")
            if self.isInterruptionRequested():
                self.log.emit("중지했습니다.")
                return

        self.log.emit(f"완료: {len(reviews)}건")
        if len(reviews) < self.max_items:
            self.log.emit(f"주의: 목표 {self.max_items}건보다 적습니다. 상품의 후기가 더 없습니다.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("컬리 후기 감성 분석")
        self.resize(1320, 800)
        self.setStyleSheet(STYLE_SHEET)
        self.df = analyze([])
        self.worker = None
        self.icons = {label: label_icon(label) for label in LABELS}
        self.build_ui()

    def build_ui(self):
        title = QLabel("컬리 후기 감성 분석")
        title.setObjectName("title")
        subtitle = QLabel("키워드 규칙으로 분류한 추정치 · 판단 근거는 표에서 확인")
        subtitle.setObjectName("subtitle")
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        self.url_edit = QLineEdit(DEFAULT_URL)
        self.url_edit.setPlaceholderText("https://www.kurly.com/goods/상품번호")
        self.url_edit.returnPressed.connect(self.start_crawl)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, MAX_ITEMS_LIMIT)
        self.max_spin.setValue(MAX_ITEMS)
        self.max_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(SORT_TYPES)

        self.start_button = QPushButton("수집 및 분석")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_crawl)
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_crawl)
        self.save_button = QPushButton("CSV 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_results)

        url_label = QLabel("상품 주소")
        url_label.setObjectName("fieldLabel")
        max_label = QLabel("수집 건수")
        max_label.setObjectName("fieldLabel")

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        control_row.addWidget(url_label)
        control_row.addWidget(self.url_edit, 1)
        control_row.addSpacing(8)
        control_row.addWidget(max_label)
        control_row.addWidget(self.max_spin)
        control_row.addWidget(self.sort_combo)
        control_row.addSpacing(8)
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(self.save_button)

        self.pie = SentimentPie()
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summaryTotal")
        self.summary_label.setWordWrap(True)
        self.keywords_label = QLabel()
        self.keywords_label.setObjectName("keywords")
        self.keywords_label.setWordWrap(True)

        chart_column = QVBoxLayout()
        chart_column.setContentsMargins(0, 0, 0, 0)
        chart_column.setSpacing(8)
        chart_column.addWidget(self.pie, 1)
        chart_column.addWidget(self.summary_label)
        chart_column.addWidget(self.keywords_label)
        chart_panel = QWidget()
        chart_panel.setLayout(chart_column)

        filter_label = QLabel("감성 필터")
        filter_label.setObjectName("fieldLabel")
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(ALL_FILTER)
        self.filter_combo.addItems(LABELS)
        self.filter_combo.currentTextChanged.connect(self.show_table)
        self.count_label = QLabel()
        self.count_label.setObjectName("fieldLabel")

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.filter_combo)
        filter_row.addWidget(self.count_label)
        filter_row.addStretch(1)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["감성", "내용", "근거", "좋아요", "작성일"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 150)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # 기본값은 첫 번째 열 기준이라, 머리글을 누르기 전에는 사이트 순서를 유지하도록 해제
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        table_column = QVBoxLayout()
        table_column.setContentsMargins(0, 0, 0, 0)
        table_column.setSpacing(8)
        table_column.addLayout(filter_row)
        table_column.addWidget(self.table, 1)
        table_panel = QWidget()
        table_panel.setLayout(table_column)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(chart_panel)
        splitter.addWidget(table_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([440, 840])

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(72)
        self.log_view.setPlaceholderText("수집 버튼을 누르면 진행 상황이 여기에 표시됩니다.")

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(title_column)
        layout.addLayout(control_row)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_view)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.show_results()

    def set_controls_enabled(self, enabled):
        for widget in (self.url_edit, self.max_spin, self.sort_combo, self.start_button):
            widget.setEnabled(enabled)
        self.stop_button.setEnabled(not enabled)

    def start_crawl(self):
        if self.worker is not None:
            return
        try:
            product_id = parse_product_id(self.url_edit.text())
        except ValueError as e:
            QMessageBox.warning(self, "주소 확인", str(e))
            return

        self.df = analyze([])
        self.show_results()
        self.log_view.clear()
        self.progress_bar.setRange(0, self.max_spin.value())
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.set_controls_enabled(False)
        self.save_button.setEnabled(False)
        self.log_view.appendPlainText(f"상품 {product_id}의 후기를 불러옵니다.")

        sort_type = SORT_TYPES[self.sort_combo.currentText()]
        self.worker = CrawlWorker(product_id, self.max_spin.value(), sort_type, self)
        self.worker.page_loaded.connect(self.update_reviews)
        self.worker.log.connect(self.log_view.appendPlainText)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.crawl_finished)
        self.worker.start()

    def stop_crawl(self):
        if self.worker is not None:
            self.worker.requestInterruption()
            self.stop_button.setEnabled(False)
            self.log_view.appendPlainText("진행 중인 요청이 끝나면 중지합니다.")

    def update_reviews(self, reviews, _total):
        self.df = analyze(reviews)
        self.show_results()
        self.progress_bar.setValue(len(reviews))

    def show_results(self):
        summary = summarize(self.df)
        self.pie.draw_summary(summary)
        self.show_table()
        if self.df.empty:
            self.summary_label.setText("")
            self.keywords_label.setText("")
            return

        self.summary_label.setText("   ".join(f"{name} {summary.loc[name, '건수']}건" for name in LABELS))
        lines = []
        for name, column in ((POSITIVE, "긍정근거"), (NEGATIVE, "부정근거")):
            words = ", ".join(f"{word}({count})" for word, count in top_keywords(self.df, column))
            lines.append(f"{name} 표현 TOP 5: {words or '없음'}")
        for name in (POSITIVE, NEGATIVE):
            lines.append(f"{name} 후기 평균 {summary.loc[name, '평균글자수']:.0f}자 · 좋아요 {summary.loc[name, '평균좋아요']:.1f}개")
        self.keywords_label.setText("\n".join(lines))

    def show_table(self):
        selected = self.filter_combo.currentText()
        rows = self.df if selected == ALL_FILTER else self.df[self.df["감성"] == selected]
        self.count_label.setText(f"{len(rows)}건")

        # 정렬이 켜져 있으면 셀을 넣는 도중에 행 순서가 바뀌어 값이 섞이므로, 채운 뒤 다시 켬
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row, review in enumerate(rows.itertuples(index=False)):
            label_item = QTableWidgetItem(self.icons[review.감성], review.감성)
            content_item = QTableWidgetItem(review.내용.replace("\n", " "))
            content_item.setToolTip(review.내용)
            evidence = self.evidence_text(review.긍정근거, review.부정근거)
            evidence_item = QTableWidgetItem(evidence)
            evidence_item.setToolTip(evidence)
            like_item = QTableWidgetItem()
            like_item.setData(Qt.ItemDataRole.DisplayRole, int(review.좋아요))  # 글자가 아닌 숫자로 정렬
            like_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            date_item = QTableWidgetItem(review.작성일)
            for column, item in enumerate((label_item, content_item, evidence_item, like_item, date_item)):
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)

    @staticmethod
    def evidence_text(positive, negative):
        parts = []
        if positive:
            parts.append(f"+ {positive}")
        if negative:
            parts.append(f"- {negative}")
        return "  ".join(parts)

    def save_results(self):
        filename, _ = QFileDialog.getSaveFileName(self, "CSV로 저장", OUTPUT_FILE, "CSV 파일 (*.csv)")
        if not filename:
            return
        try:
            # utf-8-sig: 엑셀에서 한글이 깨지지 않도록
            self.df.to_csv(filename, index=False, encoding="utf-8-sig")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))
            return
        self.log_view.appendPlainText(f"저장: {filename}")

    def show_error(self, message):
        self.log_view.appendPlainText(f"오류: {message}")
        QMessageBox.critical(self, "오류", message)

    def crawl_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_controls_enabled(True)
        self.save_button.setEnabled(not self.df.empty)
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.requestInterruption()
            self.worker.wait(TIMEOUT * 1000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
