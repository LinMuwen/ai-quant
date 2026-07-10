#!/usr/bin/env python3
"""海龟策略量化指标计算"""
import json
import numpy as np
import pandas as pd

df = pd.DataFrame(json.load(open('smic_daily_data.json')))
df['trade_date'] = pd.to_datetime(df['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)

trades = [
    ('S1','2025-08-18','2025-10-17',93.50,121.98,2848),
    ('S2','2025-09-30','2025-10-17',138.50,121.98,-1652),
    ('S1','2025-12-23','2026-01-15',120.50,124.44,394),
    ('S1','2026-04-23','2026-05-19',108.88,118.82,994),
    ('S2','2026-04-30','2026-05-19',113.31,118.82,551),
    ('S1','2026-05-21','2026-06-08',134.00,121.92,-1208),
    ('S2','2026-05-21','2026-06-08',134.00,121.92,-1208),
    ('S1','2026-06-30','2026-07-03',152.05,140.31,-1174),
    ('S2','2026-06-30','2026-07-03',152.05,140.31,-1174),
]

account = 1_000_000

# 日频资金曲线
equity = pd.DataFrame({'date': df['trade_date'], 'value': float(account)})
equity = equity.set_index('date')

for sys, ed, xd, ep, xp, pnl in trades:
    edt = pd.Timestamp(ed); xdt = pd.Timestamp(xd)
    mask = (equity.index >= edt) & (equity.index <= xdt)
    daily_pnl = (df.loc[df['trade_date'].isin(equity.index[mask]), 'close'].values - ep) * 100
    equity.loc[mask, 'value'] = equity.loc[mask, 'value'] + daily_pnl

equity['daily_return'] = equity['value'].pct_change()
equity['log_return'] = np.log(equity['value'] / equity['value'].shift(1))

# 指标
N_days = len(equity) - 1
N_years = N_days / 252
total_return = (equity['value'].iloc[-1] - account) / account
annual_return = (1 + total_return) ** (1 / N_years) - 1 if N_years > 0 else 0

rf_daily = 0.02 / 252
excess = equity['daily_return'].dropna() - rf_daily
sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0

cummax = equity['value'].cummax()
drawdown = (equity['value'] - cummax) / cummax
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()

calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

neg_returns = equity['daily_return'].dropna()
neg_returns = neg_returns[neg_returns < 0]
sortino = (excess.mean() / neg_returns.std()) * np.sqrt(252) if len(neg_returns) > 0 and neg_returns.std() > 0 else 0

volatility = equity['daily_return'].dropna().std() * np.sqrt(252)

total_trades = len(trades)
winning = [t for t in trades if t[5] > 0]
losing  = [t for t in trades if t[5] <= 0]
win_rate = len(winning) / total_trades * 100

total_pnl = sum(t[5] for t in trades)
avg_win = np.mean([t[5] for t in winning]) if winning else 0
avg_loss = abs(np.mean([t[5] for t in losing])) if losing else 0
profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
max_win = max(t[5] for t in winning) if winning else 0
max_loss = min(t[5] for t in losing) if losing else 0
hold_days = [(pd.Timestamp(xd) - pd.Timestamp(ed)).days for _, ed, xd, _, _, _ in trades]
avg_hold = np.mean(hold_days)

streak = 0; max_streak = 0
for t in trades:
    if t[5] <= 0: streak += 1; max_streak = max(max_streak, streak)
    else: streak = 0

print("=" * 70)
print("  海龟交易策略 — 量化指标报告")
print("=" * 70)
print(f"\n  回测区间: 2025-07-03 ~ 2026-07-03 ({N_days} 交易日)")
print(f"  初始资金: {account:,.0f} 元")
print(f"  最终资金: {equity['value'].iloc[-1]:,.0f} 元")
print(f"\n  --- 收益指标 ---")
print(f"  总收益率:     {total_return*100:+.2f}%")
print(f"  年化收益率:   {annual_return*100:+.2f}%")
print(f"  总盈亏:       {total_pnl:+,.0f} 元")
print(f"\n  --- 风险指标 ---")
print(f"  年化波动率:   {volatility*100:.2f}%")
print(f"  最大回撤:     {max_dd*100:.2f}%  (日期: {max_dd_date.strftime('%Y-%m-%d')})")
print(f"  夏普比率:     {sharpe:.3f}")
print(f"  索提诺比率:   {sortino:.3f}")
print(f"  卡玛比率:     {calmar:.3f}")
print(f"\n  --- 交易指标 ---")
print(f"  总交易次数:   {total_trades}")
print(f"  盈利次数:     {len(winning)} (胜率 {win_rate:.0f}%)")
print(f"  亏损次数:     {len(losing)}")
print(f"  平均盈利:     {avg_win:,.0f} 元")
print(f"  平均亏损:     {avg_loss:,.0f} 元")
print(f"  盈亏比:       {profit_factor:.2f}:1")
print(f"  最大单笔盈利: {max_win:,} 元")
print(f"  最大单笔亏损: {max_loss:,} 元")
print(f"  平均持仓:     {avg_hold:.0f} 天")
print(f"  最大连续亏损: {max_streak} 次")
print(f"\n  --- 分系统 ---")
for sys in ['S1','S2']:
    st = [t for t in trades if t[0]==sys]
    sp = sum(t[5] for t in st)
    sw = [t for t in st if t[5]>0]
    wr = len(sw)/len(st)*100 if st else 0
    print(f"  {sys}: {len(st)}笔 | 盈亏 {sp:+,.0f} | 胜率 {wr:.0f}%")
print(f"\n  资金曲线峰值: {equity['value'].max():,.0f} 元")
print(f"  资金曲线谷值: {equity['value'].min():,.0f} 元")
print("=" * 70)
