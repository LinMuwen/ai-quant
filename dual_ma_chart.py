#!/usr/bin/env python3
"""双均线策略分析图表 - 中芯国际(688981)"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.patches import FancyBboxPatch

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_csv('smic_daily_data.csv', parse_dates=['trade_date']).sort_values('trade_date')
df = df.reset_index(drop=True)

ma5 = df['close'].rolling(5).mean()
ma10 = df['close'].rolling(10).mean()
ma20 = df['close'].rolling(20).mean()

# ====== 金叉/死叉检测 ======
cross_up_idx, cross_down_idx = [], []
for i in range(1, len(df)):
    if pd.isna(ma5.iloc[i]) or pd.isna(ma20.iloc[i]):
        continue
    prev_diff = ma5.iloc[i-1] - ma20.iloc[i-1]
    curr_diff = ma5.iloc[i] - ma20.iloc[i]
    if prev_diff < 0 and curr_diff > 0:
        cross_up_idx.append(i)
    elif prev_diff > 0 and curr_diff < 0:
        cross_down_idx.append(i)

print(f"金叉次数: {len(cross_up_idx)}, 死叉次数: {len(cross_down_idx)}")

COLOR_RED   = '#ef4444'
COLOR_GREEN = '#22c55e'
COLOR_BLUE  = '#3b82f6'
COLOR_GOLD  = '#f59e0b'
BG_COLOR    = '#0f172a'
GRID_COLOR  = '#1e293b'
TEXT_COLOR  = '#cbd5e1'
TEXT_LIGHT  = '#64748b'

# ================================================================
# 图1: 完整双均线全景图 (1600x800)
# ================================================================
fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(df['trade_date'], df['close'], color=TEXT_COLOR, linewidth=1.2, alpha=0.5, label='收盘价')
ax.plot(df['trade_date'], ma5, color=COLOR_RED, linewidth=1.5, label='MA5 (快线)')
ax.plot(df['trade_date'], ma20, color=COLOR_BLUE, linewidth=1.5, label='MA20 (慢线)')

# 金叉标记
for i in cross_up_idx:
    ax.scatter(df['trade_date'].iloc[i], ma20.iloc[i], marker='^', s=120,
               color=COLOR_GOLD, edgecolors='white', linewidths=0.8, zorder=10)

# 死叉标记  
for i in cross_down_idx:
    ax.scatter(df['trade_date'].iloc[i], ma20.iloc[i], marker='v', s=120,
               color=COLOR_GREEN, edgecolors='white', linewidths=0.8, zorder=10)

# 填充金叉/死叉区间
in_bull = False; bull_start = 0
for i in range(len(df)):
    if pd.isna(ma5.iloc[i]) or pd.isna(ma20.iloc[i]):
        continue
    bull_now = ma5.iloc[i] > ma20.iloc[i]
    if bull_now and not in_bull:
        bull_start = i; in_bull = True
    elif not bull_now and in_bull:
        ax.axvspan(df['trade_date'].iloc[bull_start], df['trade_date'].iloc[i],
                   alpha=0.07, color=COLOR_RED)
        in_bull = False
if in_bull:
    ax.axvspan(df['trade_date'].iloc[bull_start], df['trade_date'].iloc[-1],
               alpha=0.07, color=COLOR_RED)

ax.set_title('中芯国际(688981) 双均线策略 — MA5 & MA20 金叉/死叉信号', 
             fontsize=16, fontweight='bold', color='white', pad=15)
ax.legend(loc='upper left', fontsize=10, facecolor=BG_COLOR, edgecolor=GRID_COLOR,
          labelcolor=TEXT_COLOR)
ax.set_xlabel('日期', fontsize=11, color=TEXT_LIGHT)
ax.set_ylabel('价格 (元)', fontsize=11, color=TEXT_LIGHT)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=TEXT_LIGHT)
plt.setp(ax.yaxis.get_ticklabels(), color=TEXT_LIGHT)

ax.grid(True, alpha=0.15, color='white')
ax.tick_params(colors=TEXT_LIGHT)
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

# 图例标注
fig.text(0.99, 0.02, '▲ 金叉(买入)  ▼ 死叉(卖出)  红色区域=快线>慢线(多头)  涨红跌绿·中国股市惯例',
         ha='right', fontsize=9, color=TEXT_LIGHT, style='italic')

plt.tight_layout()
plt.savefig('dual_ma_full.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
plt.close()
print("图1: dual_ma_full.png 已生成")

# ================================================================
# 图2: 最近60天放大图 (1600x800)
# ================================================================
recent = df.tail(60).copy()
recent = recent.reset_index(drop=True)
r_ma5  = ma5.tail(60).reset_index(drop=True)
r_ma20 = ma20.tail(60).reset_index(drop=True)
r_close = recent['close'].reset_index(drop=True)

fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.fill_between(recent['trade_date'], r_ma5, r_ma20,
                where=r_ma5 >= r_ma20, color=COLOR_RED, alpha=0.08, label='多头区间(快线>慢线)')
ax.fill_between(recent['trade_date'], r_ma5, r_ma20,
                where=r_ma5 < r_ma20, color=COLOR_GREEN, alpha=0.08, label='空头区间(快线<慢线)')

ax.plot(recent['trade_date'], r_close, color=TEXT_COLOR, linewidth=1.5, alpha=0.6, label='收盘价')
ax.plot(recent['trade_date'], r_ma5, color=COLOR_RED, linewidth=2, label='MA5 (快线)')
ax.plot(recent['trade_date'], r_ma20, color=COLOR_BLUE, linewidth=2, label='MA20 (慢线)')

# 标注最近60天内的金叉/死叉
for i in range(1, len(recent)):
    if pd.isna(r_ma5.iloc[i]) or pd.isna(r_ma20.iloc[i]):
        continue
    prev = r_ma5.iloc[i-1] - r_ma20.iloc[i-1]
    curr = r_ma5.iloc[i] - r_ma20.iloc[i]
    if prev < 0 and curr > 0:
        dt, val = recent['trade_date'].iloc[i], r_ma20.iloc[i]
        ax.scatter(dt, val, marker='^', s=200, color=COLOR_GOLD, edgecolors='white',
                   linewidths=1.2, zorder=10)
        ax.annotate('金叉\n买入', (dt, val), textcoords="offset points", xytext=(0, 18),
                    fontsize=9, color=COLOR_GOLD, ha='center', fontweight='bold')
    elif prev > 0 and curr < 0:
        dt, val = recent['trade_date'].iloc[i], r_ma20.iloc[i]
        ax.scatter(dt, val, marker='v', s=200, color=COLOR_GREEN, edgecolors='white',
                   linewidths=1.2, zorder=10)
        ax.annotate('死叉\n卖出', (dt, val), textcoords="offset points", xytext=(0, -24),
                    fontsize=9, color=COLOR_GREEN, ha='center', fontweight='bold')

ax.set_title('中芯国际(688981) 近60日双均线策略信号（局部放大）', 
             fontsize=16, fontweight='bold', color='white', pad=15)
ax.legend(loc='upper left', fontsize=10, facecolor=BG_COLOR, edgecolor=GRID_COLOR,
          labelcolor=TEXT_COLOR)
ax.set_xlabel('日期', fontsize=11, color=TEXT_LIGHT)
ax.set_ylabel('价格 (元)', fontsize=11, color=TEXT_LIGHT)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9, color=TEXT_LIGHT)
plt.setp(ax.yaxis.get_ticklabels(), color=TEXT_LIGHT)

ax.grid(True, alpha=0.15, color='white')
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

plt.tight_layout()
plt.savefig('dual_ma_recent.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
plt.close()
print("图2: dual_ma_recent.png 已生成")

# ================================================================
# 图3: 信号统计子图 (1600x1000)
# ================================================================
fig, axes = plt.subplots(2, 1, figsize=(16, 10))
fig.patch.set_facecolor(BG_COLOR)

# 子图1: 信号分布
ax1 = axes[0]
ax1.set_facecolor(BG_COLOR)

# 构建交易信号
signals = []
in_position = False
entry_price = 0
entry_date = None
for i in range(20, len(df)):
    if pd.isna(ma5.iloc[i]) or pd.isna(ma20.iloc[i]):
        continue
    prev_diff = ma5.iloc[i-1] - ma20.iloc[i-1]
    curr_diff = ma5.iloc[i] - ma20.iloc[i]
    if prev_diff < 0 and curr_diff > 0 and not in_position:
        in_position = True
        entry_price = df['close'].iloc[i]
        entry_date = df['trade_date'].iloc[i]
        signals.append(('金叉(买入)', entry_date, entry_price, None, None))
    elif prev_diff > 0 and curr_diff < 0 and in_position:
        exit_price = df['close'].iloc[i]
        exit_date = df['trade_date'].iloc[i]
        ret_pct = (exit_price - entry_price) / entry_price * 100
        signals[-1] = ('金叉(买入)', entry_date, entry_price, exit_date, ret_pct)
        in_position = False

profits = [s[4] for s in signals if s[4] is not None]
colors_profit = [COLOR_RED if p >= 0 else COLOR_GREEN for p in profits]
bars = ax1.bar(range(len(profits)), profits, color=colors_profit, alpha=0.85, edgecolor='white', linewidth=0.3)

for i, (v, c) in enumerate(zip(profits, colors_profit)):
    ax1.text(i, v + (0.5 if v >= 0 else -2.5), f'{v:+.1f}%',
             ha='center', fontsize=9, color='white' if abs(v) > 5 else c, fontweight='bold')

ax1.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)
ax1.set_title('每次金叉→死叉交易的收益率', fontsize=15, fontweight='bold', color='white', pad=12)
ax1.set_ylabel('收益率 (%)', color=TEXT_LIGHT, fontsize=11)
ax1.set_xticks(range(len(profits)))
ax1.set_xticklabels([f'#{i+1}' for i in range(len(profits))], color=TEXT_LIGHT, fontsize=9)
ax1.grid(True, alpha=0.12, color='white', axis='y')
for spine in ax1.spines.values():
    spine.set_edgecolor(GRID_COLOR)
plt.setp(ax1.yaxis.get_ticklabels(), color=TEXT_LIGHT)

# 子图2: 汇总统计表
ax2 = axes[1]
ax2.set_facecolor(BG_COLOR)
ax2.axis('off')

stats = {
    '总交易次数': len(profits),
    '盈利次数': sum(1 for p in profits if p > 0),
    '亏损次数': sum(1 for p in profits if p < 0),
    '胜率': f"{sum(1 for p in profits if p > 0) / max(len(profits), 1) * 100:.1f}%",
    '平均收益率': f"{np.mean(profits):.1f}%",
    '最大盈利': f"{max(profits):.1f}%",
    '最大亏损': f"{min(profits):.1f}%",
    '累计收益率': f"{sum(profits):.1f}%",
}

y = 0.85
ax2.text(0.5, y + 0.08, '双均线策略 (MA5+MA20) 回测统计', ha='center', fontsize=15,
         fontweight='bold', color='white', transform=ax2.transAxes)

table_data = []
for k, v in stats.items():
    table_data.append([f'  {k}', f'{v}'])

table = ax2.table(cellText=table_data, colLabels=None, colWidths=[0.3, 0.25],
                  cellLoc='left', loc='center', bbox=[0.25, 0.08, 0.5, 0.6])
table.auto_set_font_size(False)
table.set_fontsize(12)
for key, cell in table.get_celld().items():
    cell.set_edgecolor(GRID_COLOR)
    cell.set_facecolor('#1a2332')
    cell.set_text_props(color='white')
    if key[1] == 0:
        cell.set_text_props(color=TEXT_LIGHT)
    if key[1] == 1:
        cell.set_text_props(color='white', fontweight='bold')

fig.suptitle('中芯国际(688981) 双均线策略交易信号统计', 
             fontsize=18, fontweight='bold', color='white', y=0.98)
plt.tight_layout()
plt.savefig('dual_ma_stats.png', dpi=150, facecolor=BG_COLOR, bbox_inches='tight')
plt.close()
print("图3: dual_ma_stats.png 已生成")

print("\n✅ 三张图表全部生成完成!")
