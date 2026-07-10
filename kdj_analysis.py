"""
KDJ 指标介绍、计算与可视化
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
    'axes.unicode_minus': False,
    'figure.dpi': 120, 'savefig.dpi': 150,
    'savefig.bbox': 'tight', 'savefig.facecolor': '#1a1a2e',
})
RED, GREEN = '#ef4444', '#22c55e'
BG, FG, MUTED = '#1a1a2e', '#e0e0e0', '#888888'

# ============================================================
# 1. 数据加载
# ============================================================
a = pd.read_csv(r'.\smic_a_share.csv')
a['trade_date'] = pd.to_datetime(a['trade_date'], format='%Y%m%d')
a.sort_values('trade_date', inplace=True); a.reset_index(drop=True, inplace=True)

hk = pd.read_csv(r'.\smic_hk_share.csv')
hk['trade_date'] = pd.to_datetime(hk['trade_date'], format='%Y%m%d')
hk = hk[hk['trade_date'] >= pd.Timestamp('2025-07-01')]
hk.sort_values('trade_date', inplace=True); hk.reset_index(drop=True, inplace=True)

# ============================================================
# 2. KDJ 计算函数
# ============================================================
def compute_kdj(df, n=9, m1=3, m2=3):
    """KDJ(9,3,3): 标准算法"""
    low_n = df['low'].rolling(n).min()
    high_n = df['high'].rolling(n).max()
    rsv = (df['close'] - low_n) / (high_n - low_n) * 100

    k = np.full(len(df), 50.0)
    d = np.full(len(df), 50.0)
    for i in range(n, len(df)):
        k[i] = 2/3 * k[i-1] + 1/3 * rsv.iloc[i]
        d[i] = 2/3 * d[i-1] + 1/3 * k[i]
    j = 3 * k - 2 * d

    # 前 n-1 天无有效值
    k[:n] = np.nan; d[:n] = np.nan; j[:n] = np.nan
    return k, d, j

# ============================================================
# 3. 计算
# ============================================================
a['k'], a['d'], a['j'] = compute_kdj(a)
hk['k'], hk['d'], hk['j'] = compute_kdj(hk)

# ============================================================
# 4. 打印结果
# ============================================================
def kdj_summary(df, name, code):
    last = df.iloc[-1]
    kdj = df[['k','d','j']].dropna()
    k, d, j = last['k'], last['d'], last['j']
    k_sig = '超买' if k > 80 else ('超卖' if k < 20 else '中性')
    if k > d and last['j'] > last['d']: x_sig = '多头 (K>D)'
    elif k < d: x_sig = '空头 (K<D)'
    else: x_sig = '交叉点'

    # 金叉死叉检测
    golden = ((df['k'] > df['d']) & (df['k'].shift(1) <= df['d'].shift(1))).sum()
    death = ((df['k'] < df['d']) & (df['k'].shift(1) >= df['d'].shift(1))).sum()

    print(f'\n---- {name} ({code}) ----')
    print(f'最新: {last["trade_date"].date()}  收盘 {last["close"]:.2f}')
    print()
    print(f'[KDJ(9,3,3)]')
    print(f'  K={k:.2f}  D={d:.2f}  J={j:.2f}')
    print(f'  信号: {k_sig} / {x_sig}')
    print(f'  区间 K:[{kdj["k"].min():.1f}, {kdj["k"].max():.1f}]  J:[{kdj["j"].min():.1f}, {kdj["j"].max():.1f}]')
    print(f'  超买(K>80): {(kdj["k"]>80).sum()}天  超卖(K<20): {(kdj["k"]<20).sum()}天')
    print(f'  金叉: {int(golden)}次  死叉: {int(death)}次')
    # J 值极端
    j_ext_h = (kdj['j'] > 100).sum(); j_ext_l = (kdj['j'] < 0).sum()
    if j_ext_h or j_ext_l:
        print(f'  J值超界: >100 {j_ext_h}天  <0 {j_ext_l}天')

kdj_summary(a, 'A股', '688981.SH')
kdj_summary(hk, '港股', '00981.HK')

# ============================================================
# 5. 可视化
# ============================================================
def plot_kdj(df, title, filename, lookback=None):
    if lookback: d = df.tail(lookback).copy().reset_index(drop=True)
    else: d = df.copy().reset_index(drop=True)
    dates = d['trade_date'].to_numpy()

    # 涨跌颜色
    up = d['close'] >= d['open']

    fig, axes = plt.subplots(3, 1, figsize=(18, 11),
                             gridspec_kw={'height_ratios': [2, 1.5, 1.5]},
                             facecolor=BG)
    fig.suptitle(title + '  -- KDJ(9,3,3)', fontsize=14, fontweight='bold', color=FG, y=0.985)

    # ---- Panel 1: K线 ----
    ax1 = axes[0]
    ax1.set_facecolor(BG)
    for s in ax1.spines.values(): s.set_color('#333')
    ax1.tick_params(colors=MUTED, labelsize=9)
    for i in range(len(d)):
        o, c, h, l = d['open'].iloc[i], d['close'].iloc[i], d['high'].iloc[i], d['low'].iloc[i]
        color = RED if c >= o else GREEN
        ax1.plot([dates[i], dates[i]], [l, h], color=color, linewidth=0.8)
        ax1.bar(dates[i], abs(c-o), bottom=min(o,c), color=color, width=0.6, alpha=0.9)
    ax1.set_ylabel('Price', color=FG, fontsize=10)
    ax1.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 2: KDJ 线 ----
    ax2 = axes[1]
    ax2.set_facecolor(BG)
    for s in ax2.spines.values(): s.set_color('#333')
    ax2.tick_params(colors=MUTED, labelsize=9)
    ax2.plot(dates, d['k'], color='#f5f5f5', linewidth=1.0, label='K', alpha=0.95)
    ax2.plot(dates, d['d'], color='#fbbf24', linewidth=0.9, label='D', alpha=0.85)
    ax2.plot(dates, d['j'], color='#a78bfa', linewidth=0.8, label='J', alpha=0.75)
    # 超买超卖区
    ax2.axhline(80, color=RED, linewidth=0.6, linestyle='--', alpha=0.4)
    ax2.axhline(20, color=GREEN, linewidth=0.6, linestyle='--', alpha=0.4)
    ax2.axhline(50, color='#555', linewidth=0.3, linestyle='--', alpha=0.2)
    ax2.fill_between(dates, 80, 100, alpha=0.06, color=RED)
    ax2.fill_between(dates, 0, 20, alpha=0.06, color=GREEN)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel('KDJ', color=FG, fontsize=10)
    ax2.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor='#444', labelcolor=FG)
    ax2.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 3: J 值分布 (辅助判断极端区域) ----
    ax3 = axes[2]
    ax3.set_facecolor(BG)
    for s in ax3.spines.values(): s.set_color('#333')
    ax3.tick_params(colors=MUTED, labelsize=9)
    j_colors = []
    for v in d['j']:
        if pd.isna(v): j_colors.append(MUTED)
        elif v > 100: j_colors.append(RED)
        elif v < 0: j_colors.append(GREEN)
        else: j_colors.append('#a78bfa')
    ax3.bar(dates, d['j'], color=j_colors, width=0.6, alpha=0.8)
    ax3.axhline(100, color=RED, linewidth=0.6, linestyle='--', alpha=0.5)
    ax3.axhline(0, color=GREEN, linewidth=0.6, linestyle='--', alpha=0.5)
    ax3.set_ylabel('J (3K-2D)', color=FG, fontsize=10)
    ax3.set_xlabel('Date', color=FG, fontsize=10)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=0, ha='center')
    ax3.grid(axis='y', alpha=0.08, color='white')

    for ax in axes[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.05, top=0.96)
    fig.savefig(filename, facecolor=BG)
    plt.close(fig)
    print(f'  Chart saved: {filename}')

plot_kdj(a, 'SMIC A-share (688981.SH)', 'smic_a_kdj.png')
plot_kdj(hk, 'SMIC HK (00981.HK)', 'smic_hk_kdj.png', lookback=250)

print('\nDone.')
