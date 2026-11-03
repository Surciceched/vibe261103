"""대한민국 출생 통계(KOSIS 인구동향조사)를 클렌징 · 분석하고 그래프로 보여 주는 PyQt6 GUI 앱

필요 패키지:
    pip install pandas openpyxl matplotlib PyQt6

실행 예)
    python birth_analysis.py                      # 기본 경로의 엑셀을 자동으로 불러옴
    python birth_analysis.py "다른경로.xlsx"       # 엑셀 경로 지정

결과 저장 버튼을 누르면 고른 폴더에 CSV, 리포트, 그래프 이미지를 저장합니다.
"""

import html
import sys
import warnings
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_XLSX = Path(
    r"C:\Users\user\Desktop\생산성본부_바이브코딩수업\DataSet"
    r"\출생아수__합계출산율__자연증가_등_20260605082440.xlsx"
)
OUTPUT_DIR = BASE_DIR / "birth_output"

START_YEAR = 1970
END_YEAR = 2025

# 원본 항목명 → 분석용 컬럼명
COLUMN_NAMES = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}
INT_COLUMNS = ["출생아수", "자연증가건수"]

# 항목별로 값이 가질 수 있는 범위 (벗어나면 입력 오류로 간주)
VALID_RANGES = {
    "출생아수": (1, 2_000_000),
    "자연증가건수": (-2_000_000, 2_000_000),
    "조출생률": (0, 60),
    "자연증가율": (-30, 60),
    "합계출산율": (0, 10),
    "출생성비": (90, 130),
}

# 변화 분석에 쓰는 구간 (데이터에 없는 연도가 포함된 구간은 건너뜀)
PERIODS = [(1970, 1987), (1987, 1992), (1992, 2005), (2005, 2015), (2015, 2023), (2023, 2025)]

REPLACEMENT_TFR = 2.1  # 인구대체 수준 합계출산율 (일반적으로 쓰이는 기준값)
NATURAL_SEX_RATIO = 105  # 자연 출생성비 (일반적으로 쓰이는 기준값)
DRAGON_YEARS = [1976, 1988, 2000, 2012, 2024]  # 용띠 해

# 그래프 색상
COLOR_LINE = "#2a78d6"
COLOR_NEGATIVE = "#e34948"
COLOR_TEXT = "#0b0b0b"
COLOR_TEXT_SUB = "#52514e"
COLOR_GRID = "#e6e5e0"
COLOR_REFERENCE = "#8a8984"
COLOR_SURFACE = "#fcfcfb"

STYLE_SHEET = """
QMainWindow, QWidget#central { background: #fcfcfb; }
QWidget { color: #0b0b0b; font-family: "Malgun Gothic", "Segoe UI", sans-serif; font-size: 13px; }

QLabel#title { font-size: 22px; font-weight: 700; }
QLabel#subtitle { color: #52514e; }
QLabel#fieldLabel { color: #52514e; }
QLabel#statValue { font-size: 18px; font-weight: 700; }
QLabel#statCaption { color: #52514e; font-size: 12px; }
QLabel#status { color: #52514e; font-size: 12px; }

QPushButton {
    background: #ffffff; border: 1px solid #d5d4ce; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #f1f0ec; }
QPushButton:pressed { background: #e6e5e0; }
QPushButton:disabled { color: #a3a29c; background: #f6f5f2; border-color: #e6e5e0; }
QPushButton#primary { background: #2a78d6; color: #ffffff; border-color: #2a78d6; }
QPushButton#primary:hover { background: #2268bd; border-color: #2268bd; }
QPushButton#primary:disabled { background: #c9dcf3; border-color: #c9dcf3; }

QSpinBox {
    background: #ffffff; border: 1px solid #d5d4ce; border-radius: 8px;
    padding: 6px 8px; min-width: 64px;
}
QSpinBox:focus { border-color: #2a78d6; }

QTabWidget::pane { border: 1px solid #e6e5e0; border-radius: 8px; top: -1px; background: #fcfcfb; }
QTabBar::tab {
    background: transparent; color: #52514e; padding: 9px 18px;
    border: none; border-bottom: 2px solid transparent; font-weight: 600;
}
QTabBar::tab:hover { color: #0b0b0b; }
QTabBar::tab:selected { color: #0b0b0b; border-bottom-color: #2a78d6; }

QToolBar { background: transparent; border: none; spacing: 2px; }

QTableWidget {
    background: #ffffff; border: none; outline: 0;
    selection-background-color: #e8f0fb; selection-color: #0b0b0b;
}
QTableWidget::item { padding: 0 10px; border-bottom: 1px solid #f1f0ec; }
QHeaderView::section {
    background: #ffffff; color: #52514e; font-weight: 600; border: none;
    border-bottom: 1px solid #d5d4ce; padding: 8px 10px;
}
QTextBrowser { background: #ffffff; border: none; padding: 12px; }
"""

# 데이터 탭에 보여 줄 컬럼 → 머리글
TABLE_COLUMNS = {
    "출생아수": "출생아수(명)",
    "자연증가건수": "자연증가(명)",
    "조출생률": "조출생률(천명당)",
    "자연증가율": "자연증가율(천명당)",
    "합계출산율": "합계출산율(명)",
    "출생성비": "출생성비",
    "사망자수_추정": "사망자 추정(명)",
    "출생아수_증감률": "출생아수 증감률(%)",
}

# 표를 HTML로 그릴 때 천 단위 쉼표를 넣지 않는 컬럼
NO_COMMA_KEYWORDS = ("연도",)

report_lines = []
report_html = []


def log(text=""):
    """리포트의 텍스트판과 화면용 HTML판에 함께 기록한다."""
    report_lines.append(str(text))
    if text:
        report_html.append(f"<p>{html.escape(str(text))}</p>")


def log_table(table):
    """표를 리포트에 기록한다. 화면에서 줄이 맞도록 HTML 표로도 만든다."""
    report_lines.append(table.to_string())
    report_html.append(table_to_html(table))


def section(title):
    report_lines.extend(["", "=" * 70, title, "=" * 70])
    report_html.append(f"<h2>{html.escape(title)}</h2>")


def format_cell(value, column):
    if pd.isna(value):
        return "-"
    if isinstance(value, str):
        return value
    if any(keyword in str(column) for keyword in NO_COMMA_KEYWORDS):
        return str(int(value))
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.3f}".rstrip("0")


def format_table_value(value, column):
    """데이터 탭에서 같은 컬럼의 자릿수가 들쭉날쭉하지 않게 표시한다."""
    if pd.isna(value):
        return "-"
    if column in INT_COLUMNS or column == "사망자수_추정":
        return f"{value:,}"
    if column == "합계출산율":
        # 1992년 이전은 소수 2자리까지만 제공되므로 없는 자릿수를 0으로 채우지 않는다
        text = f"{value:.3f}"
        return text[:-1] if text.endswith("0") else text
    return f"{value:+.1f}" if column == "출생아수_증감률" else f"{value:.1f}"


def table_to_html(table):
    header_style = 'style="color:#52514e; border-bottom:1px solid #d5d4ce;"'
    index_name = html.escape(str(table.index.name or ""))
    head = f'<th align="left" {header_style}>{index_name}</th>' + "".join(
        f'<th align="right" {header_style}>{html.escape(str(c))}</th>' for c in table.columns
    )
    rows = []
    for label, row in table.iterrows():
        cells = "".join(
            f'<td align="right">{html.escape(format_cell(row[c], c))}</td>' for c in table.columns
        )
        rows.append(f"<tr><td><b>{html.escape(str(label))}</b></td>{cells}</tr>")
    return (f'<table cellspacing="0" cellpadding="5"><tr>{head}</tr>{"".join(rows)}</table>')


def setup_korean_font():
    """그래프의 한글이 깨지지 않도록 설치된 한글 글꼴을 지정한다."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
        if name in installed:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# 1. 데이터 클렌징
# ---------------------------------------------------------------------------
def clean_data(path):
    """연도가 가로로 펼쳐진 KOSIS 표를 연도별 한 행의 깔끔한 표로 정리한다."""
    section("1. 데이터 클렌징")

    with warnings.catch_warnings():
        # KOSIS 파일에 기본 스타일이 없어 openpyxl이 내는 경고 (데이터와 무관)
        warnings.simplefilter("ignore", UserWarning)
        raw = pd.read_excel(path, sheet_name="데이터", header=None, dtype=str)
    log(f"원본 크기: {raw.shape[0]}행 x {raw.shape[1]}열 (항목이 행, 연도가 열인 구조)")

    # 항목이 행, 연도가 열인 표를 연도가 행이 되도록 뒤집는다
    table = raw.set_index(0).T
    table.columns = [str(c).strip() for c in table.columns]
    year_column = table.columns[0]

    missing_items = set(COLUMN_NAMES) - set(table.columns)
    if missing_items:
        raise ValueError(f"필요한 항목이 없습니다: {sorted(missing_items)}")
    df = table[[year_column, *COLUMN_NAMES]].rename(columns=COLUMN_NAMES)
    df = df.rename(columns={year_column: "연도표기"})

    # "2025 p)" 같은 연도 표기에서 숫자 연도와 잠정치 여부를 분리한다
    year_text = df["연도표기"].str.strip()
    df["연도"] = pd.to_numeric(year_text.str.extract(r"^(\d{4})")[0], errors="coerce")
    df["잠정치"] = year_text.str.contains(r"p\)", regex=True)
    provisional = df.loc[df["잠정치"], "연도"].astype(int).tolist()
    log(f"연도 표기 정리: 잠정치 표시(p) 분리 → 잠정치 연도 {provisional}")

    # 쉼표·공백·KOSIS 결측 기호를 정리한 뒤 숫자로 변환한다
    columns = list(COLUMN_NAMES.values())
    text_values = df[columns].apply(lambda s: s.str.replace(",", "").str.strip())
    numeric = text_values.apply(pd.to_numeric, errors="coerce")
    bad_values = int((numeric.isna() & text_values.notna()).sum().sum())
    df[columns] = numeric
    log(f"숫자로 변환되지 않은 값: {bad_values}개")
    log(f"결측치: {int(df[columns].isna().sum().sum())}개")

    df = df.dropna(subset=["연도"])
    if df.empty:
        raise ValueError("연도를 읽을 수 없습니다. KOSIS에서 받은 파일인지 확인하세요.")
    df["연도"] = df["연도"].astype(int)
    duplicated = int(df.duplicated("연도").sum())
    df = df.drop_duplicates("연도").sort_values("연도").reset_index(drop=True)
    log(f"중복 연도: {duplicated}개")

    expected = set(range(START_YEAR, END_YEAR + 1))
    log(f"누락 연도: {sorted(expected - set(df['연도']))} / 범위 밖 연도: "
        f"{sorted(set(df['연도']) - expected)}")

    out_of_range = 0
    for column, (low, high) in VALID_RANGES.items():
        outside = df.loc[~df[column].between(low, high), "연도"].tolist()
        out_of_range += len(outside)
        if outside:
            log(f"[주의] {column} 허용 범위({low}~{high}) 이탈: {outside}")
    log(f"허용 범위를 벗어난 값: {out_of_range}개")

    df[INT_COLUMNS] = df[INT_COLUMNS].astype("Int64")
    df = df[["연도", "잠정치", *columns]].set_index("연도")

    check_consistency(df)

    log()
    log(f"클렌징 후: {df.shape[0]}행 x {df.shape[1]}열, "
        f"{df.index.min()}~{df.index.max()}년")
    return df


def check_consistency(df):
    """지표끼리 서로 맞아떨어지는지 확인한다. 값을 바꾸지 않고 결과만 보고한다."""
    log()
    log("[지표 간 정합성 검사]")

    # 자연증가율 = 조출생률 x (자연증가건수 / 출생아수) 여야 한다
    births = df["출생아수"].astype(float)
    natural = df["자연증가건수"].astype(float)
    expected_rate = df["조출생률"] * natural / births
    gap = (expected_rate - df["자연증가율"]).abs()
    # 두 비율 모두 소수 1자리 반올림이므로 0.15 이내는 반올림 오차로 본다
    log(f"자연증가율 재계산 오차: 최대 {gap.max():.3f} (0.15 초과 연도: "
        f"{gap[gap > 0.15].index.tolist()})")

    # 출생아수 / 조출생률로 역산한 인구가 급변하면 입력 오류일 수 있다
    implied_population = births / df["조출생률"] * 1000
    jumps = implied_population.pct_change().abs()
    log(f"역산 인구: {implied_population.iloc[0] / 1e4:,.0f}만 명({df.index[0]}) → "
        f"{implied_population.iloc[-1] / 1e4:,.0f}만 명({df.index[-1]}), "
        f"전년 대비 3% 초과 변동 연도: {jumps[jumps > 0.03].index.tolist()}")

    # 합계출산율 소수 자릿수가 바뀌는 시점 (비교 시 유의)
    tfr = df["합계출산율"].dropna()
    decimals = tfr.map(lambda v: len(f"{v:.3f}".rstrip("0").split(".")[1]))
    three_digit = decimals[decimals == 3].index
    if len(three_digit):
        log(f"합계출산율 소수 3자리 표기 시작: {three_digit.min()}년 "
            "(이전은 소수 2자리까지만 제공)")


# ---------------------------------------------------------------------------
# 2. 다각도 분석
# ---------------------------------------------------------------------------
def add_derived_columns(df):
    """분석에 쓰는 파생 지표를 추가한다."""
    out = df.copy()
    births = out["출생아수"].astype(float)
    out["사망자수_추정"] = (out["출생아수"] - out["자연증가건수"]).astype("Int64")
    out["출생아수_증감"] = out["출생아수"].diff().astype("Int64")
    out["출생아수_증감률"] = births.pct_change() * 100
    out["합계출산율_증감률"] = out["합계출산율"].pct_change() * 100
    # 합계출산율 1명당 출생아수: 가임기 여성 규모와 연령 구조를 보여 주는 대리 지표
    out["출산규모지수"] = births / out["합계출산율"]
    return out


def analyze_overview(df):
    section("2. 기술통계")
    columns = list(COLUMN_NAMES.values()) + ["사망자수_추정"]
    summary = df[columns].astype(float).describe().T
    summary = summary[["mean", "std", "min", "50%", "max"]]
    summary["최저연도"] = df[columns].astype(float).idxmin()
    summary["최고연도"] = df[columns].astype(float).idxmax()
    log_table(summary.round(2))


def analyze_decades(df):
    section("3. 연대별 분석")
    grouped = df.assign(연대=df.index // 10 * 10).groupby("연대")
    table = pd.DataFrame({
        "연수": grouped.size(),
        "평균출생아수": grouped["출생아수"].mean().astype(float).round(0),
        "평균합계출산율": grouped["합계출산율"].mean().round(3),
        "평균출생성비": grouped["출생성비"].mean().round(1),
        "평균자연증가": grouped["자연증가건수"].mean().astype(float).round(0),
        "평균사망자_추정": grouped["사망자수_추정"].mean().astype(float).round(0),
    })
    table["직전연대대비(%)"] = table["평균출생아수"].pct_change().mul(100).round(1)
    log_table(table)
    log("※ 2020년대는 2020~2025년 6개 연도만 포함")
    return table


def analyze_change(df):
    section("4. 전년 대비 변동")
    change = df[["출생아수", "출생아수_증감", "출생아수_증감률"]].dropna()
    log("[감소율 상위 5개 연도]")
    log_table(change.nsmallest(5, "출생아수_증감률").round(2))
    log()
    log("[증가율 상위 5개 연도]")
    log_table(change.nlargest(5, "출생아수_증감률").round(2))

    falling = change["출생아수_증감률"] < 0
    streak_id = (falling != falling.shift()).cumsum()
    streaks = falling[falling].groupby(streak_id).apply(lambda s: (s.index[0], s.index[-1], len(s)))
    log()
    log(f"감소한 해 {int(falling.sum())}개 / 증가한 해 {int((~falling).sum())}개")
    if len(streaks):
        longest = max(streaks, key=lambda s: s[2])
        log(f"최장 연속 감소: {longest[0]}~{longest[1]}년 ({longest[2]}년 연속)")

    log()
    log("[구간별 연평균 증감률]")
    births = df["출생아수"].astype(float)
    for start, end in PERIODS:
        if start in births.index and end in births.index:
            cagr = ((births[end] / births[start]) ** (1 / (end - start)) - 1) * 100
            log(f"{start}~{end}년: {births[start]:,.0f}명 → {births[end]:,.0f}명 "
                f"(연평균 {cagr:+.2f}%)")


def first_year_below(series, threshold):
    below = series[series < threshold]
    return int(below.index[0]) if len(below) else None


def analyze_milestones(df):
    section("5. 주요 이정표")
    births = df["출생아수"].astype(float)
    peak_year, low_year = births.idxmax(), births.idxmin()
    log(f"최고: {peak_year}년 {births[peak_year]:,.0f}명 / "
        f"최저: {low_year}년 {births[low_year]:,.0f}명 "
        f"(최고의 {births[low_year] / births[peak_year] * 100:.1f}%)")
    last = df.index.max()
    log(f"{year_label(df, last)} {births[last]:,.0f}명: 최저 대비 "
        f"{(births[last] / births[low_year] - 1) * 100:+.1f}%, 최고 대비 "
        f"{(births[last] / births[peak_year] - 1) * 100:+.1f}%")
    log()
    for threshold in [1_000_000, 500_000, 400_000, 300_000]:
        log(f"출생아수 {threshold // 10000}만 명 첫 미만: {first_year_below(births, threshold)}년")
    tfr = df["합계출산율"]
    log(f"합계출산율 {REPLACEMENT_TFR}(인구대체 수준) 첫 미만: "
        f"{first_year_below(tfr, REPLACEMENT_TFR)}년")
    log(f"합계출산율 1.0 첫 미만: {first_year_below(tfr, 1.0)}년")
    log(f"합계출산율 최저: {tfr.idxmin()}년 {tfr.min()}명")
    log(f"자연증가 첫 마이너스(사망 > 출생): "
        f"{first_year_below(df['자연증가건수'].astype(float), 0)}년")


def analyze_decomposition(df):
    section("6. 출생아수 변화 요인 분해 (출생아수 = 합계출산율 x 출산규모지수)")
    log("출산규모지수 = 출생아수 / 합계출산율. 가임기 여성 규모·연령 구조의 대리 지표입니다.")
    log("로그 변화량으로 나누어 어느 쪽이 얼마나 기여했는지 봅니다.")
    log()
    rows = []
    for start, end in [*PERIODS, (df.index.min(), df.index.max())]:
        if start not in df.index or end not in df.index:
            continue
        total = np.log(float(df.loc[end, "출생아수"]) / float(df.loc[start, "출생아수"]))
        rate = np.log(df.loc[end, "합계출산율"] / df.loc[start, "합계출산율"])
        scale = np.log(df.loc[end, "출산규모지수"] / df.loc[start, "출산규모지수"])
        # 전체 변화가 거의 없으면 기여율의 분모가 0에 가까워 의미가 없다
        has_change = abs(total) >= 0.01
        rows.append({
            "구간": f"{start}~{end}",
            "출생아수변화(%)": round((np.exp(total) - 1) * 100, 1),
            "합계출산율변화(%)": round((np.exp(rate) - 1) * 100, 1),
            "출산규모변화(%)": round((np.exp(scale) - 1) * 100, 1),
            "출산율기여(%)": round(rate / total * 100, 1) if has_change else np.nan,
            "규모기여(%)": round(scale / total * 100, 1) if has_change else np.nan,
        })
    log_table(pd.DataFrame(rows).set_index("구간"))
    log("※ 기여 합은 100%. 음수 기여는 해당 요인이 전체 변화와 반대로 움직였다는 뜻")
    log("※ 값이 없는 칸: 전체 변화가 1% 미만이라 기여율을 계산하지 않은 구간")


def analyze_correlation(df):
    section("7. 지표 간 상관관계")
    columns = list(COLUMN_NAMES.values())
    log("[수준값 상관] 모두 장기 추세를 공유하므로 높게 나오는 경향이 있습니다")
    log_table(df[columns].astype(float).corr().round(3))
    log()
    log("[전년 대비 차분 상관] 추세를 제거한 단기 동조 정도")
    log_table(df[columns].astype(float).diff().corr().round(3))


def analyze_sex_ratio(df):
    section("8. 출생성비")
    ratio = df["출생성비"]
    log(f"최고: {ratio.idxmax()}년 {ratio.max()} / 최저: {ratio.idxmin()}년 {ratio.min()}")
    log(f"110 이상인 해: {ratio[ratio >= 110].index.tolist()}")
    recent = ratio.loc[2007:]
    if len(recent):
        log(f"2007년 이후 범위: {recent.min()}~{recent.max()}")

    # 전후 평균에서 크게 벗어난 해 (값은 그대로 두고 표시만 한다)
    neighbors = (ratio.shift(1) + ratio.shift(-1)) / 2
    jumps = (ratio - neighbors).dropna()
    log("앞뒤 해 평균과의 차이 상위 5개 연도:")
    top = jumps.reindex(jumps.abs().sort_values(ascending=False).index).head(5)
    log_table(top.round(2).to_frame("평균과의 차이"))


def analyze_dragon_years(df):
    section("9. 용띠 해 전후 출생아수")
    log("문화적 선호가 거론되는 해의 변화를 단순 비교합니다. 인과를 입증하는 분석은 아닙니다.")
    years = [year for year in DRAGON_YEARS if year in df.index]
    table = df.loc[years, ["출생아수", "출생아수_증감률"]].copy()
    table["다음해증감률"] = df["출생아수_증감률"].shift(-1).loc[years]
    table["합계출산율증감률"] = df.loc[years, "합계출산율_증감률"]
    log_table(table.round(2))


def run_analysis(path):
    """파일 하나에 대한 클렌징과 분석 전체를 실행하고 결과를 묶어 돌려준다."""
    report_lines.clear()
    report_html.clear()

    cleaned = clean_data(path)
    df = add_derived_columns(cleaned)
    analyze_overview(df)
    decades = analyze_decades(df)
    analyze_change(df)
    analyze_milestones(df)
    analyze_decomposition(df)
    analyze_correlation(df)
    analyze_sex_ratio(df)
    analyze_dragon_years(df)

    return {
        "path": str(path),
        "cleaned": cleaned,
        "df": df,
        "decades": decades,
        "report_text": "\n".join(report_lines),
        "report_html": "".join(report_html),
    }


def save_results(result, folder, start, end):
    """분석 결과 전체를 폴더에 저장하고 저장한 파일 수를 돌려준다."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    result["cleaned"].to_csv(folder / "birth_cleaned.csv", encoding="utf-8-sig")
    result["decades"].to_csv(folder / "birth_decade_stats.csv", encoding="utf-8-sig")
    (folder / "birth_report.txt").write_text(result["report_text"], encoding="utf-8")

    # 저장 이미지는 창 크기와 상관없이 항상 같은 크기로 다시 그린다
    line_figure = Figure(figsize=(12, 6), layout="constrained", facecolor=COLOR_SURFACE)
    draw_births_line(line_figure, result["df"], start, end)
    line_figure.savefig(folder / f"births_line_{start}_{end}.png", dpi=150)

    multi_figure = Figure(figsize=(14, 9), layout="constrained", facecolor=COLOR_SURFACE)
    draw_multi_view(multi_figure, result["df"])
    multi_figure.savefig(folder / "births_multi_view.png", dpi=150)
    return 5


# ---------------------------------------------------------------------------
# 3. 그래프
# ---------------------------------------------------------------------------
def year_label(df, year):
    return f"{year}년(잠정)" if df.loc[year, "잠정치"] else f"{year}년"


def style_axis(ax):
    ax.set_facecolor(COLOR_SURFACE)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_TEXT_SUB, length=0)


def draw_births_line(fig, df, start, end):
    """고른 기간의 출생아수 라인그래프를 그리고 축을 돌려준다."""
    fig.clear()
    ax = fig.add_subplot()
    style_axis(ax)

    births = df.loc[start:end, "출생아수"].astype(float)
    provisional = df.loc[births.index, "잠정치"]
    first, last = births.index[0], births.index[-1]
    last_final = provisional[~provisional].index.max()

    # 확정치는 실선, 잠정치로 이어지는 구간은 점선으로 구분한다
    ax.plot(births.loc[:last_final], color=COLOR_LINE, linewidth=2,
            solid_capstyle="round", solid_joinstyle="round")
    if last_final < last:
        ax.plot(births.loc[last_final:], color=COLOR_LINE, linewidth=2, linestyle=(0, (2, 2)))

    def annotate(year, caption, offset, ha="center"):
        ax.scatter(year, births[year], s=50, color=COLOR_LINE, zorder=3,
                   edgecolor=COLOR_SURFACE, linewidth=1.5)
        ax.annotate(f"{year_label(df, year)} {caption}\n{births[year]:,.0f}명".replace(" \n", "\n"),
                    (year, births[year]), xytext=offset, textcoords="offset points",
                    ha=ha, color=COLOR_TEXT, fontsize=11)

    peak = births.idxmax()
    low = births.idxmin()
    annotate(peak, "최고", (8, 8), ha="left")
    if low != peak:
        annotate(low, "최저", (0, -40))
    under_500k = first_year_below(births, 500_000)
    if under_500k and first < under_500k and under_500k not in (peak, low, last):
        annotate(under_500k, "50만 명 아래로", (8, 12), ha="left")
    if last not in (peak, low):
        annotate(last, "", (10, -8), ha="left")

    change = (births[low] / births[peak] - 1) * 100
    if peak < low:
        title = (f"출생아수는 {peak}년 {births[peak] / 1e4:.0f}만 명에서 "
                 f"{low}년 {births[low] / 1e4:.0f}만 명으로 {-change:.0f}% 줄었습니다")
    else:
        title = (f"출생아수는 {low}년 {births[low] / 1e4:.0f}만 명에서 "
                 f"{peak}년 {births[peak] / 1e4:.0f}만 명으로 늘었습니다")
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color=COLOR_TEXT, pad=26)
    subtitle = f"대한민국 연간 출생아수, {first}~{last}년  |  "
    if last_final < last:
        subtitle += "점선: 잠정치  |  "
    ax.text(0, 1.02, subtitle + "자료: 국가데이터처 인구동향조사",
            transform=ax.transAxes, fontsize=10, color=COLOR_TEXT_SUB)

    span = last - first
    ax.set_ylim(0, births.max() * 1.17)
    ax.set_xlim(first - max(span * 0.02, 0.3), last + max(span * 0.11, 1))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, steps=[1, 2, 5, 10], nbins=12))
    # 값 라벨 자리로 비워 둔 오른쪽 여백에는 데이터에 없는 연도를 표시하지 않는다
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}" if first <= v <= last else ""))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 10000:,.0f}만 명" if v else "0"))
    return ax


def draw_multi_view(fig, df):
    """관련 지표를 한 축에 겹치지 않고 패널로 나누어 보여 준다."""
    fig.clear()
    fig.get_layout_engine().set(h_pad=0.12, w_pad=0.12)
    axes = fig.subplots(2, 2)
    (ax_tfr, ax_natural), (ax_change, ax_ratio) = axes
    years = df.index
    for ax in axes.flat:
        style_axis(ax)
        ax.set_xlim(years.min() - 1, years.max() + 1)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, steps=[1, 2, 5, 10], nbins=7))

    def set_title(ax, text):
        ax.set_title(text, loc="left", fontsize=12.5, fontweight="bold", color=COLOR_TEXT, pad=10)

    def reference(ax, value, label, y_offset=4):
        ax.axhline(value, color=COLOR_REFERENCE, linewidth=1)
        ax.annotate(label, (years.max() + 1, value), xytext=(0, y_offset),
                    textcoords="offset points", ha="right", color=COLOR_TEXT_SUB, fontsize=9.5)

    ax_tfr.plot(years, df["합계출산율"], color=COLOR_LINE, linewidth=2)
    reference(ax_tfr, REPLACEMENT_TFR, f"인구대체 수준 {REPLACEMENT_TFR}명")
    ax_tfr.set_ylim(0, 5)
    set_title(ax_tfr, f"합계출산율: {first_year_below(df['합계출산율'], REPLACEMENT_TFR)}년부터 "
                      "인구대체 수준 미만 (명)")

    natural = df["자연증가건수"].astype(float)
    ax_natural.plot(years, natural, color=COLOR_LINE, linewidth=2)
    reference(ax_natural, 0, "출생 = 사망")
    ax_natural.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 10000:,.0f}만" if v else "0"))
    set_title(ax_natural, f"자연증가: {first_year_below(natural, 0)}년부터 "
                          "사망이 출생보다 많음 (명)")

    change = df["출생아수_증감률"].dropna()
    ax_change.bar(change.index, change, width=0.8,
                  color=[COLOR_LINE if v >= 0 else COLOR_NEGATIVE for v in change])
    ax_change.axhline(0, color=COLOR_REFERENCE, linewidth=1)
    ax_change.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}%" if v else "0%"))
    decline_share = (change < 0).mean() * 100
    set_title(ax_change, f"출생아수 전년 대비 증감률: {decline_share:.0f}%의 해에서 감소")

    ax_ratio.plot(years, df["출생성비"], color=COLOR_LINE, linewidth=2)
    reference(ax_ratio, NATURAL_SEX_RATIO, f"자연 출생성비 약 {NATURAL_SEX_RATIO}", y_offset=-13)
    ax_ratio.set_ylim(100, 120)
    ax_ratio.set_yticks(range(100, 121, 5))
    peak_ratio = df["출생성비"].idxmax()
    set_title(ax_ratio, f"출생성비(여아 100명당 남아): {peak_ratio}년 {df['출생성비'].max()} 정점")


# ---------------------------------------------------------------------------
# 4. GUI
# ---------------------------------------------------------------------------
class AnalysisWorker(QThread):
    """엑셀 읽기와 분석이 화면을 멈추지 않도록 별도 스레드에서 실행"""

    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        # QThread 안에서 처리되지 않은 예외는 앱 전체를 종료시키므로 여기서 모두 받음
        try:
            self.succeeded.emit(run_analysis(self.path))
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, initial_path=None):
        super().__init__()
        self.setWindowTitle("출생 통계 분석기")
        self.resize(1200, 820)
        self.setStyleSheet(STYLE_SHEET)
        self.result = None
        self.worker = None
        self.line_ax = None
        self.hover_year = None
        self.build_ui()

        if initial_path and Path(initial_path).exists():
            self.load_file(initial_path)
        else:
            self.status_label.setText("엑셀 열기 버튼으로 KOSIS 출생 통계 파일을 선택하세요.")

    def build_ui(self):
        title = QLabel("대한민국 출생 통계")
        title.setObjectName("title")
        self.subtitle_label = QLabel("불러온 파일 없음")
        self.subtitle_label.setObjectName("subtitle")
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_column.addWidget(title)
        title_column.addWidget(self.subtitle_label)

        self.open_button = QPushButton("엑셀 열기")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self.choose_file)
        self.save_button = QPushButton("결과 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_all)

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        control_row.addLayout(title_column)
        control_row.addStretch(1)
        control_row.addWidget(self.open_button)
        control_row.addWidget(self.save_button)

        self.stat_labels = []
        stat_row = QHBoxLayout()
        stat_row.setSpacing(32)
        for _ in range(4):
            value = QLabel("-")
            value.setObjectName("statValue")
            caption = QLabel(" ")
            caption.setObjectName("statCaption")
            column = QVBoxLayout()
            column.setSpacing(0)
            column.addWidget(value)
            column.addWidget(caption)
            stat_row.addLayout(column)
            self.stat_labels.append((value, caption))
        stat_row.addStretch(1)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_line_tab(), "출생아수 추이")
        self.tabs.addTab(self.build_multi_tab(), "종합 지표")
        self.table = self.build_table()
        self.tabs.addTab(self.table, "데이터")
        self.report_view = QTextBrowser()
        self.report_view.document().setDefaultStyleSheet(
            "h2 { font-size: 15px; margin-top: 18px; } p { margin: 3px 0; }"
        )
        self.tabs.addTab(self.report_view, "분석 리포트")

        self.status_label = QLabel()
        self.status_label.setObjectName("status")

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)
        layout.addLayout(control_row)
        layout.addLayout(stat_row)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.status_label)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)

    def build_line_tab(self):
        self.start_spin = QSpinBox()
        self.end_spin = QSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setKeyboardTracking(False)
            spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            spin.setToolTip("연도를 입력하고 Enter를 누르거나 마우스 휠로 바꿉니다")
            spin.setEnabled(False)
            spin.valueChanged.connect(self.update_line_chart)
        self.reset_button = QPushButton("전체 기간")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_year_range)

        self.line_figure = Figure(layout="constrained", facecolor=COLOR_SURFACE)
        self.line_canvas = FigureCanvasQTAgg(self.line_figure)
        self.line_canvas.mpl_connect("motion_notify_event", self.on_line_hover)
        self.line_canvas.mpl_connect("figure_leave_event", lambda _: self.hide_hover())

        start_label = QLabel("기간")
        start_label.setObjectName("fieldLabel")
        tilde = QLabel("~")
        tilde.setObjectName("fieldLabel")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(start_label)
        row.addWidget(self.start_spin)
        row.addWidget(tilde)
        row.addWidget(self.end_spin)
        row.addWidget(self.reset_button)
        row.addStretch(1)
        row.addWidget(NavigationToolbar2QT(self.line_canvas, self, coordinates=False))

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 8)
        layout.addLayout(row)
        layout.addWidget(self.line_canvas, 1)
        page = QWidget()
        page.setLayout(layout)
        return page

    def build_multi_tab(self):
        self.multi_figure = Figure(layout="constrained", facecolor=COLOR_SURFACE)
        self.multi_canvas = FigureCanvasQTAgg(self.multi_figure)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 8)
        layout.addWidget(self.multi_canvas)
        page = QWidget()
        page.setLayout(layout)
        return page

    def build_table(self):
        table = QTableWidget(0, 0)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setShowGrid(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def choose_file(self):
        folder = str(DEFAULT_XLSX.parent) if DEFAULT_XLSX.parent.exists() else str(BASE_DIR)
        filename, _ = QFileDialog.getOpenFileName(self, "엑셀 열기", folder, "엑셀 파일 (*.xlsx)")
        if filename:
            self.load_file(filename)

    def load_file(self, path):
        self.open_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status_label.setText(f"분석 중: {path}")
        self.worker = AnalysisWorker(path, self)
        self.worker.succeeded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.start()

    def analysis_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.open_button.setEnabled(True)
        self.save_button.setEnabled(self.result is not None)

    def show_error(self, message):
        self.status_label.setText("파일을 불러오지 못했습니다.")
        QMessageBox.critical(self, "불러오기 실패", f"{message}\n\nKOSIS에서 받은 출생 통계 엑셀인지 확인하세요.")

    def show_result(self, result):
        self.result = result
        df = result["df"]
        self.subtitle_label.setText(f"{Path(result['path']).name}  ·  {df.index.min()}~{df.index.max()}년")
        self.update_stats(df)
        self.update_table(df)
        self.report_view.setHtml(result["report_html"])

        # 값을 한꺼번에 바꾸는 동안 그래프가 여러 번 다시 그려지지 않게 막는다
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(True)
            spin.setRange(int(df.index.min()), int(df.index.max()))
            spin.setEnabled(True)
        self.start_spin.setValue(int(df.index.min()))
        self.end_spin.setValue(int(df.index.max()))
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(False)
        self.reset_button.setEnabled(True)
        self.update_line_chart()

        draw_multi_view(self.multi_figure, df)
        self.multi_canvas.draw_idle()
        self.status_label.setText(f"분석 완료: {result['path']}")

    def update_stats(self, df):
        births = df["출생아수"].astype(float)
        peak, low, last = births.idxmax(), births.idxmin(), births.index[-1]
        tfr = df["합계출산율"]
        stats = [
            (f"{births[peak]:,.0f}명", f"최고 출생아수 · {peak}년"),
            (f"{births[low]:,.0f}명", f"최저 출생아수 · {low}년"),
            (f"{births[last]:,.0f}명", f"최근 출생아수 · {year_label(df, last)}"),
            (f"{tfr[last]:g}명", f"최근 합계출산율 · {year_label(df, last)}"),
        ]
        for (value_label, caption_label), (value, caption) in zip(self.stat_labels, stats):
            value_label.setText(value)
            caption_label.setText(caption)

    def update_table(self, df):
        columns = list(TABLE_COLUMNS)
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(columns) + 1)
        self.table.setHorizontalHeaderLabels([*TABLE_COLUMNS.values(), "비고"])
        self.table.setVerticalHeaderLabels([str(year) for year in df.index])
        for row, (_, values) in enumerate(df.iterrows()):
            for col, column in enumerate(columns):
                item = QTableWidgetItem(format_table_value(values[column], column))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
            note = QTableWidgetItem("잠정치" if values["잠정치"] else "")
            note.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, len(columns), note)

    def reset_year_range(self):
        df = self.result["df"]
        self.start_spin.blockSignals(True)
        self.start_spin.setValue(int(df.index.min()))
        self.start_spin.blockSignals(False)
        self.end_spin.setValue(int(df.index.max()))
        self.update_line_chart()

    def update_line_chart(self):
        if self.result is None:
            return
        df = self.result["df"]
        start, end = self.start_spin.value(), self.end_spin.value()
        # 시작 연도가 끝 연도를 넘지 않도록 서로의 범위를 제한한다
        self.start_spin.setMaximum(end - 1)
        self.end_spin.setMinimum(start + 1)

        self.line_ax = draw_births_line(self.line_figure, df, start, end)
        self.hover_line = self.line_ax.axvline(start, color=COLOR_REFERENCE, linewidth=1, visible=False)
        self.hover_dot = self.line_ax.scatter(start, 0, s=50, color=COLOR_LINE, zorder=4,
                                              edgecolor=COLOR_SURFACE, linewidth=1.5, visible=False)
        self.hover_tip = self.line_ax.annotate(
            "", (start, 0), xytext=(12, 12), textcoords="offset points", fontsize=10,
            color=COLOR_TEXT, visible=False, zorder=5, multialignment="left",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#ffffff", "edgecolor": COLOR_GRID},
        )
        self.hover_year = None
        self.line_canvas.draw_idle()

    def on_line_hover(self, event):
        if event.inaxes is not self.line_ax or event.xdata is None:
            self.hide_hover()
            return
        df = self.result["df"]
        start, end = self.start_spin.value(), self.end_spin.value()
        year = min(max(round(event.xdata), start), end)
        if year == self.hover_year:
            return
        self.hover_year = year

        value = float(df.loc[year, "출생아수"])
        lines = [year_label(df, year), f"출생아수 {value:,.0f}명"]
        change = df.loc[year, "출생아수_증감률"]
        if pd.notna(change):
            lines.append(f"전년 대비 {change:+.1f}%")
        lines.append(f"합계출산율 {df.loc[year, '합계출산율']:g}명")

        self.hover_line.set_xdata([year, year])
        self.hover_dot.set_offsets([[year, value]])
        self.hover_tip.xy = (year, value)
        self.hover_tip.set_text("\n".join(lines))
        # 그래프 오른쪽·위쪽 끝에서 말풍선이 잘리지 않도록 방향을 바꾼다
        right_side = year > (start + end) / 2
        high = value > self.line_ax.get_ylim()[1] * 0.7
        self.hover_tip.set_position((-12 if right_side else 12, -12 if high else 12))
        self.hover_tip.set_ha("right" if right_side else "left")
        self.hover_tip.set_va("top" if high else "bottom")
        for artist in (self.hover_line, self.hover_dot, self.hover_tip):
            artist.set_visible(True)
        self.line_canvas.draw_idle()

    def hide_hover(self):
        if self.hover_year is None:
            return
        self.hover_year = None
        for artist in (self.hover_line, self.hover_dot, self.hover_tip):
            artist.set_visible(False)
        self.line_canvas.draw_idle()

    def save_all(self):
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", str(BASE_DIR))
        if not folder:
            return
        try:
            count = save_results(self.result, Path(folder) / OUTPUT_DIR.name,
                                 self.start_spin.value(), self.end_spin.value())
        except OSError as e:
            # 엑셀에서 같은 파일을 열어 둔 경우에도 여기로 옴 (PermissionError)
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n파일이 다른 프로그램에서 열려 있으면 닫고 다시 시도하세요.")
            return
        self.status_label.setText(f"저장 완료: {Path(folder) / OUTPUT_DIR.name} ({count}개 파일)")

    def closeEvent(self, event):
        # 실행 중인 스레드를 정리하지 않고 종료하면 앱이 비정상 종료됨
        if self.worker is not None:
            self.hide()
            self.worker.wait()
        event.accept()


def main():
    pd.set_option("display.width", 200, "display.max_columns", 30,
                  "display.unicode.east_asian_width", True)
    setup_korean_font()

    app = QApplication(sys.argv)
    # 그래프가 밝은 배경 기준이므로 윈도우가 다크 모드여도 밝은 테마로 고정한다
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setStyle("Fusion")

    initial_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    window = MainWindow(initial_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
