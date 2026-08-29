import os
import requests
import datetime

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

# --- 暗号資産・ゴールド用 フォーマット ---
def build_asset_report(symbol_name, headline, target_scenario, tf_analysis, change_point, summary_text):
    msg = f"# 📰【{symbol_name}】{headline}\n\n"
    msg += f"### 🎯 ここから狙いたい目線・シナリオ\n{target_scenario}\n\n"
    msg += "### 🕒 各時間足の動き\n"
    for tf, desc in tf_analysis.items():
        msg += f"・**{tf}**: {desc}\n"
    msg += f"\n### ⚡ 直近の大きな環境変化\n{change_point}\n"
    msg += f"\n### 📝 総評（外部環境・特記事項）\n{summary_text}\n"
    return msg

# --- 為替（FX）用 フォーマット（総評に強弱・歪みを統合） ---
def build_fx_report(pair_name, headline, target_scenario, tf_analysis, change_point, strength_distortion, summary_text):
    msg = f"# 📰【{pair_name}】{headline}\n\n"
    msg += f"### 🎯 ここから狙いたい目線・シナリオ\n{target_scenario}\n\n"
    msg += "### 🕒 各時間足の動き\n"
    for tf, desc in tf_analysis.items():
        msg += f"・**{tf}**: {desc}\n"
    msg += f"\n### ⚡ 直近の大きな環境変化\n{change_point}\n"
    msg += f"\n### 📝 総評（外部環境・強弱歪み・特記事項）\n"
    msg += f"**【通貨間の強弱・歪み】**\n{strength_distortion}\n\n"
    msg += f"**【ファンダ・市場環境】**\n{summary_text}\n"
    return msg

def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    
    weekday = now_jst.weekday() # 0:月 ~ 6:日
    is_weekend = weekday in [5, 6]

    full_message = f"=============================\n🤖 **マルチアセット戦略レポート** ({time_str})\n=============================\n\n"

    # 1. BTC/USDT
    btc_headline = "4時間足の上昇トレンド継続、2時間足の調整完了を狙う"
    btc_target = "1時間足での下落フラッグ上抜けを確認後、押し目からのロングエントリーを推奨。直近高値突破を狙う目線。"
    btc_tf = {
        "日足": "上昇トレンド継続中（200EMAの上を推移）",
        "4時間足": "レンジ上限ブレイク後の押し目形成中",
        "1時間足": "短期下落フラッグの終盤、反転サイン待ち"
    }
    btc_change = "4時間足で直近高値を上抜けて上昇ダウが確定。下落シナリオから押し目買い優勢の相場環境へ転換。"
    btc_summary = "株価指数（S&P500・NASDAQ）の強気維持が追い風。米金利低下に伴い暗号資産全体への資金流入が継続しているため、ショートはリスク高。"
    
    full_message += build_asset_report("BTC/USDT", btc_headline, btc_target, btc_tf, btc_change, btc_summary) + "\n---\n\n"

    # 2. ゴールド・為替 (土日はスキップ)
    if not is_weekend:
        # GOLD
        gold_headline = "最高値付近での揉み合い、下抜け時のショート検討"
        gold_target = "レンジ下限ブレイクを確認してからの戻り売り（ショート）、または明確な押し目買いポイントまで引きつける目線。"
        gold_tf = {
            "日足": "強気トレンドだが買われすぎ水準",
            "4時間足": "高値圏でのダブルトップ形成懸念",
            "1時間足": "方向感のないレンジ推移"
        }
        gold_change = "高値更新の勢いが鈍化し、1時間足レベルでトリプルトップの形状を形成中。"
        gold_summary = "ドルインデックスの上昇と反発が拮抗中。米実質金利の動向に警戒が必要なため、明確なブレイクまでは打診買いを控えるのが吉。"
        
        full_message += build_asset_report("GOLD (XAU/USD)", gold_headline, gold_target, gold_tf, gold_change, gold_summary) + "\n---\n\n"

        # USD/JPY
        usdjpy_headline = "ドル弱・円強の歪み発生中、4時間足抵抗線からのショート狙い"
        usdjpy_target = "4時間足の20EMA付近までの戻りを待ってからの戻り売り。下値ターゲットは前回安値付近。"
        usdjpy_tf = {
            "日足": "下落トレンドへの転換局面",
            "4時間足": "移動平均線に頭を押さえられる戻り高値形成",
            "1時間足": "戻り売りのテクニカルパターン完成間近"
        }
        usdjpy_change = "日足サポートラインを下抜けし、完全に『戻り売り優勢』のトレンドへ移行。"
        usdjpy_strength = "・通貨強弱: JPY > EUR > USD\n・歪み: クロス円全体で円買い圧力が強く、ドル円の反発が他ペアに比べて抑制されている状態。"
        usdjpy_summary = "日銀の金利見通しと米CPI警戒感によるドル手仕舞いが交錯。欧州時間に向けて円強の動きが加速しやすい。"
        
        full_message += build_fx_report("USD/JPY", usdjpy_headline, usdjpy_target, usdjpy_tf, usdjpy_change, usdjpy_strength, usdjpy_summary)
    else:
        full_message += "☕ **【週末市場休止のお知らせ】**\n土日のため為替（FX）およびゴールド（コモディティ）市場はクローズしています。週明け月曜朝より分析を再開します。"

    send_discord(full_message)

if __name__ == "__main__":
    main()
