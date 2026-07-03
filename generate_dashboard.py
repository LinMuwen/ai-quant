# -*- coding: utf-8 -*-
"""
生成中芯国际 A股 vs 港股 对比看板
包含: K线对比、归一化走势、成交量、AH溢价率
"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "smic_combined.json")
HTML_PATH = os.path.join(BASE_DIR, "smic_dashboard.html")

def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    dates = data["dates"]
    n = len(dates)
    hkd_rate = data["hkd_cny_rate"]

    # 统计指标
    a_close = data["a_close"]
    hk_close = data["hk_close"]
    ah_premium = data["ah_premium"]
    a_ret = (a_close[-1] / a_close[0] - 1) * 100
    hk_ret = (hk_close[-1] / hk_close[0] - 1) * 100
    a_max = max(a_close)
    a_min = min(a_close)
    hk_max = max(hk_close)
    hk_min = min(hk_close)
    prem_max = max(ah_premium)
    prem_min = min(ah_premium)
    prem_avg = sum(ah_premium) / len(ah_premium)

    data_json = json.dumps(data, ensure_ascii=False)

    # HTML 模板 - 使用占位符替换，避免 f-string 转义问题
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中芯国际 AH股对比分析面板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0f1117;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1d28 0%, #252836 100%);
            padding: 28px 36px;
            border-bottom: 1px solid #2a2d3a;
        }
        .header-title {
            font-size: 26px;
            font-weight: 700;
            color: #fff;
            letter-spacing: 1px;
        }
        .header-sub {
            font-size: 14px;
            color: #8b8fa3;
            margin-top: 6px;
        }
        .stats-row {
            display: flex;
            gap: 16px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 14px 22px;
            min-width: 120px;
        }
        .stat-label { font-size: 12px; color: #8b8fa3; margin-bottom: 6px; }
        .stat-value { font-size: 20px; font-weight: 700; color: #fff; }
        .up { color: #ef4444; }
        .down { color: #22c55e; }
        .neutral { color: #60a5fa; }
        .chart-section {
            padding: 20px 28px;
            max-width: 1500px;
            margin: 0 auto;
        }
        .chart-title {
            font-size: 16px;
            font-weight: 600;
            color: #c0c4d0;
            margin-bottom: 10px;
            padding-left: 12px;
            border-left: 3px solid #60a5fa;
        }
        .chart-box {
            background: #1a1d28;
            border-radius: 12px;
            border: 1px solid #2a2d3a;
            margin-bottom: 24px;
            padding: 16px;
        }
        .chart { width: 100%; }
        .row-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        @media (max-width: 1100px) { .row-2 { grid-template-columns: 1fr; } }
        .footer {
            text-align: center;
            padding: 20px;
            color: #555;
            font-size: 12px;
        }
        .legend-dot {
            display: inline-block;
            width: 10px; height: 10px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">中芯国际 AH股对比分析面板</div>
        <div class="header-sub">
            A股 688981.SH (科创板) &nbsp;|&nbsp; 港股 00981.HK (中国香港) &nbsp;|&nbsp;
            数据区间 __DATE_RANGE__ &nbsp;|&nbsp; 共 __N__ 个交易日
        </div>
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-label">A股最新 (CNY)</div>
                <div class="stat-value up">__A_CLOSE__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">A股区间涨幅</div>
                <div class="stat-value __A_RET_CLASS__">__A_RET__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">港股最新 (HKD)</div>
                <div class="stat-value up">__HK_CLOSE__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">港股折人民币</div>
                <div class="stat-value neutral">__HK_CNY__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">港股区间涨幅</div>
                <div class="stat-value __HK_RET_CLASS__">__HK_RET__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">AH溢价率(最新)</div>
                <div class="stat-value neutral">__PREM_NOW__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">AH溢价率(均值)</div>
                <div class="stat-value neutral">__PREM_AVG__</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">汇率 HKD/CNY</div>
                <div class="stat-value" style="color:#aaa">__HKD_RATE__</div>
            </div>
        </div>
    </div>

    <div class="chart-section">
        <div class="chart-title">
            <span class="legend-dot" style="background:#ef4444"></span>A股 K线 (688981.SH)
            &emsp;&emsp;
            <span class="legend-dot" style="background:#22c55e"></span>港股 K线 (00981.HK)
        </div>
        <div class="chart-box">
            <div id="chart-kline-a" class="chart" style="height:420px"></div>
            <div id="chart-kline-hk" class="chart" style="height:420px; margin-top:8px"></div>
        </div>

        <div class="chart-title">归一化价格走势对比 (首日=100)</div>
        <div class="chart-box">
            <div id="chart-norm" class="chart" style="height:380px"></div>
        </div>

        <div class="row-2">
            <div>
                <div class="chart-title">A股成交量 (万手)</div>
                <div class="chart-box">
                    <div id="chart-vol-a" class="chart" style="height:260px"></div>
                </div>
            </div>
            <div>
                <div class="chart-title">港股成交量 (万手)</div>
                <div class="chart-box">
                    <div id="chart-vol-hk" class="chart" style="height:260px"></div>
                </div>
            </div>
        </div>

        <div class="chart-title">AH溢价率走势 (%)</div>
        <div class="chart-box">
            <div id="chart-premium" class="chart" style="height:320px"></div>
        </div>
    </div>

    <div class="footer">
        数据来源: A股 Tushare Pro &middot; 港股 腾讯行情 &middot; 生成时间 __GEN_TIME__<br>
        港币兑人民币汇率采用固定近似值 __HKD_RATE__，实际溢价率可能因汇率波动存在偏差
    </div>

    <script>
    const rawData = __DATA_JSON__;

    const upColor = '#ef4444';
    const downColor = '#22c55e';

    // ---- K线 A股 ----
    const klineA = echarts.init(document.getElementById('chart-kline-a'));
    klineA.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' }
        },
        grid: { left: '7%', right: '4%', top: '6%', bottom: '18%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 11 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { scale: true, splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 11, formatter: 'CNY {value}' } },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: '2%', height: 18, start: 0, end: 100,
              borderColor: '#3a3d4a', backgroundColor: '#1a1d28', textStyle: { color: '#8b8fa3' } }
        ],
        series: [{
            type: 'candlestick', name: 'A股', data: rawData.a_ohlc,
            itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor }
        }]
    });

    // ---- K线 港股 ----
    const klineHK = echarts.init(document.getElementById('chart-kline-hk'));
    klineHK.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' } },
        grid: { left: '7%', right: '4%', top: '6%', bottom: '18%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 11 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { scale: true, splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 11, formatter: 'HKD {value}' } },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: '2%', height: 18, start: 0, end: 100,
              borderColor: '#3a3d4a', backgroundColor: '#1a1d28', textStyle: { color: '#8b8fa3' } }
        ],
        series: [{
            type: 'candlestick', name: '港股', data: rawData.hk_ohlc,
            itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor }
        }]
    });

    // ---- 归一化走势对比 ----
    const normChart = echarts.init(document.getElementById('chart-norm'));
    normChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis',
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' } },
        legend: { data: ['A股 688981.SH', '港股 00981.HK'], textStyle: { color: '#c0c4d0' }, top: 5 },
        grid: { left: '6%', right: '4%', top: '14%', bottom: '18%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 11 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { scale: true, splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 11 } },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: '2%', height: 18, start: 0, end: 100,
              borderColor: '#3a3d4a', backgroundColor: '#1a1d28', textStyle: { color: '#8b8fa3' } }
        ],
        series: [
            { name: 'A股 688981.SH', type: 'line', data: rawData.a_norm, smooth: true,
              symbol: 'none', lineStyle: { color: '#ef4444', width: 2 },
              areaStyle: { color: 'rgba(239,68,68,0.08)' } },
            { name: '港股 00981.HK', type: 'line', data: rawData.hk_norm, smooth: true,
              symbol: 'none', lineStyle: { color: '#22c55e', width: 2 },
              areaStyle: { color: 'rgba(34,197,94,0.08)' } }
        ]
    });

    // ---- A股成交量 ----
    const volA = echarts.init(document.getElementById('chart-vol-a'));
    volA.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis',
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' },
            formatter: function(params) {
                return params[0].axisValue + '<br/>量: ' + (params[0].data.value / 10000).toFixed(2) + ' 万手';
            }
        },
        grid: { left: '8%', right: '4%', top: '6%', bottom: '22%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 10 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 10, formatter: function(v) { return (v/10000).toFixed(0) + '万'; } } },
        dataZoom: [ { type: 'inside', start: 0, end: 100 } ],
        series: [{
            type: 'bar', data: rawData.a_vol.map(function(v, i) {
                return { value: v, itemStyle: { color: rawData.a_vol_colors[i] } };
            })
        }]
    });

    // ---- 港股成交量 ----
    const volHK = echarts.init(document.getElementById('chart-vol-hk'));
    volHK.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis',
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' },
            formatter: function(params) {
                return params[0].axisValue + '<br/>量: ' + (params[0].data.value / 10000).toFixed(2) + ' 万手';
            }
        },
        grid: { left: '8%', right: '4%', top: '6%', bottom: '22%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 10 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 10, formatter: function(v) { return (v/10000).toFixed(0) + '万'; } } },
        dataZoom: [ { type: 'inside', start: 0, end: 100 } ],
        series: [{
            type: 'bar', data: rawData.hk_vol.map(function(v, i) {
                return { value: v, itemStyle: { color: rawData.hk_vol_colors[i] } };
            })
        }]
    });

    // ---- AH溢价率 ----
    const premChart = echarts.init(document.getElementById('chart-premium'));
    premChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis',
            backgroundColor: 'rgba(20,22,30,0.95)', borderColor: '#3a3d4a', textStyle: { color: '#e0e0e0' },
            formatter: function(params) {
                return params[0].axisValue + '<br/>AH溢价率: ' + params[0].data + '%';
            }
        },
        grid: { left: '6%', right: '4%', top: '10%', bottom: '18%' },
        xAxis: { type: 'category', data: rawData.dates, scale: true, boundaryGap: false,
            axisLabel: { color: '#8b8fa3', fontSize: 11 }, axisLine: { lineStyle: { color: '#3a3d4a' } } },
        yAxis: { scale: true, splitLine: { lineStyle: { color: '#2a2d3a' } },
            axisLabel: { color: '#8b8fa3', fontSize: 11, formatter: '{value}%' } },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: '2%', height: 18, start: 0, end: 100,
              borderColor: '#3a3d4a', backgroundColor: '#1a1d28', textStyle: { color: '#8b8fa3' } }
        ],
        series: [{
            type: 'line', data: rawData.ah_premium, smooth: true, symbol: 'none',
            lineStyle: { color: '#60a5fa', width: 2 },
            areaStyle: { color: 'rgba(96,165,250,0.12)' },
            markLine: {
                symbol: 'none',
                data: [
                    { type: 'average', name: '均值',
                      label: { formatter: '均值 {c}%', color: '#fbbf24' },
                      lineStyle: { color: '#fbbf24', type: 'dashed' } }
                ]
            }
        }]
    });

    // 联动 dataZoom
    const charts = [klineA, klineHK, normChart, volA, volHK, premChart];
    charts.forEach(function(chart) {
        chart.on('datazoom', function() {
            const opt = chart.getOption();
            const dz = opt.dataZoom[0];
            charts.forEach(function(c) {
                if (c !== chart) {
                    c.dispatchAction({ type: 'dataZoom', start: dz.start, end: dz.end });
                }
            });
        });
    });

    window.addEventListener('resize', function() {
        charts.forEach(function(c) { c.resize(); });
    });
    </script>
</body>
</html>"""

    # 替换占位符
    replacements = {
        "__DATE_RANGE__": f"{dates[0]} ~ {dates[-1]}",
        "__N__": str(n),
        "__A_CLOSE__": f"{a_close[-1]:.2f}",
        "__A_RET__": f"{'+' if a_ret >= 0 else ''}{a_ret:.2f}%",
        "__A_RET_CLASS__": "up" if a_ret >= 0 else "down",
        "__HK_CLOSE__": f"{hk_close[-1]:.2f}",
        "__HK_CNY__": f"{hk_close[-1] * hkd_rate:.2f}",
        "__HK_RET__": f"{'+' if hk_ret >= 0 else ''}{hk_ret:.2f}%",
        "__HK_RET_CLASS__": "up" if hk_ret >= 0 else "down",
        "__PREM_NOW__": f"{ah_premium[-1]:.2f}%",
        "__PREM_AVG__": f"{prem_avg:.2f}%",
        "__HKD_RATE__": f"{hkd_rate}",
        "__GEN_TIME__": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "__DATA_JSON__": data_json,
    }

    html = html_template
    for key, val in replacements.items():
        html = html.replace(key, val)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML 面板已生成: {HTML_PATH}")
    print(f"交易日数: {n}")


if __name__ == "__main__":
    main()
