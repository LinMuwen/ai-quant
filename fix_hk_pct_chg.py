"""修复港股 pct_chg 和 change 字段，基于前复权价格重新计算"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd

hk = pd.read_csv(r".\smic_hk_share.csv")
hk["trade_date"] = pd.to_datetime(hk["trade_date"], format="%Y%m%d")
hk = hk.sort_values("trade_date").reset_index(drop=True)

# 记录修复前的异常统计
old_up_pct = (hk["pct_chg"] > 0).sum()
old_up_chg = (hk["change"] > 0).sum()

print("=== 修复前 ===")
print(f"pct_chg 范围: [{hk['pct_chg'].min():.4f}, {hk['pct_chg'].max():.4f}]")
print(f"pct_chg 正值: {old_up_pct}/{len(hk)} ({old_up_pct/len(hk)*100:.1f}%)")
print(f"change 范围: [{hk['change'].min():.4f}, {hk['change'].max():.4f}]")
print(f"change 正值: {old_up_chg}/{len(hk)} ({old_up_chg/len(hk)*100:.1f}%)")

# 用 pre_close 重新计算 daily change 和 pct_chg
hk["change"] = round(hk["close"] - hk["pre_close"], 4)
hk["pct_chg"] = round((hk["close"] - hk["pre_close"]) / hk["pre_close"] * 100, 4)

# 验证
print("\n=== 修复后 ===")
print(f"pct_chg 范围: [{hk['pct_chg'].min():.4f}, {hk['pct_chg'].max():.4f}]")
print(f"pct_chg 正值: {(hk['pct_chg']>0).sum()}/{len(hk)} ({(hk['pct_chg']>0).sum()/len(hk)*100:.1f}%)")
print(f"change 范围: [{hk['change'].min():.4f}, {hk['change'].max():.4f}]")
print(f"change 正值: {(hk['change']>0).sum()}/{len(hk)} ({(hk['change']>0).sum()/len(hk)*100:.1f}%)")

# 验证与公式一致
diff = (hk["pct_chg"] - (hk["change"] / hk["pre_close"] * 100)).abs()
print(f"pct_chg 与公式偏差 max: {diff.max():.6f}%")

# 检查第一行 (无 pre_close 的行)
first = hk.iloc[0]
print(f"\n第一行: {first['trade_date'].date()}  close={first['close']}  pre_close={first['pre_close']}  change={first['change']}  pct_chg={first['pct_chg']}")

# 回写 trade_date 为 YYYYMMDD 字符串
hk["trade_date"] = hk["trade_date"].dt.strftime("%Y%m%d")
hk.to_csv(r".\smic_hk_share.csv", index=False, encoding="utf-8-sig")
print(f"\n已写回 smic_hk_share.csv, {len(hk)} 行")
