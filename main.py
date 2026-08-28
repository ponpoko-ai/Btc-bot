import os
import requests
import datetime

# --- Discord送信関数 ---
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

# --- 暗号資産・ゴールド用 フォーマット生成 ---
def build_asset_report(symbol_name, headline, tf_analysis, summary_text):
    msg = f"## 📰 【{symbol_name}】{headline}\n\n"
    msg += "### ⏱ 各時間足の動き\n"
    for tf, desc in tf_analysis.items():
        msg += f"- **{tf}**: {desc}\n"
    msg += f"\n### 📝 総評\n{summary_text}\n"
    return msg

# --- 為替（FX）用 フォーマット生成 ---
def build_fx_report(pair_name, headline, tf_analysis, strength_distortion, summary_text):
    msg = f"## 📰 【{pair_name}】{headline}\n\n"
    msg += "### ⏱ 各時間足の動き\n"
    for tf, desc in tf_analysis.items():
        msg += f"- **{tf}**: {desc}\n"
    msg += f"\n### ⚖️ 通貨ペア間の強弱・歪み\n{strength_distortion}\n"
    msg += f"\n### 📝 総評\n{summary_text}\n"
    return msg

def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    
    # 1. ヘッダー
    full_message = f"=============================\n🤖 **マルチアセット戦略レポート** ({time_str})\n=============================\n\n"

    # --- サンプル分析ロジック/出力例 (実際のテクニカル計算結果を当てはめます) ---
    
    # BTC分析結果の例
    btc_headline = "【押し目買い推奨】4時間足の上昇トレンド継続、2時間足の調整完了を狙う"
    btc_tf = {
        "日足": "上昇トレンド継続中（200EMAの上を推移）",
        "4時間足": "レンジ上限ブレイク後の押し目形成中",
        "1時間足": "短期下落フラッグの終盤、反転サイン待ち"
    }
    btc_summary = "株価指数（S&P500・NASDAQ）の強気維持が追い風。特記事項として、米金利低下に伴い暗号資産全体への資金流入が継続しているため、ショートはリスク高。"
    full_message += build_asset_report("BTC/USDT", btc_headline, btc_tf, btc_summary) + "\n---\n\n"

    # ゴールド（XAU）分析結果の例
    gold_headline = "【様子見〜高値警戒】最高値付近での揉み合い、下抜け時のショート検討"
    gold_tf = {
        "日足": "強気トレンドだが買われすぎ水準",
        "4時間足": "高値圏でのダブルトップ形成懸念",
        "1時間足": "方向感のないレンジ推移"
    }
    gold_summary = "ドルインデックスの上昇と反発が拮抗中。米実質金利の動向に警戒が必要なため、明確なブレイクまでは打診買いを控えるのが吉。"
    full_message += build_asset_report("ゴールド (XAU/USD)", gold_headline, gold_tf, gold_summary) + "\n---\n\n"

    # 為替（USD/JPY）分析結果の例
    usdjpy_headline = "【戻り売り優勢】ドル弱・円強の歪み発生中、4時間足抵抗線からのショート狙い"
    usdjpy_tf = {
        "日足": "下落トレンドへの転換局面",
        "4時間足": "移動平均線に頭を押さえられる戻り高値形成",
        "1時間足": "戻り売りのテクニカルパターン完成間近"
    }
    usdjpy_strength = "・通貨強弱: JPY > EUR > USD\n・歪み: クロス円全体で円買い圧力が強く、ドル円の反発が他ペアに比べて抑制されている状態。"
    usdjpy_summary = "日銀の金利見通しと米CPI警戒感によるドル手仕舞いが交錯。欧州時間に向けて円強の動きが加速しやすい。"
    full_message += build_fx_report("USD/JPY", usdjpy_headline, usdjpy_tf, usdjpy_strength, usdjpy_summary)

    # Discordに送信
    send_discord(full_message)

if __name__ == "__main__":
    main()
