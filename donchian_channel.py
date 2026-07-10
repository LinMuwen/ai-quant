#!/usr/bin/env python3
"""
唐奇安通道 (Donchian Channel) 计算与可视化
高低价格通道：上轨 = N日最高价，下轨 = N日最低价，中轨 = (上轨+下轨)/2
支持 System 1 (N=20) 和 System 2 (N=55) 两种周期
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
import argparse
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 配色 (中国股市惯例: 涨红跌绿, 暗色背景)
# ============================================================
RED    = '#ef4444'
GREEN  = '#22c55e'
BLUE   = '#3b82f6'
GOLD   = '#f59e0b'
BG     = '#0f172a'
GRID   = '#1e293b'
TEXT   = '#cbd5e1'
MUTED  = '#64748b'

# ============================================================
# 核心计算
# ============================================================
def calc_donchian(df, period=20):
    """
    计算唐奇安通道
    
    参数:
        df: DataFrame, 需含 'high'、'low'、'close' 列
        period: 通道周期 (默认20)
    
    返回:
        DataFrame, 新增列:
            dc_upper:  上轨 = 过去N日最高价
            dc_lower:  下轨 = 过去N日最低价  
            dc_mid:    中轨 = (上轨+下轨)/2
            dc_width:  通道宽度 = 上轨-下轨
            dc_width_pct: 通道宽度百分比 = (上轨-下轨)/中轨*100
    """
    df = df.copy()
    df['dc_upper'] = df['high'].rolling(period).max()
    df['dc_lower'] = df['low'].rolling(period).min()
    df['dc_mid']   = (df['dc_upper'] + df['dc_lower']) / 2
    df['dc_width'] = df['dc_upper'] - df['dc_lower']
    df['dc_width_pct'] = df['dc_width'] / df['dc_mid'] * 100
    return df

def detect_breakouts(df):
    """
    检测通道突破信号
    
    向上突破: 收盘价 > 上轨 (且前一日未突破，避免重复信号)
    向下突破: 收盘价 < 下轨 (同上)
    回归通道: 前一日突破但当日回到通道内
    """
    n = len(df)
    df = df.copy()
    df['breakout_up']   = False
    df['breakout_down'] = False
    
    for i in range(1, n):
        if pd.isna(df['dc_upper'].iloc[i]):
            continue
        # 向上突破
        if (df['close'].iloc[i] > df['dc_upper'].iloc[i] and 
            df['close'].iloc[i-1] <= df['dc_upper'].iloc[i-1]):
            df.loc[df.index[i], 'breakout_up'] = True
        # 向下突破
        if (df['close'].iloc[i] < df['dc_lower'].iloc[i] and 
            df['close'].iloc[i-1] >= df['dc_lower'].iloc[i-1]):
            df.loc[df.index[i], 'breakout_down'] = True
    
    return df

# ============================================================
# 数据加载
# ============================================================
def load_data(path):
    """支持 CSV 和 JSON"""
    p = Path(path)
    if p.suffix == '.csv':
        df = pd.read_csv(path, parse_dates=['trade_date'])
    elif p.suffix == '.json':
        with open(path) as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    else:
        raise ValueError(f"不支持的文件格式: {p.suffix}")
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df

# ============================================================
# 图表绘制
# ============================================================
def plot_donchian(df, period, code, name, output_prefix):
    """生成通道全景图 + 近期放大图"""
    valid = df.dropna(subset=['dc_upper']).reset_index(drop=True)
    breakouts_up   = valid[valid['breakout_up']]
    breakouts_down = valid[valid['breakout_down']]
    
    print(f"通道周期: {period}日")
    print(f"有效数据: {len(valid)} 条")
    print(f"向上突破信号: {len(breakouts_up)} 次")
    print(f"向下突破信号: {len(breakouts_down)} 次")
    
    # ====== 图1: 完整全景图 ======
    fig, ax = plt.subplots(figsize=(18, 8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    
    # 通道填充
    ax.fill_between(valid['trade_date'], valid['dc_upper'], valid['dc_lower'],
                    alpha=0.08, color=BLUE, label=f'{period}日通道')
    
    # 上下轨
    ax.plot(valid['trade_date'], valid['dc_upper'], color=RED, 
            linewidth=1.0, linestyle='--', alpha=0.7, label=f'上轨({period}日最高)')
    ax.plot(valid['trade_date'], valid['dc_lower'], color=GREEN, 
            linewidth=1.0, linestyle='--', alpha=0.7, label=f'下轨({period}日最低)')
    ax.plot(valid['trade_date'], valid['dc_mid'], color=GOLD, 
            linewidth=0.8, alpha=0.4, label='中轨')
    
    # 收盘价
    ax.plot(valid['trade_date'], valid['close'], color=TEXT, 
            linewidth=1.2, alpha=0.85, label='收盘价')
    
    # 向上突破标记
    if len(breakouts_up) > 0:
        ax.scatter(breakouts_up['trade_date'], breakouts_up['close'], 
                   marker='^', s=80, color=RED, edgecolors='white', 
                   linewidths=0.5, zorder=10, label=f'向上突破({len(breakouts_up)}次)')
    
    # 向下突破标记
    if len(breakouts_down) > 0:
        ax.scatter(breakouts_down['trade_date'], breakouts_down['close'], 
                   marker='v', s=80, color=GREEN, edgecolors='white', 
                   linewidths=0.5, zorder=10, label=f'向下突破({len(breakouts_down)}次)')
    
    ax.set_title(f'{name}({code}) 唐奇安通道 — {period}日周期', 
                 fontsize=16, fontweight='bold', color='white', pad=15)
    ax.legend(loc='upper left', fontsize=9, facecolor=BG, edgecolor=GRID, 
              labelcolor=TEXT, ncol=2)
    ax.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8, color=MUTED)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
    ax.grid(True, alpha=0.12, color='white')
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    
    # 标注百分比位置
    last_idx = len(valid) - 1
    last_date = valid['trade_date'].iloc[last_idx]
    for label, val, color, offset in [
        ('上轨', valid['dc_upper'].iloc[last_idx], RED, +1.0),
        ('中轨', valid['dc_mid'].iloc[last_idx], GOLD, 0),
        ('下轨', valid['dc_lower'].iloc[last_idx], GREEN, -1.5),
    ]:
        ax.annotate(f'{label} {val:.2f}', xy=(last_date, val),
                    xytext=(15, offset*6), textcoords='offset points',
                    fontsize=9, color=color, va='center', fontweight='bold')
    
    plt.tight_layout()
    f1 = f'{output_prefix}_full.png'
    plt.savefig(f1, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图1: {f1}")
    
    # ====== 图2: 近期90天放大图 ======
    recent = valid.tail(90).reset_index(drop=True)
    
    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    
    ax.fill_between(recent['trade_date'], recent['dc_upper'], recent['dc_lower'],
                    alpha=0.10, color=BLUE)
    ax.plot(recent['trade_date'], recent['dc_upper'], color=RED, 
            linewidth=1.2, linestyle='--', alpha=0.8)
    ax.plot(recent['trade_date'], recent['dc_lower'], color=GREEN, 
            linewidth=1.2, linestyle='--', alpha=0.8)
    ax.plot(recent['trade_date'], recent['dc_mid'], color=GOLD, 
            linewidth=0.8, alpha=0.4)
    ax.plot(recent['trade_date'], recent['close'], color=TEXT, 
            linewidth=1.8, alpha=0.9, label='收盘价')
    
    # 填充价格上涨/下跌区域
    for i in range(1, len(recent)):
        if recent['close'].iloc[i] >= recent['close'].iloc[i-1]:
            color = RED
        else:
            color = GREEN
        ax.plot(recent['trade_date'].iloc[i-1:i+1], 
                recent['close'].iloc[i-1:i+1], 
                color=color, linewidth=1.8)
    
    # 近90天突破
    r_up = recent[recent['breakout_up']]
    r_down = recent[recent['breakout_down']]
    if len(r_up) > 0:
        ax.scatter(r_up['trade_date'], r_up['close'], marker='^', s=120, 
                   color=RED, edgecolors='white', linewidths=0.8, zorder=10)
    if len(r_down) > 0:
        ax.scatter(r_down['trade_date'], r_down['close'], marker='v', s=120, 
                   color=GREEN, edgecolors='white', linewidths=0.8, zorder=10)
    
    # 标注最后一次突破信号
    if len(r_up) > 0:
        last_up = r_up.iloc[-1]
        ax.annotate(f'突破上轨\n{last_up["close"]:.2f}', 
                    (last_up['trade_date'], last_up['close']),
                    textcoords='offset points', xytext=(8, 16),
                    fontsize=9, color=RED, ha='center', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=RED, lw=0.8))
    if len(r_down) > 0:
        last_down = r_down.iloc[-1]
        ax.annotate(f'跌破下轨\n{last_down["close"]:.2f}', 
                    (last_down['trade_date'], last_down['close']),
                    textcoords='offset points', xytext=(8, -20),
                    fontsize=9, color=GREEN, ha='center', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=GREEN, lw=0.8))
    
    ax.set_title(f'{name}({code}) 近90日唐奇安通道 ({period}日周期)', 
                 fontsize=16, fontweight='bold', color='white', pad=15)
    ax.legend(loc='upper left', fontsize=10, facecolor=BG, edgecolor=GRID, 
              labelcolor=TEXT)
    ax.set_ylabel('价格 (元)', fontsize=11, color=MUTED)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9, color=MUTED)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
    ax.grid(True, alpha=0.12, color='white')
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    
    # 图例
    fig.text(0.99, 0.02, 
             f'▲ 突破上轨(做多信号)  ▼ 跌破下轨(做空信号)  --上轨 --下轨  涨红跌绿',
             ha='right', fontsize=9, color=MUTED, style='italic')
    
    plt.tight_layout()
    f2 = f'{output_prefix}_recent.png'
    plt.savefig(f2, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图2: {f2}")
    
    # ====== 图3: 通道宽度变化 ======
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 8), 
                                    gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)
    ax2.set_facecolor(BG)
    
    ax1.plot(valid['trade_date'], valid['close'], color=TEXT, linewidth=0.8, alpha=0.6)
    ax1.plot(valid['trade_date'], valid['dc_upper'], color=RED, linewidth=0.8, alpha=0.6)
    ax1.plot(valid['trade_date'], valid['dc_lower'], color=GREEN, linewidth=0.8, alpha=0.6)
    ax1.set_title(f'通道宽度分析: 波动率越宽通道越开', 
                  fontsize=14, fontweight='bold', color='white', pad=10)
    ax1.set_ylabel('价格 (元)', fontsize=10, color=MUTED)
    
    # 通道宽度百分比 (子图2)
    ax2.fill_between(valid['trade_date'], 0, valid['dc_width_pct'], 
                     alpha=0.4, color=GOLD)
    ax2.plot(valid['trade_date'], valid['dc_width_pct'], color=GOLD, linewidth=0.8)
    ax2.axhline(y=valid['dc_width_pct'].mean(), color='white', linewidth=0.5, 
                linestyle='--', alpha=0.4)
    ax2.set_ylabel('宽度%', fontsize=10, color=MUTED)
    ax2.text(valid['trade_date'].iloc[-1], valid['dc_width_pct'].mean(),
             f' 均值 {valid["dc_width_pct"].mean():.1f}%', 
             fontsize=8, color='white', alpha=0.5, va='center')
    
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7, color=MUTED)
        plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
        ax.grid(True, alpha=0.1, color='white')
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f3 = f'{output_prefix}_width.png'
    plt.savefig(f3, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"图3: {f3}")

# ============================================================
# 统计输出
# ============================================================
def print_stats(df, period):
    """输出通道统计摘要"""
    valid = df.dropna(subset=['dc_upper'])
    latest = valid.iloc[-1]
    
    print("\n" + "=" * 60)
    print(f"  唐奇安通道 ({period}日周期) 统计摘要")
    print("=" * 60)
    print(f"  最新日期:    {latest['trade_date'].strftime('%Y-%m-%d')}")
    print(f"  最新收盘:    {latest['close']:.2f}")
    print(f"  上轨 (最高): {latest['dc_upper']:.2f}")
    print(f"  下轨 (最低): {latest['dc_lower']:.2f}")
    print(f"  中轨:        {latest['dc_mid']:.2f}")
    print(f"  通道宽度:    {latest['dc_width']:.2f} ({latest['dc_width_pct']:.1f}%)")
    print(f"  价格位置:    距上轨 {(latest['dc_upper']-latest['close']):.2f} | 距下轨 {(latest['close']-latest['dc_lower']):.2f}")
    
    pct_in_channel = ((latest['close'] - latest['dc_lower']) / 
                      max(latest['dc_upper'] - latest['dc_lower'], 0.001) * 100)
    print(f"  通道内位置:  {pct_in_channel:.0f}% (0%=下轨, 100%=上轨)")
    
    breakups = valid['breakout_up'].sum()
    breakdowns = valid['breakout_down'].sum()
    print(f"\n  向上突破:    {breakups} 次")
    print(f"  向下突破:    {breakdowns} 次")
    print(f"  通道宽度均值: {valid['dc_width_pct'].mean():.1f}%")
    print(f"  通道宽度最大: {valid['dc_width_pct'].max():.1f}%")
    print(f"  通道宽度最小: {valid['dc_width_pct'].min():.1f}%")
    print("=" * 60)

# ============================================================
# 入口
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='唐奇安通道计算与可视化')
    parser.add_argument('--data', default='smic_daily_data.json', 
                        help='数据文件路径 (CSV或JSON)')
    parser.add_argument('--period', type=int, default=20, 
                        help='通道周期 (默认20, 海龟System2可用55)')
    parser.add_argument('--code', default='688981', help='股票代码')
    parser.add_argument('--name', default='中芯国际', help='股票名称')
    parser.add_argument('--output', default='donchian', help='输出文件前缀')
    parser.add_argument('--export', action='store_true', help='导出计算结果CSV')
    args = parser.parse_args()
    
    # 加载
    df = load_data(args.data)
    print(f"加载数据: {len(df)} 条, {df['trade_date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['trade_date'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # 计算
    df = calc_donchian(df, period=args.period)
    df = detect_breakouts(df)
    
    # 导出
    if args.export:
        out_csv = f"{args.output}_p{args.period}.csv"
        df.to_csv(out_csv, index=False)
        print(f"计算结果已导出: {out_csv}")
    
    # 统计
    print_stats(df, args.period)
    
    # 图表
    plot_donchian(df, args.period, args.code, args.name, 
                  f"{args.output}_p{args.period}")
    
    print(f"\n完成! 输出文件: {args.output}_p{args.period}_*.png")
