"""
株式分析モジュール
Yahoo Finance APIを使って日本株のデータを取得し、テクニカル分析を行う
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# デフォルト銘柄
DEFAULT_STOCKS = {
    "9104": "商船三井",
    "8604": "野村ホールディングス",
    "6098": "リクルートホールディングス",
    "8058": "三菱商事",
}

# 追加銘柄を保持するインメモリストア
additional_stocks: dict[str, str] = {}


def get_all_stocks() -> dict[str, str]:
    """デフォルト銘柄 + 追加銘柄の一覧を返す"""
    merged = {}
    merged.update(DEFAULT_STOCKS)
    merged.update(additional_stocks)
    return merged


def add_stock(code: str) -> tuple[bool, str]:
    """銘柄コードを追加する。存在確認も行う。"""
    code = code.strip()
    if not code.isdigit() or len(code) != 4:
        return False, "銘柄コードは4桁の数字で入力してください"

    if code in get_all_stocks():
        return False, f"{code} は既に登録されています"

    ticker_symbol = f"{code}.T"
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        name = info.get("longName") or info.get("shortName") or ""
        if not name:
            # infoが取れない場合、historyで存在確認
            hist = ticker.history(period="5d")
            if hist.empty:
                return False, f"銘柄コード {code} のデータが見つかりません"
            name = f"銘柄{code}"
        additional_stocks[code] = name
        return True, f"{code}（{name}）を追加しました"
    except Exception as e:
        return False, f"銘柄の取得に失敗しました: {str(e)}"


def remove_stock(code: str) -> tuple[bool, str]:
    """追加銘柄を削除する（デフォルト銘柄は削除不可）"""
    if code in DEFAULT_STOCKS:
        return False, "デフォルト銘柄は削除できません"
    if code in additional_stocks:
        name = additional_stocks.pop(code)
        return True, f"{code}（{name}）を削除しました"
    return False, f"{code} は登録されていません"


def fetch_stock_data(code: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """Yahoo Financeから株価データを取得"""
    ticker_symbol = f"{code}.T"
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def calc_sma(series: pd.Series, window: int) -> pd.Series:
    """単純移動平均"""
    return series.rolling(window=window).mean()


def calc_ema(series: pd.Series, span: int) -> pd.Series:
    """指数移動平均"""
    return series.ewm(span=span, adjust=False).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD (Moving Average Convergence Divergence)"""
    ema12 = calc_ema(series, 12)
    ema26 = calc_ema(series, 26)
    macd_line = ema12 - ema26
    signal_line = calc_ema(macd_line, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    """ボリンジャーバンド"""
    sma = calc_sma(series, window)
    std = series.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


def analyze_stock(code: str) -> Optional[dict]:
    """指定銘柄の包括的な分析を行う"""
    all_stocks = get_all_stocks()
    name = all_stocks.get(code, f"銘柄{code}")

    df = fetch_stock_data(code, period="6mo")
    if df is None or len(df) < 20:
        return None

    close = df["Close"]
    volume = df["Volume"]
    current_price = float(close.iloc[-1])

    # --- 直近の値動き ---
    # 今日の変動
    today_change = float(close.iloc[-1] - close.iloc[-2]) if len(close) >= 2 else 0
    today_change_pct = (today_change / float(close.iloc[-2]) * 100) if len(close) >= 2 else 0

    # 昨日の変動
    yesterday_change = float(close.iloc[-2] - close.iloc[-3]) if len(close) >= 3 else 0
    yesterday_change_pct = (yesterday_change / float(close.iloc[-3]) * 100) if len(close) >= 3 else 0

    # 過去1週間の変動（5営業日）
    if len(close) >= 6:
        week_ago_price = float(close.iloc[-6])
        week_change = current_price - week_ago_price
        week_change_pct = (week_change / week_ago_price) * 100
    else:
        week_ago_price = float(close.iloc[0])
        week_change = current_price - week_ago_price
        week_change_pct = (week_change / week_ago_price) * 100

    # 過去3ヶ月の平均株価との比較（約63営業日）
    three_month_data = close.tail(63) if len(close) >= 63 else close
    three_month_avg = float(three_month_data.mean())
    vs_3m_avg_pct = ((current_price - three_month_avg) / three_month_avg) * 100

    # --- テクニカル指標 ---
    # 移動平均線
    sma5 = calc_sma(close, 5)
    sma25 = calc_sma(close, 25)
    sma75 = calc_sma(close, 75)

    current_sma5 = float(sma5.iloc[-1]) if not pd.isna(sma5.iloc[-1]) else None
    current_sma25 = float(sma25.iloc[-1]) if not pd.isna(sma25.iloc[-1]) else None
    current_sma75 = float(sma75.iloc[-1]) if len(sma75) > 0 and not pd.isna(sma75.iloc[-1]) else None

    # ゴールデンクロス / デッドクロス判定
    ma_cross_signal = 0
    if current_sma5 and current_sma25:
        prev_sma5 = float(sma5.iloc[-2]) if not pd.isna(sma5.iloc[-2]) else None
        prev_sma25 = float(sma25.iloc[-2]) if not pd.isna(sma25.iloc[-2]) else None
        if prev_sma5 and prev_sma25:
            if prev_sma5 <= prev_sma25 and current_sma5 > current_sma25:
                ma_cross_signal = 2  # ゴールデンクロス
            elif prev_sma5 >= prev_sma25 and current_sma5 < current_sma25:
                ma_cross_signal = -2  # デッドクロス

    # RSI
    rsi = calc_rsi(close)
    current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

    rsi_signal = 0
    if current_rsi <= 20:
        rsi_signal = 2  # 強い買いシグナル
    elif current_rsi <= 30:
        rsi_signal = 1  # 買いシグナル
    elif current_rsi >= 80:
        rsi_signal = -2  # 強い売りシグナル
    elif current_rsi >= 70:
        rsi_signal = -1  # 売りシグナル

    # MACD
    macd_line, signal_line, macd_hist = calc_macd(close)
    current_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0
    current_signal = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0
    current_hist = float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else 0

    macd_signal = 0
    if len(macd_hist) >= 2:
        prev_hist = float(macd_hist.iloc[-2]) if not pd.isna(macd_hist.iloc[-2]) else 0
        if prev_hist <= 0 and current_hist > 0:
            macd_signal = 2  # 買い転換
        elif prev_hist >= 0 and current_hist < 0:
            macd_signal = -2  # 売り転換
        elif current_hist > 0:
            macd_signal = 1
        elif current_hist < 0:
            macd_signal = -1

    # ボリンジャーバンド
    bb_upper, bb_middle, bb_lower = calc_bollinger_bands(close)
    current_bb_upper = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None
    current_bb_lower = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None

    bb_signal = 0
    if current_bb_lower and current_price <= current_bb_lower:
        bb_signal = 2  # 下限バンド到達 → 買い
    elif current_bb_upper and current_price >= current_bb_upper:
        bb_signal = -2  # 上限バンド到達 → 売り
    elif current_bb_lower and current_bb_upper:
        bb_mid = (current_bb_upper + current_bb_lower) / 2
        if current_price < bb_mid:
            bb_signal = 1
        else:
            bb_signal = -1

    # 出来高分析
    avg_volume_20 = float(volume.tail(20).mean())
    current_volume = float(volume.iloc[-1])
    volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0

    # 価格トレンド（5日間の方向性）
    price_trend_signal = 0
    if vs_3m_avg_pct > 10:
        price_trend_signal = -1  # 過熱気味
    elif vs_3m_avg_pct > 20:
        price_trend_signal = -2  # かなり過熱
    elif vs_3m_avg_pct < -10:
        price_trend_signal = 1  # 割安気味
    elif vs_3m_avg_pct < -20:
        price_trend_signal = 2  # かなり割安

    # --- 総合判定 ---
    # 各シグナルの重み付け合計
    total_score = (
        ma_cross_signal * 1.5
        + rsi_signal * 1.2
        + macd_signal * 1.3
        + bb_signal * 1.0
        + price_trend_signal * 1.0
    )

    # 5段階判定
    if total_score >= 4:
        recommendation = "strong_buy"
        recommendation_label = "強く買い推奨"
    elif total_score >= 1.5:
        recommendation = "buy"
        recommendation_label = "買い推奨"
    elif total_score <= -4:
        recommendation = "strong_sell"
        recommendation_label = "強く売り推奨"
    elif total_score <= -1.5:
        recommendation = "sell"
        recommendation_label = "売り推奨"
    else:
        recommendation = "hold"
        recommendation_label = "様子見"

    # シグナル詳細の構築
    signals = []

    # 移動平均
    if ma_cross_signal == 2:
        signals.append({"name": "移動平均線", "detail": "ゴールデンクロス発生", "direction": "buy"})
    elif ma_cross_signal == -2:
        signals.append({"name": "移動平均線", "detail": "デッドクロス発生", "direction": "sell"})
    elif current_sma5 and current_sma25:
        if current_sma5 > current_sma25:
            signals.append({"name": "移動平均線", "detail": "短期線が長期線の上（上昇トレンド）", "direction": "buy"})
        else:
            signals.append({"name": "移動平均線", "detail": "短期線が長期線の下（下降トレンド）", "direction": "sell"})

    # RSI
    if current_rsi <= 30:
        signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（売られすぎ）", "direction": "buy"})
    elif current_rsi >= 70:
        signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（買われすぎ）", "direction": "sell"})
    else:
        signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（中立圏）", "direction": "neutral"})

    # MACD
    if macd_signal >= 1:
        signals.append({"name": "MACD", "detail": "買いシグナル", "direction": "buy"})
    elif macd_signal <= -1:
        signals.append({"name": "MACD", "detail": "売りシグナル", "direction": "sell"})
    else:
        signals.append({"name": "MACD", "detail": "中立", "direction": "neutral"})

    # ボリンジャーバンド
    if bb_signal >= 1:
        signals.append({"name": "ボリンジャーバンド", "detail": "下限付近（反発期待）", "direction": "buy"})
    elif bb_signal <= -1:
        signals.append({"name": "ボリンジャーバンド", "detail": "上限付近（反落注意）", "direction": "sell"})
    else:
        signals.append({"name": "ボリンジャーバンド", "detail": "バンド中央付近", "direction": "neutral"})

    # 3ヶ月平均との比較
    if vs_3m_avg_pct < -5:
        signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（割安圏）", "direction": "buy"})
    elif vs_3m_avg_pct > 5:
        signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（割高圏）", "direction": "sell"})
    else:
        signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（適正圏）", "direction": "neutral"})

    # 直近5日の価格推移（チャート用）
    recent_prices = []
    recent_data = df.tail(30)
    for idx, row in recent_data.iterrows():
        date_str = idx.strftime("%m/%d") if hasattr(idx, "strftime") else str(idx)[:10]
        recent_prices.append({
            "date": date_str,
            "close": round(float(row["Close"]), 1),
            "volume": int(row["Volume"]),
        })

    return {
        "code": code,
        "name": name,
        "current_price": round(current_price, 1),
        "today_change": round(today_change, 1),
        "today_change_pct": round(today_change_pct, 2),
        "yesterday_change": round(yesterday_change, 1),
        "yesterday_change_pct": round(yesterday_change_pct, 2),
        "week_change": round(week_change, 1),
        "week_change_pct": round(week_change_pct, 2),
        "three_month_avg": round(three_month_avg, 1),
        "vs_3m_avg_pct": round(vs_3m_avg_pct, 2),
        "sma5": round(current_sma5, 1) if current_sma5 else None,
        "sma25": round(current_sma25, 1) if current_sma25 else None,
        "sma75": round(current_sma75, 1) if current_sma75 else None,
        "rsi": round(current_rsi, 1),
        "macd": round(current_macd, 1),
        "macd_signal": round(current_signal, 1),
        "macd_hist": round(current_hist, 1),
        "bb_upper": round(current_bb_upper, 1) if current_bb_upper else None,
        "bb_lower": round(current_bb_lower, 1) if current_bb_lower else None,
        "volume_ratio": round(volume_ratio, 2),
        "recommendation": recommendation,
        "recommendation_label": recommendation_label,
        "total_score": round(total_score, 2),
        "signals": signals,
        "recent_prices": recent_prices,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def analyze_all_stocks() -> list[dict]:
    """全登録銘柄の分析を行う"""
    results = []
    for code in get_all_stocks():
        result = analyze_stock(code)
        if result:
            results.append(result)
    return results
