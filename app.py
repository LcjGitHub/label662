import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import csv
import json
import math

st.set_page_config(
    page_title="服务响应时效监控",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    .clickable-card {
        cursor: pointer;
        transition: all 0.2s;
        border-radius: 8px;
        padding: 12px 16px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .clickable-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .clickable-card-warning {
        border-left: 4px solid #F59E0B;
    }
    .clickable-card-critical {
        border-left: 4px solid #EF4444;
    }
    .clickable-card-normal {
        border-left: 4px solid #10B981;
    }
</style>
""", unsafe_allow_html=True)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALERTS_CSV = os.path.join(DATA_DIR, "alerts.csv")
THRESHOLDS_CSV = os.path.join(DATA_DIR, "thresholds.csv")
SERVICE_STATUS_CSV = os.path.join(DATA_DIR, "service_status.csv")
DEPENDENCIES_JSON = os.path.join(DATA_DIR, "service_dependencies.json")

os.makedirs(DATA_DIR, exist_ok=True)

ALERT_COLUMNS = [
    "alert_id", "service_name", "service_type", "alert_level",
    "alert_time", "response_time", "warning_threshold",
    "critical_threshold", "status", "resolved_time"
]

THRESHOLD_COLUMNS = ["service_type", "warning_threshold", "critical_threshold"]

SERVICE_STATUS_COLUMNS = ["service_name", "last_status", "last_check_time"]

DEFAULT_THRESHOLDS = {
    "网关服务": {"warning_threshold": 200, "critical_threshold": 500},
    "认证服务": {"warning_threshold": 150, "critical_threshold": 300},
    "数据库": {"warning_threshold": 100, "critical_threshold": 300},
    "缓存服务": {"warning_threshold": 20, "critical_threshold": 50},
    "存储服务": {"warning_threshold": 300, "critical_threshold": 800},
    "消息服务": {"warning_threshold": 100, "critical_threshold": 300},
    "搜索服务": {"warning_threshold": 300, "critical_threshold": 600},
    "支付服务": {"warning_threshold": 500, "critical_threshold": 1000},
    "通知服务": {"warning_threshold": 400, "critical_threshold": 800},
    "网络服务": {"warning_threshold": 50, "critical_threshold": 150},
    "监控服务": {"warning_threshold": 200, "critical_threshold": 500},
    "AI 服务": {"warning_threshold": 1000, "critical_threshold": 2000},
}


def init_csv_files():
    if not os.path.exists(ALERTS_CSV):
        with open(ALERTS_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=ALERT_COLUMNS)
            writer.writeheader()

    if not os.path.exists(THRESHOLDS_CSV):
        with open(THRESHOLDS_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=THRESHOLD_COLUMNS)
            writer.writeheader()
            for stype, thresholds in DEFAULT_THRESHOLDS.items():
                writer.writerow({
                    "service_type": stype,
                    "warning_threshold": thresholds["warning_threshold"],
                    "critical_threshold": thresholds["critical_threshold"]
                })

    if not os.path.exists(SERVICE_STATUS_CSV):
        with open(SERVICE_STATUS_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=SERVICE_STATUS_COLUMNS)
            writer.writeheader()


init_csv_files()


def load_thresholds():
    if os.path.exists(THRESHOLDS_CSV):
        df = pd.read_csv(THRESHOLDS_CSV, encoding="utf-8-sig")
        thresholds = {}
        for _, row in df.iterrows():
            thresholds[row["service_type"]] = {
                "warning_threshold": float(row["warning_threshold"]),
                "critical_threshold": float(row["critical_threshold"])
            }
        return thresholds
    return DEFAULT_THRESHOLDS.copy()


def save_thresholds(thresholds):
    with open(THRESHOLDS_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=THRESHOLD_COLUMNS)
        writer.writeheader()
        for stype, th in thresholds.items():
            writer.writerow({
                "service_type": stype,
                "warning_threshold": th["warning_threshold"],
                "critical_threshold": th["critical_threshold"]
            })


def load_alerts():
    if os.path.exists(ALERTS_CSV):
        dtype_map = {
            "alert_id": str, "service_name": str, "service_type": str,
            "alert_level": str, "alert_time": str, "response_time": float,
            "warning_threshold": float, "critical_threshold": float,
            "status": str, "resolved_time": str
        }
        df = pd.read_csv(ALERTS_CSV, encoding="utf-8-sig", dtype=dtype_map, keep_default_na=False)
        if df.empty:
            return pd.DataFrame(columns=ALERT_COLUMNS)
        return df
    return pd.DataFrame(columns=ALERT_COLUMNS)


def save_alert(alert_data):
    file_exists = os.path.exists(ALERTS_CSV)
    with open(ALERTS_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ALERT_COLUMNS)
        if not file_exists or os.path.getsize(ALERTS_CSV) == 0:
            writer.writeheader()
        writer.writerow(alert_data)


def update_alert_status(alert_id, status):
    df = load_alerts()
    if not df.empty and alert_id in df["alert_id"].values:
        df.loc[df["alert_id"] == alert_id, "status"] = status
        if status == "已处理":
            df.loc[df["alert_id"] == alert_id, "resolved_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.to_csv(ALERTS_CSV, index=False, encoding="utf-8-sig")


def batch_resolve_alerts(alert_ids):
    df = load_alerts()
    if not df.empty:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mask = df["alert_id"].isin(alert_ids)
        df.loc[mask, "status"] = "已处理"
        df.loc[mask, "resolved_time"] = now_str
        df.to_csv(ALERTS_CSV, index=False, encoding="utf-8-sig")


def load_service_status():
    if os.path.exists(SERVICE_STATUS_CSV):
        dtype_map = {
            "service_name": str, "last_status": str, "last_check_time": str
        }
        df = pd.read_csv(SERVICE_STATUS_CSV, encoding="utf-8-sig", dtype=dtype_map, keep_default_na=False)
        status_map = {}
        for _, row in df.iterrows():
            status_map[row["service_name"]] = {
                "last_status": row["last_status"],
                "last_check_time": row["last_check_time"]
            }
        return status_map
    return {}


def save_service_status(status_map):
    with open(SERVICE_STATUS_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SERVICE_STATUS_COLUMNS)
        writer.writeheader()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for sname, info in status_map.items():
            writer.writerow({
                "service_name": sname,
                "last_status": info.get("last_status", ""),
                "last_check_time": now_str
            })


def generate_alert_id():
    return f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}{np.random.randint(1000, 9999)}"


def get_service_status(response_time, warning_threshold, critical_threshold):
    if response_time >= critical_threshold:
        return "异常"
    elif response_time >= warning_threshold:
        return "警告"
    else:
        return "正常"


@st.cache_data
def generate_mock_data():
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
        {"service_name": "图像识别服务", "service_type": "AI 服务", "avg_response_time": 1200, "request_count": 1200},
    ]
    return pd.DataFrame(services)


def detect_and_record_alerts(services_df, thresholds):
    last_status_map = load_service_status()
    current_status_map = {}
    new_alerts = []

    for _, service in services_df.iterrows():
        stype = service["service_type"]
        sname = service["service_name"]
        rt = service["avg_response_time"]

        th = thresholds.get(stype, {"warning_threshold": 100, "critical_threshold": 500})
        warning_th = th["warning_threshold"]
        critical_th = th["critical_threshold"]
        current_status = get_service_status(rt, warning_th, critical_th)

        last_info = last_status_map.get(sname, {})
        last_status = last_info.get("last_status", "")

        current_status_map[sname] = {
            "last_status": current_status,
            "last_check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if last_status == "正常" and current_status in ["警告", "异常"]:
            alert_level = "警告" if current_status == "警告" else "异常"
            alert_data = {
                "alert_id": generate_alert_id(),
                "service_name": sname,
                "service_type": stype,
                "alert_level": alert_level,
                "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "response_time": rt,
                "warning_threshold": warning_th,
                "critical_threshold": critical_th,
                "status": "未处理",
                "resolved_time": ""
            }
            new_alerts.append(alert_data)
            save_alert(alert_data)

    save_service_status(current_status_map)

    return new_alerts


def color_status(val):
    if val == "正常":
        return "background-color: #D1FAE5; color: #065F46"
    elif val == "警告":
        return "background-color: #FEF3C7; color: #92400E"
    elif val == "异常":
        return "background-color: #FEE2E2; color: #991B1B"
    elif val == "已处理":
        return "background-color: #DBEAFE; color: #1E40AF"
    elif val == "未处理":
        return "background-color: #FEE2E2; color: #991B1B"
    return ""


def get_unresolved_alert_count():
    alerts_df = load_alerts()
    if alerts_df.empty:
        return 0
    return len(alerts_df[alerts_df["status"] == "未处理"])


def get_status_for_row(row, thresholds):
    stype = row["service_type"]
    th = thresholds.get(stype, {"warning_threshold": 100, "critical_threshold": 500})
    return get_service_status(row["avg_response_time"], th["warning_threshold"], th["critical_threshold"])


def load_dependencies():
    if os.path.exists(DEPENDENCIES_JSON):
        with open(DEPENDENCIES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": [], "edges": []}


def get_node_by_id(dep_data, node_id):
    for node in dep_data["nodes"]:
        if node["id"] == node_id:
            return node
    return None


def get_upstream_services(dep_data, node_id):
    upstream = []
    for edge in dep_data["edges"]:
        if edge["target"] == node_id:
            src = get_node_by_id(dep_data, edge["source"])
            if src:
                upstream.append({**src, "call_frequency": edge["call_frequency"], "description": edge.get("description", "")})
    return upstream


def get_downstream_services(dep_data, node_id):
    downstream = []
    for edge in dep_data["edges"]:
        if edge["source"] == node_id:
            tgt = get_node_by_id(dep_data, edge["target"])
            if tgt:
                downstream.append({**tgt, "call_frequency": edge["call_frequency"], "description": edge.get("description", "")})
    return downstream


def find_all_affected_downstream(dep_data, node_id):
    affected = set()
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        for edge in dep_data["edges"]:
            if edge["source"] == current and edge["target"] not in affected:
                affected.add(edge["target"])
                queue.append(edge["target"])
    return affected


def compute_circular_layout(dep_data):
    nodes = dep_data["nodes"]
    n = len(nodes)
    positions = {}
    radius = 1.0
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n - math.pi / 2
        positions[node["id"]] = {
            "x": radius * math.cos(angle),
            "y": radius * math.sin(angle)
        }
    return positions


def get_status_color(status):
    if status == "正常":
        return "#10B981"
    elif status == "警告":
        return "#F59E0B"
    elif status == "异常":
        return "#EF4444"
    return "#6B7280"


def get_service_info_map(dep_data, services_df, thresholds):
    info_map = {}
    for _, row in services_df.iterrows():
        sname = row["service_name"]
        stype = row["service_type"]
        status = get_status_for_row(row, thresholds)
        info_map[sname] = {
            "service_type": stype,
            "avg_response_time": row["avg_response_time"],
            "request_count": row["request_count"],
            "status": status
        }
    for node in dep_data["nodes"]:
        if node["name"] not in info_map:
            info_map[node["name"]] = {
                "service_type": node["type"],
                "avg_response_time": np.random.randint(30, 200),
                "request_count": np.random.randint(1000, 10000),
                "status": "正常"
            }
    return info_map


def generate_trend_data(service_name, service_type, base_rt, time_range="24h", granularity="hour"):
    np.random.seed(hash(service_name) % 2**32)

    if time_range == "24h":
        if granularity == "hour":
            num_points = 24
            time_points = [datetime.now() - timedelta(hours=i) for i in range(num_points - 1, -1, -1)]
        else:
            num_points = 96
            time_points = [datetime.now() - timedelta(minutes=15 * i) for i in range(num_points - 1, -1, -1)]
    else:
        if granularity == "day":
            num_points = 7
            time_points = [datetime.now() - timedelta(days=i) for i in range(num_points - 1, -1, -1)]
        else:
            num_points = 7 * 24
            time_points = [datetime.now() - timedelta(hours=i) for i in range(num_points - 1, -1, -1)]

    volatility = np.random.uniform(0.05, 0.35)
    trend = np.random.uniform(-0.02, 0.02)
    daily_pattern = np.sin(np.linspace(0, 2 * np.pi, num_points)) * 0.15

    response_times = []
    for i in range(num_points):
        noise = np.random.normal(0, volatility * base_rt)
        trend_component = trend * i * base_rt
        pattern_component = daily_pattern[i] * base_rt
        rt = base_rt + noise + trend_component + pattern_component
        if np.random.random() < 0.05:
            rt *= np.random.uniform(1.5, 3.0)
        rt = max(1, rt)
        response_times.append(round(rt, 1))

    df = pd.DataFrame({
        "timestamp": time_points,
        "service_name": service_name,
        "service_type": service_type,
        "response_time": response_times
    })
    return df


def generate_all_trends_data(time_range="24h", granularity="hour"):
    services_df = generate_mock_data()
    all_data = []
    for _, row in services_df.iterrows():
        trend_df = generate_trend_data(
            row["service_name"],
            row["service_type"],
            row["avg_response_time"],
            time_range,
            granularity
        )
        all_data.append(trend_df)
    return pd.concat(all_data, ignore_index=True)


def compute_performance_metrics(trend_df):
    if trend_df.empty:
        return {}
    rts = trend_df["response_time"].values
    mean_rt = float(np.mean(rts))
    max_rt = float(np.max(rts))
    min_rt = float(np.min(rts))
    std_rt = float(np.std(rts))
    volatility = (std_rt / mean_rt * 100) if mean_rt > 0 else 0
    stability_score = max(0, 100 - volatility * 1.5)
    return {
        "avg_response_time": round(mean_rt, 1),
        "max_response_time": round(max_rt, 1),
        "min_response_time": round(min_rt, 1),
        "volatility": round(volatility, 2),
        "stability_score": round(stability_score, 1),
        "std_response_time": round(std_rt, 1)
    }


def detect_anomalies(trend_df, threshold_z=2.0):
    if trend_df.empty:
        return trend_df
    rts = trend_df["response_time"].values
    mean = np.mean(rts)
    std = np.std(rts)
    if std == 0:
        anomalies = trend_df.iloc[0:0]
    else:
        z_scores = np.abs((rts - mean) / std)
        anomalies = trend_df[z_scores > threshold_z].copy()
    return anomalies


def get_top_volatile_services(top_n=5):
    trends_24h = generate_all_trends_data("24h", "hour")
    services_df = generate_mock_data()
    volatility_list = []
    for sname in trends_24h["service_name"].unique():
        sdf = trends_24h[trends_24h["service_name"] == sname]
        metrics = compute_performance_metrics(sdf)
        stype = services_df[services_df["service_name"] == sname]["service_type"].values[0]
        volatility_list.append({
            "service_name": sname,
            "service_type": stype,
            "volatility": metrics.get("volatility", 0),
            "stability_score": metrics.get("stability_score", 0),
            "avg_response_time": metrics.get("avg_response_time", 0),
            "max_response_time": metrics.get("max_response_time", 0)
        })
    volatility_df = pd.DataFrame(volatility_list)
    volatility_df = volatility_df.sort_values("volatility", ascending=False).head(top_n)
    return volatility_df


def render_dashboard_page():
    df = generate_mock_data()
    thresholds = load_thresholds()

    detect_and_record_alerts(df, thresholds)

    df_with_status = df.copy()
    df_with_status["status"] = df_with_status.apply(
        lambda row: get_status_for_row(row, thresholds), axis=1
    )

    with st.sidebar:
        st.header("🔧 过滤器")

        service_types = ["全部"] + sorted(df_with_status["service_type"].unique().tolist())
        selected_type = st.selectbox(
            "选择服务类型",
            service_types,
            help="筛选特定类型的服务进行查看"
        )

        status_options = ["全部", "正常", "警告", "异常"]
        selected_status = st.radio(
            "服务状态",
            status_options,
            help="根据响应时间自动判断的服务状态"
        )

        sort_option = st.selectbox(
            "排序方式",
            ["响应时间升序", "响应时间降序", "请求量降序"],
            help="选择图表和表格的排序方式"
        )

        st.divider()

        st.header("🔔 告警管理")
        unresolved_count = get_unresolved_alert_count()

        card_class = "clickable-card-normal"
        if unresolved_count > 0:
            alerts_df = load_alerts()
            if not alerts_df.empty:
                unresolved_critical = len(alerts_df[(alerts_df["status"] == "未处理") & (alerts_df["alert_level"] == "异常")])
                card_class = "clickable-card-critical" if unresolved_critical > 0 else "clickable-card-warning"

        st.markdown(f"""
        <div class="clickable-card {card_class}">
            <div style="font-size: 14px; color: #6B7280; margin-bottom: 4px;">
                🔔 未处理告警
            </div>
            <div style="font-size: 28px; font-weight: 700; color: #111827;">
                {unresolved_count} 条
            </div>
            <div style="font-size: 12px; color: #6B7280; margin-top: 4px;">
                点击下方按钮查看详情
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📋 查看告警历史", use_container_width=True, type="primary" if unresolved_count > 0 else "secondary", key="sidebar_alert_btn"):
            st.session_state["page"] = "alerts"
            st.rerun()

        if st.button("📈 性能趋势分析", use_container_width=True, type="secondary", key="sidebar_trend_btn"):
            st.session_state["page"] = "trend"
            st.rerun()

        if st.button("🔗 服务依赖关系", use_container_width=True, type="secondary", key="sidebar_dep_btn"):
            st.session_state["page"] = "dependency"
            st.rerun()

        st.divider()

        st.subheader("⚙️ 告警阈值设置")
        all_service_types = sorted(df_with_status["service_type"].unique().tolist())
        for stype in all_service_types:
            current = thresholds.get(stype, {"warning_threshold": 100, "critical_threshold": 500})
            with st.expander(f"{stype}", expanded=False):
                col_w, col_c = st.columns(2)
                with col_w:
                    new_warning = st.number_input(
                        "警告阈值 (ms)",
                        min_value=1,
                        max_value=10000,
                        value=int(current["warning_threshold"]),
                        key=f"warn_{stype}"
                    )
                with col_c:
                    new_critical = st.number_input(
                        "异常阈值 (ms)",
                        min_value=1,
                        max_value=10000,
                        value=int(current["critical_threshold"]),
                        key=f"crit_{stype}"
                    )
                if new_warning >= new_critical:
                    st.warning("⚠️ 警告阈值应小于异常阈值")
                thresholds[stype] = {
                    "warning_threshold": new_warning,
                    "critical_threshold": new_critical
                }

        if st.button("💾 保存阈值设置", use_container_width=True, type="primary", key="save_th_dash"):
            save_thresholds(thresholds)
            st.success("✅ 阈值设置已保存！")
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption("💡 提示：数据为 Mock 数据")

    st.title("⚡ 服务响应时效监控")
    st.markdown("实时监控各服务类型的平均响应时间，快速识别性能瓶颈")
    st.divider()

    filtered_df = df_with_status.copy()

    if selected_type != "全部":
        filtered_df = filtered_df[filtered_df["service_type"] == selected_type]

    if selected_status != "全部":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    if sort_option == "响应时间升序":
        filtered_df = filtered_df.sort_values("avg_response_time", ascending=True)
    elif sort_option == "响应时间降序":
        filtered_df = filtered_df.sort_values("avg_response_time", ascending=False)
    elif sort_option == "请求量降序":
        filtered_df = filtered_df.sort_values("request_count", ascending=False)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="📦 总服务数",
            value=len(filtered_df),
            help="当前筛选条件下的服务总数"
        )

    with col2:
        avg_time = filtered_df["avg_response_time"].mean() if len(filtered_df) > 0 else 0
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

    with col5:
        alert_label = "🔔 未处理告警"
        if unresolved_count > 0:
            alert_label = "🚨 未处理告警"
        st.metric(
            label=alert_label,
            value=f"{unresolved_count} 条",
            help="点击下方按钮跳转到告警历史页"
        )
        if st.button("📋 查看告警历史", use_container_width=True, type="primary" if unresolved_count > 0 else "secondary", key="metric_alert_btn"):
            st.session_state["page"] = "alerts"
            st.rerun()

    st.divider()

    col_chart1, col_chart2 = st.columns([3, 1])

    with col_chart1:
        st.subheader("📊 服务响应时间条形图")

        chart_df = filtered_df.copy()
        chart_df["status_color"] = chart_df.apply(
            lambda row: get_status_for_row(row, thresholds), axis=1
        )

        fig = px.bar(
            chart_df,
            x="avg_response_time",
            y="service_name",
            orientation="h",
            color="status_color",
            color_discrete_map={
                "正常": "#10B981",
                "警告": "#F59E0B",
                "异常": "#EF4444"
            },
            text="avg_response_time",
            title="各服务平均响应时间对比 (单位：ms)",
            hover_data={
                "service_type": True,
                "request_count": True,
                "status_color": True,
                "avg_response_time": ":.1f"
            }
        )

        fig.update_layout(
            xaxis_title="响应时间 (ms)",
            yaxis_title="服务名称",
            showlegend=True,
            legend_title="服务状态",
            height=500,
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)"
            ),
            yaxis=dict(
                showgrid=False
            )
        )

        if sort_option == "响应时间升序":
            fig.update_yaxes(categoryorder="total ascending")
        elif sort_option == "响应时间降序":
            fig.update_yaxes(categoryorder="total descending")

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

        status_count = filtered_df["status"].value_counts()

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

        st.subheader("📋 服务类型分布")
        if len(filtered_df) > 0:
            type_count = filtered_df["service_type"].value_counts()
            st.dataframe(
                type_count.to_frame(name="服务数量"),
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        st.subheader("🔥 性能波动排行榜 Top5")
        top_volatile = get_top_volatile_services(5)
        if not top_volatile.empty:
            ranked_services = top_volatile.reset_index(drop=True)
            for rank_idx, row in ranked_services.iterrows():
                rank = rank_idx + 1
                volatility = row["volatility"]
                if volatility >= 30:
                    color = "#EF4444"
                elif volatility >= 15:
                    color = "#F59E0B"
                else:
                    color = "#10B981"
                st.markdown(f"""
                <div style="
                    padding: 8px 10px;
                    border-radius: 6px;
                    margin-bottom: 6px;
                    background-color: white;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    border-left: 3px solid {color};
                ">
                    <div style="font-size: 12px; color: #6B7280;">
                        🏆 第 {rank} 名
                    </div>
                    <div style="font-size: 13px; font-weight: 600;">
                        {row["service_name"]}
                    </div>
                    <div style="font-size: 11px; color: #6B7280;">
                        波动率: <span style="color: {color}; font-weight: 600;">{volatility:.1f}%</span>
                        | 稳定: {row["stability_score"]:.0f}分
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if st.button("📈 查看详细趋势分析", use_container_width=True, type="secondary", key="go_to_trend"):
                st.session_state["page"] = "trend"
                st.rerun()
        else:
            st.info("暂无波动数据")

    st.divider()
    st.subheader("📋 详细数据")

    display_df = filtered_df[["service_name", "service_type", "avg_response_time", "request_count", "status"]].copy()
    display_df.columns = ["服务名称", "服务类型", "平均响应时间 (ms)", "请求量", "状态"]

    st.dataframe(
        display_df.style.applymap(color_status, subset=["状态"]),
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    col_footer1, col_footer2 = st.columns(2)

    with col_footer1:
        st.caption("💡 使用说明：数据仅供参考，实际生产环境请接入真实监控数据")

    with col_footer2:
        st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_alerts_page():
    with st.sidebar:
        st.header("🔔 告警管理")

        if st.button("← 返回监控首页", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()

        if st.button("📈 性能趋势分析", use_container_width=True, type="secondary", key="alt_sidebar_trend_btn"):
            st.session_state["page"] = "trend"
            st.rerun()

        if st.button("🔗 服务依赖关系", use_container_width=True, type="secondary", key="alt_sidebar_dep_btn"):
            st.session_state["page"] = "dependency"
            st.rerun()

        st.divider()

        st.subheader("🔍 告警筛选")

        alerts_df_raw = load_alerts()

        all_services = ["全部"]
        if not alerts_df_raw.empty:
            all_services += sorted(alerts_df_raw["service_name"].unique().tolist())

        alert_levels = ["全部", "警告", "异常"]
        alert_statuses = ["全部", "未处理", "已处理"]

        selected_level = st.selectbox(
            "告警级别",
            alert_levels,
            help="按告警级别筛选"
        )

        selected_alert_status = st.selectbox(
            "告警状态",
            alert_statuses,
            help="按处理状态筛选"
        )

        selected_service = st.selectbox(
            "服务名称",
            all_services,
            help="按服务名称筛选"
        )

        st.caption("📅 时间范围")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=7),
                help="告警开始日期"
            )
        with col_t2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                help="告警结束日期"
            )

        st.divider()
        st.subheader("⚙️ 告警阈值设置")
        thresholds = load_thresholds()
        df = generate_mock_data()
        all_service_types = sorted(df["service_type"].unique().tolist())
        for stype in all_service_types:
            current = thresholds.get(stype, {"warning_threshold": 100, "critical_threshold": 500})
            with st.expander(f"{stype}", expanded=False):
                col_w, col_c = st.columns(2)
                with col_w:
                    new_warning = st.number_input(
                        "警告阈值 (ms)",
                        min_value=1,
                        max_value=10000,
                        value=int(current["warning_threshold"]),
                        key=f"alt_warn_{stype}"
                    )
                with col_c:
                    new_critical = st.number_input(
                        "异常阈值 (ms)",
                        min_value=1,
                        max_value=10000,
                        value=int(current["critical_threshold"]),
                        key=f"alt_crit_{stype}"
                    )
                if new_warning >= new_critical:
                    st.warning("⚠️ 警告阈值应小于异常阈值")
                thresholds[stype] = {
                    "warning_threshold": new_warning,
                    "critical_threshold": new_critical
                }

        if st.button("💾 保存阈值设置", use_container_width=True, type="primary", key="save_th_alert"):
            save_thresholds(thresholds)
            st.success("✅ 阈值设置已保存！")
            st.rerun()

        st.divider()
        st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.title("🔔 告警历史记录")
    st.markdown("查看所有历史告警记录，支持多条件筛选和批量处理")
    st.divider()

    alerts_df = load_alerts()

    if not alerts_df.empty:
        alerts_df["alert_time_dt"] = pd.to_datetime(alerts_df["alert_time"])
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        alerts_df = alerts_df[(alerts_df["alert_time_dt"] >= start_dt) & (alerts_df["alert_time_dt"] <= end_dt)]

        if selected_level != "全部":
            alerts_df = alerts_df[alerts_df["alert_level"] == selected_level]

        if selected_alert_status != "全部":
            alerts_df = alerts_df[alerts_df["status"] == selected_alert_status]

        if selected_service != "全部":
            alerts_df = alerts_df[alerts_df["service_name"] == selected_service]

        alerts_df = alerts_df.drop(columns=["alert_time_dt"])

    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

    total_alerts = len(alerts_df) if not alerts_df.empty else 0
    unresolved = len(alerts_df[alerts_df["status"] == "未处理"]) if not alerts_df.empty else 0
    warning_count = len(alerts_df[alerts_df["alert_level"] == "警告"]) if not alerts_df.empty else 0
    critical_count = len(alerts_df[alerts_df["alert_level"] == "异常"]) if not alerts_df.empty else 0

    with col_stats1:
        st.metric(label="📋 总告警数", value=f"{total_alerts} 条", help="筛选条件下的告警总数")

    with col_stats2:
        st.metric(label="⏳ 未处理", value=f"{unresolved} 条", delta=f"{unresolved}", delta_color="inverse",
                  help="尚未处理的告警数量")

    with col_stats3:
        st.metric(label="⚠️ 警告级别", value=f"{warning_count} 条", help="响应时间超过警告阈值的告警")

    with col_stats4:
        st.metric(label="🚨 异常级别", value=f"{critical_count} 条", help="响应时间超过异常阈值的告警")

    st.divider()

    col_actions1, col_actions2, col_actions3 = st.columns([2, 1, 1])
    with col_actions1:
        st.subheader("📋 告警列表")
    with col_actions2:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    with col_actions3:
        unresolved_ids = []
        if not alerts_df.empty:
            unresolved_ids = alerts_df[alerts_df["status"] == "未处理"]["alert_id"].tolist()
        if st.button("✅ 一键处理所有未处理", use_container_width=True, disabled=len(unresolved_ids) == 0,
                     type="primary"):
            batch_resolve_alerts(unresolved_ids)
            st.success(f"✅ 已批量处理 {len(unresolved_ids)} 条告警！")
            st.rerun()

    if alerts_df.empty:
        st.info("🎉 暂无告警记录，系统运行正常！")
    else:
        display_alerts = alerts_df.copy()
        display_alerts = display_alerts.sort_values("alert_time", ascending=False)

        for idx, row in display_alerts.iterrows():
            is_critical = row["alert_level"] == "异常"
            is_unresolved = row["status"] == "未处理"

            border_color = "#EF4444" if is_critical else "#F59E0B"
            bg_color = "#FEF2F2" if (is_critical and is_unresolved) else ("#FFFBEB" if is_unresolved else "#F9FAFB")

            with st.container():
                st.markdown(f"""
                <div style="
                    padding: 16px 20px;
                    border-radius: 8px;
                    border-left: 4px solid {border_color};
                    background-color: {bg_color};
                    margin-bottom: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">
                                {'🚨' if is_critical else '⚠️'} {row['service_name']}
                                <span style="
                                    margin-left: 8px;
                                    padding: 2px 8px;
                                    border-radius: 4px;
                                    font-size: 12px;
                                    background-color: {'#EF4444' if is_critical else '#F59E0B'};
                                    color: white;
                                ">{row['alert_level']}</span>
                                <span style="
                                    margin-left: 8px;
                                    padding: 2px 8px;
                                    border-radius: 4px;
                                    font-size: 12px;
                                    background-color: {'#EF4444' if is_unresolved else '#10B981'};
                                    color: white;
                                ">{row['status']}</span>
                            </div>
                            <div style="font-size: 13px; color: #6B7280; margin-bottom: 8px;">
                                <span style="margin-right: 16px;">🏷️ {row['service_type']}</span>
                                <span style="margin-right: 16px;">⏰ {row['alert_time']}</span>
                                {'<span>✅ 处理时间：' + str(row['resolved_time']) + '</span>' if str(row['resolved_time']) != '' else ''}
                            </div>
                            <div style="font-size: 14px;">
                                <span style="margin-right: 20px;">
                                    响应时间：<strong style="color: {'#EF4444' if is_critical else '#F59E0B'};">{row['response_time']:.0f} ms</strong>
                                </span>
                                <span style="margin-right: 20px;">
                                    警告阈值：<strong>{row['warning_threshold']:.0f} ms</strong>
                                </span>
                                <span>
                                    异常阈值：<strong>{row['critical_threshold']:.0f} ms</strong>
                                </span>
                            </div>
                        </div>
                """, unsafe_allow_html=True)

                if is_unresolved:
                    col_btn1, col_btn2 = st.columns([1, 5])
                    with col_btn1:
                        if st.button(f"✅ 标记已处理", key=f"resolve_{row['alert_id']}", type="primary"):
                            update_alert_status(row["alert_id"], "已处理")
                            st.success("✅ 告警已标记为已处理！")
                            st.rerun()
                    with col_btn2:
                        pass

                st.markdown("</div></div>", unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 告警数据表格")

        table_df = alerts_df.copy()
        table_df = table_df.sort_values("alert_time", ascending=False)
        table_display = table_df[[
            "alert_id", "service_name", "service_type", "alert_level",
            "alert_time", "response_time", "warning_threshold",
            "critical_threshold", "status", "resolved_time"
        ]].copy()
        table_display.columns = [
            "告警ID", "服务名称", "服务类型", "告警级别", "告警时间",
            "响应时间(ms)", "警告阈值(ms)", "异常阈值(ms)", "状态", "处理时间"
        ]

        st.dataframe(
            table_display.style.applymap(color_status, subset=["告警级别", "状态"]),
            use_container_width=True,
            hide_index=True,
            height=400
        )

    st.divider()
    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        st.caption(f"💾 告警数据持久化存储于：{ALERTS_CSV}")
    with col_footer2:
        st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_trend_page():
    services_df = generate_mock_data()
    all_service_names = sorted(services_df["service_name"].tolist())

    if "trend_selected_services" not in st.session_state:
        st.session_state["trend_selected_services"] = all_service_names[:3]

    with st.sidebar:
        st.header("📈 趋势分析")

        if st.button("← 返回监控首页", use_container_width=True, key="trend_back_btn"):
            st.session_state["page"] = "dashboard"
            st.rerun()

        if st.button("🔔 查看告警历史", use_container_width=True, type="secondary", key="trend_alert_btn"):
            st.session_state["page"] = "alerts"
            st.rerun()

        if st.button("🔗 服务依赖关系", use_container_width=True, type="secondary", key="trend_sidebar_dep_btn"):
            st.session_state["page"] = "dependency"
            st.rerun()

        st.divider()

        st.subheader("🕒 时间范围")
        time_range = st.radio(
            "选择分析周期",
            options=["24h", "7d"],
            format_func=lambda x: "过去 24 小时" if x == "24h" else "过去 7 天",
            help="选择趋势分析的时间范围",
            horizontal=True
        )

        st.subheader("⏱️ 时间粒度")
        if time_range == "24h":
            granularity = "hour"
            st.info("24 小时模式：按小时展示（24 个数据点）")
        else:
            granularity = st.radio(
                "数据粒度",
                options=["day", "hour"],
                format_func=lambda x: "按天" if x == "day" else "按小时",
                help="选择数据点的时间间隔",
                horizontal=True
            )

        st.divider()
        st.subheader("🔧 异常检测阈值")
        z_threshold = st.slider(
            "Z-Score 阈值",
            min_value=1.0,
            max_value=3.5,
            value=2.0,
            step=0.1,
            help="标准差倍数，数值越大异常检测越严格"
        )

        st.divider()
        st.caption(f"📊 数据生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption("💡 提示：趋势数据为模拟生成")

    st.title("📈 服务性能趋势分析")
    st.markdown("分析各服务响应时间的变化趋势，快速识别性能波动和异常")
    st.divider()

    st.subheader("🔍 选择服务进行对比分析")
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        selected_services = st.multiselect(
            "选择要分析的服务（可多选对比）",
            options=all_service_names,
            default=st.session_state["trend_selected_services"],
            help="选择一个或多个服务进行趋势对比分析",
            key="trend_multiselect"
        )
        if selected_services != st.session_state["trend_selected_services"]:
            st.session_state["trend_selected_services"] = selected_services
    with col_sel2:
        st.markdown("<div style='visibility:hidden;'>_</div>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("全选", use_container_width=True, key="trend_select_all"):
                st.session_state["trend_selected_services"] = all_service_names
                st.rerun()
        with col_b2:
            if st.button("清空", use_container_width=True, key="trend_clear_all"):
                st.session_state["trend_selected_services"] = []
                st.rerun()

    if not selected_services:
        st.warning("⚠️ 请至少选择一个服务进行趋势分析")
        st.info("💡 提示：从上方下拉框中选择一个或多个服务，或点击「全选」按钮选择所有服务")
        return

    trends_data = generate_all_trends_data(time_range, granularity)
    filtered_trends = trends_data[trends_data["service_name"].isin(selected_services)].copy()

    st.divider()

    all_metrics = []
    for sname in selected_services:
        sdf = filtered_trends[filtered_trends["service_name"] == sname]
        m = compute_performance_metrics(sdf)
        m["service_name"] = sname
        all_metrics.append(m)
    metrics_df = pd.DataFrame(all_metrics)

    st.subheader(f"📊 性能汇总指标（共 {len(selected_services)} 个服务）")
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    avg_of_avg = metrics_df["avg_response_time"].mean() if len(metrics_df) > 0 else 0
    overall_max = metrics_df["max_response_time"].max() if len(metrics_df) > 0 else 0
    overall_min = metrics_df["min_response_time"].min() if len(metrics_df) > 0 else 0
    avg_volatility = metrics_df["volatility"].mean() if len(metrics_df) > 0 else 0
    avg_stability = metrics_df["stability_score"].mean() if len(metrics_df) > 0 else 0

    with col_m1:
        st.metric(
            label="📊 平均响应时间（汇总）",
            value=f"{avg_of_avg:.1f} ms",
            help=f"所选 {len(selected_services)} 个服务的平均响应时间均值"
        )
    with col_m2:
        st.metric(
            label="⏫ 最大响应时间（汇总）",
            value=f"{overall_max:.1f} ms",
            help=f"所选 {len(selected_services)} 个服务中的最大响应时间",
            delta_color="inverse"
        )
    with col_m3:
        st.metric(
            label="⏬ 最小响应时间（汇总）",
            value=f"{overall_min:.1f} ms",
            help=f"所选 {len(selected_services)} 个服务中的最小响应时间"
        )
    with col_m4:
        vol_color = "normal" if avg_volatility < 15 else ("inverse" if avg_volatility >= 30 else "off")
        st.metric(
            label="📉 平均波动率（汇总）",
            value=f"{avg_volatility:.2f}%",
            delta=f"{avg_volatility:.2f}%",
            delta_color=vol_color,
            help=f"所选 {len(selected_services)} 个服务波动率的平均值"
        )
    with col_m5:
        stability_label = "🟢 优秀" if avg_stability >= 85 else ("🟡 一般" if avg_stability >= 70 else "🔴 较差")
        st.metric(
            label=f"⭐ 稳定性评分 {stability_label}（汇总）",
            value=f"{avg_stability:.1f} 分",
            help=f"所选 {len(selected_services)} 个服务稳定性评分的平均值"
        )

    if len(selected_services) >= 1:
        st.divider()
        st.subheader("📋 各服务性能指标")
        num_services = len(selected_services)
        for sidx in range(0, num_services, 1):
            sname = selected_services[sidx]
            s_metrics = metrics_df[metrics_df["service_name"] == sname].iloc[0]
            st.markdown(f"#### 🔹 {sname}")
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            with col_s1:
                st.metric(
                    label="平均响应时间",
                    value=f"{s_metrics['avg_response_time']:.1f} ms",
                    help=f"{sname} 的平均响应时间"
                )
            with col_s2:
                st.metric(
                    label="最大响应时间",
                    value=f"{s_metrics['max_response_time']:.1f} ms",
                    help=f"{sname} 的最大响应时间",
                    delta_color="inverse"
                )
            with col_s3:
                st.metric(
                    label="最小响应时间",
                    value=f"{s_metrics['min_response_time']:.1f} ms",
                    help=f"{sname} 的最小响应时间"
                )
            with col_s4:
                s_vol = s_metrics["volatility"]
                s_vol_color = "normal" if s_vol < 15 else ("inverse" if s_vol >= 30 else "off")
                st.metric(
                    label="波动率",
                    value=f"{s_vol:.2f}%",
                    delta=f"{s_vol:.2f}%",
                    delta_color=s_vol_color,
                    help=f"{sname} 的波动率（标准差/均值）"
                )
            with col_s5:
                s_stab = s_metrics["stability_score"]
                s_stab_label = "🟢 优秀" if s_stab >= 85 else ("🟡 一般" if s_stab >= 70 else "🔴 较差")
                st.metric(
                    label=f"稳定性评分 {s_stab_label}",
                    value=f"{s_stab:.1f} 分",
                    help=f"{sname} 的稳定性评分"
                )

    st.divider()

    st.subheader("📊 响应时间趋势图")
    st.caption("💡 提示：支持鼠标框选缩放，悬停查看详细数据，双击图表重置缩放")

    color_palette = px.colors.qualitative.Plotly

    fig = px.line(
        filtered_trends,
        x="timestamp",
        y="response_time",
        color="service_name",
        color_discrete_sequence=color_palette,
        markers=True,
        hover_data={
            "service_name": True,
            "service_type": True,
            "response_time": ":.1f",
            "timestamp": "|%Y-%m-%d %H:%M:%S"
        }
    )

    for idx, sname in enumerate(selected_services):
        sdf = filtered_trends[filtered_trends["service_name"] == sname]
        s_mean = sdf["response_time"].mean()
        color = color_palette[idx % len(color_palette)]
        fig.add_hline(
            y=s_mean,
            line_dash="dash",
            line_width=1.5,
            line_color=color,
            opacity=0.6,
            annotation_text=f"{sname} 平均值: {s_mean:.1f} ms",
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color=color
        )

        anomalies = detect_anomalies(sdf, z_threshold)
        if not anomalies.empty:
            fig.add_trace(
                px.scatter(
                    anomalies,
                    x="timestamp",
                    y="response_time",
                    color_discrete_sequence=["#EF4444"],
                ).data[0].update(
                    marker=dict(size=12, symbol="diamond", color="#EF4444", line=dict(width=2, color="white")),
                    name=f"{sname} ⚠️ 异常点",
                    hovertemplate=f"<b>{sname} - 异常点</b><br>" +
                                  "时间：%{x|%Y-%m-%d %H:%M:%S}<br>" +
                                  "响应时间：%{y:.1f} ms<br>" +
                                  "<extra></extra>"
                )
            )

    fig.update_layout(
        height=550,
        xaxis_title="时间",
        yaxis_title="响应时间 (ms)",
        legend_title="服务名称",
        hovermode="x unified",
        dragmode="zoom",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            rangeslider=dict(visible=True, thickness=0.05),
            type="date"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=True,
            zerolinecolor="rgba(0,0,0,0.2)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=20, r=20, t=40, b=100)
    )

    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=5),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                      "服务类型：%{customdata[1]}<br>" +
                      "时间：%{x|%Y-%m-%d %H:%M:%S}<br>" +
                      "响应时间：%{y:.1f} ms<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📋 各服务性能指标对比")
    if len(metrics_df) > 0:
        display_metrics = metrics_df[[
            "service_name", "avg_response_time", "max_response_time",
            "min_response_time", "std_response_time", "volatility", "stability_score"
        ]].copy()
        display_metrics.columns = [
            "服务名称", "平均响应时间(ms)", "最大响应时间(ms)",
            "最小响应时间(ms)", "标准差(ms)", "波动率(%)", "稳定性评分"
        ]

        def highlight_volatility(val):
            if val >= 30:
                return "background-color: #FEE2E2; color: #991B1B; font-weight: 600;"
            elif val >= 15:
                return "background-color: #FEF3C7; color: #92400E; font-weight: 600;"
            else:
                return "background-color: #D1FAE5; color: #065F46; font-weight: 600;"

        def highlight_stability(val):
            if val >= 85:
                return "background-color: #D1FAE5; color: #065F46; font-weight: 600;"
            elif val >= 70:
                return "background-color: #FEF3C7; color: #92400E; font-weight: 600;"
            else:
                return "background-color: #FEE2E2; color: #991B1B; font-weight: 600;"

        styled_metrics = display_metrics.style \
            .applymap(highlight_volatility, subset=["波动率(%)"]) \
            .applymap(highlight_stability, subset=["稳定性评分"])

        st.dataframe(
            styled_metrics,
            use_container_width=True,
            hide_index=True,
            height=min(400, 40 + len(display_metrics) * 35)
        )

    st.divider()

    if len(selected_services) >= 2:
        st.subheader("🔀 波动率对比")
        vol_chart_df = metrics_df[["service_name", "volatility", "stability_score"]].copy()
        fig_vol = px.bar(
            vol_chart_df,
            x="service_name",
            y="volatility",
            color="stability_score",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            text="volatility",
            title="各服务波动率对比 (%)",
            hover_data={
                "service_name": True,
                "volatility": ":.2f",
                "stability_score": ":.1f"
            }
        )
        fig_vol.update_layout(
            height=400,
            xaxis_title="服务名称",
            yaxis_title="波动率 (%)",
            coloraxis_colorbar=dict(title="稳定性评分")
        )
        fig_vol.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>" +
                          "波动率：%{y:.2f}%<br>" +
                          "稳定性评分：%{marker.color:.1f} 分<extra></extra>"
        )
        st.plotly_chart(fig_vol, use_container_width=True)

        st.divider()

    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        st.caption("💡 使用说明：趋势数据为模拟生成，包含每日周期性波动、随机噪声和偶发异常尖峰")
    with col_footer2:
        st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_dependency_page():
    dep_data = load_dependencies()
    services_df = generate_mock_data()
    thresholds = load_thresholds()
    service_info = get_service_info_map(dep_data, services_df, thresholds)

    if "dep_selected_node" not in st.session_state:
        st.session_state["dep_selected_node"] = None
    if "dep_impact_analysis" not in st.session_state:
        st.session_state["dep_impact_analysis"] = None
    if "dep_impact_service_select" not in st.session_state:
        st.session_state["dep_impact_service_select"] = ""

    all_node_types = sorted(list(set([n["type"] for n in dep_data["nodes"]])))
    all_statuses = ["正常", "警告", "异常"]

    alert_services = []
    for n in dep_data["nodes"]:
        st_info = service_info.get(n["name"], {"status": "正常"})
        if st_info.get("status", "正常") in ["警告", "异常"]:
            alert_services.append(n)

    with st.sidebar:
        st.header("🔗 依赖关系")

        if st.button("← 返回监控首页", use_container_width=True, key="dep_back_btn"):
            st.session_state["page"] = "dashboard"
            st.session_state["dep_selected_node"] = None
            st.session_state["dep_impact_analysis"] = None
            st.session_state["dep_impact_service_select"] = ""
            st.rerun()

        if st.button("📈 性能趋势分析", use_container_width=True, type="secondary", key="dep_trend_btn"):
            st.session_state["page"] = "trend"
            st.rerun()

        if st.button("🔔 查看告警历史", use_container_width=True, type="secondary", key="dep_alert_btn"):
            st.session_state["page"] = "alerts"
            st.rerun()

        st.divider()
        st.subheader("🔍 筛选选项")

        selected_types = st.multiselect(
            "按服务类型过滤",
            options=all_node_types,
            default=all_node_types,
            help="只显示选定类型的服务节点"
        )

        selected_statuses = st.multiselect(
            "按状态过滤显示",
            options=all_statuses,
            default=all_statuses,
            help="只显示选定状态的服务节点"
        )

        st.divider()
        st.subheader("⚠️ 影响分析")

        if alert_services:
            st.caption(f"🚨 当前有 {len(alert_services)} 个服务处于告警状态")
            for i, asvc in enumerate(alert_services):
                ainfo = service_info.get(asvc["name"], {"status": "警告"})
                astatus = ainfo.get("status", "警告")
                astatus_color = get_status_color(astatus)
                badge = f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{astatus_color};margin-right:4px;'></span>"
                col_a1, col_a2 = st.columns([4, 1])
                with col_a1:
                    st.markdown(f"<div style='font-size:12px;'>{badge}{asvc['name']} <span style='color:#6B7280;'>({astatus})</span></div>", unsafe_allow_html=True)
                with col_a2:
                    if st.button("分析", key=f"quick_analyze_{i}", use_container_width=True, type="secondary"):
                        st.session_state["dep_impact_analysis"] = asvc["id"]
                        st.session_state["dep_selected_node"] = asvc["id"]
                        st.session_state["dep_impact_service_select"] = asvc["name"]
                        st.rerun()
            st.divider()

        all_node_names = [""] + [n["name"] for n in dep_data["nodes"]]
        current_select_idx = 0
        if st.session_state.get("dep_impact_service_select", "") in all_node_names:
            current_select_idx = all_node_names.index(st.session_state["dep_impact_service_select"])

        impact_service = st.selectbox(
            "选择异常服务",
            options=all_node_names,
            help="选择一个服务，高亮显示所有受其影响的下游服务",
            index=current_select_idx,
            key="dep_impact_selectbox"
        )

        col_impact1, col_impact2 = st.columns(2)
        with col_impact1:
            if st.button("🔍 分析影响", use_container_width=True, key="run_impact", type="primary"):
                if impact_service:
                    node = next((n for n in dep_data["nodes"] if n["name"] == impact_service), None)
                    if node:
                        st.session_state["dep_impact_analysis"] = node["id"]
                        st.session_state["dep_selected_node"] = node["id"]
                        st.session_state["dep_impact_service_select"] = impact_service
                        st.rerun()
                else:
                    st.warning("请先选择一个服务")
        with col_impact2:
            if st.button("❌ 清除", use_container_width=True, key="clear_impact"):
                st.session_state["dep_impact_analysis"] = None
                st.session_state["dep_selected_node"] = None
                st.session_state["dep_impact_service_select"] = ""
                st.rerun()

        if st.session_state["dep_impact_analysis"]:
            impact_node = get_node_by_id(dep_data, st.session_state["dep_impact_analysis"])
            affected = find_all_affected_downstream(dep_data, st.session_state["dep_impact_analysis"])
            affected_names = [get_node_by_id(dep_data, aid)["name"] for aid in affected if get_node_by_id(dep_data, aid)]
            st.info(f"⚠️ 服务「{impact_node['name']}」异常将影响下游 **{len(affected_names)}** 个服务")

        st.divider()
        st.subheader("📋 图例说明")
        legend_html = """
        <div style="font-size: 12px; line-height: 1.8;">
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#10B981;margin-right:6px;border:2px solid white;box-shadow:0 0 0 1px #E5E7EB;"></span>正常</div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#F59E0B;margin-right:6px;border:2px solid white;box-shadow:0 0 0 1px #E5E7EB;"></span>警告</div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#EF4444;margin-right:6px;border:2px solid white;box-shadow:0 0 0 1px #E5E7EB;"></span>异常</div>
            <div style="margin-top:6px;"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#10B981;margin-right:6px;border:3px solid #3B82F6;"></span>已选中</div>
            <div style="margin-top:6px;"><strong>节点大小</strong>：请求量越大，节点越大</div>
            <div><strong>连线粗细</strong>：调用频率越高，连线越粗</div>
            <div><strong>连线箭头</strong>：指向被调用的服务方向</div>
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

        st.divider()
        st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.title("🔗 服务依赖关系可视化")
    st.markdown("展示各服务之间的依赖关系和调用链路，支持节点详情查看、状态筛选和异常影响分析")
    st.divider()

    filtered_node_ids = set()
    for node in dep_data["nodes"]:
        info = service_info.get(node["name"], {"service_type": node["type"], "status": "正常"})
        if node["type"] in selected_types and info.get("status", "正常") in selected_statuses:
            filtered_node_ids.add(node["id"])

    positions = compute_circular_layout(dep_data)

    all_request_counts = [service_info.get(n["name"], {"request_count": 1000})["request_count"] for n in dep_data["nodes"]]
    min_req, max_req = min(all_request_counts), max(all_request_counts)
    all_freqs = [e["call_frequency"] for e in dep_data["edges"]]
    min_freq, max_freq = min(all_freqs), max(all_freqs)

    def scale_node_size(req):
        if max_req == min_req:
            return 30
        norm = (req - min_req) / (max_req - min_req) if max_req > min_req else 0.5
        return 22 + norm * 32

    def scale_edge_width(freq):
        if max_freq == min_freq:
            return 2
        norm = (freq - min_freq) / (max_freq - min_freq) if max_freq > min_freq else 0.5
        return 1.2 + norm * 5.5

    def get_label_position(x, y):
        angle = math.atan2(y, x)
        deg = math.degrees(angle)
        if -22.5 <= deg < 22.5:
            return "middle right"
        elif 22.5 <= deg < 67.5:
            return "top center"
        elif 67.5 <= deg < 112.5:
            return "top center"
        elif 112.5 <= deg < 157.5:
            return "top center"
        elif 157.5 <= deg or deg < -157.5:
            return "middle left"
        elif -157.5 <= deg < -112.5:
            return "bottom center"
        elif -112.5 <= deg < -67.5:
            return "bottom center"
        else:
            return "bottom center"

    def smart_wrap_label(name, x, y):
        angle = math.atan2(y, x)
        deg = math.degrees(angle)
        is_left = abs(deg) > 90
        if is_left:
            if len(name) > 6:
                mid = len(name) // 2
                return name[:mid] + "<br>" + name[mid:]
        else:
            if len(name) > 6:
                mid = len(name) // 2
                return name[:mid] + "<br>" + name[mid:]
        return name

    impact_affected_ids = set()
    if st.session_state["dep_impact_analysis"]:
        impact_affected_ids = find_all_affected_downstream(dep_data, st.session_state["dep_impact_analysis"])

    edge_traces = []
    arrow_annotations = []

    for edge in dep_data["edges"]:
        if edge["source"] not in filtered_node_ids or edge["target"] not in filtered_node_ids:
            continue
        src_pos = positions.get(edge["source"])
        tgt_pos = positions.get(edge["target"])
        if not src_pos or not tgt_pos:
            continue
        src_node = get_node_by_id(dep_data, edge["source"])
        tgt_node = get_node_by_id(dep_data, edge["target"])
        src_name = src_node["name"] if src_node else edge["source"]
        tgt_name = tgt_node["name"] if tgt_node else edge["target"]

        is_highlighted = False
        line_color = "rgba(107, 114, 128, 0.55)"
        arrow_color = "rgba(107, 114, 128, 0.7)"
        if st.session_state["dep_impact_analysis"]:
            if edge["source"] == st.session_state["dep_impact_analysis"] or edge["source"] in impact_affected_ids:
                is_highlighted = True
                line_color = "rgba(239, 68, 68, 0.9)"
                arrow_color = "rgba(239, 68, 68, 1)"
        if st.session_state["dep_selected_node"]:
            sel_id = st.session_state["dep_selected_node"]
            if edge["source"] == sel_id or edge["target"] == sel_id:
                is_highlighted = True
                line_color = "rgba(59, 130, 246, 0.92)"
                arrow_color = "rgba(59, 130, 246, 1)"

        width = scale_edge_width(edge["call_frequency"]) if is_highlighted else scale_edge_width(edge["call_frequency"]) * 0.7
        if not is_highlighted and st.session_state["dep_impact_analysis"]:
            line_color = "rgba(209, 213, 219, 0.2)"
            arrow_color = "rgba(209, 213, 219, 0.3)"
            width *= 0.4

        dx = tgt_pos["x"] - src_pos["x"]
        dy = tgt_pos["y"] - src_pos["y"]
        dist = math.sqrt(dx * dx + dy * dy)
        arrow_x = tgt_pos["x"]
        arrow_y = tgt_pos["y"]
        if dist > 0:
            tgt_size = scale_node_size(service_info.get(tgt_name, {"request_count": 1000})["request_count"])
            offset = tgt_size * 0.0085
            arrow_x = tgt_pos["x"] - (dx / dist) * offset
            arrow_y = tgt_pos["y"] - (dy / dist) * offset
            mid_x = src_pos["x"] + (dx / dist) * (dist - tgt_size * 0.012)
            mid_y = src_pos["y"] + (dy / dist) * (dist - tgt_size * 0.012)
        else:
            mid_x = arrow_x
            mid_y = arrow_y

        edge_trace = go.Scatter(
            x=[src_pos["x"], arrow_x, None],
            y=[src_pos["y"], arrow_y, None],
            mode="lines",
            line=dict(width=width, color=line_color),
            hoverinfo="text",
            text=f"{src_name} → {tgt_name}<br>调用频率: {edge['call_frequency']:,} 次/日<br>{edge.get('description', '')}",
            showlegend=False
        )
        edge_traces.append(edge_trace)

        if is_highlighted or not st.session_state["dep_impact_analysis"]:
            arrow_annotations.append(dict(
                ax=src_pos["x"],
                ay=src_pos["y"],
                axref="x",
                ayref="y",
                x=mid_x,
                y=mid_y,
                xref="x",
                yref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.0 if is_highlighted else 0.7,
                arrowwidth=width * 0.9,
                arrowcolor=arrow_color,
                text="",
                hovertext=f"{src_name} → {tgt_name}",
                opacity=1.0 if is_highlighted else 0.55
            ))

    node_x = []
    node_y = []
    node_sizes = []
    node_colors = []
    node_border_colors = []
    node_border_widths = []
    node_texts = []
    node_text_positions = []
    node_hover_texts = []
    node_ids = []

    for node in dep_data["nodes"]:
        if node["id"] not in filtered_node_ids:
            continue
        pos = positions.get(node["id"])
        if not pos:
            continue
        info = service_info.get(node["name"], {"status": "正常", "request_count": 1000, "avg_response_time": 50})
        status = info.get("status", "正常")
        req_count = info.get("request_count", 1000)
        color = get_status_color(status)

        is_selected = st.session_state["dep_selected_node"] == node["id"]
        is_impact_source = st.session_state["dep_impact_analysis"] == node["id"]
        is_impact_affected = node["id"] in impact_affected_ids

        base_color = color
        border_color = "white"
        border_width = 2
        dimmed = False

        if is_selected:
            border_color = "#3B82F6"
            border_width = 5
        elif is_impact_source:
            border_color = "#EF4444"
            border_width = 5
        elif is_impact_affected:
            border_color = "#F97316"
            border_width = 4

        if st.session_state["dep_impact_analysis"] and not (is_impact_source or is_impact_affected or is_selected):
            dimmed = True
            r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
            color = f"rgba({r}, {g}, {b}, 0.3)"
            border_color = f"rgba(255, 255, 255, 0.4)"

        node_x.append(pos["x"])
        node_y.append(pos["y"])
        size = scale_node_size(req_count)
        node_sizes.append(size * 1.25 if is_selected or is_impact_source else size)
        node_colors.append(color)
        node_border_colors.append(border_color)
        node_border_widths.append(border_width)
        node_ids.append(node["id"])

        label_text = smart_wrap_label(node["name"], pos["x"], pos["y"])
        node_texts.append(label_text)
        node_text_positions.append(get_label_position(pos["x"], pos["y"]))

        status_emoji = {"正常": "✅", "警告": "⚠️", "异常": "🚨"}.get(status, "ℹ️")
        highlight_note = ""
        if is_selected:
            highlight_note = "<br><i style='color:#3B82F6;'>[已选中]</i>"
        elif is_impact_source:
            highlight_note = "<br><i style='color:#EF4444;'>[异常源]</i>"
        elif is_impact_affected:
            highlight_note = "<br><i style='color:#F97316;'>[受影响]</i>"

        node_hover_texts.append(
            f"<b>{node['name']}</b> {status_emoji}<br>"
            f"类型: {node['type']}<br>"
            f"状态: <b style='color:{get_status_color(status)};'>{status}</b><br>"
            f"响应时间: {info.get('avg_response_time', 0):.0f} ms<br>"
            f"请求量: {req_count:,} 次/日<br>"
            f"负责人: {node.get('owner', 'N/A')}{highlight_note}<br>"
            f"<i>点击查看详情</i>"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_texts,
        textposition=node_text_positions,
        textfont=dict(size=10, color="#1F2937"),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=node_border_widths, color=node_border_colors),
            opacity=1.0
        ),
        hoverinfo="text",
        hovertext=node_hover_texts,
        customdata=node_ids,
        showlegend=False
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        height=680,
        margin=dict(l=10, r=10, t=20, b=20),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-1.45, 1.45]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-1.45, 1.45],
            scaleanchor="x",
            scaleratio=1
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(249, 250, 251, 1)",
        clickmode="event+select",
        dragmode="pan",
        annotations=arrow_annotations
    )

    col_net, col_detail = st.columns([2, 1])
    with col_net:
        st.subheader("🕸️ 服务依赖网络图")
        st.caption("💡 点击节点查看服务详情；在侧边栏选择服务进行影响分析；连线上的箭头表示调用方向")
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="dep_chart")

        if event and event.selection and len(event.selection.points) > 0:
            for pt in event.selection.points:
                if hasattr(pt, "trace_index"):
                    total_edge_traces = len(edge_traces)
                    if pt.trace_index == total_edge_traces and hasattr(pt, "customdata") and pt.customdata is not None:
                        st.session_state["dep_selected_node"] = pt.customdata
                        break
                elif hasattr(pt, "customdata") and pt.customdata is not None:
                    st.session_state["dep_selected_node"] = pt.customdata
                    break

    with col_detail:
        st.subheader("📋 服务详情")
        selected_node_id = st.session_state.get("dep_selected_node")
        if selected_node_id:
            node = get_node_by_id(dep_data, selected_node_id)
            if node:
                info = service_info.get(node["name"], {})
                status = info.get("status", "正常")
                status_color = get_status_color(status)

                highlight_tag = ""
                if st.session_state.get("dep_impact_analysis") == selected_node_id:
                    highlight_tag = " <span style='padding:2px 8px;border-radius:10px;background-color:#EF4444;color:white;font-size:11px;'>异常源</span>"
                elif selected_node_id in impact_affected_ids:
                    highlight_tag = " <span style='padding:2px 8px;border-radius:10px;background-color:#F97316;color:white;font-size:11px;'>受影响</span>"

                status_badge = f"<span style='padding:2px 10px;border-radius:12px;background-color:{status_color};color:white;font-size:13px;font-weight:600;'>{status}</span>{highlight_tag}"

                st.markdown(f"""
                <div style="padding: 16px; background-color: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px;">
                    <h3 style="margin: 0 0 8px 0; font-size: 18px;">{node['name']}</h3>
                    <div style="margin-bottom: 12px;">{status_badge}</div>
                    <div style="font-size: 13px; color: #6B7280; line-height: 1.6;">
                        {node.get('description', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.metric(
                        label="⏱️ 响应时间",
                        value=f"{info.get('avg_response_time', 0):.0f} ms",
                        help="服务平均响应时间"
                    )
                with col_d2:
                    st.metric(
                        label="📦 请求量",
                        value=f"{info.get('request_count', 0):,}",
                        help="日均请求次数"
                    )

                st.markdown("**🏷️ 服务类型**: " + node["type"])
                st.markdown("**👥 负责团队**: " + node.get("owner", "N/A"))

                upstream = get_upstream_services(dep_data, selected_node_id)
                downstream = get_downstream_services(dep_data, selected_node_id)

                with st.expander(f"🔻 上游依赖服务（{len(upstream)} 个）", expanded=True):
                    if upstream:
                        for up in upstream:
                            up_info = service_info.get(up["name"], {"status": "正常"})
                            up_color = get_status_color(up_info.get("status", "正常"))
                            st.markdown(f"""
                            <div style="padding: 8px 12px; margin-bottom: 6px; border-radius: 6px; background-color: #F9FAFB; border-left: 3px solid {up_color};">
                                <div style="font-weight: 600; font-size: 13px;">{up['name']}</div>
                                <div style="font-size: 11px; color: #6B7280;">
                                    {up.get('description', '')} · 调用频率: {up['call_frequency']:,} 次/日
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("无上游依赖")

                with st.expander(f"🔺 下游被依赖服务（{len(downstream)} 个）", expanded=True):
                    if downstream:
                        for down in downstream:
                            down_info = service_info.get(down["name"], {"status": "正常"})
                            down_color = get_status_color(down_info.get("status", "正常"))
                            st.markdown(f"""
                            <div style="padding: 8px 12px; margin-bottom: 6px; border-radius: 6px; background-color: #F9FAFB; border-left: 3px solid {down_color};">
                                <div style="font-weight: 600; font-size: 13px;">{down['name']}</div>
                                <div style="font-size: 11px; color: #6B7280;">
                                    {down.get('description', '')} · 调用频率: {down['call_frequency']:,} 次/日
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("无下游依赖")
            else:
                st.info("👈 请点击网络图中的节点查看详情，或在侧边栏选择服务进行影响分析")
        else:
            st.info("👈 请点击网络图中的节点查看详情，或在侧边栏选择服务进行影响分析")

    st.divider()

    st.subheader("📊 依赖关系汇总统计")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric(label="🔗 服务节点总数", value=len(dep_data["nodes"]))
    with col_s2:
        st.metric(label="➡️ 依赖关系总数", value=len(dep_data["edges"]))
    with col_s3:
        normal_count = len([n for n in dep_data["nodes"] if service_info.get(n["name"], {}).get("status") == "正常"])
        st.metric(label="✅ 正常服务", value=normal_count)
    with col_s4:
        alert_count = len([n for n in dep_data["nodes"] if service_info.get(n["name"], {}).get("status") in ["警告", "异常"]])
        st.metric(label="⚠️ 告警服务", value=alert_count, delta=alert_count, delta_color="inverse")

    st.divider()
    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        st.caption(f"💾 依赖关系配置文件：{DEPENDENCIES_JSON}")
    with col_footer2:
        st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    if st.session_state["page"] == "dashboard":
        render_dashboard_page()
    elif st.session_state["page"] == "alerts":
        render_alerts_page()
    elif st.session_state["page"] == "trend":
        render_trend_page()
    elif st.session_state["page"] == "dependency":
        render_dependency_page()
    else:
        render_dashboard_page()


if __name__ == "__main__":
    main()
