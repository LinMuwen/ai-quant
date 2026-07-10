#!/usr/bin/env python3
"""资金曲线 + 回撤图"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RED, GREEN, GOLD, BG, GRID, TEXT, MUTED = '#ef4444','#22c55e','#f59e0b','#0f172a','#1e293b','#cbd5e1','#64748b'

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
equity = pd.DataFrame({'date': df['trade_date'], 'value': float(account)})
equity = equity.set_index('date')

for sys, ed, xd, ep, xp, pnl in trades:
    edt = pd.Timestamp(ed); xdt = pd.Timestamp(xd)
    mask = (equity.index >= edt) & (equity.index <= xdt)
    daily_pnl = (df.loc[df['trade_date'].isin(equity.index[mask]), 'close'].values - ep) * 100
    equity.loc[mask, 'value'] = equity.loc[mask, 'value'] + daily_pnl

cummax = equity['value'].cummax()
drawdown = (equity['value'] - cummax) / cummax * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 8), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
fig.patch.set_facecolor(BG)

# 资金曲线
ax1.set_facecolor(BG)
ax1.plot(equity.index, equity['value'], color=GOLD, linewidth=1.5, label='资金曲线')
ax1.axhline(y=account, color='white', linewidth=0.5, linestyle='--', alpha=0.3, label='初始资金')

# 标注每笔交易盈亏
for sys, ed, xd, ep, xp, pnl in trades:
    ax1.plot([pd.Timestamp(ed), pd.Timestamp(xd)], [account + pnl, account + pnl],
             color=RED if pnl > 0 else GREEN, linewidth=2, alpha=0.6)
    label_c = RED if pnl > 0 else GREEN
    ax1.text(pd.Timestamp(xd), account + pnl, f' {pnl:+,}', fontsize=7, color=label_c, va='center')

ax1.set_title('资金曲线 + 逐笔盈亏', fontsize=16, fontweight='bold', color='white', pad=12)
ax1.set_ylabel('资金 (元)', fontsize=11, color=MUTED)
ax1.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
ax1.grid(True, alpha=0.1, color='white')
for sp in ax1.spines.values(): sp.set_edgecolor(GRID)
plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
plt.setp(ax1.xaxis.get_ticklabels(), visible=False)

max_dd_val = drawdown.min()
ax1.text(0.99, 0.95, f'初始: {account:,.0f} | 最终: {equity["value"].iloc[-1]:,.0f} | '
         f'总盈亏: {equity["value"].iloc[-1]-account:+,.0f} | '
         f'最大回撤: {max_dd_val:.2f}%',
         transform=ax1.transAxes, fontsize=10, color=TEXT, ha='right', va='top',
         bbox=dict(boxstyle='round,pad=0.5', facecolor=BG, edgecolor=GRID, alpha=0.8))

# 回撤
ax2.set_facecolor(BG)
ax2.fill_between(equity.index, 0, drawdown, alpha=0.4, color=RED, label='回撤')
ax2.plot(equity.index, drawdown, color=RED, linewidth=0.8)
ax2.set_ylabel('回撤 %', fontsize=10, color=MUTED)
ax2.set_ylim(min(drawdown.min() * 1.5, -0.1), 0.1)
ax2.grid(True, alpha=0.1, color='white')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
for sp in ax2.spines.values(): sp.set_edgecolor(GRID)

plt.tight_layout()
plt.savefig('turtle_metrics.png', dpi=200, facecolor=BG, bbox_inches='tight')
plt.close()
print("图: turtle_metrics.png")
