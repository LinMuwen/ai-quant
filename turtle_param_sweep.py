#!/usr/bin/env python3
"""
海龟策略参数敏感性分析
横向扫描: 标的(A/H) × 入场周期 × 止损倍数 × 离场周期
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RED, GREEN, GOLD, BLUE, PINK, CYAN = '#ef4444','#22c55e','#f59e0b','#3b82f6','#ec4899','#06b6d4'
BG, GRID, TEXT, MUTED = '#0f172a','#1e293b','#cbd5e1','#64748b'

# ============================================================
# 海龟回测引擎
# ============================================================
def turtle_backtest(df, entry_period=20, stop_n=2.0, exit_period=10, atr_period=20):
    """
    返回: dict of metrics
    """
    df = df.copy()
    
    # ATR (N值)
    prev_close = df['close'].shift(1)
    tr = np.maximum(df['high'] - df['low'],
                    np.maximum(abs(df['high'] - prev_close),
                               abs(df['low'] - prev_close)))
    df['N'] = tr.ewm(span=atr_period, adjust=False).mean()
    
    # 通道
    df['upper'] = df['high'].shift(1).rolling(entry_period).max()
    df['exit_line'] = df['low'].shift(1).rolling(exit_period).min()
    df['breakout'] = (df['high'] > df['upper']) & df['upper'].notna()
    df['exit_sig'] = (df['low'] < df['exit_line']) & df['exit_line'].notna()
    
    # 模拟
    trades = []
    in_position = False
    entry_price = entry_idx = None
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        N = row['N']
        if pd.isna(N) or N <= 0:
            continue
        
        if in_position:
            stop_price = entry_price - stop_n * N
            # 止损 or 离场信号
            if row['low'] <= stop_price:
                # 止损触发 (取 min(收盘, 止损价))
                exit_p = min(row['close'], stop_price)
                pnl = (exit_p - entry_price) * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                               'entry_p': entry_price, 'exit_p': exit_p,
                               'pnl': pnl, 'reason': 'stop', 'days': i - entry_idx})
                in_position = False
            elif row.get('exit_sig'):
                exit_p = row['close']
                pnl = (exit_p - entry_price) * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                               'entry_p': entry_price, 'exit_p': exit_p,
                               'pnl': pnl, 'reason': 'exit', 'days': i - entry_idx})
                in_position = False
        else:
            if row.get('breakout'):
                entry_price = row['open']  # 突破当日开盘价入场
                entry_idx = i
                in_position = True
    
    # 强制平仓
    if in_position:
        last = df.iloc[-1]
        pnl = (last['close'] - entry_price) * 100
        trades.append({'entry_idx': entry_idx, 'exit_idx': len(df)-1,
                       'entry_p': entry_price, 'exit_p': last['close'],
                       'pnl': pnl, 'reason': 'force', 'days': len(df)-1 - entry_idx})
    
    if not trades:
        return {'total_trades': 0, 'total_pnl': 0, 'win_rate': 0,
                'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0,
                'max_win': 0, 'max_loss': 0, 'max_dd': 0,
                'avg_hold': 0, 'max_consecutive_loss': 0}
    
    total_trades = len(trades)
    winning = [t for t in trades if t['pnl'] > 0]
    losing  = [t for t in trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = len(winning) / total_trades if total_trades > 0 else 0
    avg_win = np.mean([t['pnl'] for t in winning]) if winning else 0
    avg_loss = abs(np.mean([t['pnl'] for t in losing])) if losing else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
    max_win = max(t['pnl'] for t in winning) if winning else 0
    max_loss = min(t['pnl'] for t in losing) if losing else 0
    avg_hold = np.mean([t['days'] for t in trades])
    
    # 最大连续亏损
    streak = max_streak = 0
    for t in trades:
        if t['pnl'] <= 0: streak += 1; max_streak = max(max_streak, streak)
        else: streak = 0
    
    # 最大回撤 (简化: 基于逐笔盈亏)
    cum = 0; peak = 0; max_dd = 0
    for t in trades:
        cum += t['pnl']
        peak = max(peak, cum)
        dd = (cum - peak) / (1_000_000 + abs(peak) + 1)  # 近似
        max_dd = min(max_dd, dd)
    
    return {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_win': max_win,
        'max_loss': max_loss,
        'max_dd': max_dd,
        'avg_hold': avg_hold,
        'max_consecutive_loss': max_streak,
        'win_count': len(winning),
        'lose_count': len(losing),
    }

# ============================================================
# 加载数据
# ============================================================
def load_a_share():
    with open('smic_daily_data.json') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df.sort_values('trade_date').reset_index(drop=True)

def load_hk_share():
    df = pd.read_csv('smic_hk_share.csv')
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    return df.sort_values('trade_date').reset_index(drop=True)

# ============================================================
# 参数扫描
# ============================================================
def sweep():
    datasets = {
        '中芯A股(688981)': load_a_share(),
        '中芯港股(00981)': load_hk_share(),
    }
    
    entry_periods = [10, 20, 30, 40, 55]
    stop_factors  = [1.5, 2.0, 2.5, 3.0]
    exit_periods  = [5, 10, 15]
    
    results = []
    
    for stock_name, df in datasets.items():
        for ep in entry_periods:
            for sf in stop_factors:
                for xp in exit_periods:
                    m = turtle_backtest(df, entry_period=ep, stop_n=sf, exit_period=xp)
                    m['stock'] = stock_name
                    m['entry_period'] = ep
                    m['stop_n'] = sf
                    m['exit_period'] = xp
                    m['data_days'] = len(df)
                    results.append(m)
    
    return pd.DataFrame(results)

# ============================================================
# 打印最佳组合
# ============================================================
def print_top(rdf):
    print("\n" + "=" * 80)
    print("  TOP 10 最佳参数组合 (按总盈亏排序)")
    print("=" * 80)
    top10 = rdf.nlargest(10, 'total_pnl')
    for i, (_, row) in enumerate(top10.iterrows()):
        stock_short = 'A股' if 'A股' in row['stock'] else '港股'
        print(f"  {i+1}. {stock_short} | 入场周期={row['entry_period']:2.0f}日 "
              f"止损={row['stop_n']:.1f}N 离场={row['exit_period']:2.0f}日 | "
              f"盈亏 {row['total_pnl']:+,.0f} | 胜率 {row['win_rate']*100:.0f}% | "
              f"盈亏比 {row['profit_factor']:.2f}:1 | 交易 {row['total_trades']:2.0f}笔")
    
    print("\n" + "=" * 80)
    print("  TOP 5 最佳夏普/盈亏比组合")
    print("=" * 80)
    top_pf = rdf.nlargest(5, 'profit_factor')
    for i, (_, row) in enumerate(top_pf.iterrows()):
        stock_short = 'A股' if 'A股' in row['stock'] else '港股'
        print(f"  {i+1}. {stock_short} | 入场周期={row['entry_period']:2.0f}日 "
              f"止损={row['stop_n']:.1f}N 离场={row['exit_period']:2.0f}日 | "
              f"盈亏比 {row['profit_factor']:.2f}:1 | 胜率 {row['win_rate']*100:.0f}% | "
              f"盈亏 {row['total_pnl']:+,.0f} | 交易 {row['total_trades']:2.0f}笔")

    # 分市场对比
    for stock in rdf['stock'].unique():
        sr = rdf[rdf['stock'] == stock]
        print(f"\n--- {stock} ({len(sr)}组合) ---")
        print(f"  平均盈亏:      {sr['total_pnl'].mean():+,.0f}")
        print(f"  最佳盈亏:      {sr['total_pnl'].max():+,.0f}")
        print(f"  最差盈亏:      {sr['total_pnl'].min():+,.0f}")
        print(f"  平均胜率:      {sr['win_rate'].mean()*100:.0f}%")
        print(f"  平均盈亏比:    {sr['profit_factor'].mean():.2f}:1")
        print(f"  平均交易次数:  {sr['total_trades'].mean():.0f}")

# ============================================================
# 可视化热力图
# ============================================================
def plot_heatmaps(rdf):
    # 图1: 入场周期 vs 止损倍数 → 总盈亏 (A股/港股对比)
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    fig.patch.set_facecolor(BG)
    
    for stock_idx, stock in enumerate(rdf['stock'].unique()):
        sr = rdf[rdf['stock'] == stock]
        stock_short = 'A股688981' if 'A股' in stock else '港股00981'
        
        for col_idx, (metric, title, cmap, fmt) in enumerate([
            ('total_pnl', '总盈亏(元)', 'RdYlGn', '{:+,.0f}'),
            ('win_rate', '胜率', 'Blues', '{:.0%}'),
        ]):
            ax = axes[stock_idx][col_idx]
            ax.set_facecolor(BG)
            
            # 对止损2.0N、离场10日的情况建热力矩阵
            sr_fixed = sr[sr['exit_period'] == 10]
            pivot = sr_fixed.pivot_table(values=metric, index='entry_period', columns='stop_n', aggfunc='mean')
            
            im = ax.imshow(pivot.values, aspect='auto', cmap=cmap, vmin=pivot.values.min(), vmax=pivot.values.max())
            
            for i in range(pivot.shape[0]):
                for j in range(pivot.shape[1]):
                    v = pivot.iloc[i, j]
                    color = 'white' if (v < pivot.values.mean()) else 'black'
                    txt = f'{int(v)}' if metric == 'total_pnl' else f'{v*100:.0f}%'
                    ax.text(j, i, txt, ha='center', va='center', fontsize=9, color=color, fontweight='bold')
            
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([f'{x:.1f}N' for x in pivot.columns])
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([f'{x}' for x in pivot.index])
            ax.set_xlabel('止损倍数', fontsize=11, color=MUTED)
            ax.set_ylabel('入场周期(日)', fontsize=11, color=MUTED)
            ax.set_title(f'{stock_short} — {title} (离场=10日)', fontsize=13, fontweight='bold', color='white', pad=10)
            plt.setp(ax.xaxis.get_ticklabels(), color=MUTED)
            plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
            for spine in ax.spines.values(): spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f1 = 'sweep_heatmap.png'
    plt.savefig(f1, dpi=200, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"热力图: {f1}")
    
    # 图2: 离场周期 vs 总盈亏
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    fig.patch.set_facecolor(BG)
    
    for idx, stock in enumerate(rdf['stock'].unique()):
        ax = axes[idx]
        ax.set_facecolor(BG)
        stock_short = 'A股' if 'A股' in stock else '港股'
        sr = rdf[rdf['stock'] == stock]
        
        exit_periods = sorted(sr['exit_period'].unique())
        entry_periods = sorted(sr['entry_period'].unique())
        x = range(len(exit_periods))
        width = 0.18
        
        for i, ep in enumerate(entry_periods):
            vals = []
            for xp in exit_periods:
                sub = sr[(sr['entry_period'] == ep) & (sr['exit_period'] == xp)]
                v = sub['total_pnl'].mean()
                vals.append(v)
            offset = (i - len(entry_periods)/2 + 0.5) * width
            ax.bar([xi + offset for xi in x], vals, width=width, alpha=0.85,
                   label=f'入场{ep}日')
        
        ax.set_xticks(x)
        ax.set_xticklabels([f'{xp}日' for xp in exit_periods])
        ax.set_xlabel('离场周期', fontsize=11, color=MUTED)
        ax.set_ylabel('平均盈亏(元)', fontsize=11, color=MUTED)
        ax.set_title(f'{stock_short} — 离场周期对比', fontsize=13, fontweight='bold', color='white', pad=10)
        ax.legend(fontsize=8, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
        ax.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)
        ax.grid(True, alpha=0.08, color='white')
        plt.setp(ax.xaxis.get_ticklabels(), color=MUTED)
        plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
        for spine in ax.spines.values(): spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f2 = 'sweep_exit_compare.png'
    plt.savefig(f2, dpi=200, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"离场对比: {f2}")
    
    # 图3: 止损倍数 vs 胜率/盈亏比 (Trade-off)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))
    fig.patch.set_facecolor(BG)
    
    for ax in [ax1, ax2]:
        ax.set_facecolor(BG)
    
    for stock in rdf['stock'].unique():
        stock_short = 'A股' if 'A股' in stock else '港股'
        sr = rdf[rdf['stock'] == stock]
        sf_vals = sorted(sr['stop_n'].unique())
        
        wr = [sr[sr['stop_n'] == sf]['win_rate'].mean() for sf in sf_vals]
        pf = [sr[sr['stop_n'] == sf]['profit_factor'].mean() for sf in sf_vals]
        
        ax1.plot(sf_vals, wr, marker='o', linewidth=2, markersize=8,
                 label=stock_short)
        ax2.plot(sf_vals, pf, marker='s', linewidth=2, markersize=8,
                 label=stock_short)
    
    ax1.set_xlabel('止损倍数 (N)', fontsize=11, color=MUTED)
    ax1.set_ylabel('平均胜率', fontsize=11, color=MUTED)
    ax1.set_title('止损倍数 vs 胜率', fontsize=13, fontweight='bold', color='white', pad=10)
    ax1.legend(fontsize=10, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax1.grid(True, alpha=0.08, color='white')
    
    ax2.set_xlabel('止损倍数 (N)', fontsize=11, color=MUTED)
    ax2.set_ylabel('平均盈亏比', fontsize=11, color=MUTED)
    ax2.set_title('止损倍数 vs 盈亏比', fontsize=13, fontweight='bold', color='white', pad=10)
    ax2.legend(fontsize=10, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax2.grid(True, alpha=0.08, color='white')
    
    for ax in [ax1, ax2]:
        plt.setp(ax.xaxis.get_ticklabels(), color=MUTED)
        plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
        for spine in ax.spines.values(): spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f3 = 'sweep_stop_tradeoff.png'
    plt.savefig(f3, dpi=200, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"止损权衡: {f3}")
    
    # 图4: 入场周期 vs 交易次数
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    
    for stock in rdf['stock'].unique():
        stock_short = 'A股' if 'A股' in stock else '港股'
        sr = rdf[rdf['stock'] == stock]
        ep_vals = sorted(sr['entry_period'].unique())
        trades_count = [sr[sr['entry_period'] == ep]['total_trades'].mean() for ep in ep_vals]
        ax.plot(ep_vals, trades_count, marker='D', linewidth=2, markersize=10,
                label=f'{stock_short}')
    
    ax.set_xlabel('入场周期 (日)', fontsize=11, color=MUTED)
    ax.set_ylabel('平均交易次数', fontsize=11, color=MUTED)
    ax.set_title('入场周期 vs 交易频率', fontsize=14, fontweight='bold', color='white', pad=10)
    ax.legend(fontsize=11, facecolor=BG, edgecolor=GRID, labelcolor=TEXT)
    ax.grid(True, alpha=0.08, color='white')
    plt.setp(ax.xaxis.get_ticklabels(), color=MUTED)
    plt.setp(ax.yaxis.get_ticklabels(), color=MUTED)
    for spine in ax.spines.values(): spine.set_edgecolor(GRID)
    
    plt.tight_layout()
    f4 = 'sweep_entry_freq.png'
    plt.savefig(f4, dpi=200, facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"入场频率: {f4}")
    
    return f1, f2, f3, f4

# ============================================================
# 入口
# ============================================================
if __name__ == '__main__':
    print("海龟策略参数敏感性分析")
    print(f"扫描: 2标的 × 5入场周期 × 4止损倍数 × 3离场周期 = 120组合")
    
    rdf = sweep()
    rdf.to_csv('turtle_sweep_results.csv', index=False, encoding='utf-8-sig')
    print(f"结果已保存: turtle_sweep_results.csv ({len(rdf)}行)")
    
    print_top(rdf)
    plot_heatmaps(rdf)
    
    print("\n完成!")
