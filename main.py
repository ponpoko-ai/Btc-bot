import os
import sys
import datetime
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# --- Discord 送信関数 (テキスト + 画像対応) ---
def send_discord(message=None, image_path=None):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK is not set.")
        return

    payload = {}
    if message:
        payload["content"] = message

    files = {}
    if image_path and os.path.exists(image_path):
        files["file"] = open(image_path, "rb")

    try:
        if files:
            response = requests.post(webhook_url, data=payload, files=files)
        else:
            response = requests.post(webhook_url, json=payload)

        if response.status_code not in [200, 204]:
            print(f"Failed to send message: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Discord send error: {e}")
    finally:
        if "file" in files:
            files["file"].close()

# --- 1. HTF Map & Stoch Cloud 計算 ---
def analyze_stoch_hub(ticker):
    try:
        df_d = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        df_4h_raw = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)

        if df_d.empty or df_4h_raw.empty:
            return None

        if isinstance(df_d.columns, pd.MultiIndex):
            df_d.columns = df_d.columns.get_level_values(0)
        if isinstance(df_4h_raw.columns, pd.MultiIndex):
            df_4h_raw.columns = df_4h_raw.columns.get_level_values(0)

        df_4h = df_4h_raw.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()

        # HTF 14 Range (D & 4H)
        htf_k = 14
        d_hi = float(df_d['High'].rolling(htf_k).max().iloc[-1])
        d_lo = float(df_d['Low'].rolling(htf_k).min().iloc[-1])
        zD80 = d_lo + 0.80 * (d_hi - d_lo)
        zD20 = d_lo + 0.20 * (d_hi - d_lo)

        h4_hi = float(df_4h['High'].rolling(htf_k).max().iloc[-1])
        h4_lo = float(df_4h['Low'].rolling(htf_k).min().iloc[-1])
        z4H80 = h4_lo + 0.80 * (h4_hi - h4_lo)
        z4H20 = h4_lo + 0.20 * (h4_hi - h4_lo)

        # Chart TF Stoch Cloud (15, 21, 21)
        c_close = df_4h['Close']
        hh_c = df_4h['High'].rolling(15).max()
        ll_c = df_4h['Low'].rolling(15).min()
        fast_k = 100.0 * (c_close - ll_c) / (hh_c - ll_c + 1e-9)
        stoch_k = fast_k.rolling(21).mean()
        stoch_d = stoch_k.rolling(21).mean()

        last_k = float(stoch_k.iloc[-1])
        last_d = float(stoch_d.iloc[-1])
        prev_k = float(stoch_k.iloc[-2]) if len(stoch_k) > 1 else last_k

        cur_price = float(c_close.iloc[-1])

        # ゾーン判定
        zone_d = "80%以上 (高値圏)" if cur_price >= zD80 else ("20%以下 (安値圏)" if cur_price <= zD20 else "中立")
        zone_4h = "80%以上 (高値圏)" if cur_price >= z4H80 else ("20%以下 (安値圏)" if cur_price <= z4H20 else "中立")

        return {
            "price": cur_price,
            "zone_d": zone_d,
            "zone_4h": zone_4h,
            "stoch_k": last_k,
            "stoch_d": last_d,
            "k_change": last_k - prev_k
        }
    except Exception as e:
        print(f"Error analyze_stoch_hub({ticker}): {e}")
        return None

# --- 2. 相関分析 (BTC, XAU, EUR/USD) ---
def analyze_correlations():
    try:
        tickers = {"BTC": "BTC-USD", "XAU": "GC=F", "EURUSD": "EURUSD=X"}
        df_data = pd.DataFrame()

        for name, sym in tickers.items():
            data = yf.download(sym, period="30d", interval="1d", progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            df_data[name] = data['Close']

        returns = df_data.pct_change().dropna()
        corr_matrix = returns.corr()

        btc_xau = corr_matrix.loc["BTC", "XAU"]
        btc_eur = corr_matrix.loc["BTC", "EURUSD"]
        xau_eur = corr_matrix.loc["XAU", "EURUSD"]

        def fmt_corr(val):
            if val >= 0.6:
                return f"{val:.2f} (強い正の相関 🔗)"
            elif val <= -0.6:
                return f"{val:.2f} (強い逆相関 🔄)"
            else:
                return f"{val:.2f} (ほぼ無相関 ⚪)"

        msg = "**🔗 資産間相関分析 (直近30日)**\n"
        msg += f"・**BTC vs GOLD (XAU)**: {fmt_corr(btc_xau)}\n"
        msg += f"・**BTC vs EUR/USD**: {fmt_corr(btc_eur)}\n"
        msg += f"・**GOLD vs EUR/USD**: {fmt_corr(xau_eur)}\n"
        return msg
    except Exception as e:
        print(f"Error in analyze_correlations: {e}")
        return "相関データの取得に失敗しました。"

# --- 3. 通貨強弱グラフ生成＆解説 ---
def generate_currency_strength():
    try:
        pairs = {
            'USDJPY=X': ('USD', 'JPY'),
            'EURUSD=X': ('EUR', 'USD'),
            'GBPUSD=X': ('GBP', 'USD'),
            'AUDUSD=X': ('AUD', 'USD'),
            'EURJPY=X': ('EUR', 'JPY'),
            'GBPJPY=X': ('GBP', 'JPY')
        }
        df_all = pd.DataFrame()
        for p_sym in pairs.keys():
            d = yf.download(p_sym, period="1d", interval="5m", progress=False, auto_adjust=True)
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)
            df_all[p_sym] = d['Close']

        # 累積変動率から相対強弱を算出
        returns = df_all.pct_change().fillna(0)
        c_returns = (1 + returns).cumprod() - 1

        strength = pd.DataFrame(index=c_returns.index)
        strength['USD'] = -c_returns['EURUSD=X'] - c_returns['GBPUSD=X'] - c_returns['AUDUSD=X'] + c_returns['USDJPY=X']
        strength['EUR'] = c_returns['EURUSD=X'] + c_returns['EURJPY=X']
        strength['GBP'] = c_returns['GBPUSD=X'] + c_returns['GBPJPY=X']
        strength['JPY'] = -c_returns['USDJPY=X'] - c_returns['EURJPY=X'] - c_returns['GBPJPY=X']

        # 通貨強弱グラフの描画
        plt.figure(figsize=(8, 4))
        plt.plot(strength.index, strength['USD'], label='USD', color='blue')
        plt.plot(strength.index, strength['EUR'], label='EUR', color='orange')
        plt.plot(strength.index, strength['GBP'], label='GBP', color='green')
        plt.plot(strength.index, strength['JPY'], label='purple')
        plt.title("Currency Strength (Today)")
        plt.legend(loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.5)

        img_path = "currency_strength.png"
        plt.savefig(img_path, bbox_inches='tight')
        plt.close()

        # 最新順位の判定
        last_str = strength.iloc[-1].sort_values(ascending=False)
        strongest = last_str.index[0]
        weakest = last_str.index[-1]

        comment = f"**📊 本日の通貨強弱解説**\n"
        comment += f"・最買われ通貨: **{strongest}** / 最売られ通貨: **{weakest}**\n"
        comment += f"・現在、`{strongest}/{weakest}` のペアで最も明確なトレンドが発生しやすい環境です。"

        return img_path, comment
    except Exception as e:
        print(f"Error generate_currency_strength: {e}")
        return None, "通貨強弱の生成に失敗しました。"

# --- メイン処理 ---
def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")

    # Header
    msg = f"=============================\n📢 **市場戦略定期レポート** ({time_str})\n=============================\n\n"

    # 1. Stoch Hub 分析 (BTC, GOLD, USDJPY)
    symbols = {"BTC/USDT": "BTC-USD", "GOLD (XAU)": "GC=F", "USD/JPY": "JPY=X"}
    msg += "### 🎯 **Stoch Hub + HTF 80/20 ゾーン変化**\n"

    large_changes = []

    for name, ticker in symbols.items():
        res = analyze_stoch_hub(ticker)
        if res:
            p_str = f"{res['price']:,.2f}" if res['price'] > 10 else f"{res['price']:,.4f}"
            msg += f"・**{name}** ({p_str})\n"
            msg += f"  - 日足ゾーン: `{res['zone_d']}` | 4Hゾーン: `{res['zone_4h']}`\n"
            msg += f"  - Stoch Cloud: K `{res['stoch_k']:.1f}` / D `{res['stoch_d']:.1f}` (前枠差: `{res['k_change']:+.1f}`)\n"

            if abs(res['k_change']) >= 15.0:
                large_changes.append(f"⚠️ **{name}**: Stoch Kが `{res['k_change']:+.1f}` ポイントの急変を検出！")

    if large_changes:
        msg += "\n**🔥 大きく変化した銘柄**\n" + "\n".join(large_changes) + "\n"

    msg += "\n---\n\n"

    # 2. 相関分析
    msg += analyze_correlations() + "\n\n---\n\n"

    # 3. 通貨強弱 (画像付き)
    img_path, strength_comment = generate_currency_strength()
    msg += strength_comment

    # Discord送信
    send_discord(message=msg, image_path=img_path)

if __name__ == "__main__":
    main()
