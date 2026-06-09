import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="服务响应时效监控",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# 生成 mock 数据
@st.cache_data
def generate_mock_data():
    """生成服务响应时间的 mock 数据"""
    services = [
        {"service_name": "API 网关", "service_type": "网关服务", "avg_response_time": 120, "request_count": 15000},
        {"service_name": "用户认证服务", "service_type": "认证服务", "avg_response_time": 85, "request_count": 8500},
        {"service_name": "MySQL 主库", "service_type": "数据库", "avg_response_time": 45, "request_count": 25000},
        {"service_name": "Redis 缓存", "service_type": "缓存服务", "avg_response_time": 8, "request_count": 50000},
        {"service_name": "MongoDB", "service_type": "数据库", "avg_response_time": 65, "request_count": 12000},
        {"service_name": "文件存储服务", "service_type": "存储服务", "avg_response_time": 230, "request_count": 3200},
        {"service_name": "消息队列 Kafka", "service_type": "消息服务", "avg_response_time": 35, "request_count": 18000},
        {"service_name": "搜索引擎 Elasticsearch", "service_type": "搜索服务", "avg_response_time": 180, "request_count": 6500},
        {"service_name": "支付网关", "service_type": "支付服务", "avg_response_time": 450, "request_count": 2100},
        {"service_name": "邮件服务", "service_type": "通知服务", "avg_response_time": 320, "request_count": 4800},
        {"service_name": "短信服务", "service_type": "通知服务", "avg_response_time": 280, "request_count": 3600},
        {"service_name": "CDN 加速", "service_type": "网络服务", "avg_response_time": 25, "request_count": 35000},
        {"service_name": "负载均衡器", "service_type": "网络服务", "avg_response_time": 15, "request_count": 45000},
        {"service_name": "日志收集服务", "service_type": "监控服务", "avg_response_time": 95, "request_count": 22000},
        {"service_name": "图像识别服务", "service_type": "AI 服务", "avg_response_time": 850, "request_count": 1200},
    ]
    
    # 添加状态字段
    for service in services:
        if service["avg_response_time"] < 100:
            service["status"] = "正常"
        elif service["avg_response_time"] < 500:
            service["status"] = "警告"
        else:
            service["status"] = "异常"
    
    return pd.DataFrame(services)

# 加载数据
df = generate_mock_data()

# 侧边栏
with st.sidebar:
    st.header("🔧 过滤器")
    
    # 服务类型筛选
    service_types = ["全部"] + sorted(df["service_type"].unique().tolist())
    selected_type = st.selectbox(
        "选择服务类型",
        service_types,
        help="筛选特定类型的服务进行查看"
    )
    
    # 状态筛选
    status_options = ["全部", "正常", "警告", "异常"]
    selected_status = st.radio(
        "服务状态",
        status_options,
        help="根据响应时间自动判断的服务状态"
    )
    
    # 排序选项
    sort_option = st.selectbox(
        "排序方式",
        ["响应时间升序", "响应时间降序", "请求量降序"],
        help="选择图表和表格的排序方式"
    )
    
    st.divider()
    
    # 显示数据更新时间
    st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("💡 提示：数据为 Mock 数据")

# 主标题
st.title("⚡ 服务响应时效监控")
st.markdown("实时监控各服务类型的平均响应时间，快速识别性能瓶颈")
st.divider()

# 数据筛选
filtered_df = df.copy()

if selected_type != "全部":
    filtered_df = filtered_df[filtered_df["service_type"] == selected_type]

if selected_status != "全部":
    filtered_df = filtered_df[filtered_df["status"] == selected_status]

# 数据排序
if sort_option == "响应时间升序":
    filtered_df = filtered_df.sort_values("avg_response_time", ascending=True)
elif sort_option == "响应时间降序":
    filtered_df = filtered_df.sort_values("avg_response_time", ascending=False)
elif sort_option == "请求量降序":
    filtered_df = filtered_df.sort_values("request_count", ascending=False)

# 统计指标
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📦 总服务数",
        value=len(filtered_df),
        help="当前筛选条件下的服务总数"
    )

with col2:
    avg_time = filtered_df["avg_response_time"].mean()
    st.metric(
        label="⏱️ 平均响应时间",
        value=f"{avg_time:.1f} ms",
        help="所有服务的平均响应时间"
    )

with col3:
    if len(filtered_df) > 0:
        fastest = filtered_df.loc[filtered_df["avg_response_time"].idxmin()]
        st.metric(
            label="🚀 最快服务",
            value=fastest["service_name"],
            delta=f"{fastest['avg_response_time']} ms"
        )
    else:
        st.metric(label="🚀 最快服务", value="N/A")

with col4:
    if len(filtered_df) > 0:
        slowest = filtered_df.loc[filtered_df["avg_response_time"].idxmax()]
        st.metric(
            label="🐢 最慢服务",
            value=slowest["service_name"],
            delta=f"-{slowest['avg_response_time']} ms",
            delta_color="inverse"
        )
    else:
        st.metric(label="🐢 最慢服务", value="N/A")

st.divider()

# 创建图表
col_chart1, col_chart2 = st.columns([3, 1])

with col_chart1:
    st.subheader("📊 服务响应时间条形图")
    
    # 创建颜色映射 - 根据响应时间
    filtered_df["color"] = filtered_df["avg_response_time"].apply(
        lambda x: "正常" if x < 100 else ("警告" if x < 500 else "异常")
    )
    
    # 创建 Plotly 条形图
    fig = px.bar(
        filtered_df,
        x="avg_response_time",
        y="service_name",
        orientation="h",
        color="avg_response_time",
        color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"],
        text="avg_response_time",
        title="各服务平均响应时间对比 (单位：ms)",
        hover_data={
            "service_type": True,
            "request_count": True,
            "status": True,
            "avg_response_time": ":.1f"
        }
    )
    
    # 更新图表布局
    fig.update_layout(
        xaxis_title="响应时间 (ms)",
        yaxis_title="服务名称",
        showlegend=False,
        height=500,
        xaxis=dict(
            showgrid=True,
            gridstyle="dash",
            gridcolor="rgba(0,0,0,0.1)"
        ),
        yaxis=dict(
            showgrid=False,
            categoryorder="total ascending" if sort_option == "响应时间升序" else "total descending"
        )
    )
    
    # 更新文本标签
    fig.update_traces(
        texttemplate="%{text:.0f} ms",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>" +
                     "响应时间：%{x:.0f} ms<br>" +
                     "服务类型：%{customdata[0]}<br>" +
                     "请求量：%{customdata[1]:,}<br>" +
                     "状态：%{customdata[2]}<extra></extra>"
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    st.subheader("📈 状态分布")
    
    # 状态统计
    status_count = filtered_df["status"].value_counts()
    
    # 创建状态分布饼图
    if len(status_count) > 0:
        fig_pie = px.pie(
            values=status_count.values,
            names=status_count.index,
            color=status_count.index,
            color_discrete_map={
                "正常": "#10B981",
                "警告": "#F59E0B",
                "异常": "#EF4444"
            },
            hole=0.4
        )
        
        fig_pie.update_layout(
            height=300,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # 显示各类型服务数量
    st.subheader("📋 服务类型分布")
    if len(filtered_df) > 0:
        type_count = filtered_df["service_type"].value_counts()
        st.dataframe(
            type_count.to_frame(name="服务数量"),
            use_container_width=True,
            hide_index=True
        )

# 详细数据表格
st.divider()
st.subheader("📋 详细数据")

# 显示数据表格
display_df = filtered_df[["service_name", "service_type", "avg_response_time", "request_count", "status"]].copy()
display_df.columns = ["服务名称", "服务类型", "平均响应时间 (ms)", "请求量", "状态"]

# 添加颜色标记
def color_status(val):
    if val == "正常":
        return "background-color: #D1FAE5; color: #065F46"
    elif val == "警告":
        return "background-color: #FEF3C7; color: #92400E"
    elif val == "异常":
        return "background-color: #FEE2E2; color: #991B1B"
    return ""

st.dataframe(
    display_df.style.applymap(color_status, subset=["状态"]),
    use_container_width=True,
    hide_index=True
)

# 底部信息
st.divider()
col_footer1, col_footer2 = st.columns(2)

with col_footer1:
    st.caption("💡 使用说明：数据仅供参考，实际生产环境请接入真实监控数据")

with col_footer2:
    st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
