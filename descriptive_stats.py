"""中芯国际 A股 + 港股 修正后描述性统计"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np

a = pd.read_csv(r".\smic_a_share.csv")
hk = pd.read_csv(r".\smic_hk_share.csv")

for df, name, code in [(a, "A股", "688981.SH"), (hk, "港股", "00981.HK")]:
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    d = df.sort_values("trade_date")

    print("=" * 64)
    print(f"  {name} ({code})")
    print("=" * 64)

    # 区间
    print(f"\n区间: {d['trade_date'].min().date()} ~ {d['trade_date'].max().date()}  |  {len(d)} 个交易日")

    # 价格统计
    for col in ["open", "high", "low", "close"]:
        s = d[col]
        print(f"\n  [{col}]  mean={s.mean():.2f}  std={s.std():.2f}  min={s.min():.2f}  "
              f"Q1={s.quantile(.25):.2f}  median={s.median():.2f}  Q3={s.quantile(.75):.2f}  max={s.max():.2f}")

    # 收益率
    ret = d["pct_chg"].dropna()
    print(f"\n  [pct_chg 日收益率]")
    print(f"    mean={ret.mean():.2f}%  std={ret.std():.2f}%  skew={ret.skew():.2f}  kurt={ret.kurtosis():.2f}")
    print(f"    min={ret.min():.2f}%  max={ret.max():.2f}%")
    print(f"    上涨={sum(ret>0):d}  下跌={sum(ret<0):d}  涨跌比={sum(ret>0)/max(len(ret),1)*100:.1f}%")

    # 成交量 & 成交额 (统一到万手 / 亿元)
    vol = d["vol"] / 1e4
    if code == "688981.SH":
        amt = d["amount"] * 1000 / 1e8  # Tushare 千元 → 亿
    else:
        amt = d["amount"] / 1e8          # 港股已是元 → 亿
    print(f"\n  [成交量 (万手)]  mean={vol.mean():.1f}  median={vol.median():.1f}  max={vol.max():.1f}")
    print(f"  [成交额 (亿元)]  mean={amt.mean():.1f}  median={amt.median():.1f}  max={amt.max():.1f}")

    # 振幅
    amp = (d["high"] - d["low"]) / d["pre_close"] * 100
    print(f"  [振幅 (%)]       mean={amp.mean():.2f}%  median={amp.median():.2f}%  max={amp.max():.2f}%")

print()
