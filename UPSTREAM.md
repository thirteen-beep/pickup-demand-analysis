# 上游来源与改造范围

来源：https://github.com/streamlit/demo-uber-nyc-pickups

基线提交：`62fa70f59da265450b97429e9bfae99b85bcacdd`。保留完整Git历史和原样LICENSE，新增代码通过AI辅助实现。

1. 重写streamlit_app.py，增加日期筛选、日趋势、24小时分布、星期归一化、热点网格及JSON下载。
2. demand_analysis.py读取完整公开数据，校验日期、经纬度及分析区域；纽约当地时间明确标注。
3. SQLite GROUP BY与Pandas独立计算每日聚合并自动核对，星期统计按实际有记录日期数归一化。
4. 保留同时间同坐标的记录，报告完全相同行数量；无订单ID时不能判定这些行是重复订单。

原始README在UPSTREAM_README文件中保留。原框架、库和样例的原有能力属于上游；本项目新增业务和测试见以上清单。
