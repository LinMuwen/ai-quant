# -*- coding: utf-8 -*-
"""
获取中芯国际 A股(688981.SH) + 港股(00981.HK) 近一年日线行情数据
A股数据来源: Tushare Pro API
港股数据来源: 腾讯股票行情API (Tushare hk_daily 频率限制为1次/小时)
"""
import tushare as ts
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta

TUSHARE_TOKEN = "44eba786220504ae80b8b31aa83bf4e2d4e33606d0161bcc02bb9992"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

# 港币兑人民币汇率 (近似值)
HKD_CNY_RATE = 0.92


def fetch_a_share():
    """通过 Tushare 获取 A股 日线数据"""
    print("正在获取 688981.SH (A股) 日线数据 [Tushare]...")
    pro = ts.pro_api(TUSHARE_TOKEN)
    df = pro.daily(
        ts_code="688981.SH",
        start_date=START_DATE,
        end_date=END_DATE,
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
    )
    if df is None or df.empty:
        print("  ERROR: A股数据获取失败")
        return None
    df = df.sort_values("trade_date").reset_index(drop=True)
    csv_path = os.path.join(OUTPUT_DIR, "smic_a_share.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV: {csv_path} ({len(df)} 条)")
    print(f"  最新收盘: {df['close'].iloc[-1]} CNY")
    return df


def fetch_hk_share():
    """通过腾讯股票API获取港股日线数据"""
    print("\n正在获取 00981.HK (港股) 日线数据 [腾讯行情]...")

    start_fmt = f"{START_DATE[:4]}-{START_DATE[4:6]}-{START_DATE[6:]}"
    end_fmt = f"{END_DATE[:4]}-{END_DATE[4:6]}-{END_DATE[6:]}"

    url = f"https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?param=hk00981,day,{start_fmt},{end_fmt},640,qfq"

    session = requests.Session()
    session.trust_env = False
    session.proxies = {"http": None, "https": None}

    resp = session.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://web.ifzq.gtimg.cn/",
    })
    data = resp.json()

    stock_data = data.get("data", {}).get("hk00981", {})
    klines = stock_data.get("qfqday") or stock_data.get("day") or []

    if not klines:
        print("  ERROR: 港股数据获取失败")
        return None

    # 解析: [date, open, close, high, low, volume, {}, turnover, amount]
    records = []
    for k in klines:
        date_str = k[0].replace("-", "")  # YYYYMMDD
        close = float(k[2])
        open_ = float(k[1])
        records.append({
            "ts_code": "0981.HK",
            "trade_date": date_str,
            "open": open_,
            "close": close,
            "high": float(k[3]),
            "low": float(k[4]),
            "vol": float(k[5]) / 100,      # 股 -> 手
            "amount": float(k[8]) * 10000 if len(k) > 8 and k[8] else 0,  # 万 -> 元
            "pct_chg": float(k[7]) if len(k) > 7 and k[7] else 0,
            "change": close - open_,
        })

    df = pd.DataFrame(records)
    df["pre_close"] = df["close"].shift(1)
    df.loc[0, "pre_close"] = df.loc[0, "close"] - df.loc[0, "change"]

    csv_path = os.path.join(OUTPUT_DIR, "smic_hk_share.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV: {csv_path} ({len(df)} 条)")
    print(f"  最新收盘: {df['close'].iloc[-1]} HKD")
    return df


def build_combined(df_a, df_hk):
    """构建对比数据集"""
    dates_a = set(df_a["trade_date"].tolist())
    dates_hk = set(df_hk["trade_date"].tolist())
    common_dates = sorted(dates_a & dates_hk)
    print(f"\n共同交易日: {len(common_dates)} 天")

    a_map = df_a.set_index("trade_date").to_dict("index")
    hk_map = df_hk.set_index("trade_date").to_dict("index")

    dates, a_ohlc, a_vol, a_vol_colors = [], [], [], []
    hk_ohlc, hk_vol, hk_vol_colors = [], [], []
    a_close, hk_close, ah_premium = [], [], []

    for d in common_dates:
        formatted = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        dates.append(formatted)

        a = a_map[d]
        a_close.append(float(a["close"]))
        a_ohlc.append([float(a["open"]), float(a["close"]), float(a["low"]), float(a["high"])])
        a_vol.append(float(a["vol"]))
        a_vol_colors.append("#ef4444" if float(a["close"]) >= float(a["pre_close"]) else "#22c55e")

        hk = hk_map[d]
        hk_close.append(float(hk["close"]))
        hk_ohlc.append([float(hk["open"]), float(hk["close"]), float(hk["low"]), float(hk["high"])])
        hk_vol.append(float(hk["vol"]))
        hk_vol_colors.append("#ef4444" if float(hk["close"]) >= float(hk["pre_close"]) else "#22c55e")

        # AH溢价率 = (A股价格 - H股价格*汇率) / (H股价格*汇率) * 100
        hk_cny = float(hk["close"]) * HKD_CNY_RATE
        premium = ((float(a["close"]) - hk_cny) / hk_cny) * 100
        ah_premium.append(round(premium, 2))

    # 归一化 (首日=100)
    a_norm = [round(p / a_close[0] * 100, 2) for p in a_close]
    hk_norm = [round(p / hk_close[0] * 100, 2) for p in hk_close]

    combined = {
        "dates": dates,
        "a_close": a_close, "a_ohlc": a_ohlc, "a_vol": a_vol, "a_vol_colors": a_vol_colors,
        "hk_close": hk_close, "hk_ohlc": hk_ohlc, "hk_vol": hk_vol, "hk_vol_colors": hk_vol_colors,
        "a_norm": a_norm, "hk_norm": hk_norm, "ah_premium": ah_premium,
        "hkd_cny_rate": HKD_CNY_RATE,
    }

    json_path = os.path.join(OUTPUT_DIR, "smic_combined.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False)
    print(f"对比JSON: {json_path}")

    # 摘要
    print(f"\n{'='*50}")
    print(f"中芯国际 AH 股对比摘要")
    print(f"{'='*50}")
    print(f"A股 688981.SH: 最新 {a_close[-1]:.2f} CNY | 区间涨幅 {(a_close[-1]/a_close[0]-1)*100:+.2f}%")
    print(f"港股 00981.HK: 最新 {hk_close[-1]:.2f} HKD (约 {hk_close[-1]*HKD_CNY_RATE:.2f} CNY) | 区间涨幅 {(hk_close[-1]/hk_close[0]-1)*100:+.2f}%")
    print(f"AH溢价率: 最新 {ah_premium[-1]:.2f}% | 区间 {min(ah_premium):.2f}% ~ {max(ah_premium):.2f}%")
    return combined


def main():
    df_a = fetch_a_share()
    df_hk = fetch_hk_share()
    if df_a is None or df_hk is None:
        print("数据获取不完整，终止")
        return
    build_combined(df_a, df_hk)


if __name__ == "__main__":
    main()
