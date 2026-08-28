import os
import requests
import pandas as pd
import pandas_ta as ta
import ccxt

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
SYMBOL = 'BTC/USDT'

exchange = ccxt.binance()

TIMEFRAMES = {
    '5m': '5m',
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    'D': '1d'
}

def analyze():
    results = {}
    for tf_display, tf_code in TIMEFRAMES.items():
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=tf_code, limit=300)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # EMA
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['ema200'] = ta.ema(df['close'], length=200)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        po = "Bull" if last['ema20'] > last['ema50'] > last['ema200'] else ("Bear" if last['ema20'] < last['ema50'] < last['ema200'] else "Mix")
        
        dir_s = "↑" if last['ema20'] > prev['ema20'] else "↓"
        dir_m = "↑" if last['ema50'] > prev['ema50'] else "↓"
        dir_l = "↑" if last['ema200'] > prev['ema200'] else "↓"
        ema_str = f"{dir_s}{dir_m}{dir_l}"

        # BB / State
        bb = ta.bbands(df['close'], length=20, std=2.0)
        basis = bb['BBM_20_2.0'].iloc[-1]
        
        if last['close'] > basis and last['ema20'] > prev['ema20']:
            state = "TU"
        elif last['close'] < basis and last['ema20'] < prev['ema20']:
            state = "TD"
        else:
            state = "RG"

        # Stoch (14,3,3)
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        stoch_v = round(stoch.iloc[-1]['STOCHk_14_3_3'], 1)

        # Slow Stoch (140,84,84)
        slow = ta.stoch(df['high'], df['low'], df['close'], k=140, d=84, smooth_k=84)
        slow_v = round(slow.iloc[-1]['STOCHk_140_84_84'], 1)
        slow_prev = slow.iloc[-2]['STOCHk_140_84_84']
        sdir = "Up" if slow_v > slow_prev else "Dn"

        results[tf_display] = {
            'state': state, 'po': po, 'ema': ema_str,
            'stoch': stoch_v, 'slow': slow_v, 'sdir': sdir
        }
    return results

def build_commentary(res):
    d, h4, h1, m15, m5 = res['D'], res['4H'], res['1H'], res['15m'], res['5m']
    
    comments = []
    
    # 日足
    if d['state'] == 'TU':
        comments.append("・**日足（D）**：強い上昇環境。" + ("ただしStoch高値圏で過熱感あり。" if d['stoch'] > 80 else ""))
    elif d['state'] == 'TD':
        comments.append("・**日足（D）**：下落環境傾向。" + ("Stoch低水準で売られすぎ。" if d['stoch'] < 20 else ""))
    else:
        comments.append("・**日足（D）**：レンジ・方向感模索中。")
        
    # 4時間足
    if h4['state'] == 'TU':
        comments.append("・**4時間足（4H）**：上昇トレンド進行中。押し目買いの基本土台。")
    elif h4['state'] == 'TD':
        comments.append("・**4時間足（4H）**：下降トレンド進行中。戻り売りの基本土台。")
    else:
        comments.append("・**4時間足（4H）**：レンジ構成中。")
        
    # 1時間足
    if h1['stoch'] < 30:
        comments.append("・**1時間足（1H）**：調整が進み、上位足に対する押し目・買場を形成中。")
    elif h1['stoch'] > 70:
        comments.append("・**1時間足（1H）**：高値圏まで上昇済み。ミクロの過熱に注意。")
    else:
        comments.append("・**1時間足（1H）**：中間圏で推移。")
        
    # 15m & 5m
    if m5['stoch'] < 20 and m15['sdir'] == 'Up':
        comments.append("・**15m/5m**：短期売られすぎからの反発局面。エントリータイミングを探るゾーン。")
    elif m5['stoch'] > 80:
        comments.append("・**15m/5m**：短期買われすぎ。一旦の押し（下げ）を待ちたい場面。")
    else:
        comments.append(f"・**15m/5m**：短期Stoch={m5['stoch']}、SDir={m5['sdir']}。")

    # 総評
    if d['state'] == 'TU' and h4['state'] == 'TU':
        if h1['stoch'] < 40 and m5['stoch'] < 30:
            summary = "🔥 **【絶好の押し目買いチャンス】** 上位足が強い上昇トレンドの中、下位足がしっかり調整完了。ロング狙いの優位性が非常に高い局面です。"
        elif m5['stoch'] > 70:
            summary = "⏳ **【押し目待ち】** 上位足は上昇トレンドですが、短期足が高値圏です。5m/15mのStochが低水準まで下がってきたところを狙うのが安全です。"
        else:
            summary = "🟢 **【上昇トレンド継続】** 基本戦略はロング。下位足の反発（SDir Up）を確認して押し目を拾う局面です。"
    elif d['state'] == 'TD' and h4['state'] == 'TD':
        if h1['stoch'] > 60 and m5['stoch'] > 70:
            summary = "🔥 **【絶好の戻り売りチャンス】** 上位足が下落トレンドの中、短期足が買われすぎまで上昇。ショート狙いの優位性が高い局面です。"
        else:
            summary = "🔴 **【下落トレンド継続】** 基本戦略は戻り売り。下位足の失速を確認して入る局面です。"
    else:
        summary = "🟡 **【様子見・レンジ戦略】** 上位足の方向感が一致していません。無理なトレンドフォローは避け、下位足の引きつけ徹底を推奨。"

    return "\n".join(comments), summary

def main():
    res = analyze()
    comments, summary = build_commentary(res)
    
    table_str = "```\n"
    table_str += f"{'TF':<5} | {'State':<5} | {'PO':<5} | {'EMA':<5} | {'Stoch':<5} | {'Slow':<5} | {'SDir':<4}\n"
    table_str += "-" * 50 + "\n"
    for tf, data in res.items():
        table_str += f"{tf:<5} | {data['state']:<5} | {data['po']:<5} | {data['ema']:<5} | {data['stoch']:<5.1f} | {data['slow']:<5.1f} | {data['sdir']:<4}\n"
    table_str += "```"

    msg = f"📱 **【BTC/USDT 4時間定期レポート】**\n\n"
    msg += f"{table_str}\n\n"
    msg += f"📝 **各足の短評**\n{comments}\n\n"
    msg += f"💡 **全体総評**\n{summary}"

    requests.post(WEBHOOK_URL, json={'content': msg})

if _
