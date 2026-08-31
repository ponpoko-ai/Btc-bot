import os
import sys

# 必要なライブラリの自動インストール処理
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
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
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 204:
        print("Successfully sent message to Discord.")
    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")

# --- Pine Script相当のテクニカル指標計算エンジン ---
def calculate_stoch(df, k_len, k_smooth, d_smooth):
    lowest_low = df['Low'].rolling(window=k_len).min()
    highest_high = df['High'].rolling(window=k_len).max()
    raw_k = 100 * ((df['Close'] - lowest_low) / (highest_high - lowest_low + 1e-9))
    stoch_k = raw_k.rolling(window=k_smooth).mean()
    stoch_d = stoch_k.rolling(window=d_smooth).mean()
    return stoch_d

def analyze_symbol(ticker, symbol_name):
    try:
        # データ取得 (日足: 1y, 4H/1H: 60d)
        df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
        df_4h = yf.download(ticker, period="60d", interval="1h", progress=False) # 4H代替（1Hをリサンプリング）
        df_1h = yf.download(ticker, period="60d", interval="1h", progress=False)

        if df_d.empty or df_1h.empty:
            return None

        # 4Hデータのリサンプリング
        df_4h = df_4h.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()

        res = {}
        tfs = {'日足': df_d, '4H': df_4h, '1H': df_1h}

        for tf_name, df in tfs.items():
            if len(df) < 200:
                continue

            close = df['Close']
            
            # 1. EMA & PO
            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean()
            ema200 = close.ewm(span=200, adjust=False).mean()

            last_c = close.iloc[-1]
            last_e20 = ema20.iloc[-1]
            last_e50 = ema50.iloc[-1]
            last_e200 = ema200.iloc[-1]

            po = "Bull" if (last_e20 > last_e50 > last_e200) else ("Bear" if (last_e20 < last_e50 < last_e200) else "Mix")

            # 2. BB State
            basis = close.rolling(20).mean()
            dev = close.rolling(20).std() * 2.0
            upper = basis + dev
            lower = basis - dev
            bandwidth = (upper - lower) / (basis + 1e-9) * 100.0
            bb_rank = bandwidth.rank(pct=True).iloc[-1] * 100.0

            state = "RG"
            if last_c > basis.iloc[-1] and bb_rank >= 12.0:
                state = "TU"
            elif last_c < basis.iloc[-1] and bb_rank >= 12.0:
                state = "TD"
            elif bb_rank <= 6.0:
                state = "BD"

            # 3. Std Stoch (14, 3, 3) & Slow Stoch (140, 84, 84)
            std_stoch = calculate_stoch(df, 14, 3, 3)
            slow_stoch = calculate_stoch(df, 140, 84, 84)

            last_std = std_stoch.iloc[-1] if not np.isnan(std_stoch.iloc[-1]) else 50.0
            last_slow = slow_stoch.iloc[-1] if not np.isnan(slow_stoch.iloc[-1]) else 50.0
            prev_slow = slow_stoch.iloc[-2] if not np.isnan(slow_stoch.iloc[-2]) else last_slow

            slow_dir = "Up" if last_slow > prev_slow else "Dn"

            res[tf_name] = {
                'close': last_c,
                'po': po,
                'state': state,
                'std_stoch': last_std,
                'slow_stoch': last_slow,
                'slow_dir': slow_dir
            }
        return res
    except Exception as e:
        print(f"Error processing {symbol_name}: {e}")
        return None

# --- レポート文章の生成 ---
def generate_report(symbol_name, data, is_fx=False):
    if not data or '日足' not in data or '4H' not in data or '1H' not in data:
        return f"# 📰【{symbol_name}】データ取得失敗\n"

    price = data['1H']['close']
    price_str = f"{price:,.2f}" if price > 10 else f"{price:,.4f}"

    # 見出し作成 (状態判定ベース)
    state_4h = data['4H']['state']
    po_4h = data['4H']['po']
    slow_dir_4h = data['4H']['slow_dir']

    headline = ""
    if state_4h == "TU" or (po_4h == "Bull" and slow_dir_4h == "Up"):
        headline = f"4H足強気トレンド進行中。押し目買い優勢（現在値: {price_str}）"
    elif state_4h == "TD" or (po_4h == "Bear" and slow_dir_4h == "Dn"):
        headline = f"4H足下落圧力継続。戻り売り優勢（現在値: {price_str}）"
    elif state_4h == "BD":
        headline = f"4H足スクイーズ（エネルギー蓄積中）。ブレイク待ち（現在値: {price_str}）"
    else:
        headline = f"レンジ推移・方向感模索局面（現在値: {price_str}）"

    msg = f"# 📰【{symbol_name}】{headline}\n\n"

    # 🕒 時間足分析
    msg += "### 🕒 時間足分析（Pine Fusion Table準拠）\n"
    for tf in ['日足', '4H', '1H']:
        d = data[tf]
        msg += f"・**{tf}**: State [{d['state']}] | PO [{d['po']}] | SlowStoch [{d['slow_stoch']:.1f} ({d['slow_dir']})]\n"

    # ⚔️ ターゲットシナリオ
    msg += "\n### ⚔️ ターゲットシナリオ\n"
    if po_4h == "Bull":
        msg += f"・🟢 **買い手の狙い**: 1H足のSlowStoch({data['1H']['slow_stoch']:.1f})売られすぎ水準（20以下）からの反発でロング。\n"
        msg += f"・🔴 **売り手の狙い**: 日足/4H足の過熱感（StdStoch: {data['4H']['std_stoch']:.1f}）を確認しての短期逆張りショート。\n"
    else:
        msg += f"・🟢 **買い手の狙い**: 1H/4H足での底打ち・Wボトム形成（SlowStoch反転）を確認しての打診買い。\n"
        msg += f"・🔴 **売り手の狙い**: 1H/4H足EMAラインへの戻り目から、SlowStoch({data['4H']['slow_stoch']:.1f})低下に沿った戻り売り。\n"

    # 📝 総評（ストキャス＆他指標相関）
    msg += "\n### 📝 総評（MTF Fusion & ストキャス環境）\n"
    msg += f"・**SlowStoch(140,84,84)**: 日足 [{data['日足']['slow_stoch']:.1f}] / 4H [{data['4H']['slow_stoch']:.1f}] / 1H [{data['1H']['slow_stoch']:.1f}]\n"
    msg += f"・**StdStoch(14,3,3)**: 4H [{data['4H']['std_stoch']:.1f}] (80以上=買われすぎ / 20以下=売られすぎ)\n"

    # 評価コメント判定
    slow_4h = data['4H']['slow_stoch']
    if slow_4h >= 80:
        msg += "→ 4H足スローストキャスが高値圏（過熱域）に位置。高値更新追撃はリスクが高く、1H足の調整消化を待つのが吉。"
    elif slow_4h <= 20:
        msg += "→ 4H足スローストキャスが底値圏（売られすぎ域）に位置。売り一巡からの反発・底打ち形成を警戒する局面。"
    else:
        msg += "→ 4H足スローストキャスは中立域を推移。下位足（1H）のセットアップとブレイク方向に追従。"

    return msg

def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    
    weekday = now_jst.weekday()
    is_weekend = weekday in [5, 6]

    full_message = f"=============================\n🤖 **マルチアセット戦略レポート** ({time_str})\n=============================\n\n"

    # 1. BTC/USDT (Yahoo Finance ticker: BTC-USD)
    btc_data = analyze_symbol("BTC-USD", "BTC/USDT")
    if btc_data:
        full_message += generate_report("BTC/USDT", btc_data) + "\n---\n\n"

    # 2. GOLD & USD/JPY (土日はスキップ)
    if not is_weekend:
        # GOLD (GC=F)
        gold_data = analyze_symbol("GC=F", "GOLD (XAU/USD)")
        if gold_data:
            full_message += generate_report("GOLD (XAU/USD)", gold_data) + "\n---\n\n"

        # USD/JPY (JPY=X)
        usdjpy_data = analyze_symbol("JPY=X", "USD/JPY")
        if usdjpy_data:
            full_message += generate_report("USD/JPY", usdjpy_data, is_fx=True)
    else:
        full_message += "☕ **【週末市場休止のお知らせ】**\n土日のため為替（FX）およびゴールド（コモディティ）市場はクローズしています。週明け月曜朝より分析を再開します。"

    send_discord(full_message)

if __name__ == "__main__":
    main()
