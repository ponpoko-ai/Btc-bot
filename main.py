import os
import sys

# 必要なライブラリの自動インストール
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance pandas numpy requests")
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import requests

import datetime

# --- Discord 送信関数 ---
def send_discord(message):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK is not set.")
        return
    
    # Discordの2000文字制限対策
    if len(message) > 1900:
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            requests.post(webhook_url, json={"content": chunk})
    else:
        response = requests.post(webhook_url, json={"content": message})
        if response.status_code != 204:
            print(f"Failed to send message: {response.status_code}, {response.text}")

# --- ストキャスティクス計算 ---
def calc_stoch(df, k_len, k_smooth, d_smooth):
    lowest_low = df['Low'].rolling(window=k_len).min()
    highest_high = df['High'].rolling(window=k_len).max()
    denom = highest_high - lowest_low
    denom = denom.replace(0, np.nan)
    raw_k = 100 * ((df['Close'] - lowest_low) / denom)
    raw_k = raw_k.fillna(50)
    stoch_k = raw_k.rolling(window=k_smooth).mean()
    stoch_d = stoch_k.rolling(window=d_smooth).mean()
    return stoch_d.fillna(50)

# --- 単一銘柄のデータ取得と計算 ---
def analyze_symbol(ticker):
    try:
        # yfinance からデータ取得 (auto_adjust=True)
        df_d = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        df_1h = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)

        if df_d.empty or df_1h.empty:
            print(f"[{ticker}] Data is empty.")
            return None

        # MultiIndexの解消（Column整理）
        if isinstance(df_d.columns, pd.MultiIndex):
            df_d.columns = df_d.columns.get_level_values(0)
        if isinstance(df_1h.columns, pd.MultiIndex):
            df_1h.columns = df_1h.columns.get_level_values(0)

        # 4H足の生成 (1Hからのリサンプリング)
        df_4h = df_1h.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()

        res = {}
        tfs = {'5m': df_1h, '15m': df_1h, '1H': df_1h, '4H': df_4h, 'D': df_d}

        for tf_name, df in tfs.items():
            if len(df) < 50:
                continue

            close = df['Close']
            high = df['High']
            low = df['Low']

            # EMA & PO (Perfect Order)
            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean()
            ema200 = close.ewm(span=200, adjust=False).mean()

            c_val = float(close.iloc[-1])
            e20 = float(ema20.iloc[-1])
            e50 = float(ema50.iloc[-1])
            e200 = float(ema200.iloc[-1])

            po = "Bull" if (e20 > e50 > e200) else ("Bear" if (e20 < e50 < e200) else "Mix")

            # BB State
            basis = close.rolling(20).mean()
            dev = close.rolling(20).std() * 2.0
            upper = basis + dev
            lower = basis - dev
            bandwidth = (upper - lower) / (basis + 1e-9) * 100.0
            bb_rank = float(bandwidth.rank(pct=True).iloc[-1] * 100.0) if len(bandwidth) > 0 else 50.0

            basis_last = float(basis.iloc[-1])
            if c_val > basis_last and bb_rank >= 12.0:
                state = "TU" # Trend Up
            elif c_val < basis_last and bb_rank >= 12.0:
                state = "TD" # Trend Down
            elif bb_rank <= 6.0:
                state = "BD" # Build
            else:
                state = "RG" # Range

            # Std Stoch (14, 3, 3) & Slow Stoch (140, 84, 84)
            std_stoch = calc_stoch(df, 14, 3, 3)
            slow_stoch = calc_stoch(df, 140, 84, 84)

            last_std = float(std_stoch.iloc[-1])
            last_slow = float(slow_stoch.iloc[-1])
            prev_slow = float(slow_stoch.iloc[-2]) if len(slow_stoch) > 1 else last_slow

            slow_dir = "Up" if last_slow > prev_slow else ("Dn" if last_slow < prev_slow else "Flat")

            res[tf_name] = {
                'close': c_val,
                'state': state,
                'po': po,
                'std_stoch': last_std,
                'slow_stoch': last_slow,
                'slow_dir': slow_dir
            }
        return res
    except Exception as e:
        print(f"Error in analyze_symbol({ticker}): {e}")
        return None

# --- レポート文章の生成 ---
def generate_report(symbol_name, data):
    if not data or '1H' not in data or '4H' not in data or 'D' not in data:
        return f"### 📰【{symbol_name}】データ解析中..."

    price = data['1H']['close']
    price_str = f"{price:,.2f}" if price > 10 else f"{price:,.4f}"

    state_4h = data['4H']['state']
    po_4h = data['4H']['po']
    slow_dir_4h = data['4H']['slow_dir']

    # ヘッドライン判定
    if state_4h == "TU" or (po_4h == "Bull" and slow_dir_4h == "Up"):
        headline = "強気トレンド進行中。押し目買い優勢"
    elif state_4h == "TD" or (po_4h == "Bear" and slow_dir_4h == "Dn"):
        headline = "下落圧力継続。戻り売り優勢"
    elif state_4h == "BD":
        headline = "スクイーズ（エネルギー蓄積中）。ブレイク待ち"
    else:
        headline = "レンジ推移・方向感模索局面"

    msg = f"## 📰【{symbol_name}】{headline} (現在値: {price_str})\n"
    
    # 時間足分析テーブル風表示
    msg += "```\n"
    msg += f"{'TF':<6} | {'State':<5} | {'PO':<5} | {'Stoch':<6} | {'Slow':<6} | {'SDir':<4}\n"
    msg += "-" * 42 + "\n"
    for tf in ['1H', '4H', 'D']:
        if tf in data:
            d = data[tf]
            msg += f"{tf:<6} | {d['state']:<5} | {d['po']:<5} | {d['std_stoch']:<6.1f} | {d['slow_stoch']:<6.1f} | {d['slow_dir']:<4}\n"
    msg += "```\n"

    # ターゲットシナリオ
    msg += "**⚔️ ターゲットシナリオ**\n"
    if po_4h == "Bull":
        msg += f"・🟢 **買い手の狙い**: 1H足 SlowStoch ({data['1H']['slow_stoch']:.1f}) の押し目（20近辺）からの反発狙い。\n"
        msg += f"・🔴 **売り手の狙い**: 4H/日足の高値圏（StdStoch: {data['4H']['std_stoch']:.1f}）での逆張り短期ショート。\n"
    else:
        msg += f"・🟢 **買い手の狙い**: 1H/4H足のSlowStoch反転および底固め確認後の打診買い。\n"
        msg += f"・🔴 **売り手の狙い**: EMA戻り目および 4H SlowStoch ({data['4H']['slow_stoch']:.1f}) 低下に沿った戻り売り。\n"

    # 総評
    slow_4h = data['4H']['slow_stoch']
    msg += "\n**📝 総評（Pine MTF Fusion 判定）**\n"
    if slow_4h >= 80:
        msg += "・4H足スローストキャスが**高値圏（過熱域）**です。高値追いは避け、下位足の調整待ちを推奨。\n"
    elif slow_4h <= 20:
        msg += "・4H足スローストキャスが**底値圏（売られすぎ域）**です。売り一巡からの底打ち反発を警戒。\n"
    else:
        msg += "・4H足スローストキャスは**中立域**を推移。1H足のセットアップと抜け方向に素直に追従。\n"

    return msg

def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    
    weekday = now_jst.weekday()
    is_weekend = weekday in [5, 6]

    header_msg = f"=============================\n🤖 **マルチアセット戦略レポート** ({time_str})\n=============================\n\n"
    send_discord(header_msg)

    # 1. BTC/USDT
    btc_data = analyze_symbol("BTC-USD")
    if btc_data:
        send_discord(generate_report("BTC/USDT", btc_data))

    # 2. GOLD & USD/JPY (土日以外)
    if not is_weekend:
        gold_data = analyze_symbol("GC=F")
        if gold_data:
            send_discord(generate_report("GOLD (XAU/USD)", gold_data))

        usdjpy_data = analyze_symbol("JPY=X")
        if usdjpy_data:
            send_discord(generate_report("USD/JPY", usdjpy_data))
    else:
        send_discord("☕ **【週末市場休止】**\n土日のためFX・ゴールド市場はクローズ中です。週明け月曜朝より配信を再開します。")

if __name__ == "__main__":
    main()
