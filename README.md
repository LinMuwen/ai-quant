# AI 量化交易

基于 Python + Tushare 的 A股/港股行情数据获取与可视化分析项目。

## 项目内容

### 中芯国际 AH 股对比分析

- **A股代码**: 688981.SH（科创板）
- **港股代码**: 00981.HK（中国香港）

#### 数据来源

| 市场 | 数据源 | 说明 |
|------|--------|------|
| A股 | Tushare Pro API | 日线行情（开高低收、成交量、成交额等） |
| 港股 | 腾讯行情 API | 前复权日线数据 |

#### 文件说明

| 文件 | 说明 |
|------|------|
| `fetch_smic_data.py` | 数据获取脚本（A股+港股） |
| `generate_dashboard.py` | HTML 可视化面板生成脚本 |
| `smic_a_share.csv` | 中芯国际 A股日线数据 |
| `smic_hk_share.csv` | 中芯国际 港股日线数据 |
| `smic_combined.json` | A+H 合并数据（JSON） |
| `smic_dashboard.html` | 交互式可视化面板 |

#### 面板功能

- A股 K线图 + 成交量（涨红跌绿，中国股市惯例）
- 港股 K线图 + 成交量
- A股 vs 港股归一化走势对比（首日=100）
- AH 溢价率走势图
- 全图表时间轴联动缩放

## 环境配置

```bash
pip install tushare pandas requests
```

## 使用

```bash
# 1. 获取数据
python fetch_smic_data.py

# 2. 生成可视化面板
python generate_dashboard.py

# 3. 打开面板
# 用浏览器打开 smic_dashboard.html
```

## 技术栈

- Python 3.13
- Tushare Pro（A股数据）
- 腾讯行情 API（港股数据）
- ECharts（前端可视化）
