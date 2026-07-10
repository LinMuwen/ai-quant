#!/usr/bin/env python3
"""
海龟策略综合可视化 -- 股价 + 通道 + 买卖信号 + 盈亏标注
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import json
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RED    = '#ef4444'
GREEN  = '#22c55e'
BLUE   = '#3b82f6'
GOLD   = '#f59e0b'
CYAN   = '#06b6d4'
PINK   = '#ec4899'
BG     = '#0f172a'
GRID   = '#1e293b'
TEXT   = '#cbd5e1'
MUTED  = '#64748b'

# ============================================================
# 指标计算（与 turtle_signals.py 一致）
# ============================================================
def compute_indicators(df):
    df = df.copy()
    # ATR (N值)
    prev_close = df['close'].shift(1)
    tr = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - prev_close), abs(df['low'] - prev_close))
    )
    df['N'] = tr.ewm(span=20, adjust=False).mean()
    df['N2'] = df['N'] * 2

    # S1 通道 (前20日)
    df['S1_upper'] = df['high'].shift(1).rolling(20).max()
    df['S1_lower'] = df['low'].shift(1).rolling(20).min()
    
    # 离场线 (前10日低)
    df['exit_lower'] = df['low'].shift(1).rolling(10).min()
    
    # 突破信号
    df['buy_sig'] = (df['high'] > df['S1_upper']) & df['S1_upper'].notna()
    df['sell_sig'] = (df['low'] < df['exit_lower']) & df['exit_lower'].notna()
    
    return df

def load_data(path):
    p = Path(path)
    if p.suffix == '.csv':
        return pd.read_csv(path, parse_dates=['trade_date']).sort_values('trade_date').reset_index(drop=True)
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df.sort_values('trade_date').reset_index(drop=True)

# ============================================================
# 交易记录（与回测结果一致）
# ============================================================
TRADES = [
    # (sys, entry_date, entry_price, exit_date, exit_price, pnl, reason)
    ("S1", "2025-08-18", 93.50, "2025-10-17", 121.98, +2848, "exit"),
    ("S2", "2025-09-30", 138.50, "2025-10-17", 121.98, -1652, "stop"),
    ("S1", "2025-12-23", 120.50, "2026-01-15", 124.44, +394, "exit"),
    ("S1", "2026-04-23", 108.88, "2026-05-19", 118.82, +994, "exit"),
    ("S2", "2026-04-30", 113.31, "2026-05-19", 118.82, +551, "exit"),
    ("S1", "2026-05-21", 134.00, "2026-06-08", 121.92, -1208, "exit"),
    ("S2", "2026-05-21", 134.00, "2026-06-08", 121.92, -1208, "exit"),
    ("S1", "2026-06-30", 152.05, "2026-07-03", 140.31, -1174, "force"),
    ("S2", "2026-06-30", 152.05, "2026-07-03", 140.31, -1174, "force"),
]

# ============================================================
# 主图表
# ============================================================
def draw(valid, output="turtle_dashboard"):
    n = len(valid)
    
    fig = plt.figure(figsize=(22, 13))
    fig.patch.set_facecolor(BG)
    
    # 上方大图: 价格 + 通道 + 信号 (占 75%)
    gs = fig.add_gridspec(3, 1, height_ratios=[4, 1, 1], hspace=0.08)
    ax_price  = fig.add_subplot(gs[0])
    ax_vol    = fig.add_subplot(gs[1], sharex=ax_price)
    ax_atr    = fig.add_subplot(gs[2], sharex=ax_price)
    
    for ax in [ax_price, ax_vol, ax_atr]:
        ax.set_facecolor(BG)
    
    # ==================== 面板1: 价格 + 通道 + 信号 ====================
    
    # 通道填充
    valid_nonan = valid.dropna(subset=['S1_upper'])
    ax_price.fill_between(valid_nonan['trade_date'], 
                          valid_nonan['S1_upper'], valid_nonan['S1_lower'],
                          alpha=0.06, color=BLUE)
    
    # 上轨 / 下轨
    ax_price.plot(valid_nonan['trade_date'], valid_nonan['S1_upper'],
                  color=RED, linewidth=0.8, linestyle='--', alpha=0.45,
                  label='S1上轨 (前20日最高)')
    ax_price.plot(valid_nonan['trade_date'], valid_nonan['S1_lower'],
                  color=GREEN, linewidth=0.8, linestyle='--', alpha=0.45,
                  label='S1下轨 (前20日最低)')
    
    # 离场线
    exit_vals = valid['exit_lower'].dropna()
    if len(exit_vals) > 0:
        ax_price.plot(valid['trade_date'].iloc[-len(exit_vals):], exit_vals.values,
                      color=GOLD, linewidth=0.6, linestyle=':', alpha=0.5,
                      label='离场线 (前10日低)')
    
    # 红绿分段收盘价
    for i in range(1, len(valid)):
        c = RED if valid['close'].iloc[i] >= valid['close'].iloc[i-1] else GREEN
        ax_price.plot(valid['trade_date'].iloc[i-1:i+1],
                      valid['close'].iloc[i-1:i+1],
                      color=c, linewidth=1.3, alpha=0.85)
    
    # 所有毛突破信号（半透明小点）
    buy_signals = valid[valid['buy_sig'] == True]
    ax_price.scatter(buy_signals['trade_date'], buy_signals['high'],
                     marker='o', s=15, color=CYAN, alpha=0.3, zorder=4)
    
    # ---- 实际成交: 买入/卖出大标记 ----
    entry_dates = []
    entry_prices = []
    exit_dates = []
    exit_prices = []
    exit_colors = []
    exit_labels = []
    
    for sys, ed, ep, xd, xp, pnl, reason in TRADES:
        entry_dates.append(pd.Timestamp(ed))
        entry_prices.append(ep)
        exit_dates.append(pd.Timestamp(xd))
        exit_prices.append(xp)
        exit_colors.append(RED if pnl > 0 else GREEN)
        exit_labels.append(f'{pnl:+,.0f}')
    
    # 入场标记: 大红三角 + "买"标签
    ax_price.scatter(entry_dates, entry_prices,
                     marker='^', s=200, color=RED, edgecolors='white',
                     linewidths=1.2, zorder=20, label='买入信号')
    
    # 出场标记: 绿/红倒三角 + 盈亏标签
    for i, (xd, xp, ec) in enumerate(zip(exit_dates, exit_prices, exit_colors)):
        ax_price.scatter(xd, xp,
                         marker='v', s=120, color=ec, edgecolors='white',
                         linewidths=0.8, zorder=20)
    
    # 逐笔交易标注 (用曲线连接入场-离场)
    y_offset = 0
    for i, (sys, ed, ep, xd, xp, pnl, reason) in enumerate(TRADES):
        y_offset = (i % 3) * 18  # 错开重叠标注
        mid_x = pd.Timestamp(ed) + (pd.Timestamp(xd) - pd.Timestamp(ed)) / 2
        # 连接线
        ax_price.plot([pd.Timestamp(ed), pd.Timestamp(xd)], [ep, xp],
                      color=RED if pnl > 0 else GREEN,
                      linewidth=0.5, alpha=0.3, linestyle='-')
        
        # 入场标签
        label_color = RED if pnl > 0 else GREEN
        reason_cn = {'exit': '离场信号', 'stop': '止损触发', 'force': '强制平仓'}
        ax_price.annotate(
            f'{sys} | {pnl:+,.0f}\n{reason_cn.get(reason, reason)}',
            xy=(pd.Timestamp(xd), xp),
            xytext=(15, 18 - y_offset),
            textcoords='offset points',
            fontsize=7, color=label_color, ha='left', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=BG, edgecolor=label_color,
                      alpha=0.8, linewidth=0.5),
            arrowprops=dict(arrowstyle='->', color=label_color, lw=0.5, alpha=0.6)
        )
    
    # 标注最近一次买入信号的状态
    last = valid.iloc[-1]
    if pd.notna(last.get('S1_upper')):
        gap_to_entry = last['S1_upper'] - last['close']
        ax_price.annotate(
            f'当前价 {last["close"]:.1f}\n距买入触发 {gap_to_entry:.1f} 元',
            xy=(last['trade_date'], last['close']),
            xytext=(-80, 30), textcoords='offset points',
            fontsize=9, color=CYAN, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=BG, edgecolor=CYAN,
                      alpha=0.9, linewidth=0.8),
            arrowprops=dict(arrowstyle='->', color=CYAN, lw=0.8)
        )
    
    ax_price.set_title('海龟策略 S1(20日) — 中芯国际 688981', 
                       fontsize=18, fontweight='bold', color='white', pad=18)
    ax_price.set_ylabel('价格 (元)', fontsize=12, color=MUTED)
    ax_price.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID,
                    labelcolor=TEXT, ncol=2)
    ax_price.grid(True, alpha=0.08, color='white')
    for spine in ax_price.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax_price.yaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax_price.xaxis.get_ticklabels(), visible=False)
    
    # 图例补充
    legend_elements = [
        mpatches.Patch(color=RED, alpha=0.6, label='盈利交易'),
        mpatches.Patch(color=GREEN, alpha=0.6, label='亏损交易'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=RED,
                   markersize=10, label='买入'),
        plt.Line2D([0], [0], marker='v', color='w', markerfacecolor=GREEN,
                   markersize=8, label='卖出 (止损/离场)'),
    ]
    ax_price.legend(handles=legend_elements, loc='upper right', fontsize=8,
                    facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    
    # ==================== 面板2: 成交量 ====================
    vol_colors = [RED if valid['close'].iloc[i] >= valid['close'].iloc[i-1] 
                  else GREEN for i in range(len(valid))]
    ax_vol.bar(valid['trade_date'], valid['vol'], color=vol_colors, 
               alpha=0.3, width=1.0)
    ax_vol.set_ylabel('成交量', fontsize=10, color=MUTED)
    ax_vol.grid(True, alpha=0.08, color='white')
    plt.setp(ax_vol.yaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax_vol.xaxis.get_ticklabels(), visible=False)
    for spine in ax_vol.spines.values():
        spine.set_edgecolor(GRID)
    
    # ==================== 面板3: N值 + 止损线 ====================
    ax_atr.fill_between(valid['trade_date'], 0, valid['N'],
                        alpha=0.4, color=GOLD, label='N值 (20日ATR)')
    ax_atr.plot(valid['trade_date'], valid['N'], color=GOLD, linewidth=1.2)
    ax_atr.axhline(y=valid['N'].mean(), color='white', linewidth=0.4,
                   linestyle='--', alpha=0.3)
    ax_atr.text(valid['trade_date'].iloc[-1], valid['N'].mean(), 
                f' 均值 {valid["N"].mean():.1f}',
                fontsize=7, color='white', alpha=0.4, va='center')
    
    ax_atr.set_ylabel('N值 (元)', fontsize=10, color=MUTED)
    ax_atr.set_xlabel('')
    ax_atr.grid(True, alpha=0.08, color='white')
    plt.setp(ax_atr.yaxis.get_ticklabels(), color=MUTED)
    ax_atr.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax_atr.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.setp(ax_atr.xaxis.get_majorticklabels(), rotation=45, ha='right', 
             fontsize=8, color=MUTED)
    for spine in ax_atr.spines.values():
        spine.set_edgecolor(GRID)
    
    # 在下方文字中标注时间周期
    ax_atr.text(0.01, -0.55, 
                '周期: 2025-07 ~ 2026-07 | S1(20日) 入场: 突破前20日高 | 离场: 跌破前10日低 | 止损: 2N | 过滤器: 上次盈利则跳过',
                transform=ax_atr.transAxes, fontsize=8, color=MUTED, style='italic')
    
    plt.tight_layout()
    fig.subplots_adjust(bottom=0.07)
    fname = f'{output}.png'
    plt.savefig(fname, dpi=200, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图: {fname}")
    return fname

if __name__ == '__main__':
    df = load_data('smic_daily_data.json')
    df = compute_indicators(df)
    draw(df, 'turtle_dashboard')
