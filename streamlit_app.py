"""Modified from Streamlit's Apache-2.0 NYC pickup demo; see UPSTREAM.md."""
import json
import pandas as pd
import streamlit as st
from demand_analysis import DATA, clean_data, analyze

st.set_page_config(page_title='出行需求分析', layout='wide')
st.title('纽约出行需求分析')
st.caption('2014年9月公开历史数据 · 纽约当地时间 · 数据量与接车记录，不代表当前需求或营收')


@st.cache_data
def load():
    return clean_data(pd.read_csv(DATA))


frame, quality = load()
dates = st.date_input('观察日期', (frame.timestamp.dt.date.min(), frame.timestamp.dt.date.max()),
                      min_value=frame.timestamp.dt.date.min(), max_value=frame.timestamp.dt.date.max())
if len(dates) != 2:
    st.info('请选择开始和结束日期。')
    st.stop()
selected = frame[frame.day.between(dates[0].isoformat(), dates[1].isoformat())]
if selected.empty:
    st.warning('所选区间没有记录。')
    st.stop()
result = analyze(selected)
c1, c2, c3 = st.columns(3)
c1.metric('接车记录', f"{result['rows']:,}")
c2.metric('有记录天数', result['observed_days'])
c3.metric('记录最多时段', f"{result['peak_hour']}:00")
tabs = st.tabs(['每日趋势', '小时分布', '星期归一化', '热点网格', '质量与口径'])
with tabs[0]:
    st.line_chart(pd.DataFrame(result['daily']).set_index('day'))
with tabs[1]:
    st.bar_chart(pd.DataFrame(result['hourly']).set_index('hour'))
with tabs[2]:
    st.dataframe(pd.DataFrame(result['weekday']), hide_index=True)
    st.caption('以各星期实际出现的日期数作为分母，避免不同星期天数不同导致误判。')
with tabs[3]:
    st.dataframe(pd.DataFrame(result['hotspots']), hide_index=True)
    st.caption('0.01度经纬度网格，面积并非完全相同；记录数不能推出供需缺口。')
with tabs[4]:
    st.json(quality)
    st.write('Pandas 与 SQLite 每日聚合已核对一致。完全相同行保留，因为数据没有唯一订单号。')
st.download_button('下载分析 JSON', json.dumps({'quality': quality, 'analysis': result}, ensure_ascii=False, indent=2),
                   file_name='pickup-analysis.json', mime='application/json')
