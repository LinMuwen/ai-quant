#!/usr/bin/env python3
"""
ATR (Average True Range / 平均真实波幅) 计算与可视化
TR  = Max( H-L, |H-PC|, |L-PC| )
ATR = TR 的 EMA (海龟系统 N 值默认周期=20)
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RED    = '#ef4444'
GREEN  = '#22c55e'
BLUE   = '#3b82f6'
GOLD   = '#f59e0b'
PURPLE = '#a855f7'
BG     = '#0f172a'
GRID   = '#1e293b'
TEXT   = '#cbd5e1'
MUTED  = '#64748b'

# ============================================================
# 计算
# ============================================================
def calc_atr(df, period=20):
    """
    返回 TR/ATR 及相关字段
    
    列:
        tr_raw:  当日真实波幅
        atr:     EMA(tr_raw, period) -- 海龟系统的 N 值
        atr_pct: ATR / close * 100 百分比化
        atr_14:  传统14日ATR (对比用)
    """
    df = df.copy()
    prev_close = df['close'].shift(1)
    df['tr_raw'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - prev_close),
            abs(df['low'] - prev_close)
        )
    )
    # 用 Span 对应 EMA 的平滑系数: alpha = 2/(span+1)
    df['atr'] = df['tr_raw'].ewm(span=period, adjust=False).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    # 传统标准 14 日 ATR
    df['atr_14'] = df['tr_raw'].ewm(span=14, adjust=False).mean()
    return df

def load_data(path):
    p = Path(path)
    if p.suffix == '.csv':
        df = pd.read_csv(path, parse_dates=['trade_date'])
    else:
        with open(path) as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df

# ============================================================
# 图表
# ============================================================
def plot_atr(df, period, code, name, output_prefix):
    valid = df.dropna(subset=['atr']).reset_index(drop=True)
    
    print(f"\nATR 周期: {period} (海龟N值)")
    print(f"有效数据: {len(valid)} 条")
    
    # ====== 图1: 价格 + ATR 通道 ======
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 9),
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     sharex=True)
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    # 上面板: 收盘价 + colse±ATR 通道
    ax1.fill_between(valid['trade_date'],
                     valid['close'] - valid['atr'],
                     valid['close'] + valid['atr'],
                     alpha=0.12, color=BLUE, label=f'{period}日ATR通道')
    ax1.fill_between(valid['trade_date'],
                     valid['close'] - valid['atr'] * 2,
                     valid['close'] + valid['atr'] * 2,
                     alpha=0.05, color=GOLD, label='2×ATR通道')
    
    # 红绿分段价线
    for i in range(1, len(valid)):
        c = RED if valid['close'].iloc[i] >= valid['close'].iloc[i-1] else GREEN
        ax1.plot(valid['trade_date'].iloc[i-1:i+1],
                 valid['close'].iloc[i-1:i+1],
                 color=c, linewidth=1.2)
    
    # 1x ATR 上下界
    ax1.plot(valid['trade_date'], valid['close'] + valid['atr'],
             color=BLUE, linewidth=0.6, alpha=0.4, linestyle='--')
    ax1.plot(valid['trade_date'], valid['close'] - valid['atr'],
             color=BLUE, linewidth=0.6, alpha=0.4, linestyle='--')
    
    ax1.set_title(f'{name}({code}) {period}日ATR (N值) 通道', 
                  fontsize=15, fontweight='bold', color='white', pad=12)
    ax1.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax1.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
    
    # 下面板: ATR 数值走势
    ax2.fill_between(valid['trade_date'], 0, valid['atr'],
                     alpha=0.5, color=GOLD, label=f'ATR({period})')
    ax2.plot(valid['trade_date'], valid['atr'], color=GOLD, linewidth=1.2)
    ax2.plot(valid['trade_date'], valid['atr_14'], color=PURPLE, 
             linewidth=0.8, alpha=0.6, label='ATR(14) 传统')
    
    ax2.axhline(y=valid['atr'].mean(), color='white', linewidth=0.5,
                linestyle='--', alpha=0.3)
    ax2.set_ylabel('ATR (元)', fontsize=11, color=MUTED)
    ax2.set_xlabel('')
    ax2.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax2.grid(True, alpha=0.1, color='white')
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
    
    plt.tight_layout()
    f1 = f'{output_prefix}_atr{period}_full.png'
    plt.savefig(f1, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图1: {f1}")
    
    # ====== 图2: 近90日放大 ======
    recent = valid.tail(90).reset_index(drop=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8),
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     sharex=True)
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    ax1.fill_between(recent['trade_date'],
                     recent['close'] - recent['atr'],
                     recent['close'] + recent['atr'],
                     alpha=0.15, color=BLUE)
    ax1.fill_between(recent['trade_date'],
                     recent['close'] - recent['atr'] * 2,
                     recent['close'] + recent['atr'] * 2,
                     alpha=0.06, color=GOLD)
    
    for i in range(1, len(recent)):
        c = RED if recent['close'].iloc[i] >= recent['close'].iloc[i-1] else GREEN
        ax1.plot(recent['trade_date'].iloc[i-1:i+1],
                 recent['close'].iloc[i-1:i+1], color=c, linewidth=1.5)
    
    ax1.plot(recent['trade_date'], recent['close'] + recent['atr'],
             color=BLUE, linewidth=0.6, alpha=0.4, linestyle='--')
    ax1.plot(recent['trade_date'], recent['close'] - recent['atr'],
             color=BLUE, linewidth=0.6, alpha=0.4, linestyle='--')
    
    ax1.set_title(f'近90日 ATR({period}) 细节', 
                  fontsize=15, fontweight='bold', color='white', pad=12)
    ax1.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax1.yaxis.get_ticklabels(), color=MUTED)
    
    # 标注海龟止损示例
    last = recent.iloc[-1]
    ax1.axhline(y=last['close'] - last['atr'] * 2, color=RED, linewidth=0.8, 
                linestyle='--', alpha=0.6)
    ax1.text(recent['trade_date'].iloc[-1],
             last['close'] - last['atr'] * 2,
             f'  止损线 2N={last["atr"]*2:.1f}', 
             fontsize=9, color=RED, va='center')
    
    ax2.fill_between(recent['trade_date'], 0, recent['atr'],
                     alpha=0.5, color=GOLD)
    ax2.plot(recent['trade_date'], recent['atr'], color=GOLD, linewidth=1.5)
    ax2.axhline(y=recent['atr'].mean(), color='white', linewidth=0.5,
                linestyle='--', alpha=0.3)
    ax2.set_ylabel('ATR', fontsize=11, color=MUTED)
    ax2.grid(True, alpha=0.1, color='white')
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax2.yaxis.get_ticklabels(), color=MUTED)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=10))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
    
    # 图例标注
    fig.text(0.98, 0.01,
             '蓝色=1×ATR通道  金色=2×ATR通道  N值=20日EMA(TR)  ←止损例:入场价-2N  ≤该价必走',
             ha='right', fontsize=8, color=MUTED, style='italic')
    
    plt.tight_layout()
    f2 = f'{output_prefix}_atr{period}_recent.png'
    plt.savefig(f2, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图2: {f2}")
    
    # ====== 图3: TR 原始值分布 ======
    fig, ax = plt.subplots(figsize=(16, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    
    tr_vals = valid['tr_raw'].dropna()
    ax.hist(tr_vals, bins=40, color=GOLD, alpha=0.7, edgecolor=BG, linewidth=0.5)
    ax.axvline(x=tr_vals.mean(), color='white', linewidth=0.8, linestyle='--',
               label=f'均值={tr_vals.mean():.2f}')
    ax.axvline(x=tr_vals.median(), color=RED, linewidth=0.8, linestyle='--',
               label=f'中位={tr_vals.median():.2f}')
    
    ax.set_title(f'TR (真实波幅) 分布直方图 | 均值={tr_vals.mean():.2f} P50={tr_vals.median():.2f} P95={tr_vals.quantile(0.95):.2f}',
                 fontsize=13, color='white', pad=10)
    ax.set_xlabel('TR (元)', fontsize=11, color=MUTED)
    ax.set_ylabel('频次', fontsize=11, color=MUTED)
    ax.legend(fontsize=9, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax.grid(True, alpha=0.1, color='white', axis='y')
    plt.setp(ax.xaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f3 = f'{output_prefix}_atr{period}_hist.png'
    plt.savefig(f3, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图3: {f3}")

# ============================================================
# 统计
# ============================================================
def print_stats(df, period):
    valid = df.dropna(subset=['atr'])
    latest = valid.iloc[-1]
    
    # 海龟头寸计算示例
    account = 1_000_000  # 假设100万账户
    unit_risk = account * 0.01       # 每笔风险 1%
    atr_n = latest['atr']
    shares = int(unit_risk / (atr_n * 2) / 100) * 100  # 手 (100股/手)
    stop_price = latest['close'] - atr_n * 2
    
    print("\n" + "=" * 60)
    print(f"  ATR / N值 ({period}日EMA) 统计 -- 海龟风控示例")
    print("=" * 60)
    print(f"  最新日期:  {latest['trade_date'].strftime('%Y-%m-%d')}")
    print(f"  最新收盘:  {latest['close']:.2f} 元")
    print(f"  {period}日ATR(N值): {atr_n:.2f} 元 (波动率 {latest['atr_pct']:.1f}%)")
    print(f"  14日ATR(传统): {latest['atr_14']:.2f} 元")
    print(f"  2×N:       {atr_n*2:.2f} 元")
    print(f"  0.5×N:     {atr_n*0.5:.2f} 元 (加仓步距)")
    print()
    print(f"  --- 海龟仓位计算 (假设账户 {account:,.0f} 元) ---")
    print(f"  单笔风险(1%):     {unit_risk:,.0f} 元")
    print(f"  每单位股数:       {shares} 股 ({shares//100} 手)")
    print(f"  满仓(4单位):      {shares*4} 股 约 {shares*4*latest['close']:,.0f} 元")
    print(f"  海龟止损价(2N):   {stop_price:.2f} 元 (从{latest['close']:.2f}需跌{atr_n*2:.2f})")
    print()
    print(f"  ATR 统计:")
    print(f"    均值:   {valid['atr'].mean():.2f}")
    print(f"    最大:   {valid['atr'].max():.2f}")
    print(f"    最小:   {valid['atr'].min():.2f}")
    print(f"    P25:    {valid['atr'].quantile(0.25):.2f}")
    print(f"    P75:    {valid['atr'].quantile(0.75):.2f}")
    print(f"  TR 统计 (原始波幅):")
    print(f"    均值:   {valid['tr_raw'].mean():.2f}")
    print(f"    最大:   {valid['tr_raw'].max():.2f} ({valid.loc[valid['tr_raw'].idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")
    print(f"    P95:    {valid['tr_raw'].quantile(0.95):.2f}")
    print("=" * 60)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--data', default='smic_daily_data.json')
    p.add_argument('--period', type=int, default=20, help='ATR周期 (海龟默认20)')
    p.add_argument('--code', default='688981')
    p.add_argument('--name', default='中芯国际')
    p.add_argument('--output', default='atr', help='输出前缀')
    p.add_argument('--export', action='store_true')
    args = p.parse_args()
    
    df = load_data(args.data)
    df = calc_atr(df, period=args.period)
    
    if args.export:
        out = f"{args.output}_p{args.period}.csv"
        cols = ['trade_date', 'open', 'high', 'low', 'close', 'tr_raw', 'atr', 'atr_pct', 'atr_14']
        df[cols].to_csv(out, index=False)
        print(f"导出: {out}")
    
    print_stats(df, args.period)
    plot_atr(df, args.period, args.code, args.name, args.output)
    
    print(f"\n完成! {args.output}_atr{args.period}_*.png")
