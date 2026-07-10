"""
中芯国际 A股 + 港股 技术指标计算与可视化
指标: RSI(14), MACD(12/26/9), 布林带(20, 2sigma)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# 全局样式
plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
    'axes.unicode_minus': False,
    'figure.dpi': 120,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.facecolor': '#1a1a2e',
})
RED, GREEN = '#ef4444', '#22c55e'
BG, FG, MUTED = '#1a1a2e', '#e0e0e0', '#888888'

# ============================================================
# 1. 加载数据
# ============================================================
a = pd.read_csv(r".\smic_a_share.csv")
hk = pd.read_csv(r".\smic_hk_share.csv")

for df in [a, hk]:
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df.sort_values("trade_date", inplace=True)
    df.reset_index(drop=True, inplace=True)

# ============================================================
# 2. 指标计算
# ============================================================
def compute_rsi(close, period=14):
    """Wilder's RSI"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_macd(close, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = 2 * (dif - dea)
    return dif, dea, hist

def compute_bollinger(close, period=20, num_std=2):
    """Bollinger Bands"""
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    width = (upper - lower) / ma * 100
    return ma, upper, lower, width

def add_indicators(df):
    df["rsi"] = compute_rsi(df["close"])
    df["dif"], df["dea"], df["macd_hist"] = compute_macd(df["close"])
    df["bb_ma"], df["bb_upper"], df["bb_lower"], df["bb_width"] = compute_bollinger(df["close"])
    return df

a = add_indicators(a)
hk = add_indicators(hk)

# ============================================================
# 3. 可视化
# ============================================================

def plot_dashboard(df, title, filename, lookback=None):
    if lookback:
        d = df.tail(lookback).copy().reset_index(drop=True)
    else:
        d = df.copy().reset_index(drop=True)
    dates = d["trade_date"].to_numpy()
    close = d["close"].to_numpy()
    vol = d["vol"].to_numpy()
    # 涨跌颜色
    up = d["close"] >= d["open"]

    fig, axes = plt.subplots(5, 1, figsize=(18, 14),
                             gridspec_kw={'height_ratios': [2.5, 1, 1.2, 1.2, 1.2]},
                             facecolor=BG)
    fig.suptitle(title, fontsize=16, fontweight='bold', color=FG, y=0.985)

    # ---- Panel 1: K线 + 布林带 ----
    ax1 = axes[0]
    ax1.set_facecolor(BG)
    ax1.tick_params(colors=MUTED, labelsize=9)
    ax1.spines[:].set_color('#333')
    # 布林带填充
    ax1.fill_between(dates, d["bb_upper"], d["bb_lower"], alpha=0.10, color='#60a5fa')
    ax1.plot(dates, d["bb_upper"], color='#60a5fa', linewidth=0.7, linestyle='--', alpha=0.6, label='BB Upper')
    ax1.plot(dates, d["bb_ma"], color='#fbbf24', linewidth=1.0, alpha=0.8, label='BB Mid(MA20)')
    ax1.plot(dates, d["bb_lower"], color='#60a5fa', linewidth=0.7, linestyle='--', alpha=0.6, label='BB Lower')
    # K线实体
    for i in range(len(d)):
        o, c, h, l = d["open"].iloc[i], d["close"].iloc[i], d["high"].iloc[i], d["low"].iloc[i]
        color = RED if c >= o else GREEN
        body_bottom = min(o, c)
        body_top = max(o, c)
        ax1.plot([dates[i], dates[i]], [l, h], color=color, linewidth=0.8)
        ax1.bar(dates[i], body_top - body_bottom, bottom=body_bottom, color=color, width=0.6, alpha=0.9)
    ax1.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor='#444', labelcolor=FG)
    ax1.set_ylabel('Price', color=FG, fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax1.tick_params(axis='x', rotation=0)
    ax1.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 2: 成交量 + 量均线 ----
    ax2 = axes[1]
    ax2.set_facecolor(BG)
    ax2.tick_params(colors=MUTED, labelsize=9)
    ax2.spines[:].set_color('#333')
    vol_colors = [RED if up.iloc[i] else GREEN for i in range(len(d))]
    ax2.bar(dates, vol, color=vol_colors, width=0.6, alpha=0.8)
    vol_ma = pd.Series(vol).rolling(5).mean().to_numpy()
    ax2.plot(dates, vol_ma, color='#fbbf24', linewidth=0.8, alpha=0.7, label='Vol MA5')
    ax2.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor='#444', labelcolor=FG)
    ax2.set_ylabel('Volume', color=FG, fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax2.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 3: MACD ----
    ax3 = axes[2]
    ax3.set_facecolor(BG)
    ax3.tick_params(colors=MUTED, labelsize=9)
    ax3.spines[:].set_color('#333')
    macd_colors = [RED if d["macd_hist"].iloc[i] >= 0 else GREEN for i in range(len(d))]
    ax3.bar(dates, d["macd_hist"], color=macd_colors, width=0.6, alpha=0.7)
    ax3.plot(dates, d["dif"], color='#f5f5f5', linewidth=0.9, label='DIF', alpha=0.9)
    ax3.plot(dates, d["dea"], color='#fbbf24', linewidth=0.8, label='DEA', alpha=0.8)
    ax3.axhline(0, color='#555', linewidth=0.5)
    ax3.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor='#444', labelcolor=FG)
    ax3.set_ylabel('MACD', color=FG, fontsize=10)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax3.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 4: RSI ----
    ax4 = axes[3]
    ax4.set_facecolor(BG)
    ax4.tick_params(colors=MUTED, labelsize=9)
    ax4.spines[:].set_color('#333')
    ax4.plot(dates, d["rsi"], color='#a78bfa', linewidth=1.0, alpha=0.9)
    ax4.axhline(70, color='#ef4444', linewidth=0.6, linestyle='--', alpha=0.5)
    ax4.axhline(30, color='#22c55e', linewidth=0.6, linestyle='--', alpha=0.5)
    ax4.axhline(50, color='#555', linewidth=0.4, linestyle='--', alpha=0.3)
    ax4.fill_between(dates, 70, d["rsi"], where=(d["rsi"]>=70), color=RED, alpha=0.12)
    ax4.fill_between(dates, 30, d["rsi"], where=(d["rsi"]<=30), color=GREEN, alpha=0.12)
    ax4.set_ylim(0, 100)
    ax4.set_ylabel('RSI(14)', color=FG, fontsize=10)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax4.grid(axis='y', alpha=0.08, color='white')

    # ---- Panel 5: 布林带宽度 ----
    ax5 = axes[4]
    ax5.set_facecolor(BG)
    ax5.tick_params(colors=MUTED, labelsize=9)
    ax5.spines[:].set_color('#333')
    ax5.fill_between(dates, d["bb_width"], 0, color='#60a5fa', alpha=0.25)
    ax5.plot(dates, d["bb_width"], color='#93c5fd', linewidth=0.9, alpha=0.9)
    ax5.set_ylabel('BB Width%', color=FG, fontsize=10)
    ax5.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=0, ha='center')
    ax5.grid(axis='y', alpha=0.08, color='white')
    ax5.set_xlabel('Date', color=FG, fontsize=10)

    # 全图 x 轴联动
    for ax in axes[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.05, top=0.96)
    fig.savefig(filename, facecolor=BG)
    plt.close(fig)
    print(f"  → 已保存: {filename}")

# 港股用近一年 (640天太多)
plot_dashboard(a, "中芯国际 A股 (688981.SH) — RSI / MACD / Bollinger", "smic_a_indicator.png")
plot_dashboard(hk, "中芯国际 港股 (00981.HK) — RSI / MACD / Bollinger", "smic_hk_indicator.png", lookback=250)

# ============================================================
# 4. 指标摘要
# ============================================================
print("\n" + "="*60)
print("  最新指标信号")
print("="*60)

for name, df_, code in [("A股", a, "688981.SH"), ("港股", hk, "00981.HK")]:
    d = df_.iloc[-1]
    long = df_.tail(3)
    rsi = d["rsi"]
    macd_h = d["macd_hist"]
    bb_pos = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"]) * 100 if d.get("bb_upper") else None
    bb_signal = "上轨附近" if bb_pos and bb_pos > 90 else ("下轨附近" if bb_pos and bb_pos < 10 else "中轨附近")

    rsi_signal = "超买" if rsi > 70 else ("超卖" if rsi < 30 else "中性")
    macd_signal = "金叉" if long["dif"].iloc[-1] > long["dea"].iloc[-1] and long["dif"].iloc[-2] <= long["dea"].iloc[-2] else \
                  ("死叉" if long["dif"].iloc[-1] < long["dea"].iloc[-1] and long["dif"].iloc[-2] >= long["dea"].iloc[-2] else \
                   ("多头" if d["dif"] > d["dea"] else "空头"))

    print(f"\n{name} ({code}) — {d['trade_date'].date()}")
    print(f"  收盘价: {d['close']:.2f}")
    print(f"  RSI(14): {rsi:.1f}  →  {rsi_signal}")
    print(f"  MACD DIF={d['dif']:.3f}  DEA={d['dea']:.3f}  Hist={d['macd_hist']:.3f}  →  {macd_signal}")
    print(f"  Bollinger: {'%.2f'%d['bb_upper']} / {'%.2f'%d['bb_ma']} / {'%.2f'%d['bb_lower']}  →  {bb_signal}")
    print(f"  BB Width: {d['bb_width']:.2f}%")

print(f"\n图表已保存于当前目录。")
