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
def build_asset_report(symbol_name, is_changed, unchanged_since, headline, tf_analysis, buyer_plan, seller_plan, summary_text):
    msg = f"# 📰【{symbol_name}】"
    if is_changed:
        msg += f"{headline}\n\n"
    else:
        msg += f"【{unchanged_since}から変更なし】{headline}\n\n"
    
    # 🕒 各時間足短評 (長・中・短)
    msg += "### 🕒 時間足分析（長・中・短）\n"
    msg += f"・**長期（日足）**: {tf_analysis['日足']}\n"
    msg += f"・**中期（4H足）**: {tf_analysis['4時間足']}\n"
    msg += f"・**短期（1H足）**: {tf_analysis['1時間足']}\n\n"

    # ⚔️ 買い手・売り手の狙い
    msg += "### ⚔️ ターゲットシナリオ\n"
    msg += f"・**🟢 買い手の狙い**: {buyer_plan}\n"
    msg += f"・**🔴 売り手の狙い**: {seller_plan}\n\n"

    # 📝 総評（相関・長期ストキャス分析）
    msg += f"### 📝 総評（相関環境・長期ストキャス比較）\n{summary_text}\n"
    return msg

# --- 為替（FX）用 フォーマット ---
def build_fx_report(pair_name, is_changed, unchanged_since, headline, tf_analysis, buyer_plan, seller_plan, summary_text):
    msg = f"# 📰【{pair_name}】"
    if is_changed:
        msg += f"{headline}\n\n"
    else:
        msg += f"【{unchanged_since}から変更なし】{headline}\n\n"
    
    # 🕒 各時間足短評
    msg += "### 🕒 時間足分析（長・中・短）\n"
    msg += f"・**長期（日足）**: {tf_analysis['日足']}\n"
    msg += f"・**中期（4H足）**: {tf_analysis['4時間足']}\n"
    msg += f"・**短期（1H足）**: {tf_analysis['1時間足']}\n\n"

    # ⚔️ 買い手・売り手の狙い
    msg += "### ⚔️ ターゲットシナリオ\n"
    msg += f"・**🟢 買い手の狙い**: {buyer_plan}\n"
    msg += f"・**🔴 売り手の狙い**: {seller_plan}\n\n"

    # 📝 総評（歪み・相関・長期ストキャス）
    msg += f"### 📝 総評（歪み・相関環境・長期ストキャス）\n{summary_text}\n"
    return msg

def main():
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    
    weekday = now_jst.weekday() # 0:月 ~ 6:日
    is_weekend = weekday in [5, 6]

    full_message = f"=============================\n🤖 **マルチアセット戦略レポート** ({time_str})\n=============================\n\n"

    # --------------------------------------------------
    # 1. BTC/USDT (例: 変更ありパターン)
    # --------------------------------------------------
    btc_is_changed = True
    btc_unchanged_since = "8/25"
    btc_headline = "4時間足の上昇ダウ再開、1時間足フラッグ上抜けでロング加速"
    
    btc_tf = {
        "日足": "強気トレンド維持（200EMA上を推移、押し目買い領域）",
        "4時間足": "レンジ上限をブレイクし上昇再開の兆候",
        "1時間足": "短期下落フラッグを上方ブレイク完了"
    }
    
    btc_buyer = "1時間足の押し目（94,500付近）を引きつけてロング。目標は直近高値突破。"
    btc_seller = "4時間足レジスタンスでの上ヒゲ確認後、短期の逆張りショート（深追いは厳禁）。"
    
    btc_summary = (
        "【長期ストキャス分析】\n"
        "・BTC(1D/4H): 高値圏（買われすぎエリア85〜90付近）を推移中。上昇勢いは強いが過熱感あり。\n"
        "・GOLD(4H): 底値圏（15〜20付近）まで低下しており反発警戒域。\n"
        "・株価指数(NAS100): 4Hストキャス中立。市場全体としてはリスクオン環境が継続。\n"
        "→ BTCは高値圏だがモメンタムが強く、短期の調整消化からの押し目買いが優勢。"
    )
    
    full_message += build_asset_report(
        "BTC/USDT", btc_is_changed, btc_unchanged_since, btc_headline, 
        btc_tf, btc_buyer, btc_seller, btc_summary
    ) + "\n---\n\n"

    # --------------------------------------------------
    # 2. ゴールド・為替 (土日はスキップ)
    # --------------------------------------------------
    if not is_weekend:
        # GOLD (例: 変更なしパターン)
        gold_is_changed = False
        gold_unchanged_since = "8/25"
        gold_headline = "長期上昇トレンドの押し目探し。上昇の勢いが治まりつつある"
        
        gold_tf = {
            "日足": "高値圏での保ち合い（買われすぎ警戒感継続）",
            "4時間足": "ダブルトップ形成後の調整局面",
            "1時間足": "方向感のないレンジ推移（底値模索）"
        }
        
        gold_buyer = "4Hストキャス底値圏からの反発サイン（Wボトムなど）を確認してロング。"
        gold_seller = "レンジ下限ライン下抜け確定で短期戻り売り。"
        
        gold_summary = (
            "【長期ストキャス分析】\n"
            "・GOLD(4H/1H): ストキャスが底値付近（買われすぎから一転して売られすぎ水準）に到達。\n"
            "・DXY(米ドル指数): 4Hストキャスが高値圏へ浮上しており、ゴールドの押し圧力を形成。\n"
            "→ ドル高が一巡すれば、ストキャス底値圏に位置するゴールドの買戻し（反発）が入る可能性が高い。"
        )
        
        full_message += build_asset_report(
            "GOLD (XAU/USD)", gold_is_changed, gold_unchanged_since, gold_headline, 
            gold_tf, gold_buyer, gold_seller, gold_summary
        ) + "\n---\n\n"

        # USD/JPY
        usdjpy_is_changed = True
        usdjpy_unchanged_since = "8/26"
        usdjpy_headline = "ドル弱・円強の歪み継続、4時間足EMAラインからの戻り売り優勢"
        
        usdjpy_tf = {
            "日足": "下落トレンドへの転換局面",
            "4時間足": "20EMAに頭を押さえられる綺麗に戻り高値を形成中",
            "1時間足": "戻り売りのテクニカルパターン完成間近"
        }
        
        usdjpy_buyer = "153.50の強いサポートでの短期反発狙い（ロングは素早い撤退が前提）。"
        usdjpy_seller = "4H 20EMA（154.50）付近までの戻りを待って本命の戻り売り。"
        
        usdjpy_summary = (
            "【強弱歪み & 長期ストキャス分析】\n"
            "・通貨強弱: JPY > EUR > USD (円買い圧力が優勢)\n"
            "・USD/JPY(4H): ストキャスは50付近の中立領域から下向き。急反発の兆候は薄い。\n"
            "・EUR/USD(1D): ストキャスが高値圏へ向かっており、対ドルでのドル安傾向を裏付け。\n"
            "→ 円の独自高とドルの上値の重さが合致しており、戻り売り目線を継続。"
        )
        
        full_message += build_fx_report(
            "USD/JPY", usdjpy_is_changed, usdjpy_unchanged_since, usdjpy_headline, 
            usdjpy_tf, usdjpy_buyer, usdjpy_seller, usdjpy_summary
        )
    else:
        full_message += "☕ **【週末市場休止のお知らせ】**\n土日のため為替（FX）およびゴールド（コモディティ）市場はクローズしています。週明け月曜朝より分析を再開します。"

    send_discord(full_message)

if __name__ == "__main__":
    main()
