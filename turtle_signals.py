#!/usr/bin/env python3
"""
海龟交易策略 -- 完整信号生成与回测

信号规则 (仅做多):
  入场 System1: 收盘价突破20日最高价
  入场 System2: 收盘价突破55日最高价
  离场:        收盘价跌破10日最低价
  止损(硬):    入场价 - 2N (N = 20日ATR)
  加仓:        每涨0.5N加1单位, 最多4单位
  过滤器:      上次突破为盈利则跳过下一次同系统信号

仓位管理:
  每单位风险 = 账户的1%
  每单位股数 = floor(风险金额 / 2N / 股价) × 100股
  仅做多 (A股)
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RED    = '#ef4444'
GREEN  = '#22c55e'
BLUE   = '#3b82f6'
GOLD   = '#f59e0b'
CYAN   = '#06b6d4'
BG     = '#0f172a'
GRID   = '#1e293b'
TEXT   = '#cbd5e1'
MUTED  = '#64748b'

# ============================================================
# 数据结构
# ============================================================
@dataclass
class Trade:
    system: str         # 'S1' (20日) or 'S2' (55日)
    entry_idx: int
    entry_date: str
    entry_price: float
    units: int          # 实际建仓单位数
    exit_idx: int
    exit_date: str
    exit_price: float
    exit_reason: str    # 'exit_signal' / 'stop_loss'
    pnl: float
    pnl_pct: float

# ============================================================
# 指标计算
# ============================================================
def prep_indicators(df, period_s1=20, period_s2=55, atr_period=20):
    """一次性计算所有海龟指标"""
    df = df.copy()
    
    # N值 (20日ATR)
    prev_close = df['close'].shift(1)
    tr = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - prev_close), abs(df['low'] - prev_close))
    )
    df['N'] = tr.ewm(span=atr_period, adjust=False).mean()
    
    # System 1 唐奇安通道 (20日) - 上轨 = 前20日最高价 (shift 1 防止当根包含)
    df['S1_upper']  = df['high'].shift(1).rolling(period_s1).max()
    df['S1_lower']  = df['low'].shift(1).rolling(period_s1).min()
    
    # System 2 唐奇安通道 (55日)
    df['S2_upper']  = df['high'].shift(1).rolling(period_s2).max()
    df['S2_lower']  = df['low'].shift(1).rolling(period_s2).min()
    
    # 离场通道 (10日)
    df['exit_lower'] = df['low'].shift(1).rolling(10).min()
    
    # 突破信号: 当日 HIGH 突破前 N 日最高 (突破当日即时入场)
    df['S1_break'] = (df['high'] > df['S1_upper']) & (df['S1_upper'].notna())
    df['S2_break'] = (df['high'] > df['S2_upper']) & (df['S2_upper'].notna())
    # 离场信号: 当日 LOW 跌破前 10 日最低
    df['exit_sig'] = (df['low'] < df['exit_lower']) & (df['exit_lower'].notna())
    
    return df

# ============================================================
# 交易模拟
# ============================================================
def simulate_trades(df, account=1_000_000, risk_per_unit=0.01):
    """
    海龟交易模拟 -- 仅做多
    
    返回: trades list, signals DataFrame
    """
    n = len(df)
    trades: List[Trade] = []
    active = { 'S1': None, 'S2': None }  # 当前持仓: {system: Trade or None}
    last_S1_winner = None  # 过滤器: 上次S1突破是否盈利
    last_S2_winner = None
    
    for i in range(1, n):
        row = df.iloc[i]
        if pd.isna(row.get('N')) or row['N'] <= 0:
            continue
        
        N = row['N']
        close = row['close']
        date = row['trade_date'].strftime('%Y-%m-%d')
        
        # ---- 逐日检查持仓状态 ----
        for sys_key in ['S1', 'S2']:
            t = active[sys_key]
            if t is None:
                continue
            
            # 硬止损: 触碰 2N
            if close <= t.entry_price - N * 2:
                t.exit_idx = i
                t.exit_date = date
                t.exit_price = close
                t.exit_reason = 'stop_loss'
                t.pnl = (close - t.entry_price) * t.units * 100
                t.pnl_pct = (close - t.entry_price) / t.entry_price * 100
                trades.append(t)
                active[sys_key] = None
                continue
            
            # 离场信号: 跌破10日低点
            if row.get('exit_sig') and not pd.isna(row.get('exit_sig')):
                t.exit_idx = i
                t.exit_date = date
                t.exit_price = close
                t.exit_reason = 'exit_signal'
                t.pnl = (close - t.entry_price) * t.units * 100
                t.pnl_pct = (close - t.entry_price) / t.entry_price * 100
                trades.append(t)
                active[sys_key] = None
                continue
        
        # ---- 入场信号 ----
        
        # System 1 (20日突破)
        if active['S1'] is None and row.get('S1_break'):
            # 过滤: 如果上次S1突破盈利, 跳过本次
            if last_S1_winner:
                last_S1_winner = None
            else:
                trade = _enter_trade('S1', i, row, account, risk_per_unit)
                active['S1'] = trade
        
        # System 2 (55日突破)
        if active['S2'] is None and row.get('S2_break'):
            if last_S2_winner:
                last_S2_winner = None
            else:
                trade = _enter_trade('S2', i, row, account, risk_per_unit)
                active['S2'] = trade
    
    # 如果还有未平仓, 以最后一日收盘价强制平仓
    for sys_key in ['S1', 'S2']:
        t = active[sys_key]
        if t is None:
            continue
        last_row = df.iloc[-1]
        t.exit_idx = n - 1
        t.exit_date = last_row['trade_date'].strftime('%Y-%m-%d')
        t.exit_price = last_row['close']
        t.exit_reason = 'force_close'
        t.pnl = (last_row['close'] - t.entry_price) * t.units * 100
        t.pnl_pct = (last_row['close'] - t.entry_price) / t.entry_price * 100
        trades.append(t)
    
    # 回溯标记过滤器: 按系统分别处理
    for sys_key in ['S1', 'S2']:
        sys_trades = [t for t in trades if t.system == sys_key]
        for idx, t in enumerate(sys_trades):
            if idx < len(sys_trades) - 1:
                # 如果这笔交易盈利, 设置过滤器跳过下一次同系统信号
                pass  # 过滤器在逐日循环中处理
    
    # 修正: 在逐日循环中处理过滤逻辑
    # 重新执行带过滤器的模拟
    return _simulate_with_filters(df, account, risk_per_unit)

def _enter_trade(system, idx, row, account, risk_per_unit):
    """计算入场仓位
    突破当日入场价 = 当日开盘价 (突破后立即成交, 接近开盘价)
    """
    N = row['N']
    # 用当日开盘价作为入场价 (突破后即时成交)
    entry_price = row['open'] if row['open'] > 0 else row['close']
    risk_amount = account * risk_per_unit
    units = max(1, int(risk_amount / (N * 2) / entry_price / 100))  # 至少1手
    
    return Trade(
        system=system,
        entry_idx=idx,
        entry_date=row['trade_date'].strftime('%Y-%m-%d'),
        entry_price=entry_price,
        units=units,
        exit_idx=-1,
        exit_date='',
        exit_price=0,
        exit_reason='',
        pnl=0,
        pnl_pct=0
    )

def _simulate_with_filters(df, account, risk_per_unit):
    """带过滤器的完整模拟"""
    n = len(df)
    trades: List[Trade] = []
    active = { 'S1': None, 'S2': None }
    skip_next = { 'S1': False, 'S2': False }
    
    for i in range(1, n):
        row = df.iloc[i]
        if pd.isna(row.get('N')) or row['N'] <= 0:
            continue
        
        N = row['N']
        close = row['close']
        date = row['trade_date'].strftime('%Y-%m-%d')
        
        # ---- 持仓检查 ----
        for sys_key in ['S1', 'S2']:
            t = active[sys_key]
            if t is None:
                continue
            
            # 硬止损
            if close <= t.entry_price - N * 2:
                t.exit_idx = i
                t.exit_date = date
                t.exit_price = close
                t.exit_reason = 'stop_loss'
                t.pnl = (close - t.entry_price) * t.units * 100
                t.pnl_pct = (close - t.entry_price) / t.entry_price * 100
                trades.append(t)
                active[sys_key] = None
                # 止损出场不触发过滤器 (只有离场信号触发的才判断)
                continue
            
            # 离场信号: 跌破10日低点
            if row.get('exit_sig'):
                t.exit_idx = i
                t.exit_date = date
                t.exit_price = close
                t.exit_reason = 'exit_signal'
                t.pnl = (close - t.entry_price) * t.units * 100
                t.pnl_pct = (close - t.entry_price) / t.entry_price * 100
                trades.append(t)
                active[sys_key] = None
                # 如果盈利, 跳过下一次同系统信号
                if t.pnl > 0:
                    skip_next[sys_key] = True
                continue
        
        # ---- 入场 ----
        for sys_key, break_col in [('S1', 'S1_break'), ('S2', 'S2_break')]:
            if active[sys_key] is not None:
                continue
            if not row.get(break_col):
                continue
            
            if skip_next[sys_key]:
                skip_next[sys_key] = False
                continue
            
            t = _enter_trade(sys_key, i, row, account, risk_per_unit)
            active[sys_key] = t
    
    # 强制平仓
    for sys_key in ['S1', 'S2']:
        t = active[sys_key]
        if t is None:
            continue
        last_row = df.iloc[-1]
        t.exit_idx = n - 1
        t.exit_date = last_row['trade_date'].strftime('%Y-%m-%d')
        t.exit_price = last_row['close']
        t.exit_reason = 'force_close'
        t.pnl = (last_row['close'] - t.entry_price) * t.units * 100
        t.pnl_pct = (last_row['close'] - t.entry_price) / t.entry_price * 100
        trades.append(t)
    
    return sorted(trades, key=lambda x: x.entry_idx)

# ============================================================
# 图表
# ============================================================
def plot_trades(df, trades, code, name, output_prefix):
    """生成交易信号图"""
    valid = df.dropna(subset=['N']).reset_index(drop=True)
    
    # ====== 图1: System1 信号 ======
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     sharex=True)
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    # S1 通道
    ax1.plot(valid['trade_date'], valid['S1_upper'], color=RED, linewidth=0.8, 
             linestyle='--', alpha=0.5, label='S1上轨(前20日高)')
    ax1.plot(valid['trade_date'], valid['S1_lower'], color=GREEN, linewidth=0.8, 
             linestyle='--', alpha=0.5, label='S1下轨(前20日低)')
    
    # 离场线
    ex = valid['exit_lower'].dropna()
    if len(ex) > 0:
        ax1.plot(valid['trade_date'].iloc[-len(ex):], ex.values, color=GOLD, 
                 linewidth=0.6, alpha=0.4, label='离场线(前10日低)')
    
    # 红绿分段收盘价
    for i in range(1, len(valid)):
        c = RED if valid['close'].iloc[i] >= valid['close'].iloc[i-1] else GREEN
        ax1.plot(valid['trade_date'].iloc[i-1:i+1],
                 valid['close'].iloc[i-1:i+1], color=c, linewidth=1.0)
    
    # 标记所有突破信号
    s1_breaks = valid[valid['S1_break'] == True]
    if len(s1_breaks) > 0:
        ax1.scatter(s1_breaks['trade_date'], s1_breaks['close'],
                    marker='o', s=30, color=CYAN, alpha=0.4, zorder=5, label='S1突破信号')
    
    # 标记实际交易
    s1_trades = [t for t in trades if t.system == 'S1']
    for t in s1_trades:
        if t.entry_idx >= len(valid) or t.exit_idx >= len(valid):
            continue
        # 入场
        ax1.annotate(f'买\n{t.units}手',
                     (valid['trade_date'].iloc[t.entry_idx], t.entry_price),
                     textcoords='offset points', xytext=(0, 16),
                     fontsize=8, color=RED, ha='center', fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color=RED, lw=0.8, alpha=0.7))
        ax1.scatter(valid['trade_date'].iloc[t.entry_idx], t.entry_price,
                    marker='^', s=120, color=RED, edgecolors='white',
                    linewidths=0.8, zorder=10)
        
        # 离场
        exit_color = RED if t.pnl > 0 else GREEN
        exit_label = f'{t.exit_reason}\n{t.pnl:+.0f}'
        ax1.annotate(exit_label,
                     (valid['trade_date'].iloc[t.exit_idx], t.exit_price),
                     textcoords='offset points', xytext=(0, -22),
                     fontsize=7, color=exit_color, ha='center',
                     arrowprops=dict(arrowstyle='->', color=exit_color, lw=0.6, alpha=0.6))
        ax1.scatter(valid['trade_date'].iloc[t.exit_idx], t.exit_price,
                    marker='v', s=80, color=exit_color, edgecolors='white',
                    linewidths=0.5, zorder=10)
    
    ax1.set_title(f'{name}({code}) 海龟System1 (20日) 交易信号', 
                  fontsize=15, fontweight='bold', color='white', pad=12)
    ax1.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax1.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
    
    # N值
    ax2.fill_between(valid['trade_date'], 0, valid['N'],
                     alpha=0.5, color=GOLD)
    ax2.plot(valid['trade_date'], valid['N'], color=GOLD, linewidth=1.0)
    ax2.set_ylabel('N值', fontsize=10, color=MUTED)
    ax2.grid(True, alpha=0.1, color='white')
    plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
    
    plt.tight_layout()
    f1 = f'{output_prefix}_S1.png'
    plt.savefig(f1, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图1 (S1信号): {f1}")
    
    # ====== 图2: System2 信号 ======
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     sharex=True)
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    ax1.plot(valid['trade_date'], valid['S2_upper'], color=RED, linewidth=0.8, 
             linestyle='--', alpha=0.5, label='S2上轨(前55日高)')
    ax1.plot(valid['trade_date'], valid['S2_lower'], color=GREEN, linewidth=0.8, 
             linestyle='--', alpha=0.5, label='S2下轨(前55日低)')
    if len(ex) > 0:
        ax1.plot(valid['trade_date'].iloc[-len(ex):], ex.values, color=GOLD, 
                 linewidth=0.6, alpha=0.4, label='离场线(前10日低)')
    
    for i in range(1, len(valid)):
        c = RED if valid['close'].iloc[i] >= valid['close'].iloc[i-1] else GREEN
        ax1.plot(valid['trade_date'].iloc[i-1:i+1],
                 valid['close'].iloc[i-1:i+1], color=c, linewidth=1.0)
    
    s2_breaks = valid[valid['S2_break'] == True]
    if len(s2_breaks) > 0:
        ax1.scatter(s2_breaks['trade_date'], s2_breaks['close'],
                    marker='o', s=30, color=CYAN, alpha=0.4, zorder=5, label='S2突破信号')
    
    s2_trades = [t for t in trades if t.system == 'S2']
    for t in s2_trades:
        if t.entry_idx >= len(valid) or t.exit_idx >= len(valid):
            continue
        ax1.annotate(f'买\n{t.units}手',
                     (valid['trade_date'].iloc[t.entry_idx], t.entry_price),
                     textcoords='offset points', xytext=(0, 16),
                     fontsize=8, color=RED, ha='center', fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color=RED, lw=0.8, alpha=0.7))
        ax1.scatter(valid['trade_date'].iloc[t.entry_idx], t.entry_price,
                    marker='^', s=120, color=RED, edgecolors='white',
                    linewidths=0.8, zorder=10)
        
        exit_color = RED if t.pnl > 0 else GREEN
        ax1.annotate(f'{t.exit_reason}\n{t.pnl:+.0f}',
                     (valid['trade_date'].iloc[t.exit_idx], t.exit_price),
                     textcoords='offset points', xytext=(0, -22),
                     fontsize=7, color=exit_color, ha='center',
                     arrowprops=dict(arrowstyle='->', color=exit_color, lw=0.6, alpha=0.6))
        ax1.scatter(valid['trade_date'].iloc[t.exit_idx], t.exit_price,
                    marker='v', s=80, color=exit_color, edgecolors='white',
                    linewidths=0.5, zorder=10)
    
    ax1.set_title(f'{name}({code}) 海龟System2 (55日) 交易信号', 
                  fontsize=15, fontweight='bold', color='white', pad=12)
    ax1.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax1.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
    
    ax2.fill_between(valid['trade_date'], 0, valid['N'], alpha=0.5, color=GOLD)
    ax2.plot(valid['trade_date'], valid['N'], color=GOLD, linewidth=1.0)
    ax2.set_ylabel('N值', fontsize=10, color=MUTED)
    ax2.grid(True, alpha=0.1, color='white')
    plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
    
    plt.tight_layout()
    f2 = f'{output_prefix}_S2.png'
    plt.savefig(f2, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图2 (S2信号): {f2}")
    
    # ====== 图3: 权益曲线 ======
    if trades:
        _plot_equity_curve(trades, df, output_prefix)
    
    return f1, f2

def _plot_equity_curve(trades, df, output_prefix):
    """资金曲线 + 逐笔收益分布"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    # 按出场时间排序, 累计收益
    pts = []
    for t in trades:
        pts.append((t.exit_date, t.pnl))
    pts.sort()
    
    cum = 0
    dates = []
    cum_pnl = []
    for d, p in pts:
        cum += p
        dates.append(d)
        cum_pnl.append(cum)
    
    ax1.fill_between(range(len(dates)), 0, cum_pnl, alpha=0.3, color=GOLD)
    ax1.plot(cum_pnl, color=GOLD, linewidth=1.5)
    ax1.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)
    ax1.set_title('累计盈亏', fontsize=15, fontweight='bold', color='white', pad=10)
    ax1.set_xlabel('交易序号', fontsize=11, color=MUTED)
    ax1.set_ylabel('累计盈亏 (元)', fontsize=11, color=MUTED)
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax1.xaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
    
    # 逐笔收益
    pnl_list = [t.pnl for t in trades]
    colors = [RED if p > 0 else GREEN for p in pnl_list]
    bar_x = range(len(pnl_list))
    ax2.bar(bar_x, pnl_list, color=colors, alpha=0.7, edgecolor=BG, linewidth=0.5)
    ax2.axhline(y=0, color='white', linewidth=0.5)
    ax2.set_title('逐笔交易盈亏', fontsize=15, fontweight='bold', color='white', pad=10)
    ax2.set_xlabel('交易序号', fontsize=11, color=MUTED)
    ax2.set_ylabel('盈亏 (元)', fontsize=11, color=MUTED)
    ax2.grid(True, alpha=0.1, color='white', axis='y')
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax2.xaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
    
    plt.tight_layout()
    f3 = f'{output_prefix}_equity.png'
    plt.savefig(f3, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图3 (资金曲线): {f3}")

# ============================================================
# 统计打印
# ============================================================
def print_trade_summary(trades, account):
    """打印交易汇总"""
    if not trades:
        print("\n=== 无交易信号 ===")
        return
    
    winning = [t for t in trades if t.pnl > 0]
    losing  = [t for t in trades if t.pnl <= 0]
    total_pnl = sum(t.pnl for t in trades)
    
    print("\n" + "=" * 80)
    print("  海龟交易策略 -- 交易明细")
    print("=" * 80)
    print(f"{'系统':<5} {'入场日':<12} {'入场价':>8} {'手数':>5} {'离场日':<12} {'离场价':>8} {'盈亏':>10} {'盈亏%':>7} {'原因':<12}")
    print("-" * 80)
    for t in trades:
        print(f"{t.system:<5} {t.entry_date:<12} {t.entry_price:>7.2f} {t.units:>4}手 "
              f"{t.exit_date:<12} {t.exit_price:>7.2f} {t.pnl:>+9.0f} {t.pnl_pct:>+6.1f}% {t.exit_reason:<12}")
    
    print("-" * 80)
    print(f"\n  交易汇总:")
    print(f"    总交易:    {len(trades)} 笔")
    print(f"    盈利:      {len(winning)} 笔 (胜率 {len(winning)/len(trades)*100:.0f}%)")
    print(f"    亏损:      {len(losing)} 笔")
    print(f"    总盈亏:    {total_pnl:+,.0f} 元")
    print(f"    收益率:    {total_pnl/account*100:+.1f}%")
    if winning:
        print(f"    平均盈利:  {sum(t.pnl for t in winning)/len(winning):,.0f} 元")
        print(f"    最大盈利:  {max(t.pnl for t in winning):,.0f} 元")
    if losing:
        print(f"    平均亏损:  {sum(t.pnl for t in losing)/len(losing):,.0f} 元")
        print(f"    最大亏损:  {min(t.pnl for t in losing):,.0f} 元")
    if winning and losing:
        avg_win = sum(t.pnl for t in winning) / len(winning)
        avg_loss = abs(sum(t.pnl for t in losing) / len(losing))
        print(f"    盈亏比:    {avg_win/avg_loss:.1f}:1" if avg_loss > 0 else "    N/A")
    
    # 分系统
    for sys_key, sys_name in [('S1', 'System1(20日)'), ('S2', 'System2(55日)')]:
        st = [t for t in trades if t.system == sys_key]
        if st:
            sp = sum(t.pnl for t in st)
            sw = [t for t in st if t.pnl > 0]
            print(f"\n  {sys_name}: {len(st)}笔 | 盈亏 {sp:+,.0f} | 胜率 {len(sw)/len(st)*100:.0f}%")
    
    print("=" * 80)

# ============================================================
# 入口
# ============================================================
def load_data(path):
    p = Path(path)
    if p.suffix == '.csv':
        return pd.read_csv(path, parse_dates=['trade_date']).sort_values('trade_date').reset_index(drop=True)
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df.sort_values('trade_date').reset_index(drop=True)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='海龟策略信号生成与回测')
    ap.add_argument('--data', default='smic_daily_data.json')
    ap.add_argument('--account', type=float, default=1_000_000, help='账户资金(元)')
    ap.add_argument('--risk', type=float, default=0.01, help='每笔风险比例')
    ap.add_argument('--code', default='688981')
    ap.add_argument('--name', default='中芯国际')
    ap.add_argument('--output', default='turtle', help='输出前缀')
    ap.add_argument('--export', action='store_true', help='导出交易记录CSV')
    args = ap.parse_args()
    
    # 加载 & 计算指标
    df = load_data(args.data)
    print(f"数据: {len(df)} 条, {df['trade_date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['trade_date'].iloc[-1].strftime('%Y-%m-%d')}")
    df = prep_indicators(df)
    
    # 回测
    trades = simulate_trades(df, account=args.account, risk_per_unit=args.risk)
    print_trade_summary(trades, args.account)
    
    # 导出
    if args.export and trades:
        import csv
        out = f"{args.output}_trades.csv"
        with open(out, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['系统', '入场日', '入场价', '手数', '离场日', '离场价', '盈亏', '盈亏%', '原因'])
            for t in trades:
                w.writerow([t.system, t.entry_date, f'{t.entry_price:.2f}',
                           t.units, t.exit_date, f'{t.exit_price:.2f}',
                           f'{t.pnl:.0f}', f'{t.pnl_pct:.1f}%', t.exit_reason])
        print(f"导出交易记录: {out}")
    
    # 图表
    plot_trades(df, trades, args.code, args.name, args.output)
