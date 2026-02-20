"""
株式分析モジュール
Yahoo Finance APIを使って日本株のデータを取得し、テクニカル分析を行う
"""

import json
import logging
import time
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# デフォルト銘柄
DEFAULT_STOCKS = {
    "9104": "商船三井",
    "8604": "野村ホールディングス",
    "6098": "リクルートホールディングス",
    "8058": "三菱商事",
    "7203": "トヨタ自動車",
    "6758": "ソニーグループ",
    "9984": "ソフトバンクグループ",
    "7974": "任天堂",
    "6861": "キーエンス",
    "8306": "三菱UFJフィナンシャル・グループ",
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
        df = _download_stock(ticker_symbol, period="5d")
        if df is None or df.empty:
            return False, f"銘柄コード {code} のデータが見つかりません"
        # 銘柄名の取得を試みる（JSONDecodeError が発生しやすい箇所）
        name = f"銘柄{code}"
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info or {}
            name = info.get("longName") or info.get("shortName") or name
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"銘柄名取得でJSONエラー {code}: {e}")
        except Exception as e:
            logger.warning(f"銘柄名取得失敗 {code}: {e}")
        additional_stocks[code] = name
        return True, f"{code}（{name}）を追加しました"
    except Exception as e:
        logger.error(f"銘柄追加失敗 {code}: {e}")
        return False, f"銘柄の取得に失敗しました: {str(e)}"


def remove_stock(code: str) -> tuple[bool, str]:
    """追加銘柄を削除する（デフォルト銘柄は削除不可）"""
    if code in DEFAULT_STOCKS:
        return False, "デフォルト銘柄は削除できません"
    if code in additional_stocks:
        name = additional_stocks.pop(code)
        return True, f"{code}（{name}）を削除しました"
    return False, f"{code} は登録されていません"


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """MultiIndex カラムをフラット化する"""
    if isinstance(df.columns, pd.MultiIndex):
        # ("Close", "9104.T") -> "Close" のようにフラット化
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df


def _download_stock(ticker_symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """yf.download を使って株価データを取得し、カラムをフラット化する。
    yf.download が失敗した場合は Ticker.history() をフォールバックとして使用する。
    """
    # 方法1: yf.download
    for attempt in range(3):
        try:
            df = yf.download(
                ticker_symbol,
                period=period,
                progress=False,
                auto_adjust=True,
                timeout=15,
            )
            if df is not None and not df.empty:
                df = _flatten_columns(df)
                logger.info(f"[download] 取得成功 {ticker_symbol}: {len(df)}行, カラム={list(df.columns)}")
                return df
            logger.warning(f"[download] 空データ {ticker_symbol} (attempt {attempt + 1}/3)")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[download] JSONパースエラー {ticker_symbol} (attempt {attempt + 1}/3): {e}")
        except Exception as e:
            logger.error(f"[download] 取得エラー {ticker_symbol} (attempt {attempt + 1}/3): {e}")
        if attempt < 2:
            time.sleep(2 * (attempt + 1))  # 2秒, 4秒 の指数バックオフ

    # 方法2: Ticker.history() をフォールバックとして使用
    logger.info(f"[history] フォールバック開始 {ticker_symbol}")
    for attempt in range(2):
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period=period, timeout=15)
            if df is not None and not df.empty:
                df = _flatten_columns(df)
                logger.info(f"[history] 取得成功 {ticker_symbol}: {len(df)}行, カラム={list(df.columns)}")
                return df
            logger.warning(f"[history] 空データ {ticker_symbol} (attempt {attempt + 1}/2)")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[history] JSONパースエラー {ticker_symbol} (attempt {attempt + 1}/2): {e}")
        except Exception as e:
            logger.error(f"[history] 取得エラー {ticker_symbol} (attempt {attempt + 1}/2): {e}")
        if attempt < 1:
            time.sleep(3)

    logger.error(f"全ての取得方法が失敗: {ticker_symbol}")
    return None


def fetch_stock_data(code: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """Yahoo Financeから株価データを取得"""
    ticker_symbol = f"{code}.T"
    return _download_stock(ticker_symbol, period)


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


def _safe_float(val) -> Optional[float]:
    """pandas の値を安全に float に変換する"""
    try:
        f = float(val)
        if pd.isna(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def analyze_stock(code: str) -> Optional[dict]:
    """指定銘柄の包括的な分析を行う"""
    all_stocks = get_all_stocks()
    name = all_stocks.get(code, f"銘柄{code}")

    logger.info(f"分析開始: {code} ({name})")

    df = fetch_stock_data(code, period="6mo")
    if df is None:
        logger.error(f"データ取得失敗: {code}")
        return None

    if len(df) < 20:
        logger.error(f"データ不足: {code} ({len(df)}行)")
        return None

    # カラムの存在確認
    required_cols = {"Close", "Volume"}
    available_cols = set(df.columns)
    if not required_cols.issubset(available_cols):
        logger.error(f"必要なカラムが不足: {code}, 利用可能={available_cols}")
        return None

    try:
        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        # Series に変換（DataFrame の場合）
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        current_price = float(close.iloc[-1])

        # --- 直近の値動き ---
        today_change = float(close.iloc[-1] - close.iloc[-2]) if len(close) >= 2 else 0
        today_change_pct = (today_change / float(close.iloc[-2]) * 100) if len(close) >= 2 else 0

        yesterday_change = float(close.iloc[-2] - close.iloc[-3]) if len(close) >= 3 else 0
        yesterday_change_pct = (yesterday_change / float(close.iloc[-3]) * 100) if len(close) >= 3 else 0

        if len(close) >= 6:
            week_ago_price = float(close.iloc[-6])
            week_change = current_price - week_ago_price
            week_change_pct = (week_change / week_ago_price) * 100
        else:
            week_ago_price = float(close.iloc[0])
            week_change = current_price - week_ago_price
            week_change_pct = (week_change / week_ago_price) * 100 if week_ago_price != 0 else 0

        # 過去3ヶ月の平均株価との比較（約63営業日）
        three_month_data = close.tail(63) if len(close) >= 63 else close
        three_month_avg = float(three_month_data.mean())
        vs_3m_avg_pct = ((current_price - three_month_avg) / three_month_avg) * 100 if three_month_avg != 0 else 0

        # --- テクニカル指標 ---
        sma5 = calc_sma(close, 5)
        sma25 = calc_sma(close, 25)
        sma75 = calc_sma(close, 75)

        current_sma5 = _safe_float(sma5.iloc[-1])
        current_sma25 = _safe_float(sma25.iloc[-1])
        current_sma75 = _safe_float(sma75.iloc[-1]) if len(sma75) > 0 else None

        # ゴールデンクロス / デッドクロス判定
        ma_cross_signal = 0
        if current_sma5 is not None and current_sma25 is not None:
            prev_sma5 = _safe_float(sma5.iloc[-2])
            prev_sma25 = _safe_float(sma25.iloc[-2])
            if prev_sma5 is not None and prev_sma25 is not None:
                if prev_sma5 <= prev_sma25 and current_sma5 > current_sma25:
                    ma_cross_signal = 2  # ゴールデンクロス
                elif prev_sma5 >= prev_sma25 and current_sma5 < current_sma25:
                    ma_cross_signal = -2  # デッドクロス

        # RSI
        rsi = calc_rsi(close)
        current_rsi = _safe_float(rsi.iloc[-1]) or 50.0

        rsi_signal = 0
        if current_rsi <= 20:
            rsi_signal = 2
        elif current_rsi <= 30:
            rsi_signal = 1
        elif current_rsi >= 80:
            rsi_signal = -2
        elif current_rsi >= 70:
            rsi_signal = -1

        # MACD
        macd_line, signal_line, macd_hist = calc_macd(close)
        current_macd = _safe_float(macd_line.iloc[-1]) or 0.0
        current_signal = _safe_float(signal_line.iloc[-1]) or 0.0
        current_hist = _safe_float(macd_hist.iloc[-1]) or 0.0

        macd_signal = 0
        if len(macd_hist) >= 2:
            prev_hist = _safe_float(macd_hist.iloc[-2]) or 0.0
            if prev_hist <= 0 and current_hist > 0:
                macd_signal = 2
            elif prev_hist >= 0 and current_hist < 0:
                macd_signal = -2
            elif current_hist > 0:
                macd_signal = 1
            elif current_hist < 0:
                macd_signal = -1

        # ボリンジャーバンド
        bb_upper, bb_middle, bb_lower = calc_bollinger_bands(close)
        current_bb_upper = _safe_float(bb_upper.iloc[-1])
        current_bb_lower = _safe_float(bb_lower.iloc[-1])

        bb_signal = 0
        if current_bb_lower is not None and current_price <= current_bb_lower:
            bb_signal = 2
        elif current_bb_upper is not None and current_price >= current_bb_upper:
            bb_signal = -2
        elif current_bb_lower is not None and current_bb_upper is not None:
            bb_mid = (current_bb_upper + current_bb_lower) / 2
            if current_price < bb_mid:
                bb_signal = 1
            else:
                bb_signal = -1

        # 出来高分析
        avg_volume_20 = float(volume.tail(20).mean())
        current_volume = float(volume.iloc[-1])
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0

        # 価格トレンド（条件順序を修正: 大きい値を先に判定）
        price_trend_signal = 0
        if vs_3m_avg_pct > 20:
            price_trend_signal = -2  # かなり過熱
        elif vs_3m_avg_pct > 10:
            price_trend_signal = -1  # 過熱気味
        elif vs_3m_avg_pct < -20:
            price_trend_signal = 2  # かなり割安
        elif vs_3m_avg_pct < -10:
            price_trend_signal = 1  # 割安気味

        # --- 総合判定 ---
        total_score = (
            ma_cross_signal * 1.5
            + rsi_signal * 1.2
            + macd_signal * 1.3
            + bb_signal * 1.0
            + price_trend_signal * 1.0
        )

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

        # シグナル詳細
        signals = []

        if ma_cross_signal == 2:
            signals.append({"name": "移動平均線", "detail": "ゴールデンクロス発生", "direction": "buy"})
        elif ma_cross_signal == -2:
            signals.append({"name": "移動平均線", "detail": "デッドクロス発生", "direction": "sell"})
        elif current_sma5 is not None and current_sma25 is not None:
            if current_sma5 > current_sma25:
                signals.append({"name": "移動平均線", "detail": "短期線が長期線の上（上昇トレンド）", "direction": "buy"})
            else:
                signals.append({"name": "移動平均線", "detail": "短期線が長期線の下（下降トレンド）", "direction": "sell"})

        if current_rsi <= 30:
            signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（売られすぎ）", "direction": "buy"})
        elif current_rsi >= 70:
            signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（買われすぎ）", "direction": "sell"})
        else:
            signals.append({"name": "RSI", "detail": f"RSI={current_rsi:.1f}（中立圏）", "direction": "neutral"})

        if macd_signal >= 1:
            signals.append({"name": "MACD", "detail": "買いシグナル", "direction": "buy"})
        elif macd_signal <= -1:
            signals.append({"name": "MACD", "detail": "売りシグナル", "direction": "sell"})
        else:
            signals.append({"name": "MACD", "detail": "中立", "direction": "neutral"})

        if bb_signal >= 1:
            signals.append({"name": "ボリンジャーバンド", "detail": "下限付近（反発期待）", "direction": "buy"})
        elif bb_signal <= -1:
            signals.append({"name": "ボリンジャーバンド", "detail": "上限付近（反落注意）", "direction": "sell"})
        else:
            signals.append({"name": "ボリンジャーバンド", "detail": "バンド中央付近", "direction": "neutral"})

        if vs_3m_avg_pct < -5:
            signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（割安圏）", "direction": "buy"})
        elif vs_3m_avg_pct > 5:
            signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（割高圏）", "direction": "sell"})
        else:
            signals.append({"name": "3ヶ月平均比較", "detail": f"平均比 {vs_3m_avg_pct:+.1f}%（適正圏）", "direction": "neutral"})

        # 直近30日の価格推移（チャート用）
        recent_prices = []
        recent_data = df.tail(30)
        for idx, row in recent_data.iterrows():
            date_str = idx.strftime("%m/%d") if hasattr(idx, "strftime") else str(idx)[:10]
            close_val = float(row["Close"]) if not isinstance(row["Close"], pd.Series) else float(row["Close"].iloc[0])
            vol_val = int(row["Volume"]) if not isinstance(row["Volume"], pd.Series) else int(row["Volume"].iloc[0])
            recent_prices.append({
                "date": date_str,
                "close": round(close_val, 1),
                "volume": vol_val,
            })

        result = {
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
            "sma5": round(current_sma5, 1) if current_sma5 is not None else None,
            "sma25": round(current_sma25, 1) if current_sma25 is not None else None,
            "sma75": round(current_sma75, 1) if current_sma75 is not None else None,
            "rsi": round(current_rsi, 1),
            "macd": round(current_macd, 1),
            "macd_signal": round(current_signal, 1),
            "macd_hist": round(current_hist, 1),
            "bb_upper": round(current_bb_upper, 1) if current_bb_upper is not None else None,
            "bb_lower": round(current_bb_lower, 1) if current_bb_lower is not None else None,
            "volume_ratio": round(volume_ratio, 2),
            "recommendation": recommendation,
            "recommendation_label": recommendation_label,
            "total_score": round(total_score, 2),
            "signals": signals,
            "recent_prices": recent_prices,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        logger.info(f"分析完了: {code} -> {recommendation_label} (score={total_score:.2f})")
        return result

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"分析中にJSONパースエラー: {code}: {e}")
        return None
    except Exception as e:
        logger.error(f"分析中にエラー: {code}: {e}", exc_info=True)
        return None


def analyze_all_stocks() -> dict:
    """全登録銘柄の分析を行う"""
    results = []
    errors = []
    for code, name in get_all_stocks().items():
        try:
            result = analyze_stock(code)
            if result:
                results.append(result)
            else:
                errors.append({"code": code, "name": name, "reason": "データ取得または分析に失敗"})
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"銘柄 {code} のJSON解析エラー: {e}")
            errors.append({"code": code, "name": name, "reason": f"JSONパースエラー: {e}"})
        except Exception as e:
            logger.error(f"銘柄 {code} の分析中にエラー: {e}")
            errors.append({"code": code, "name": name, "reason": str(e)})
    return {"results": results, "errors": errors}


def debug_fetch(code: str) -> dict:
    """デバッグ用: 生データ取得テスト"""
    ticker_symbol = f"{code}.T"
    info = {"code": code, "ticker": ticker_symbol, "steps": []}

    # Step 1: yf.download を試す
    try:
        df = yf.download(ticker_symbol, period="5d", progress=False, auto_adjust=True, timeout=15)
        if df is not None and not df.empty:
            df_flat = _flatten_columns(df.copy())
            info["steps"].append({
                "method": "yf.download",
                "success": True,
                "rows": len(df),
                "columns": str(list(df_flat.columns)),
                "column_type": str(type(df.columns)),
            })
        else:
            info["steps"].append({"method": "yf.download", "success": False, "reason": "empty"})
    except (json.JSONDecodeError, ValueError) as e:
        info["steps"].append({"method": "yf.download", "success": False, "reason": f"JSONDecodeError: {e}"})
    except Exception as e:
        info["steps"].append({"method": "yf.download", "success": False, "reason": str(e)})

    # Step 2: Ticker.history を試す
    try:
        ticker = yf.Ticker(ticker_symbol)
        df2 = ticker.history(period="5d")
        if df2 is not None and not df2.empty:
            info["steps"].append({
                "method": "Ticker.history",
                "success": True,
                "rows": len(df2),
                "columns": str(list(df2.columns)),
                "column_type": str(type(df2.columns)),
            })
        else:
            info["steps"].append({"method": "Ticker.history", "success": False, "reason": "empty"})
    except (json.JSONDecodeError, ValueError) as e:
        info["steps"].append({"method": "Ticker.history", "success": False, "reason": f"JSONDecodeError: {e}"})
    except Exception as e:
        info["steps"].append({"method": "Ticker.history", "success": False, "reason": str(e)})

    # Step 3: yfinance バージョン情報
    info["yfinance_version"] = yf.__version__

    return info
