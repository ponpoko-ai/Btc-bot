import os
import requests
import pandas as pd
import ccxt
import yfinance as yf

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# ---------- 1. BTC 単独 & MTF詳細分析 ----------
TIMEFRAMES = {'5m': '5m', '15m': '15m', '1H': '1h', '4H': '4h', 'D': '1d'}

def fetch_btc_analysis():
    exchange = ccxt.kraken({'enableRateLimit': True})
    results = {}
    for tf_display, tf_code in TIMEFRAMES.items():
        ohlcv = exchange.fetch_ohlcv('BTC/USD', timeframe=tf_code, limit=300)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['bb_middle'] = df['close'].rolling(20).mean()
        
        low14, high14 = df['low'].rolling(14).min(), df['high'].rolling(14).max()
        df['stoch_k'] = (100 * ((df['close'] - low14) / (high14 - low14))).rolling(3).mean()
        
        low140, high140 = df['low'].rolling(140).min(), df['high'].rolling(140).max()
        df['slow_k'] = (100 * ((df['close'] - low140) / (high140 - low140))).rolling(84).mean()
        
        last, prev = df.iloc[-1], df.iloc[-2]
        po = "Bull" if last['ema20'] > last['ema50'] > last['ema200'] else ("Bear" if last['ema20'] < last['ema50'] < last['ema200'] else "Mix")
        ema_str = f"{'↑' if last['ema20']>prev['ema20'] else '↓'}{'↑' if last['ema50']>prev['ema50'] else '↓'}{'↑' if last['ema200']>prev['ema200'] else '↓'}"
        
        state = "TU" if last['close'] > last['bb_middle'] and last['ema20'] > prev['ema20'] else ("TD" if last['close'] < last['bb_middle'] and last['ema20'] < prev['ema20'] else "RG")
        sdir = "Up" if last['slow_k'] > prev['slow_k'] else "Dn"
        
        results[tf_display] = {
            'state': state, 'po': po, 'ema': ema_str,
            'stoch': round(last['stoch_k'], 1),
            'stoch_diff': round(last['stoch_k'] - prev['stoch_k'], 1),
            'slow': round(last['slow_k'], 1), 'sdir': sdir,
            'close': last['close'], 'close_prev': prev['close']
        }
    return results

# ---------- 2. マクロ & 為替分析 ----------
TICKERS = {
    'GOLD': 'GC=F', 'DXY': 'DX-Y.NYB', 'US10Y': '^TNX', 'NAS100': '^IXIC',
    'EURUSD': 'EURUSD=X', 'GBPUSD': 'GBPUSD=X', 'USDJPY': 'JPY=X',
    'EURJPY': 'EURJPY=X', 'GBPJPY': 'GBPJPY=X', 'EURGBP': 'EURGBP=X'
}

def fetch_macro_and_forex():
    tickers_list = list(TICKERS.values())
    df_all = yf.download(tickers_list, period='10d', interval='1h', progress=False)['Close']
    data = {}
    
    for name, ticker in TICKERS.items():
        if ticker in df_all.columns:
            s = df_all[ticker].dropna()
            ema20 = s.ewm(span=20, adjust=False).mean()
            ema50 = s.ewm(span=50, adjust=False).mean()
            low14, high14 = s.rolling(14).min(), s.rolling(14).max()
            stoch = (100 * ((s - low14) / (high14 - low14))).rolling(3).mean()
            
            data[name] = {
                'price': round(s.iloc[-1], 2),
                'change_4h': round(((s.iloc[-1] - s.iloc[-5]) / s.iloc[-5]) * 100, 2),
                'trend': 'Bull' if ema20.iloc[-1] > ema50.iloc[-1] else 'Bear',
                'stoch': round(stoch.iloc[-1], 1) if not pd.isna(stoch.iloc[-1]) else 50.0
            }
    return data

def main():
    btc_res = fetch_btc_analysis()
    macro = fetch_macro_and_forex()
    
    d, h4, h1, m15, m5 = btc_res['D'], btc_res['4H'], btc_res['1H'], btc_res['15m'], btc_res['5m']
    h4_chg = round(((h4['close'] - h4['close_prev']) / h4['close_prev']) * 100, 2)
    btc_env = f"DXY:{'安(+)' if macro['DXY']['trend']=='Bear' else '高(-)'} / NAS100:{'高(+)' if macro['NAS100']['trend']=='Bull' else '安(-)'}"
    
    msg = "⏰ **【4時間足確定：次の4時間のトレード戦略】**\n\n"
    
    # --- 1. BTC 戦略 ---
    msg += "🪙 **【BTC/USDT 戦略】**\n"
    msg += "```\n"
    msg += f"{'TF':<5} | {'State':<5} | {'PO':<5} | {'EMA':<5} | {'Stoch':<5} | {'Slow':<5} | {'SDir':<4}\n"
    msg += "-" * 50 + "\n"
    for tf, r in btc_res.items():
        msg += f"{tf:<5} | {r['state']:<5} | {r['po']:<5} | {r['ema']:<5} | {r['stoch']:<5.1f} | {r['slow']:<5.1f} | {r['sdir']:<4}\n"
    msg += "```\n"
    msg += f"・**4H確定値**: ${h4['close']} ({h4_chg}%) | 外部: {btc_env}\n"
    
    # BTC 次の4時間戦略
    msg += "🎯 **BTC戦略**: "
    if h4['state'] == 'TU':
        if h1['stoch'] < 40:
            msg += "【押し目買い狙い】4H上昇継続中。1H足の引きつけ完了。15m/5mのStochゴールデンクロスでロングエントリー。\n\n"
        elif m5['stoch'] > 70:
            msg += "【高値警戒・押し待ち】トレンド強いが短期高値圏。15mレベルの調整（Stoch<30）を待ってからの押し目買い。\n\n"
        else:
            msg += "【上目線維持】順張りロング継続。短期足の波乗り（SDir: Up）に従う。\n\n"
    elif h4['state'] == 'TD':
        if h1['stoch'] > 60:
            msg += "【戻り売り狙い】4H下落継続中。1H足の戻り完了。15m/5mのデッドクロスでショートエントリー。\n\n"
        else:
            msg += "【下目線維持】順張りショート継続。戻りを待っての売り崩し。\n\n"
    else:
        msg += "【レンジ静観】4H方向感なし。上位足サポート・レジスタンス引きつけ、または抜け待ち。\n\n"

    # --- 2. GOLD 戦略 ---
    gold = macro['GOLD']
    gold_env = f"DXY:{'安(+)' if macro['DXY']['trend']=='Bear' else '高(-)'} / US10Y:{'低下(+)' if macro['US10Y']['trend']=='Bear' else '上昇(-)'}"
    
    msg += "🏆 **【GOLD（金） 戦略】**\n"
    msg += f"・**4H確定値**: ${gold['price']} ({gold['change_4h']}%) | Trend: {gold['trend']} | Stoch: {gold['stoch']}\n"
    msg += f"・**相関環境**: {gold_env}\n"
    
    msg += "🎯 **GOLD戦略**: "
    if gold['trend'] == 'Bull':
        if gold['stoch'] > 80:
            msg += "上昇トレンド中だが過熱感あり。一旦の調整下げを待ってからの押し目買い推奨。\n\n"
        else:
            msg += "ドルの弱さ/金利低下の追い風あり。押し目からのロング買い優勢。\n\n"
    else:
        if gold['stoch'] < 20:
            msg += "下落傾向だが売られすぎ圏。安値追いは避け、戻りを待ってからのショート検討。\n\n"
        else:
            msg += "上値が重い展開。戻り売りスタンス維持。\n\n"

    # --- 3. 為替（ドル円焦点 & 通貨強弱歪み） ---
    usdjpy, eurusd, gbpusd, eurjpy = macro['USDJPY'], macro['EURUSD'], macro['GBPUSD'], macro['EURJPY']
    
    scores = {'USD': 0, 'EUR': 0, 'GBP': 0, 'JPY': 0}
    if eurusd['stoch'] > 70: scores['EUR'] += 1; scores['USD'] -= 1
    elif eurusd['stoch'] < 30: scores['EUR'] -= 1; scores['USD'] += 1
    if gbpusd['stoch'] > 70: scores['GBP'] += 1; scores['USD'] -= 1
    elif gbpusd['stoch'] < 30: scores['GBP'] -= 1; scores['USD'] += 1
    if usdjpy['stoch'] > 70: scores['USD'] += 1; scores['JPY'] -= 1
    elif usdjpy['stoch'] < 30: scores['USD'] -= 1; scores['JPY'] += 1
    if eurjpy['stoch'] > 70: scores['EUR'] += 1; scores['JPY'] -= 1
    elif eurjpy['stoch'] < 30: scores['EUR'] -= 1; scores['JPY'] += 1

    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)

    msg += "💱 **【為替（ドル円 & 歪み戦略）】**\n"
    msg += f"・**USD/JPY確定**: {usdjpy['price']} (Trend: {usdjpy['trend']} | Stoch: {usdjpy['stoch']})\n"
    msg += f"・**4通貨強弱順位**: [強] {strongest} ＞ ... ＞ [弱] {weakest}\n"
    
    msg += "🎯 **為替戦略**: "
    if strongest == 'USD' and weakest == 'JPY':
        msg += "ドル独歩高×円独歩安。USD/JPYの押し目買いが最優勢だが、過熱感からの急な調整売りに注意。\n"
    elif strongest == 'JPY' and weakest == 'USD':
        msg += "円高×ドル安。USD/JPYの戻り売り狙い。\n"
    elif strongest != weakest:
        msg += f"最も乖離が大きい組み合わせは `{strongest}/{weakest}`。ペアの過熱反転や歪み狙いが効率的。\n"
    else:
        msg += "通貨間のバランスが拮抗中。明確なトレンド発生まで静観推奨。\n"

    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={'content': msg})

if __name__ == '__main__':
    main()
