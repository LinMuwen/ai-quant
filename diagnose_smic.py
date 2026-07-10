"""
中芯国际 A股 + 港股 数据诊断分析
检查缺失值、计算描述性统计量、OHLC一致性、日期连续性
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np

# ============================================================
# 1. 加载数据
# ============================================================
a_raw = pd.read_csv(r".\smic_a_share.csv")
hk_raw = pd.read_csv(r".\smic_hk_share.csv")

def diagnose(df, label, market):
    print("=" * 72)
    print(f"  {label} ({market})")
    print("=" * 72)

    # --- 基础信息 ---
    print(f"\n[基础信息]")
    print(f"  行数: {len(df)}  列数: {len(df.columns)}")
    print(f"  列名: {list(df.columns)}")

    # trade_date 转 datetime
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    print(f"  日期范围: {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")
    print(f"  交易日天数: {df['trade_date'].nunique()} (去重后)")

    # --- 缺失值检查 ---
    print(f"\n[缺失值检查]")
    missing = df.isnull().sum()
    missing_pct = (df.isnull().sum() / len(df) * 100).round(2)
    miss_df = pd.DataFrame({"缺失数": missing, "缺失率(%)": missing_pct})
    miss_df = miss_df[miss_df["缺失数"] > 0]
    if miss_df.empty:
        print("  所有列无缺失值 ✓")
    else:
        print(miss_df.to_string())

    # --- 重复日期检查 ---
    dups = df["trade_date"].duplicated()
    dup_count = dups.sum()
    if dup_count > 0:
        print(f"\n[重复日期] ⚠ {dup_count} 个重复交易日:")
        print(df[df["trade_date"].duplicated(keep=False)].sort_values("trade_date")[["trade_date"]].to_string())
    else:
        print(f"\n[重复日期] 无重复交易日 ✓")

    # --- 数据类型 ---
    print(f"\n[数据类型]")
    print(df.dtypes.to_string())

    # --- OHLC 一致性检查 ---
    print(f"\n[OHLC 一致性检查]")
    ohlc_cols = ["open", "high", "low", "close"]
    cols_exist = [c for c in ohlc_cols if c in df.columns]
    if len(cols_exist) == 4:
        # high >= low
        bad_hl = (df["high"] < df["low"]).sum()
        # high >= open
        bad_ho = (df["high"] < df["open"]).sum()
        # high >= close
        bad_hc = (df["high"] < df["close"]).sum()
        # low <= open
        bad_lo = (df["low"] > df["open"]).sum()
        # low <= close
        bad_lc = (df["low"] > df["close"]).sum()
        # 零值/负值检查
        zero_price = ((df[cols_exist] <= 0).any(axis=1)).sum()

        print(f"  high < low  : {bad_hl:>4} 行 {'⚠' if bad_hl else '✓'}")
        print(f"  high < open : {bad_ho:>4} 行 {'⚠' if bad_ho else '✓'}")
        print(f"  high < close: {bad_hc:>4} 行 {'⚠' if bad_hc else '✓'}")
        print(f"  low > open  : {bad_lo:>4} 行 {'⚠' if bad_lo else '✓'}")
        print(f"  low > close : {bad_lc:>4} 行 {'⚠' if bad_lc else '✓'}")
        print(f"  零值/负价格 : {zero_price:>4} 行 {'⚠' if zero_price else '✓'}")
    else:
        print(f"  缺失 OHLC 列，跳过")

    # --- 成交量检查 ---
    if "vol" in df.columns:
        neg_vol = (df["vol"] < 0).sum()
        zero_vol = (df["vol"] == 0).sum()
        print(f"\n[成交量检查]")
        print(f"  负成交量: {neg_vol} 行 {'⚠' if neg_vol else '✓'}")
        print(f"  零成交量: {zero_vol} 行")

    # --- 涨跌幅验证 ---
    if "pct_chg" in df.columns and "close" in df.columns and "pre_close" in df.columns:
        calc_pct = ((df["close"] - df["pre_close"]) / df["pre_close"] * 100).round(4)
        diff = (df["pct_chg"] - calc_pct).abs()
        bad_pct = (diff > 0.02).sum()  # 容忍 0.02% 误差
        print(f"\n[涨跌幅一致性]")
        print(f"  pct_chg 与 (close-pre_close)/pre_close*100 偏差>0.02% 的行: {bad_pct}")
        if bad_pct > 0 and bad_pct <= 10:
            bad_rows = df[diff > 0.02]
            for _, r in bad_rows.iterrows():
                print(f"    {r['trade_date'].date()}  pct_chg={r['pct_chg']:.4f}  计算值={calc_pct.loc[r.name]:.4f}")

    # --- 描述性统计 ---
    print(f"\n[描述性统计]")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # 排除 ts_code 这样的标识列
    stat_cols = [c for c in numeric_cols if c not in ["ts_code"] and df[c].notna().any()]
    if stat_cols:
        desc = df[stat_cols].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).round(4)
        print(desc.to_string())
    else:
        print("  无数值列可统计")

    # --- 收益率分布 ---
    if "pct_chg" in df.columns:
        print(f"\n[日收益率分布]")
        ret = df["pct_chg"].dropna()
        print(f"  均值: {ret.mean():.4f}%")
        print(f"  标准差: {ret.std():.4f}%")
        print(f"  偏度: {ret.skew():.4f}")
        print(f"  峰度: {ret.kurtosis():.4f}")
        print(f"  最小值: {ret.min():.4f}%  ({df.loc[ret.idxmin(), 'trade_date'].date()})")
        print(f"  最大值: {ret.max():.4f}%  ({df.loc[ret.idxmax(), 'trade_date'].date()})")
        # 涨跌天数
        up_days = (ret > 0).sum()
        dn_days = (ret < 0).sum()
        flat = (ret == 0).sum()
        print(f"  上涨: {up_days}天  下跌: {dn_days}天  平盘: {flat}天")
        print(f"  上涨比例: {up_days/len(ret)*100:.1f}%")

    # --- 日期缺口检查 (非连续交易日) ---
    print(f"\n[日期连续性]")
    df_sorted = df.sort_values("trade_date").reset_index(drop=True)
    gaps = df_sorted["trade_date"].diff().dropna()
    large_gaps = gaps[gaps > pd.Timedelta(days=7)]
    if len(large_gaps) > 0:
        print(f"  间隔 > 7天 的缺口: {len(large_gaps)} 处")
        for i in large_gaps.index[:10]:
            prev_date = df_sorted.loc[i-1, "trade_date"].date()
            curr_date = df_sorted.loc[i, "trade_date"].date()
            days = large_gaps.loc[i].days
            print(f"    {prev_date} → {curr_date}  间隔 {days} 天")
    else:
        print(f"  无超过7天的异常缺口 (正常节假日休市) ✓")

    print()
    return df

# ============================================================
# 2. 执行诊断
# ============================================================
a_df = diagnose(a_raw, "中芯国际 A股", "688981.SH 科创板")
hk_df = diagnose(hk_raw, "中芯国际 港股", "00981.HK 中国香港")

# ============================================================
# 3. A+H 对比摘要
# ============================================================
print("=" * 72)
print("  A+H 交叉对比")
print("=" * 72)

# 取 date-only 用于交集
a_dates = set(a_df["trade_date"].dt.date)
hk_dates = set(hk_df["trade_date"].dt.date)
common = a_dates & hk_dates
only_a = a_dates - hk_dates
only_hk = hk_dates - a_dates

print(f"\n[日期间对比]")
print(f"  A股有: {len(a_dates)}天  港股有: {len(hk_dates)}天")
print(f"  共同交易日: {len(common)}天")
print(f"  仅A股: {len(only_a)}天")
if only_a:
    print(f"    日期: {sorted(only_a)[:5]}...")
print(f"  仅港股: {len(only_hk)}天")
if only_hk:
    print(f"    日期: {sorted(only_hk)[:5]}...")

# 取共同交易日做相关系数
if len(common) >= 5:
    a_close = a_df.set_index(a_df["trade_date"].dt.date)["close"]
    hk_close = hk_df.set_index(hk_df["trade_date"].dt.date)["close"]
    common_sorted = sorted(common)
    a_series = a_close.reindex(common_sorted)
    hk_series = hk_close.reindex(common_sorted)
    corr = a_series.corr(hk_series)
    print(f"\n[收盘价相关性 (Pearson)]: {corr:.4f}")

    # 日收益率相关性
    a_ret = a_series.pct_change().dropna()
    hk_ret = hk_series.pct_change().dropna()
    common_ret_idx = a_ret.index & hk_ret.index
    if len(common_ret_idx) >= 5:
        ret_corr = a_ret.loc[common_ret_idx].corr(hk_ret.loc[common_ret_idx])
        print(f"[日收益率相关性 (Pearson)]: {ret_corr:.4f}")

print("\n诊断完成。")
