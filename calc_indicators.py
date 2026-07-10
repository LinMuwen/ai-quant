import sys, io, numpy as np, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def calc_rsi(close, p=14):
    d=close.diff(); g=d.clip(lower=0); l=(-d).clip(lower=0)
    ag=g.ewm(alpha=1/p,min_periods=p).mean(); al=l.ewm(alpha=1/p,min_periods=p).mean()
    rs=ag/al.replace(0,np.nan); return 100-100/(1+rs)

def calc_macd(close, f=12, s=26, sig=9):
    ef=close.ewm(span=f,adjust=False).mean(); es=close.ewm(span=s,adjust=False).mean()
    dif=ef-es; dea=dif.ewm(span=sig,adjust=False).mean(); hist=2*(dif-dea)
    return dif,dea,hist

def calc_bb(close, p=20, n=2):
    ma=close.rolling(p).mean(); std=close.rolling(p).std()
    return ma, ma+n*std, ma-n*std

def report(df, name, code):
    d=df.copy()
    d['rsi']=calc_rsi(d['close'])
    d['dif'],d['dea'],d['macd_h']=calc_macd(d['close'])
    d['bb_mid'],d['bb_up'],d['bb_lo']=calc_bb(d['close'])
    d['bb_width']=(d['bb_up']-d['bb_lo'])/d['bb_mid']*100
    d['bb_pos']=(d['close']-d['bb_lo'])/(d['bb_up']-d['bb_lo'])*100
    last=d.iloc[-1]; prev=d.iloc[-2]; long=d.tail(60)
    rsi=d['rsi'].dropna()
    rsi_h=(rsi>70).sum(); rsi_l=(rsi<30).sum()
    rsi_sig='超买' if last['rsi']>70 else ('超卖' if last['rsi']<30 else '中性')
    cm='金叉' if last['dif']>last['dea'] and prev['dif']<=prev['dea'] else ('死叉' if last['dif']<last['dea'] and prev['dif']>=prev['dea'] else ('多头' if last['dif']>last['dea'] else '空头'))
    bb_sig='上轨附近' if last['bb_pos']>90 else ('下轨附近' if last['bb_pos']<10 else ('偏上' if last['bb_pos']>65 else ('偏下' if last['bb_pos']<35 else '中轨')))

    print(f'\n---- {name} ({code}) ----')
    print(f'最新: {last["trade_date"].date()}  收盘 {last["close"]:.2f}')
    print()
    print(f'[RSI(14)]')
    print(f'  最新值: {last["rsi"]:.1f}  ->  {rsi_sig}')
    print(f'  区间: [{rsi.min():.1f}, {rsi.max():.1f}]  均值: {rsi.mean():.1f}  中位数: {rsi.median():.1f}')
    print(f'  超买(>70): {rsi_h}天 ({rsi_h/len(rsi)*100:.1f}%)  超卖(<30): {rsi_l}天 ({rsi_l/len(rsi)*100:.1f}%)')
    print()
    print(f'[MACD(12,26,9)]')
    print(f'  DIF={last["dif"]:.3f}  DEA={last["dea"]:.3f}  Hist={last["macd_h"]:.3f}')
    print(f'  前一日: DIF={prev["dif"]:.3f}  DEA={prev["dea"]:.3f}  Hist={prev["macd_h"]:.3f}')
    print(f'  信号: {cm}')
    print(f'  近3月 Hist 均值: {long["macd_h"].mean():.3f}  std: {long["macd_h"].std():.3f}')
    print()
    print(f'[Bollinger Bands(20,2)]')
    print(f'  上轨: {last["bb_up"]:.2f}  中轨: {last["bb_mid"]:.2f}  下轨: {last["bb_lo"]:.2f}')
    print(f'  价格位置: {last["bb_pos"]:.1f}% -> {bb_sig}')
    print(f'  带宽: {last["bb_width"]:.2f}%  (近3月带宽 [{long["bb_width"].min():.2f}%, {long["bb_width"].max():.2f}%])')

a=pd.read_csv(r'.\smic_a_share.csv'); a['trade_date']=pd.to_datetime(a['trade_date'],format='%Y%m%d')
a.sort_values('trade_date',inplace=True); a.reset_index(drop=True,inplace=True)
hk=pd.read_csv(r'.\smic_hk_share.csv'); hk['trade_date']=pd.to_datetime(hk['trade_date'],format='%Y%m%d')
hk=hk[hk['trade_date']>=pd.Timestamp('2025-07-01')].sort_values('trade_date').reset_index(drop=True)

print('技术指标计算结果 (近一年)')
print('='*56)
report(a,'A股','688981.SH')
report(hk,'港股','00981.HK')
