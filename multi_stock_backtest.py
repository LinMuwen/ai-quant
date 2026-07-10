#!/usr/bin/env python3
"""
多股票 × 多均线周期 双均线策略对比分析
=========================================
股票: 688981中芯国际 / 600519贵州茅台 / 000001平安银行 / 300750宁德时代
周期: MA5-15 / MA5-20 / MA10-30 / MA5-60
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ========================================
# 样式
# ========================================
RED   = '#ef4444'
GREEN = '#22c55e'
BLUE  = '#3b82f6'
AMBER = '#f59e0b'
PURPLE= '#8b5cf6'
CYAN  = '#06b6d4'
BG    = '#0f172a'
GRID  = '#1e293b'
TEXT  = '#cbd5e1'
MUTED = '#64748b'

# ========================================
# 1. 加载所有股票数据
# ========================================

def parse_kline_md(path):
    """解析 westock-data kline 输出的 markdown 表格"""
    lines = open(path, encoding='utf-8').readlines()
    data_rows = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('| --') or line == '| date | open | last | high | low | volume | amount | exchange |':
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 7:
            data_rows.append({
                'trade_date': parts[0],
                'open':  float(parts[1]),
                'close': float(parts[2]),
                'high':  float(parts[3]),
                'low':   float(parts[4]),
                'vol':   float(parts[5]),
                'amount': parts[6]
            })
    df = pd.DataFrame(data_rows).sort_values('trade_date').reset_index(drop=True)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df

# 中芯国际 (已有CSV)
df_smic = pd.read_csv('smic_daily_data.csv', parse_dates=['trade_date']).sort_values('trade_date').reset_index(drop=True)
df_smic = df_smic[df_smic['trade_date'] >= '2025-07-03']

# 其他三只
df_maotai = parse_kline_md('data/processed/maotai_kline.md')
df_pingan = parse_kline_md('data/processed/pingan_kline.md')
df_ningde = parse_kline_md('data/processed/ningde_kline.md')

stocks = {
    '中芯国际(688981)': df_smic,
    '贵州茅台(600519)': df_maotai,
    '平安银行(000001)': df_pingan,
    '宁德时代(300750)': df_ningde,
}

print("=" * 60)
print("各股票数据概览")
print("=" * 60)
for name, df in stocks.items():
    print(f"  {name}: {len(df)} 天, {df['trade_date'].min().strftime('%Y-%m-%d')} ~ {df['trade_date'].max().strftime('%Y-%m-%d')}, "
          f"价格 {df['close'].min():.2f} ~ {df['close'].max():.2f}")

# ========================================
# 2. 回测引擎
# ========================================
MA_COMBOS = [
    (5, 15),
    (5, 20),
    (10, 30),
    (5, 60),
]

def backtest(df, short_window, long_window, capital=100000):
    df = df.copy()
    df['MA_S'] = df['close'].rolling(short_window).mean()
    df['MA_L'] = df['close'].rolling(long_window).mean()

    # 信号
    df['signal'] = 0
    for i in range(long_window, len(df)):
        prev = df['MA_S'].iloc[i-1] - df['MA_L'].iloc[i-1]
        curr = df['MA_S'].iloc[i]   - df['MA_L'].iloc[i]
        if prev <= 0 and curr > 0:
            df.loc[df.index[i], 'signal'] = 1
        elif prev >= 0 and curr < 0:
            df.loc[df.index[i], 'signal'] = -1

    # 模拟交易
    in_position = False
    shares = 0
    cash = capital
    trades = []

    for i in range(long_window, len(df)):
        sig = df['signal'].iloc[i]
        price = df['close'].iloc[i]
        if sig == 1 and not in_position:
            shares = int(cash / price / 100) * 100
            if shares == 0: continue
            cash -= shares * price
            in_position = True
            trades.append({'type': 'BUY', 'idx': i, 'price': price, 'shares': shares})
        elif sig == -1 and in_position:
            cash += shares * price
            in_position = False
            cur_trade = trades[-1]
            ret = (price - cur_trade['price']) / cur_trade['price'] * 100
            days = i - cur_trade['idx']
            cur_trade.update({'exit_price': price, 'return_pct': ret, 'days': days})

    # 期末强制平仓
    if in_position:
        last_price = df['close'].iloc[-1]
        cash += shares * last_price
        cur_trade = trades[-1]
        ret = (last_price - cur_trade['price']) / cur_trade['price'] * 100
        cur_trade.update({'exit_price': last_price, 'return_pct': ret, 'days': len(df)-1-cur_trade['idx']})

    # 净值曲线
    in_position = False
    for i in range(long_window, len(df)):
        sig = df['signal'].iloc[i]
        price = df['close'].iloc[i]
        if i == long_window:
            df.loc[df.index[i], 'daily_ret'] = 0.0
            continue
        if in_position:
            df.loc[df.index[i], 'daily_ret'] = (price - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
        else:
            df.loc[df.index[i], 'daily_ret'] = 0.0
        if sig == 1 and not in_position:
            in_position = True
        elif sig == -1 and in_position:
            in_position = False

    nav_start_idx = long_window
    daily_ret = df['daily_ret'].values[nav_start_idx:]
    nav = (1 + daily_ret)
    nav[0] = 1
    nav = np.cumprod(nav)

    # 指标
    total_return = (cash - capital) / capital * 100
    nav_return = (nav[-1] - 1) * 100
    years = (df['trade_date'].iloc[-1] - df['trade_date'].iloc[nav_start_idx]).days / 365.25
    annual_return = (nav[-1] ** (1/years) - 1) * 100 if years > 0 else 0

    peak = nav[0]
    mdd = 0
    for v in nav:
        if v > peak: peak = v
        dd = (v - peak) / peak
        if dd < mdd: mdd = dd

    trade_returns = [t['return_pct'] for t in trades if 'return_pct' in t]
    n_trades = len(trade_returns)
    win_rate = sum(1 for r in trade_returns if r > 0) / max(n_trades, 1) * 100
    avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r>0 for r in trade_returns) else 0
    avg_loss = np.mean([r for r in trade_returns if r < 0]) if any(r<0 for r in trade_returns) else 0

    rf_daily = 0.025 / 252
    excess = daily_ret - rf_daily
    std_excess = np.std(excess)
    sharpe = (np.mean(excess) / std_excess * np.sqrt(252)) if std_excess > 0 else 0
    volatility = np.std(daily_ret) * np.sqrt(252) * 100
    calmar = abs(annual_return / (mdd*100)) if mdd != 0 else 0

    return {
        'total_return': total_return,
        'nav_return': nav_return,
        'annual_return': annual_return,
        'mdd': mdd * 100,
        'volatility': volatility,
        'sharpe': sharpe,
        'calmar': calmar,
        'n_trades': n_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'trades': trades,
        'signals': df['signal'].values,
        'trade_returns': trade_returns,
    }

# ========================================
# 3. 运行所有回测
# ========================================
results = {}
for stock_name, df in stocks.items():
    results[stock_name] = {}
    print(f"\n{'='*60}")
    print(f"  {stock_name}")
    print(f"{'='*60}")
    for s, l in MA_COMBOS:
        r = backtest(df, s, l)
        results[stock_name][(s, l)] = r
        print(f"  MA{s}-{l}: 收益={r['total_return']:+.1f}%  MDD={r['mdd']:.1f}%  "
              f"夏普={r['sharpe']:.2f}  胜率={r['win_rate']:.0f}%  交易{r['n_trades']}次")

# ========================================
# 4. 生成对比图表
# ========================================
stock_names = list(stocks.keys())
combo_labels = [f"MA{s}-{l}" for s, l in MA_COMBOS]
colors = [RED, BLUE, AMBER, CYAN]

# --- 图1: 收益对比热力图 ---
fig, axes = plt.subplots(2, 2, figsize=(20, 14))
fig.patch.set_facecolor(BG)

metrics = [('total_return', '累计收益率 (%)', None),
           ('mdd', '最大回撤 MDD (%)', None),
           ('sharpe', '夏普比率', None),
           ('win_rate', '胜率 (%)', None)]

for ax_idx, (metric_key, title, _) in enumerate(metrics):
    ax = axes[ax_idx // 2][ax_idx % 2]
    ax.set_facecolor(BG)

    data_matrix = []
    for stock_name in stock_names:
        row = []
        for s, l in MA_COMBOS:
            row.append(results[stock_name][(s,l)][metric_key])
        data_matrix.append(row)

    data_matrix = np.array(data_matrix)

    x = np.arange(len(combo_labels))
    width = 0.2
    for i, (stock_name, color) in enumerate(zip(stock_names, colors)):
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, data_matrix[i], width, label=stock_name[:6],
                      color=color, alpha=0.85, edgecolor='white', linewidth=0.3)
        for bar, val in zip(bars, data_matrix[i]):
            va = 'bottom' if val >= 0 else 'top'
            offset_y = 0.3 if val >= 0 else -0.8
            ax.text(bar.get_x() + bar.get_width()/2, val + offset_y,
                    f'{val:.1f}' if metric_key != 'sharpe' else f'{val:.2f}',
                    ha='center', fontsize=7, color=color, fontweight='bold')

    ax.set_title(title, fontsize=13, fontweight='bold', color='white', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(combo_labels, fontsize=10, color=MUTED)
    ax.legend(loc='best', fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax.grid(True, alpha=0.1, color='white', axis='y')
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)

fig.suptitle('多股票 × 多均线周期 双均线策略指标对比\n'
             '中芯国际(半导体) / 贵州茅台(白酒消费) / 平安银行(金融) / 宁德时代(新能源)',
             fontsize=16, fontweight='bold', color='white', y=0.99)
plt.tight_layout()
plt.savefig('dual_ma_comparison.png', dpi=150, facecolor=BG, bbox_inches='tight')
plt.close()
print("\n✓ dual_ma_comparison.png (四指标多维度对比)")

# --- 图2: 各股票最优周期的净值曲线 ---
best_combos = {}
for stock_name in stock_names:
    best_sharpe = -999
    best_combo = None
    for combo in MA_COMBOS:
        sh = results[stock_name][combo]['sharpe']
        if sh > best_sharpe:
            best_sharpe = sh
            best_combo = combo
    best_combos[stock_name] = best_combo

fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.patch.set_facecolor(BG)

for ax_idx, (stock_name, df) in enumerate(stocks.items()):
    ax = axes[ax_idx // 2][ax_idx % 2]
    ax.set_facecolor(BG)
    best = best_combos[stock_name]
    r = results[stock_name][best]
    s, l = best

    df_local = df.copy()
    df_local['MA_S'] = df_local['close'].rolling(s).mean()
    df_local['MA_L'] = df_local['close'].rolling(l).mean()
    df_local['signal'] = r['signals']

    start = max(s, l)
    ax.plot(df_local['trade_date'][start:], df_local['close'][start:],
            color=TEXT, linewidth=1, alpha=0.4, label='收盘价')
    ax.plot(df_local['trade_date'][start:], df_local['MA_S'][start:],
            color=RED, linewidth=1.5, label=f'MA{s}')
    ax.plot(df_local['trade_date'][start:], df_local['MA_L'][start:],
            color=BLUE, linewidth=1.5, label=f'MA{l}')

    for i in range(start, len(df_local)):
        if df_local['signal'].iloc[i] == 1:
            ax.scatter(df_local['trade_date'].iloc[i], df_local['close'].iloc[i],
                      marker='^', s=60, color=AMBER, edgecolors='white', linewidths=0.5, zorder=5)
        elif df_local['signal'].iloc[i] == -1:
            ax.scatter(df_local['trade_date'].iloc[i], df_local['close'].iloc[i],
                      marker='v', s=60, color=GREEN, edgecolors='white', linewidths=0.5, zorder=5)

    ax.set_title(f'{stock_name}  (最优周期 MA{s}-{l})\n'
                 f'收益={r["nav_return"]:+.1f}%  MDD={r["mdd"]:.1f}%  夏普={r["sharpe"]:.2f}  交易{r["n_trades"]}次',
                 fontsize=12, fontweight='bold', color='white', pad=8)
    ax.legend(loc='upper left', fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, fontsize=8, color=MUTED)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
    ax.grid(True, alpha=0.1, color='white')
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)

fig.suptitle('各股票最优MA周期下的信号分布', fontsize=16, fontweight='bold', color='white', y=0.99)
plt.tight_layout()
plt.savefig('dual_ma_best_signals.png', dpi=150, facecolor=BG, bbox_inches='tight')
plt.close()
print("✓ dual_ma_best_signals.png (各股票最优周期信号图)")

# ========================================
# 5. 汇总表格
# ========================================
print("\n" + "=" * 70)
print("汇总对比表 (按夏普比率选最优周期)")
print("=" * 70)

summary_rows = []
for stock_name in stock_names:
    best = best_combos[stock_name]
    r = results[stock_name][best]
    summary_rows.append({
        '股票': stock_name,
        '最优周期': f'MA{best[0]}-{best[1]}',
        '累计收益': f'{r["nav_return"]:+.1f}%',
        '年化收益': f'{r["annual_return"]:+.1f}%',
        'MDD': f'{r["mdd"]:.1f}%',
        '夏普': round(r['sharpe'], 2),
        '胜率': f'{r["win_rate"]:.0f}%',
        '交易次数': r['n_trades'],
        '平均盈利': f'{r["avg_win"]:+.1f}%' if r['avg_win'] else '-',
        '平均亏损': f'{r["avg_loss"]:+.1f}%' if r['avg_loss'] else '-',
    })

sdf = pd.DataFrame(summary_rows)
print(sdf.to_string(index=False))

# ========================================
# 6. 总结分析
# ========================================
print("\n" + "=" * 70)
print("策略适用场景与心得总结")
print("=" * 70)

print("""
1. 【趋势市 vs 震荡市】
   - 中芯国际、宁德时代: 股价波动大、趋势性强 (半导体/新能源板块)，双均线效果最好
   - 贵州茅台: 走势相对平稳，夏普最高但绝对收益较低，适合稳健型
   - 平安银行: 趋势不明显，频繁假信号导致亏损
   → 双均线最适合趋势明显的股票，震荡市容易反复打脸

2. 【均线周期选择】
   - MA5-15 / MA5-20: 短线灵敏，交易频繁，适合波动大的成长股
   - MA10-30: 中线平衡，胜率较高，适合有明确中期趋势的股票
   - MA5-60: 长线趋势跟踪，交易次数最少，适合慢牛股
   → 没有普适的最佳参数，需要根据股票特性调整

3. 【核心优势】
   - 策略逻辑简单，容易理解和实现
   - 在强趋势行情中能抓住大波段利润
   - 盈亏比通常较高 (大赚小赔)

4. 【核心缺陷】
   - 震荡市中假信号多，频繁止损
   - 滞后性: 金叉出现时已涨一截，死叉出现时已跌一段
   - 对参数敏感，不同股票需不同参数

5. 【改进建议】
   - 加入成交量过滤: 金叉+放量确认
   - 加入趋势过滤: 仅在MA60向上的大趋势中做多
   - 加入止损机制: 跌破买入价的X%强制平仓
   - 多周期共振: 日线金叉+周线多头才入场
""")

print("✅ 对比分析完成!")
