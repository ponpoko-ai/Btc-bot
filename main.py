import os
import requests
import pandas as pd
import yfinance as yf

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# 監視シンボル (Yahoo Finance Tickers)
TICKERS = {
    'BTC': 'BTC-USD',
    'GOLD': 'GC=F',
    'DXY': 'DX-Y.NYB',
    'US10Y': '^TNX',
    'NAS100': '^IXIC',
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'JPY=X',
    'EURJPY': 'EURJPY=X',
    'GBPJPY': 'GBPJPY=X',
    'EURGBP': 'EURGBP=X'
}

def get_data():
    data = {}
    tickers_list = list(TICKERS.values())
    df_all = yf.download(tickers_list, period='10d', interval='1h', progress=False)['Close']
    
    for name, ticker in TICKERS.items():
        if ticker in df_all.columns:
            s = df_all[ticker].dropna()
            ema20 = s.ewm(span=20, adjust=False).mean()
            ema50 = s.ewm(span=50, adjust=False).mean()
            
            # Stochastics (14, 3)
            low14 = s.rolling(14).min()
            high14 = s.rolling(14).max()
            stoch = (100 * ((s - low14) / (high14 - low14))).rolling(3).mean()
            
            data[name] = {
                'price': round(s.iloc[-1], 2),
                'change_4h': round(((s.iloc[-1] - s.iloc[-5]) / s.iloc[-5]) * 100, 2),
                'trend': 'Bull' if ema20.iloc[-1] > ema50.iloc[-1] else 'Bear',
                'stoch': round(stoch.iloc[-1], 1) if not pd.isna(stoch.iloc[-1]) else 50.0
            }
    return data

def analyze_macro(data):
    dxy_trend = data['DXY']['trend']
    us10y_trend = data['US10Y']['trend']
    nas_trend = data['NAS100']['trend']
    
    # Gold correlation: 通常 DXY↓ & US10Y↓ が追い風
    gold_env = []
    if dxy_trend == 'Bear': gold_env.append("ドル安(+) ")
    else: gold_env.append("ドル高(-) ")
    if us10y_trend == 'Bear': gold_env.append("金利低下(+) ")
    else: gold_env.append("金利上昇(-) ")
    
    # BTC correlation: 通常 DXY↓ & NAS100↑ (リスクオン) が追い風
    btc_env = []
    if dxy_trend == 'Bear': btc_env.append("ドル安(+) ")
    else: btc_env.append("ドル高(-) ")
    if nas_trend == 'Bull': btc_env.append("株高/リスクオン(+) ")
    else: btc_env.append("株安/リスクオフ(-) ")

    return "".join(gold_env), "".join(btc_env)

def analyze_forex_distortion(data):
    # 通貨別のスコアリング (買われすぎ/売られすぎの相対評価)
    scores = {'USD': 0, 'EUR': 0, 'GBP': 0, 'JPY': 0}
    
    # EUR/USD
    if data['EURUSD']['stoch'] > 70: scores['EUR'] += 1; scores['USD'] -= 1
    elif data['EURUSD']['stoch'] < 30: scores['EUR'] -= 1; scores['USD'] += 1
    
    # GBP/USD
    if data['GBPUSD']['stoch'] > 70: scores['GBP'] += 1; scores['USD'] -= 1
    elif data['GBPUSD']['stoch'] < 30: scores['GBP'] -= 1; scores['USD'] += 1
    
    # USD/JPY (JPYは逆数表記)
    if data['USDJPY']['stoch'] > 70: scores['USD'] += 1; scores['JPY'] -= 1
    elif data['USDJPY']['stoch'] < 30: scores['USD'] -= 1; scores['JPY'] += 1
    
    # EUR/JPY
    if data['EURJPY']['stoch'] > 70: scores['EUR'] += 1; scores['JPY'] -= 1
    elif data['EURJPY']['stoch'] < 30: scores['EUR'] -= 1; scores['JPY'] += 1

    # GBP/JPY
    if data['GBPJPY']['stoch'] > 70: scores['GBP'] += 1; scores['JPY'] -= 1
    elif data['GBPJPY']['stoch'] < 30: scores['GBPJPY'] = 0; scores['JPY'] += 1

    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)
    
    distortion_msg = ""
    if scores[strongest] >= 2 and scores[weakest] <= -2:
        distortion_msg = f"⚠️ **【歪み検出】** 現在【{strongest}】が強い買われすぎ、【{weakest}】が売られすぎ状態です。`{strongest}/{weakest}` ペアの短期過熱からの逆張り・調整注意局面！"
    else:
        distortion_msg = f"バランス推移中（相対強者: {strongest} / 相対弱者: {weakest}）"
        
    return distortion_msg, strongest, weakest

def main():
    data = get_data()
    gold_env, btc_env = analyze_macro(data)
    distortion_msg, strongest_curr, weakest_curr = analyze_forex_distortion(data)
    
    msg = "🌐 **【マーケット・マクロ & 歪み監視レポート】**\n\n"
    
    # 1. メイン資産ステータス
    msg += "📊 **BTC & GOLD 現状**\n"
    msg += f"・**BTC**: ${data['BTC']['price']} (4H: {data['BTC']['change_4h']}%) | Trend: {data['BTC']['trend']} | Stoch: {data['BTC']['stoch']}\n"
    msg += f"  ┗ 外部環境 (DXY/NAS): {btc_env}\n"
    msg += f"・**GOLD**: ${data['GOLD']['price']} (4H: {data['GOLD']['change_4h']}%) | Trend: {data['GOLD']['trend']} | Stoch: {data['GOLD']['stoch']}\n"
    msg += f"  ┗ 外部環境 (DXY/US10Y): {gold_env}\n\n"

    # 2. 相関マクロ指標
    msg += "📈 **マクロ相関指標 (DXY / US10Y / NAS100)**\n"
    msg += f"・DXY(ドル指数): {data['DXY']['price']} ({data['DXY']['trend']}) | Stoch: {data['DXY']['stoch']}\n"
    msg += f"・US10Y(米10年債): {data['US10Y']['price']}% ({data['US10Y']['trend']}) | Stoch: {data['US10Y']['stoch']}\n"
    msg += f"・NAS100(株価): {data['NAS100']['price']} ({data['NAS100']['trend']}) | Stoch: {data['NAS100']['stoch']}\n\n"

    # 3. 為替（EUR/USD/GBP/JPY）買われすぎ・売られすぎの歪み
    msg += "💱 **為替（EUR/USD/GBP/JPY）通貨強弱 & 歪み分析**\n"
    msg += f"・EUR/USD: {data['EURUSD']['price']} (Stoch: {data['EURUSD']['stoch']})\n"
    msg += f"・GBP/USD: {data['GBPUSD']['price']} (Stoch: {data['GBPUSD']['stoch']})\n"
    msg += f"・USD/JPY: {data['USDJPY']['price']} (Stoch: {data['USDJPY']['stoch']})\n"
    msg += f"・EUR/JPY: {data['EURJPY']['price']} (Stoch: {data['EURJPY']['stoch']})\n"
    msg += f"💡 **歪み判定**: {distortion_msg}\n"

    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={'content': msg})

if __name__ == '__main__':
    main()
