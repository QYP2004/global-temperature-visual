# 全球气温监测

## 项目目标
构建一个基于flask(后端)和pyecharts(图表生成)的数据可视化大屏，通过对 Berkeley Earth 气温数据集的清洗与分析，展示全球变暖趋势、地区差异及季节性波动。

### 技术栈
**后端框架**: **Flask** (Python 微框架，负责路由与数据接口)
**数据处理**: **Pandas** (用于处理 CSV、清洗缺失值及聚合计算)
**前端图表**: **Echarts** (Echarts 的 Python 封装，支持动态交互与大屏布局)

### 数据集 

 GlobalTemperatures.csv
    dt (Date/Time)：日期/时间
    LandAverageTemperature (陆地平均温度)
    LandAverageTemperatureUncertainty (陆地平均温度不确定度,代表测量误差范围或置信区间。)
    LandMaxTemperature (陆地最高温度)
    LandMaxTemperatureUncertainty (陆地最高温度不确定度)
    LandMinTemperature (陆地最低温度)
    LandMinTemperatureUncertainty (陆地最低温度不确定度)
    LandAndOceanAverageTemperature (陆地与海洋平均总温)
    LandAndOceanAverageTemperatureUncertainty (陆地与海洋平均总温不确定度)

 GlobalLandTemperaturesByCity.csv
    dt（Date/Time）：日期/时间
    AverageTemperature（平均温度）
    AverageTemperatureUncertainty（平均温度不确定度 / 测量误差范围）
    City（城市）
    Country（国家）
    Latitude（纬度）
    Longitude（经度）

 GlobalLandTemperaturesByCountry.csv
    dt (Date/Time)：日期/时间
    AverageTemperature：平均温度
    AverageTemperatureUncertainty：平均温度不确定度 (或测量误差范围)
    Country：国家

 GlobalLandTemperaturesByMajorCity.csv
    dt（Date/Time）：日期/时间
    AverageTemperature（平均温度）
    AverageTemperatureUncertainty（平均温度不确定度 / 测量误差范围）
    City（城市）
    Country（国家）
    Latitude（纬度）
    Longitude（经度）

 GlobalLandTemperaturesByState.csv
    dt（Date/Time）：日期/时间
    AverageTemperature（平均温度）
    AverageTemperatureUncertainty（平均温度不确定度 / 测量误差范围）
    State（一级行政区，如省）
    Country（国家）

### 数据处理流
源数据CSV -> data_engine.py -> 生成目标数据 -> Flask页面路由，向前端发送JSON -> 前端通过fetch发送请求数据 -> echarts用拿到的数据画图



## 表
qyp 柱状
### 全球气温变化折线图
