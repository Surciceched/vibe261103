"""S&P 500 과거 데이터 클렌징 · 다각도 분석 · 종가 라인그래프 출력

실행 예)
    python sp500_analysis.py                      # 스크립트 옆의 CSV 사용, 그래프 창 표시
    python sp500_analysis.py "다른경로.csv"        # CSV 경로 지정
    python sp500_analysis.py --no-show            # 그래프 창 없이 파일로만 저장

결과물은 sp500_output 폴더에 저장됩니다.
"""

import argparse
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = BASE_DIR / "S&P 500 과거 데이터.csv"
OUTPUT_DIR = BASE_DIR / "sp500_output"

START_DATE = "2000-01-01"
END_DATE = "2019-12-31"
TRADING_DAYS = 252

# 그래프 색상
COLOR_LINE = "#2a78d6"
COLOR_NEGATIVE = "#e34948"
COLOR_TEXT = "#0b0b0b"
COLOR_TEXT_SUB = "#52514e"
COLOR_GRID = "#e6e5e0"
COLOR_SURFACE = "#fcfcfb"

report_lines = []


def log(text=""):
    """콘솔에 출력하면서 리포트 파일용으로도 모아 둔다."""
    print(text)
    report_lines.append(str(text))


def section(title):
    log()
    log("=" * 70)
    log(title)
    log("=" * 70)


# ---------------------------------------------------------------------------
# 1. 데이터 클렌징
# ---------------------------------------------------------------------------
def load_and_clean(csv_path):
    """CSV를 읽어 정제된 DataFrame(날짜 인덱스, 오름차순)을 반환한다."""
    section("1. 데이터 클렌징")

    # 쉼표·% 때문에 자동 형변환이 어긋나므로 전부 문자열로 읽는다 (BOM 제거: utf-8-sig)
    raw = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str)
    log(f"원본 크기: {raw.shape[0]:,}행 x {raw.shape[1]}열")

    df = raw.rename(
        columns={
            "날짜": "date",
            "종가": "close",
            "시가": "open",
            "고가": "high",
            "저가": "low",
            "거래량": "volume",
            "변동 %": "change_pct",
        }
    )

    # 거래량은 값이 하나도 없으면 분석에 쓸 수 없으므로 제거
    missing_ratio = df["volume"].isna().mean()
    if missing_ratio == 1:
        df = df.drop(columns="volume")
        log("- 거래량: 전체 결측(100%) → 컬럼 제거")

    # "2019- 11- 14" 처럼 공백이 섞인 날짜 → datetime
    df["date"] = pd.to_datetime(
        df["date"].str.replace(" ", "", regex=False), format="%Y-%m-%d", errors="coerce"
    )
    log("- 날짜: 공백 제거 후 datetime 변환")

    # "3,096.60" → 3096.6
    for col in ["close", "open", "high", "low"]:
        df[col] = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")
    log("- 가격: 천 단위 쉼표 제거 후 숫자 변환")

    # "-0.20%" → -0.2
    df["change_pct"] = pd.to_numeric(
        df["change_pct"].str.replace("%", "", regex=False), errors="coerce"
    )
    log("- 변동 %: % 기호 제거 후 숫자 변환")

    # 변환 실패(결측) · 중복 날짜 제거
    before = len(df)
    df = df.dropna(subset=["date", "close"]).drop_duplicates(subset="date")
    log(f"- 변환 실패/중복 날짜 제거: {before - len(df)}행")

    # 최신순 → 과거순 정렬 (시계열 계산의 전제 조건)
    df = df.sort_values("date").set_index("date")
    log("- 정렬: 최신순 → 과거순")

    # OHLC 논리 오류 보정: 고가는 시가/종가/저가 이상, 저가는 시가/종가/고가 이하여야 한다
    ohlc = df[["open", "high", "low", "close"]]
    bad = df[(df["high"] < ohlc.max(axis=1)) | (df["low"] > ohlc.min(axis=1))]
    for date, row in bad.iterrows():
        log(
            f"- OHLC 오류 보정: {date.date()} 시가 {row['open']:,.1f} > 고가 {row['high']:,.1f}"
            " → 고가를 최댓값으로 수정"
        )
    df["high"] = ohlc.max(axis=1)
    df["low"] = ohlc.min(axis=1)

    # 일간 수익률: 첫날은 전일 종가가 없으므로 원본의 변동 %로 채운다
    df["return"] = df["close"].pct_change()
    df.loc[df.index[0], "return"] = df["change_pct"].iloc[0] / 100

    # 검증 (데이터를 바꾸지 않고 결과만 보고)
    log()
    log("[검증]")
    diff = (df["return"] * 100 - df["change_pct"]).abs()
    log(f"- 원본 변동 %와 재계산 수익률 차이 0.02pt 초과: {(diff > 0.02).sum()}건")
    log(f"- 주말 데이터: {(df.index.dayofweek >= 5).sum()}건")
    gaps = df.index.to_series().diff().dt.days
    for date, gap in gaps[gaps >= 5].items():
        log(f"- {gap:.0f}일 공백: {date.date()} 이전 (휴장 추정, 보간하지 않음)")
    z_score = (df["return"] - df["return"].mean()) / df["return"].std()
    log(
        f"- |z| > 5 인 일간 수익률: {(z_score.abs() > 5).sum()}건"
        " (원본 변동 %와 일치하므로 실제 급등락으로 보고 유지)"
    )

    log()
    log(f"정제 후 크기: {df.shape[0]:,}행 x {df.shape[1]}열")
    log(f"실제 기간: {df.index.min().date()} ~ {df.index.max().date()}")
    if df.index.max() < pd.Timestamp(END_DATE):
        log(f"※ 요청 종료일({END_DATE})보다 데이터가 먼저 끝납니다. 이후 구간은 원본에 없습니다.")
    return df


# ---------------------------------------------------------------------------
# 2. 다각도 분석
# ---------------------------------------------------------------------------
def annualize_vol(returns):
    return returns.std() * np.sqrt(TRADING_DAYS)


def compound(returns):
    return (1 + returns).prod() - 1


def analyze_overview(df):
    section("2-1. 전체 요약")
    close = df["close"]
    years = (df.index[-1] - df.index[0]).days / 365.25
    cagr = (close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1
    log(f"시작 종가: {close.iloc[0]:,.1f} ({df.index[0].date()})")
    log(f"마지막 종가: {close.iloc[-1]:,.1f} ({df.index[-1].date()})")
    log(f"최고 종가: {close.max():,.1f} ({close.idxmax().date()})")
    log(f"최저 종가: {close.min():,.1f} ({close.idxmin().date()})")
    log(f"누적 수익률: {close.iloc[-1] / close.iloc[0] - 1:.1%}")
    log(f"연평균 성장률(CAGR): {cagr:.2%}  ※ 가격지수 기준, 배당 미포함")
    log(f"연환산 변동성: {annualize_vol(df['return']):.2%}")
    log()
    log(df[["close", "open", "high", "low"]].describe().round(1).to_string())


def analyze_annual(df):
    section("2-2. 연도별 성과 (* 2019년은 11/14까지)")
    grouped = df.groupby(df.index.year)
    annual = pd.DataFrame(
        {
            "수익률(%)": grouped["return"].apply(compound) * 100,
            "변동성(%)": grouped["return"].apply(annualize_vol) * 100,
            "연말종가": grouped["close"].last(),
            "거래일수": grouped["close"].size(),
            "평균일중변동폭(%)": ((df["high"] - df["low"]) / df["close"] * 100)
            .groupby(df.index.year)
            .mean(),
        }
    )
    annual.index.name = "연도"
    log(annual.round(2).to_string())
    log()
    log(f"상승 연도 {(annual['수익률(%)'] > 0).sum()}개 / 하락 연도 {(annual['수익률(%)'] < 0).sum()}개")
    log(f"최고 연도: {annual['수익률(%)'].idxmax()}년 ({annual['수익률(%)'].max():.2f}%)")
    log(f"최저 연도: {annual['수익률(%)'].idxmin()}년 ({annual['수익률(%)'].min():.2f}%)")

    # 5년 단위 구간 비교
    log()
    log("[5년 구간별]")
    bins = pd.cut(
        df.index.year,
        [1999, 2004, 2009, 2014, 2019],
        labels=["2000-04", "2005-09", "2010-14", "2015-19*"],
    )
    periods = df.groupby(bins, observed=True)["return"]
    period_table = pd.DataFrame(
        {
            "누적수익률(%)": periods.apply(compound) * 100,
            "변동성(%)": periods.apply(annualize_vol) * 100,
        }
    )
    log(period_table.round(2).to_string())
    return annual


def analyze_seasonality(df):
    section("2-3. 계절성 (월별 · 요일별)")
    # 2019년 11월은 14일까지만 있어 월간 통계에서 제외
    complete = df[df.index < "2019-11-01"]
    monthly = complete.groupby(complete.index.to_period("M"))["return"].apply(compound)
    by_month = monthly.groupby(monthly.index.month).agg(
        평균수익률=lambda r: r.mean() * 100,
        상승확률=lambda r: (r > 0).mean() * 100,
    )
    by_month.index.name = "월"
    log(by_month.round(2).to_string())
    log()

    names = ["월", "화", "수", "목", "금"]
    by_weekday = df.groupby(df.index.dayofweek)["return"].agg(
        평균수익률=lambda r: r.mean() * 100,
        상승확률=lambda r: (r > 0).mean() * 100,
    )
    by_weekday.index = [names[i] for i in by_weekday.index]
    by_weekday.index.name = "요일"
    log(by_weekday.round(3).to_string())
    log()

    # 평균 차이가 우연인지 가늠하기 위한 표준오차
    log(f"월평균 수익률의 표준오차는 약 {monthly.std() / np.sqrt(len(monthly) / 12) * 100:.2f}%p로,")
    log("월별 평균 차이 대부분은 통계적으로 유의하다고 보기 어렵습니다.")
    return by_month


def analyze_risk(df):
    section("2-4. 수익률 분포 · 낙폭")
    ret = df["return"]
    log(f"일평균 수익률: {ret.mean():.4%}")
    log(f"일간 표준편차: {ret.std():.3%}")
    log(f"왜도: {ret.skew():.3f} / 초과첨도: {ret.kurt():.3f} (정규분포는 둘 다 0)")
    log(f"상승일 비율: {(ret > 0).mean():.1%}")
    log(f"VaR 95%: {ret.quantile(0.05):.2%} / VaR 99%: {ret.quantile(0.01):.2%} (일간)")
    log(f"±3% 초과 변동일: {(ret.abs() > 0.03).sum()}일")
    log()

    log("[일간 상승 상위 5]")
    log((ret.nlargest(5) * 100).round(2).to_string())
    log()
    log("[일간 하락 상위 5]")
    log((ret.nsmallest(5) * 100).round(2).to_string())
    log()

    # 고점 대비 낙폭: 신고가가 나올 때마다 새 구간이 시작된다
    peak = df["close"].cummax()
    drawdown = df["close"] / peak - 1
    log(f"최대 낙폭(MDD): {drawdown.min():.2%} ({drawdown.idxmin().date()})")
    log()
    log("[고점 대비 -20% 이상 하락 구간]")
    episode_id = (df["close"] >= peak).cumsum()
    next_starts = drawdown.groupby(episode_id).apply(lambda g: g.index[0]).shift(-1)
    for episode, group in drawdown.groupby(episode_id):
        if group.min() > -0.2:
            continue
        start, trough = group.index[0], group.idxmin()
        recovery = next_starts.loc[episode]
        recovered = "미회복" if pd.isna(recovery) else f"{recovery.date()} 회복"
        log(f"- 고점 {start.date()} → 저점 {trough.date()} ({group.min():.1%}) → {recovered}")
    return drawdown


def analyze_trend(df):
    section("2-5. 추세 (이동평균)")
    ma50 = df["close"].rolling(50).mean()
    ma200 = df["close"].rolling(200).mean()
    valid = ma200.notna()
    above = (ma50 > ma200)[valid]
    crosses = above.astype(int).diff().fillna(0)
    log(f"골든크로스(50일선이 200일선 상향 돌파): {(crosses == 1).sum()}회")
    log(f"데드크로스(50일선이 200일선 하향 돌파): {(crosses == -1).sum()}회")
    log(f"종가가 200일선 위에 있던 비율: {(df['close'] > ma200)[valid].mean():.1%}")

    # 200일선 위/아래에서의 다음 날 수익률 비교 (미래 참조를 막기 위해 하루 밀어서 계산)
    position = (df["close"] > ma200).shift(1)[valid]
    returns = df["return"][valid]
    for label, mask in [("200일선 위", position == True), ("200일선 아래", position == False)]:  # noqa: E712
        log(
            f"- 전일 종가가 {label}: 다음 날 평균 {returns[mask].mean():.3%},"
            f" 연환산 변동성 {annualize_vol(returns[mask]):.1%}"
        )


# ---------------------------------------------------------------------------
# 3. 그래프
# ---------------------------------------------------------------------------
def setup_matplotlib():
    # 설치된 한글 폰트 선택 (없으면 기본 폰트로 동작)
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in ["Malgun Gothic", "AppleGothic", "NanumGothic"]:
        if font_name in installed:
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams.update(
        {
            "figure.facecolor": COLOR_SURFACE,
            "axes.facecolor": COLOR_SURFACE,
            "axes.edgecolor": COLOR_GRID,
            "axes.labelcolor": COLOR_TEXT_SUB,
            "axes.titlecolor": COLOR_TEXT,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": COLOR_GRID,
            "grid.linewidth": 0.8,
            "xtick.color": COLOR_TEXT_SUB,
            "ytick.color": COLOR_TEXT_SUB,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
        }
    )


def annotate_point(ax, date, value, label, offset):
    ax.scatter([date], [value], s=36, color=COLOR_LINE, edgecolor=COLOR_SURFACE, linewidth=1.5, zorder=3)
    ax.annotate(
        f"{label}\n{value:,.0f}",
        xy=(date, value),
        xytext=offset,
        textcoords="offset points",
        ha="center",
        fontsize=9,
        color=COLOR_TEXT_SUB,
    )


def plot_close_line(df, save_path):
    """요청 그래프: 2000년 1월 ~ 2019년 12월 종가 라인그래프"""
    close = df.loc[START_DATE:END_DATE, "close"]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(close.index, close.values, color=COLOR_LINE, linewidth=1.6)

    # 주요 고점·저점과 마지막 값만 표시
    marks = [
        (close["2000":"2001"].idxmax(), "닷컴 고점", (22, 10)),
        (close["2002":"2003"].idxmin(), "저점", (0, -32)),
        (close["2007":"2008"].idxmax(), "금융위기 전 고점", (0, 10)),
        (close["2008":"2009"].idxmin(), "금융위기 저점", (0, -32)),
        (close.index[-1], f"마지막 ({close.index[-1]:%Y-%m-%d})", (-62, 2)),
    ]
    for date, label, offset in marks:
        annotate_point(ax, date, close[date], label, offset)

    first, last = close.index[0], close.index[-1]
    ax.set_title(
        f"S&P 500 일별 종가 ({first.year}년 {first.month}월 ~ {last.year}년 {last.month}월 {last.day}일)",
        fontsize=14,
        pad=14,
    )
    ax.set_ylabel("종가 (포인트)")
    ax.set_xlim(pd.Timestamp(START_DATE), pd.Timestamp(END_DATE))
    ax.set_ylim(0, 3500)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
    ax.grid(axis="x", visible=False)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    return fig


def plot_multi_view(df, annual, by_month, drawdown, save_path):
    """다각도 분석 요약: 연수익률 · 낙폭 · 변동성 · 월별 평균"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.5))

    # 연도별 수익률
    ax = axes[0, 0]
    returns = annual["수익률(%)"]
    colors = [COLOR_LINE if value >= 0 else COLOR_NEGATIVE for value in returns]
    ax.bar(returns.index, returns.values, color=colors, width=0.8)
    ax.axhline(0, color=COLOR_TEXT_SUB, linewidth=0.8)
    ax.set_title("연도별 수익률 (%, 2019년은 11/14까지)")
    ax.set_xticks(range(2000, 2020, 2))
    ax.margins(y=0.1)
    ax.grid(axis="x", visible=False)
    for year in [returns.idxmax(), returns.idxmin()]:
        value = returns[year]
        ax.annotate(
            f"{value:.1f}%",
            xy=(year, value),
            xytext=(0, 4 if value > 0 else -14),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=COLOR_TEXT_SUB,
        )

    # 고점 대비 낙폭
    ax = axes[0, 1]
    ax.plot(drawdown.index, drawdown.values * 100, color=COLOR_NEGATIVE, linewidth=1.4)
    ax.set_title(f"고점 대비 낙폭 (%, 최대 {drawdown.min():.1%})")
    ax.set_ylim(drawdown.min() * 100 - 5, 0)
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="x", visible=False)

    # 60거래일 이동 변동성
    ax = axes[1, 0]
    rolling_vol = df["return"].rolling(60).std() * np.sqrt(TRADING_DAYS) * 100
    ax.plot(rolling_vol.index, rolling_vol.values, color=COLOR_LINE, linewidth=1.4)
    ax.set_title("연환산 변동성 (%, 60거래일 이동)")
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="x", visible=False)

    # 월별 평균 수익률
    ax = axes[1, 1]
    monthly = by_month["평균수익률"]
    colors = [COLOR_LINE if value >= 0 else COLOR_NEGATIVE for value in monthly]
    ax.bar(monthly.index, monthly.values, color=colors, width=0.8)
    ax.axhline(0, color=COLOR_TEXT_SUB, linewidth=0.8)
    ax.set_title("월별 평균 수익률 (%)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{month}월" for month in range(1, 13)])
    ax.grid(axis="x", visible=False)

    fig.suptitle("S&P 500 다각도 분석", x=0.01, ha="left", fontsize=15, fontweight="bold", color=COLOR_TEXT)
    fig.tight_layout(h_pad=2.5, w_pad=2.5)
    fig.savefig(save_path, dpi=150)
    return fig


def main():
    parser = argparse.ArgumentParser(description="S&P 500 데이터 클렌징 및 분석")
    parser.add_argument("csv", nargs="?", default=DEFAULT_CSV, type=Path, help="입력 CSV 경로")
    parser.add_argument("--no-show", action="store_true", help="그래프 창을 띄우지 않고 파일로만 저장")
    args = parser.parse_args()

    # Windows 콘솔에서 한글이 깨지지 않도록 설정
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 120)
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = load_and_clean(args.csv)
    analyze_overview(df)
    annual = analyze_annual(df)
    by_month = analyze_seasonality(df)
    drawdown = analyze_risk(df)
    analyze_trend(df)

    setup_matplotlib()
    plot_close_line(df, OUTPUT_DIR / "sp500_close_2000_2019.png")
    plot_multi_view(df, annual, by_month, drawdown, OUTPUT_DIR / "sp500_multi_view.png")

    df.to_csv(OUTPUT_DIR / "sp500_cleaned.csv", encoding="utf-8-sig")
    annual.round(2).to_csv(OUTPUT_DIR / "sp500_annual_stats.csv", encoding="utf-8-sig")
    (OUTPUT_DIR / "sp500_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n결과 저장 위치: {OUTPUT_DIR}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
