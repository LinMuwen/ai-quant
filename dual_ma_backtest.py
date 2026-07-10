#!/usr/bin/env python3
"""
双均线策略完整回测系统
======================
1. 加载股价数据
2. 计算 MA5 / MA15 均线
3. 检测金叉(买入)/死叉(卖出)信号
4. 绘制可视化图表
5. 模拟交易 → 计算累计收益率 / MDD / 夏普比率等指标

数据源: smic_daily_data.csv (中芯国际 688981)
均线周期: 5日(快线) + 15日(长线)

交易规则:
  - 金叉 → 全仓买入
  - 死叉 → 全部卖出平仓
  - 不考虑手续费和滑点(简化模型)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ========================================
# 全局样式
# ========================================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

RED   = '#ef4444'
GREEN = '#22c55e'
BLUE  = '#3b82f6'
GOLD  = '#f59e0b'
PURPLE= '#8b5cf6'
BG    = '#0f172a'
GRID  = '#1e293b'
TEXT  = '#cbd5e1'
MUTED = '#64748b'

# ========================================
# 1. 加载数据
# ========================================
print("=" * 60)
print("第1步: 加载股价数据")
print("=" * 60)

df = pd.read_csv('smic_daily_data.csv', parse_dates=['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)
print(f"  数据条数: {len(df)}")
print(f"  日期范围: {df['trade_date'].min().strftime('%Y-%m-%d')} ~ {df['trade_date'].max().strftime('%Y-%m-%d')}")
print(f"  股票代码: {df['ts_code'].iloc[0]}")
print(f"  收盘价范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")

# ========================================
# 2. 计算均线
# ========================================
print("\n" + "=" * 60)
print("第2步: 计算均线 MA5 / MA15")
print("=" * 60)

SHORT_WINDOW = 5
LONG_WINDOW  = 15

df['MA5']  = df['close'].rolling(window=SHORT_WINDOW).mean()
df['MA15'] = df['close'].rolling(window=LONG_WINDOW).mean()

print(f"  快线周期: {SHORT_WINDOW}日")
print(f"  慢线周期: {LONG_WINDOW}日")
print(f"  MA5 最新值:  {df['MA5'].iloc[-1]:.2f}")
print(f"  MA15 最新值: {df['MA15'].iloc[-1]:.2f}")
print(f"  当前状态: {'多头(MA5>MA15)' if df['MA5'].iloc[-1] > df['MA15'].iloc[-1] else '空头(MA5<MA15)'}")

# ========================================
# 3. 计算交易信号 (金叉/死叉)
# ========================================
print("\n" + "=" * 60)
print("第3步: 检测交易信号")
print("=" * 60)

df['signal'] = 0
df['position'] = 0

cross_up_dates   = []
cross_up_prices  = []
cross_down_dates = []
cross_down_prices= []

for i in range(1, len(df)):
    if pd.isna(df.loc[i, 'MA5']) or pd.isna(df.loc[i, 'MA15']):
        continue
    prev_diff = df.loc[i-1, 'MA5'] - df.loc[i-1, 'MA15']
    curr_diff = df.loc[i, 'MA5'] - df.loc[i, 'MA15']
    if prev_diff <= 0 and curr_diff > 0:
        df.loc[i, 'signal'] = 1
        cross_up_dates.append(df.loc[i, 'trade_date'])
        cross_up_prices.append(df.loc[i, 'close'])
    elif prev_diff >= 0 and curr_diff < 0:
        df.loc[i, 'signal'] = -1
        cross_down_dates.append(df.loc[i, 'trade_date'])
        cross_down_prices.append(df.loc[i, 'close'])

# 计算持仓状态
in_position = False
for i in range(len(df)):
    if df.loc[i, 'signal'] == 1 and not in_position:
        in_position = True
        df.loc[i, 'position'] = 1
    elif df.loc[i, 'signal'] == -1 and in_position:
        in_position = False
        df.loc[i, 'position'] = -1

print(f"  金叉(买入)次数: {len(cross_up_dates)}")
print(f"  死叉(卖出)次数: {len(cross_down_dates)}")
for d, p in zip(cross_up_dates, cross_up_prices):
    print(f"    ▲ 金叉: {d.strftime('%Y-%m-%d')}  价格: {p:.2f}")
for d, p in zip(cross_down_dates, cross_down_prices):
    print(f"    ▼ 死叉: {d.strftime('%Y-%m-%d')}  价格: {p:.2f}")

# ========================================
# 4. 绘制可视化图表
# ========================================
print("\n" + "=" * 60)
print("第4步: 生成可视化图表")
print("=" * 60)

# --- 图1: 全景图 ---
fig, axes = plt.subplots(3, 1, figsize=(18, 14),
                         gridspec_kw={'height_ratios': [2.5, 1, 1.5]})
fig.patch.set_facecolor(BG)
for ax in axes:
    ax.set_facecolor(BG)

ax1, ax2, ax3 = axes

# 多空背景色
for i in range(LONG_WINDOW, len(df)):
    if df.loc[i, 'MA5'] > df.loc[i, 'MA15']:
        ax1.axvspan(df.loc[i-1, 'trade_date'], df.loc[i, 'trade_date'],
                     color=RED, alpha=0.04)
    else:
        ax1.axvspan(df.loc[i-1, 'trade_date'], df.loc[i, 'trade_date'],
                     color=GREEN, alpha=0.04)

# 收盘价柱状图 (红涨绿跌)
for i in range(LONG_WINDOW, len(df)):
    color = RED if df.loc[i, 'close'] >= df.loc[i-1, 'close'] else GREEN
    ax1.bar(df.loc[i, 'trade_date'], df.loc[i, 'close'], color=color,
            width=0.8, alpha=0.5)

ax1.plot(df['trade_date'], df['MA5'],  color=RED,  linewidth=1.5, label=f'MA{SHORT_WINDOW} 快线')
ax1.plot(df['trade_date'], df['MA15'], color=BLUE, linewidth=1.8, label=f'MA{LONG_WINDOW} 慢线')

# 金叉/死叉标注
if cross_up_dates:
    ax1.scatter(cross_up_dates, cross_up_prices, marker='^', s=180,
                color=GOLD, edgecolors='white', linewidths=1, zorder=10)
if cross_down_dates:
    ax1.scatter(cross_down_dates, cross_down_prices, marker='v', s=180,
                color=GREEN, edgecolors='white', linewidths=1, zorder=10)

# 第一个和最后一个信号加注释
if cross_up_dates:
    fi = list(df['trade_date'].values).index(cross_up_dates[0])
    ax1.annotate('金叉买入', (cross_up_dates[0], cross_up_prices[0]),
                 textcoords="offset points", xytext=(-10, -25),
                 fontsize=9, color=GOLD, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.2))
if cross_up_dates:
    li = list(df['trade_date'].values).index(cross_up_dates[-1])
    ax1.annotate('金叉买入', (cross_up_dates[-1], cross_up_prices[-1]),
                 textcoords="offset points", xytext=(10, -25),
                 fontsize=9, color=GOLD, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.2))
if cross_down_dates:
    di = list(df['trade_date'].values).index(cross_down_dates[-1])
    ax1.annotate('死叉卖出', (cross_down_dates[-1], cross_down_prices[-1]),
                 textcoords="offset points", xytext=(-10, 20),
                 fontsize=9, color=GREEN, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.2))

ax1.set_title(f'中芯国际 (688981) 双均线策略 MA{SHORT_WINDOW} + MA{LONG_WINDOW}\n金叉(▲买入) / 死叉(▼卖出) 信号',
              fontsize=16, fontweight='bold', color='white', pad=12)
ax1.legend(loc='upper left', fontsize=10, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
ax1.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
ax1.grid(True, alpha=0.12, color='white')
for spine in ax1.spines.values():
    spine.set_edgecolor(GRID)

# --- 子图2: 信号分布 ---
ax2.fill_between(df['trade_date'], 0, df['signal'] * df['close'] * 0.03,
                  where=df['signal'] > 0, color=RED,  alpha=0.6, label='金叉(买入信号)')
ax2.fill_between(df['trade_date'], 0, df['signal'] * df['close'] * 0.03,
                  where=df['signal'] < 0, color=GREEN, alpha=0.6, label='死叉(卖出信号)')
ax2.axhline(y=0, color='white', linewidth=0.3)
ax2.set_ylabel('交易信号', fontsize=11, color=MUTED)
ax2.set_ylim(-0.02 * df['close'].max(), 0.02 * df['close'].max())
ax2.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
plt.setp(ax2.xaxis.get_majorticklabels(), visible=False)
plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
ax2.grid(True, alpha=0.12, color='white', axis='y')
for spine in ax2.spines.values():
    spine.set_edgecolor(GRID)

# --- 子图3: 成交量 ---
colors_vol = [RED if df.loc[i, 'close'] >= df.loc[i-1, 'close'] else GREEN
              for i in range(1, len(df))]
ax3.bar(df['trade_date'][1:], df['vol'][1:], color=colors_vol,
        width=0.8, alpha=0.5)
ax3.set_ylabel('成交量 (手)', fontsize=11, color=MUTED)
ax3.set_xlabel('日期', fontsize=11, color=MUTED)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
plt.setp(ax3.yaxis.get_ticklabels(), color=MUTED)
ax3.grid(True, alpha=0.12, color='white', axis='y')
for spine in ax3.spines.values():
    spine.set_edgecolor(GRID)

plt.tight_layout()
plt.savefig('dual_ma_strategy_chart1.png', dpi=150, facecolor=BG, bbox_inches='tight')
plt.close()
print("  ✓ dual_ma_strategy_chart1.png (全景信号图)")

# ========================================
# 5. 模拟交易与回测
# ========================================
print("\n" + "=" * 60)
print("第5步: 模拟交易与回测")
print("=" * 60)

INITIAL_CAPITAL = 100_000.0
capital = INITIAL_CAPITAL
shares  = 0
trades  = []

in_position = False
entry_date = None
entry_price= 0

for i in range(LONG_WINDOW, len(df)):
    sig = df.loc[i, 'signal']
    price = df.loc[i, 'close']
    date  = df.loc[i, 'trade_date']

    if sig == 1 and not in_position:
        shares = int(capital / price / 100) * 100
        if shares == 0:
            continue
        cost = shares * price
        capital -= cost
        in_position = True
        entry_date = date
        entry_price= price
        trades.append(('买入', date, price, shares, cost, capital + shares * price))

    elif sig == -1 and in_position:
        revenue = shares * price
        capital += revenue
        profit = (price - entry_price) / entry_price * 100
        trades.append(('卖出', date, price, shares, revenue, capital,
                        profit, (date - entry_date).days))
        shares = 0
        in_position = False
        entry_date = None
        entry_price= 0

# 如果期末仍持仓，按最后收盘价平仓
if in_position:
    last_price = df['close'].iloc[-1]
    revenue = shares * last_price
    capital += revenue
    profit = (last_price - entry_price) / entry_price * 100
    trades.append(('卖出(强制平仓)', df['trade_date'].iloc[-1], last_price, shares,
                    revenue, capital, profit, (df['trade_date'].iloc[-1] - entry_date).days))

final_capital = capital
total_return  = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

print(f"\n  初始资金:       {INITIAL_CAPITAL:,.0f} 元")
print(f"  最终资金:       {final_capital:,.0f} 元")
print(f"  累计收益率:     {total_return:+.2f}%")

# 每笔交易详情
print("\n  交易记录:")
print(f"  {'序号':<4} {'类型':<12} {'日期':<12} {'价格':<8} {'股数':<6} {'金额':>12} {'收益':>8} {'持仓天数':>6}")
print(f"  {'-'*70}")
buy_trade_returns = []
for idx, t in enumerate(trades):
    if t[0].startswith('卖出'):
        ret_str = f"{t[6]:+.2f}%" if len(t) >= 7 else ''
        days_str = f"{t[7]}天" if len(t) >= 8 else ''
        buy_trade_returns.append(t[6] if len(t) >= 7 else 0)
        print(f"  {idx:<4} {t[0]:<12} {str(t[1])[:10]:<12} {t[2]:<8.2f} {t[3]:<6} {t[4]:>12,.0f} {ret_str:>8} {days_str:>6}")
    else:
        print(f"  {idx:<4} {t[0]:<12} {str(t[1])[:10]:<12} {t[2]:<8.2f} {t[3]:<6} {t[4]:>12,.0f}")

# ========================================
# 计算净值曲线和量化指标
# ========================================

# 构建每日净值曲线 (全区间)
df['daily_ret'] = 0.0
in_position = False
entry_price = 0

for i in range(len(df)):
    sig = df.loc[i, 'signal']
    price = df.loc[i, 'close']

    # 先用昨天的持仓状态计算今日收益率 (信号当日按收盘价执行, 次日生效)
    if i > 0:
        if in_position:
            df.loc[i, 'daily_ret'] = (price - df.loc[i-1, 'close']) / df.loc[i-1, 'close']
        else:
            df.loc[i, 'daily_ret'] = 0.0

    # 再处理今日信号 (影响明日持仓)
    if sig == 1 and not in_position:
        in_position = True
        entry_price = price
    elif sig == -1 and in_position:
        in_position = False

# 净值
df['nav'] = (1 + df['daily_ret']).cumprod()
nav_series = df['nav'].values

# --- 累计收益率 ---
cumulative_return = (nav_series[-1] - 1) * 100

# --- 年化收益率 ---
start_date = df['trade_date'].iloc[LONG_WINDOW]
end_date   = df['trade_date'].iloc[-1]
years      = (end_date - start_date).days / 365.25
annual_return = (nav_series[-1] ** (1 / years) - 1) * 100 if years > 0 else 0

# --- 最大回撤 MDD ---
peak = nav_series[0]
mdd  = 0
mdd_start_idx = 0
mdd_end_idx   = 0
current_peak_idx = 0

for i, v in enumerate(nav_series):
    if v > peak:
        peak = v
        current_peak_idx = i
    dd = (v - peak) / peak
    if dd < mdd:
        mdd = dd
        mdd_start_idx = current_peak_idx
        mdd_end_idx   = i

# --- 夏普比率 ---
daily_returns = df['daily_ret'].values[LONG_WINDOW:]
risk_free_annual = 0.025
risk_free_daily = risk_free_annual / 252
excess_returns = daily_returns - risk_free_daily
if np.std(excess_returns) > 0:
    sharpe_daily = np.mean(excess_returns) / np.std(excess_returns)
    sharpe_annual = sharpe_daily * np.sqrt(252)
else:
    sharpe_annual = 0

# --- 胜率 ---
if buy_trade_returns:
    win_rate = sum(1 for r in buy_trade_returns if r > 0) / len(buy_trade_returns) * 100
    avg_win  = np.mean([r for r in buy_trade_returns if r > 0]) if any(r > 0 for r in buy_trade_returns) else 0
    avg_loss = np.mean([r for r in buy_trade_returns if r < 0]) if any(r < 0 for r in buy_trade_returns) else 0
else:
    win_rate = avg_win = avg_loss = 0

# --- 波动率 ---
volatility = np.std(daily_returns) * np.sqrt(252) * 100

# --- Calmar比率 ---
calmar = abs(annual_return / (mdd * 100)) if mdd != 0 else 0

# --- 最大连续盈利/亏损天数 ---
max_consecutive_up = 0
max_consecutive_down = 0
consecutive_up = 0
consecutive_down = 0
for r in daily_returns:
    if r > 0:
        consecutive_up += 1
        consecutive_down = 0
    elif r < 0:
        consecutive_down += 1
        consecutive_up = 0
    else:
        consecutive_up = 0
        consecutive_down = 0
    max_consecutive_up = max(max_consecutive_up, consecutive_up)
    max_consecutive_down = max(max_consecutive_down, consecutive_down)

print("\n" + "=" * 60)
print("量化评估指标")
print("=" * 60)
print(f"  累计收益率:        {cumulative_return:+.2f}%")
print(f"  年化收益率:        {annual_return:+.2f}%")
print(f"  年化波动率:        {volatility:.2f}%")
print(f"  最大回撤 (MDD):    {mdd*100:.2f}%")
print(f"  夏普比率 (年化):   {sharpe_annual:.2f}")
print(f"  Calmar比率:        {calmar:.2f}")
print(f"  胜率:              {win_rate:.1f}%")
print(f"  平均盈利:          {avg_win:+.2f}%")
print(f"  平均亏损:          {avg_loss:+.2f}%")
print(f"  盈亏比:            {abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}")
print(f"  交易次数:          {len(buy_trade_returns)}")
print(f"  最长连续上涨日:    {max_consecutive_up} 天")
print(f"  最长连续下跌日:    {max_consecutive_down} 天")
print(f"  回测周期:          {years:.1f} 年 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})")

# ========================================
# 图2: 回测结果综合图
# ========================================
fig = plt.figure(figsize=(16, 14))
fig.patch.set_facecolor(BG)

gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.25,
                       height_ratios=[2, 1.2, 1.5])

# (0,0): 净值曲线 + MDD 标注
ax_nav = fig.add_subplot(gs[0, :])
ax_nav.set_facecolor(BG)

start_plot_idx = LONG_WINDOW
dates_nav = df['trade_date'].values[start_plot_idx:]

ax_nav.plot(dates_nav, nav_series[start_plot_idx:], color=BLUE, linewidth=2, label='策略净值')
ax_nav.axhline(y=1, color='white', linestyle='--', linewidth=0.8, alpha=0.3, label='基准线')
ax_nav.fill_between(dates_nav, 1, nav_series[start_plot_idx:],
                     where=nav_series[start_plot_idx:] >= 1, color=RED, alpha=0.06)
ax_nav.fill_between(dates_nav, 1, nav_series[start_plot_idx:],
                     where=nav_series[start_plot_idx:] < 1, color=GREEN, alpha=0.06)

# 标注 MDD 区间
if mdd < 0:
    mdd_start_date = df['trade_date'].iloc[mdd_start_idx]
    mdd_end_date   = df['trade_date'].iloc[mdd_end_idx]
    ax_nav.axvspan(mdd_start_date, mdd_end_date, color=RED, alpha=0.08)
    ax_nav.annotate(f'MDD: {mdd*100:.1f}%',
                     xy=(mdd_end_date, nav_series[mdd_end_idx]),
                     xytext=(mdd_end_date, nav_series[mdd_start_idx] * 1.02),
                     fontsize=10, color=RED, fontweight='bold', ha='center',
                     arrowprops=dict(arrowstyle='->', color=RED, lw=1))

ax_nav.set_title(f'双均线策略 (MA{SHORT_WINDOW} + MA{LONG_WINDOW}) 回测净值曲线\n'
                 f'累计收益: {cumulative_return:+.2f}%  年化: {annual_return:+.2f}%  '
                 f'MDD: {mdd*100:.2f}%  夏普: {sharpe_annual:.2f}',
                 fontsize=14, fontweight='bold', color='white', pad=12)
ax_nav.legend(loc='upper left', fontsize=10, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
ax_nav.set_ylabel('净值', fontsize=11, color=MUTED)
ax_nav.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax_nav.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
plt.setp(ax_nav.yaxis.get_ticklabels(), color=MUTED)
ax_nav.grid(True, alpha=0.12, color='white')
for spine in ax_nav.spines.values():
    spine.set_edgecolor(GRID)

# (1,0): 每笔交易收益率
ax_trade = fig.add_subplot(gs[1, 0])
ax_trade.set_facecolor(BG)
if buy_trade_returns:
    colors_bar = [RED if r >= 0 else GREEN for r in buy_trade_returns]
    bars = ax_trade.bar(range(1, len(buy_trade_returns)+1), buy_trade_returns,
                        color=colors_bar, alpha=0.85, edgecolor='white', linewidth=0.3)
    for i, (v, c) in enumerate(zip(buy_trade_returns, colors_bar)):
        offset = 0.8 if v >= 0 else -3
        ax_trade.text(i+1, v + offset, f'{v:+.1f}%', ha='center', fontsize=9,
                      color='white' if abs(v) > 3 else c, fontweight='bold')
ax_trade.axhline(y=0, color='white', linewidth=0.3, alpha=0.4)
ax_trade.set_title('每笔交易收益率', fontsize=13, fontweight='bold', color='white', pad=8)
ax_trade.set_ylabel('收益率 (%)', fontsize=10, color=MUTED)
ax_trade.set_xlabel('交易编号', fontsize=10, color=MUTED)
ax_trade.grid(True, alpha=0.1, color='white', axis='y')
for spine in ax_trade.spines.values():
    spine.set_edgecolor(GRID)
plt.setp(ax_trade.yaxis.get_ticklabels(), color=MUTED)
plt.setp(ax_trade.xaxis.get_ticklabels(), color=MUTED)

# (1,1): 回撤曲线
ax_dd = fig.add_subplot(gs[1, 1])
ax_dd.set_facecolor(BG)

dd_series = []
peak_val = nav_series[0]
for v in nav_series:
    if v > peak_val:
        peak_val = v
    dd_series.append((v - peak_val) / peak_val * 100)
dd_series = np.array(dd_series)
ax_dd.fill_between(dates_nav, 0, dd_series[start_plot_idx:], color=RED, alpha=0.3)
ax_dd.plot(dates_nav, dd_series[start_plot_idx:], color=RED, linewidth=1)
ax_dd.set_title(f'回撤曲线  MDD={mdd*100:.2f}%', fontsize=13, fontweight='bold', color='white', pad=8)
ax_dd.set_ylabel('回撤 (%)', fontsize=10, color=MUTED)
ax_dd.set_xlabel('日期', fontsize=10, color=MUTED)
ax_dd.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.setp(ax_dd.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
plt.setp(ax_dd.yaxis.get_ticklabels(), color=MUTED)
ax_dd.grid(True, alpha=0.1, color='white')
for spine in ax_dd.spines.values():
    spine.set_edgecolor(GRID)

# (2): 指标汇总表
ax_table = fig.add_subplot(gs[2, :])
ax_table.set_facecolor(BG)
ax_table.axis('off')

metrics = [
    ('累计收益率',    f'{cumulative_return:+.2f}%'),
    ('年化收益率',    f'{annual_return:+.2f}%'),
    ('最大回撤 MDD',  f'{mdd*100:.2f}%'),
    ('年化波动率',    f'{volatility:.2f}%'),
    ('夏普比率',      f'{sharpe_annual:.2f}'),
    ('Calmar 比率',   f'{calmar:.2f}'),
    ('胜率',          f'{win_rate:.1f}%'),
    ('盈亏比',        f'{abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}'),
    ('交易次数',      f'{len(buy_trade_returns)}'),
    ('平均盈利',      f'{avg_win:+.2f}%' if buy_trade_returns else '-'),
    ('平均亏损',      f'{avg_loss:+.2f}%' if buy_trade_returns else '-'),
    ('最长连续下跌日', f'{max_consecutive_down}天'),
]

rows_per_col = 6
col_data = [metrics[i:i+rows_per_col] for i in range(0, len(metrics), rows_per_col)]

for col_idx, col_metrics in enumerate(col_data):
    for row_idx, (label, value) in enumerate(col_metrics):
        x = 0.1 + col_idx * 0.42
        y = 0.85 - row_idx * 0.15
        ax_table.text(x, y, label, fontsize=12, color=MUTED, transform=ax_table.transAxes)
        ax_table.text(x + 0.18, y, value, fontsize=12, color='white',
                      fontweight='bold', transform=ax_table.transAxes)

ax_table.set_title('回测指标汇总', fontsize=15, fontweight='bold', color='white', pad=20)

plt.savefig('dual_ma_strategy_chart2.png', dpi=150, facecolor=BG, bbox_inches='tight')
plt.close()
print("  ✓ dual_ma_strategy_chart2.png (回测结果综合图)")

# ========================================
# 图3: 最近交易标注明细图
# ========================================
recent_n = min(80, len(df))
df_recent = df.tail(recent_n).reset_index(drop=True)

fig, (ax_price, ax_pos) = plt.subplots(2, 1, figsize=(18, 10),
                                        gridspec_kw={'height_ratios': [3, 1]})
fig.patch.set_facecolor(BG)
ax_price.set_facecolor(BG)
ax_pos.set_facecolor(BG)

for i in range(len(df_recent)):
    if df_recent.loc[i, 'MA5'] > df_recent.loc[i, 'MA15']:
        ax_price.axvspan(df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'trade_date'],
                          color=RED, alpha=0.04)

for i in range(1, len(df_recent)):
    color = RED if df_recent.loc[i, 'close'] >= df_recent.loc[i-1, 'close'] else GREEN
    ax_price.bar(df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'close'],
                 color=color, width=0.8, alpha=0.45)

ax_price.plot(df_recent['trade_date'], df_recent['MA5'],  color=RED,  linewidth=2, label=f'MA{SHORT_WINDOW}')
ax_price.plot(df_recent['trade_date'], df_recent['MA15'], color=BLUE, linewidth=2, label=f'MA{LONG_WINDOW}')

for i in range(1, len(df_recent)):
    sig = df_recent.loc[i, 'signal']
    if sig == 1:
        ax_price.scatter(df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'close'],
                         marker='^', s=220, color=GOLD, edgecolors='white',
                         linewidths=1.5, zorder=10)
        ax_price.annotate('买入', (df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'close']),
                          textcoords="offset points", xytext=(0, 15),
                          fontsize=10, color=GOLD, ha='center', fontweight='bold')
    elif sig == -1:
        ax_price.scatter(df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'close'],
                         marker='v', s=220, color=GREEN, edgecolors='white',
                         linewidths=1.5, zorder=10)
        ax_price.annotate('卖出', (df_recent.loc[i, 'trade_date'], df_recent.loc[i, 'close']),
                          textcoords="offset points", xytext=(0, -20),
                          fontsize=10, color=GREEN, ha='center', fontweight='bold')

ax_price.set_title(f'近{recent_n}日交易信号明细 (▲买入金叉 / ▼卖出死叉)',
                   fontsize=14, fontweight='bold', color='white', pad=10)
ax_price.legend(loc='upper left', fontsize=10, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
ax_price.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
ax_price.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax_price.xaxis.set_major_locator(mdates.DayLocator(interval=7))
plt.setp(ax_price.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9, color=MUTED)
plt.setp(ax_price.yaxis.get_ticklabels(), color=MUTED)
ax_price.grid(True, alpha=0.12, color='white')
for spine in ax_price.spines.values():
    spine.set_edgecolor(GRID)

# 持仓状态
pos_colors = []
for i in range(len(df_recent)):
    if df_recent.loc[i, 'MA5'] > df_recent.loc[i, 'MA15']:
        pos_colors.append(RED)
    else:
        pos_colors.append(GREEN)

ax_pos.fill_between(df_recent['trade_date'], 0, 1, color=RED, alpha=0.15)
ax_pos.fill_between(df_recent['trade_date'], -1, 0, color=GREEN, alpha=0.15)
ax_pos.plot(df_recent['trade_date'], [1 if df_recent.loc[i, 'MA5'] > df_recent.loc[i, 'MA15']
              else 0 for i in range(len(df_recent))], color=RED, linewidth=2)
ax_pos.set_ylim(-0.1, 1.3)
ax_pos.set_yticks([0, 1])
ax_pos.set_yticklabels(['空仓/空头', '持仓/多头'], color=MUTED, fontsize=9)
ax_pos.set_ylabel('仓位', fontsize=11, color=MUTED)
ax_pos.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax_pos.xaxis.set_major_locator(mdates.DayLocator(interval=7))
plt.setp(ax_pos.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9, color=MUTED)
ax_pos.grid(True, alpha=0.12, color='white', axis='y')
for spine in ax_pos.spines.values():
    spine.set_edgecolor(GRID)

plt.tight_layout()
plt.savefig('dual_ma_strategy_chart3.png', dpi=150, facecolor=BG, bbox_inches='tight')
plt.close()
print("  ✓ dual_ma_strategy_chart3.png (近期信号明细图)")

print("\n" + "=" * 60)
print("✅ 全部图表和指标计算完成!")
print("=" * 60)
print("\n输出文件:")
print("  📊 dual_ma_strategy_chart1.png  — 全景信号图 (K线+均线+信号+成交量)")
print("  📊 dual_ma_strategy_chart2.png  — 回测结果图 (净值曲线+回撤+指标汇总)")
print("  📊 dual_ma_strategy_chart3.png  — 近期交易明细图 (信号标注+仓位状态)")
