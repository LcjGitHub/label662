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
SLA_CONFIG_JSON = os.path.join(DATA_DIR, "sla_config.json")
SLA_HISTORY_JSON = os.path.join(DATA_DIR, "sla_history.json")

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

DEFAULT_SLA_CONFIG = {
    "网关服务": {"sla_threshold": 200, "target_availability": 99.9},
    "认证服务": {"sla_threshold": 150, "target_availability": 99.95},
    "数据库": {"sla_threshold": 50, "target_availability": 99.99},
    "缓存服务": {"sla_threshold": 10, "target_availability": 99.99},
    "存储服务": {"sla_threshold": 300, "target_availability": 99.5},
    "消息服务": {"sla_threshold": 100, "target_availability": 99.9},
    "搜索服务": {"sla_threshold": 200, "target_availability": 99.0},
    "支付服务": {"sla_threshold": 500, "target_availability": 99.99},
    "通知服务": {"sla_threshold": 400, "target_availability": 99.0},
    "网络服务": {"sla_threshold": 50, "target_availability": 99.99},
    "监控服务": {"sla_threshold": 200, "target_availability": 99.5},
    "AI 服务": {"sla_threshold": 1000, "target_availability": 95.0},
}

SLA_COLUMNS = ["service_type", "sla_threshold", "target_availability"]


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

    if not os.path.exists(SLA_CONFIG_JSON):
        with open(SLA_CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SLA_CONFIG, f, ensure_ascii=False, indent=2)

    if not os.path.exists(SLA_HISTORY_JSON):
        with open(SLA_HISTORY_JSON, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


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


def load_sla_config():
    if os.path.exists(SLA_CONFIG_JSON):
        with open(SLA_CONFIG_JSON, "r", encoding="utf-8") as f:
            config = json.load(f)
        for stype in DEFAULT_SLA_CONFIG:
            if stype not in config:
                config[stype] = DEFAULT_SLA_CONFIG[stype].copy()
        return config
    return DEFAULT_SLA_CONFIG.copy()


def save_sla_config(sla_config):
    with open(SLA_CONFIG_JSON, "w", encoding="utf-8") as f:
        json.dump(sla_config, f, ensure_ascii=False, indent=2)


def export_sla_config_to_json(sla_config):
    return json.dumps(sla_config, ensure_ascii=False, indent=2)


def import_sla_config_from_json(json_str):
    try:
        config = json.loads(json_str)
        required_keys = ["sla_threshold", "target_availability"]
        for stype, values in config.items():
            if not isinstance(values, dict):
                return None, f"服务类型 {stype} 的配置格式错误"
            for key in required_keys:
                if key not in values:
                    return None, f"服务类型 {stype} 缺少必需字段: {key}"
        return config, None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析错误: {str(e)}"
    except Exception as e:
        return None, f"导入失败: {str(e)}"


def load_sla_history():
    if os.path.exists(SLA_HISTORY_JSON):
        with open(SLA_HISTORY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sla_history(history):
    with open(SLA_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def generate_sla_daily_data():
    services_df = generate_mock_data()
    sla_config = load_sla_config()
    history = load_sla_history()
    today = datetime.now().strftime("%Y-%m-%d")

    if today not in history:
        history[today] = {}

    for _, service in services_df.iterrows():
        sname = service["service_name"]
        stype = service["service_type"]
        base_rt = service["avg_response_time"]
        sla_cfg = sla_config.get(stype, {"sla_threshold": 200, "target_availability": 99.0})
        sla_threshold = sla_cfg["sla_threshold"]

        np.random.seed(hash(f"{sname}_{today}") % 2**32)
        num_samples = 1000
        samples = np.random.normal(loc=base_rt, scale=base_rt * 0.15, size=num_samples)
        samples = np.maximum(1, samples)
        if np.random.random() < 0.1:
            spike_count = int(num_samples * np.random.uniform(0.01, 0.05))
            spike_idx = np.random.choice(num_samples, spike_count, replace=False)
            samples[spike_idx] *= np.random.uniform(1.5, 3.0, spike_count)

        avg_rt = float(np.mean(samples))
        p95_rt = float(np.percentile(samples, 95))
        p99_rt = float(np.percentile(samples, 99))
        success_count = int(np.sum(samples <= sla_threshold))
        achievement_rate = (success_count / num_samples) * 100
        is_achieved = achievement_rate >= sla_cfg["target_availability"]

        history[today][sname] = {
            "service_name": sname,
            "service_type": stype,
            "avg_response_time": round(avg_rt, 1),
            "p95_response_time": round(p95_rt, 1),
            "p99_response_time": round(p99_rt, 1),
            "sla_threshold": sla_threshold,
            "target_availability": sla_cfg["target_availability"],
            "total_requests": num_samples,
            "success_requests": success_count,
            "achievement_rate": round(achievement_rate, 2),
            "is_achieved": is_achieved
        }

    save_sla_history(history)
    return history


def get_last_7_days_sla():
    history = generate_sla_daily_data()
    services_df = generate_mock_data()
    all_service_names = sorted(services_df["service_name"].tolist())

    date_list = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        date_list.append(day)

    result = {}
    for sname in all_service_names:
        service_data = []
        for day in date_list:
            if day in history and sname in history[day]:
                service_data.append(history[day][sname])
            else:
                svc = services_df[services_df["service_name"] == sname]
                if len(svc) > 0:
                    svc_row = svc.iloc[0]
                    stype = svc_row["service_type"]
                    sla_cfg = load_sla_config().get(stype, {"sla_threshold": 200, "target_availability": 99.0})
                    base_rt = svc_row["avg_response_time"]
                    np.random.seed(hash(f"{sname}_{day}") % 2**32)
                    num_samples = 1000
                    samples = np.random.normal(loc=base_rt, scale=base_rt * 0.15, size=num_samples)
                    samples = np.maximum(1, samples)
                    avg_rt = float(np.mean(samples))
                    success_count = int(np.sum(samples <= sla_cfg["sla_threshold"]))
                    achievement_rate = (success_count / num_samples) * 100
                    is_achieved = achievement_rate >= sla_cfg["target_availability"]
                    day_data = {
                        "service_name": sname,
                        "service_type": stype,
                        "avg_response_time": round(avg_rt, 1),
                        "p95_response_time": round(float(np.percentile(samples, 95)), 1),
                        "p99_response_time": round(float(np.percentile(samples, 99)), 1),
                        "sla_threshold": sla_cfg["sla_threshold"],
                        "target_availability": sla_cfg["target_availability"],
                        "total_requests": num_samples,
                        "success_requests": success_count,
                        "achievement_rate": round(achievement_rate, 2),
                        "is_achieved": is_achieved
                    }
                    service_data.append(day_data)
                    if day not in history:
                        history[day] = {}
                    history[day][sname] = day_data
        result[sname] = {"dates": date_list, "data": service_data}

    save_sla_history(history)
    return result


def compute_consecutive_achieved_days(service_trend_data):
    data = service_trend_data["data"]
    count = 0
    for i in range(len(data) - 1, -1, -1):
        if data[i]["is_achieved"]:
            count += 1
        else:
            break
    return count


def compute_sla_summary():
    all_trends = get_last_7_days_sla()
    sla_config = load_sla_config()
    services_df = generate_mock_data()

    summary = []
    for sname, trend in all_trends.items():
        if not trend["data"]:
            continue
        latest = trend["data"][-1]
        all_rates = [d["achievement_rate"] for d in trend["data"]]
        avg_achievement = float(np.mean(all_rates))
        consecutive_days = compute_consecutive_achieved_days(trend)
        all_rts = [d["avg_response_time"] for d in trend["data"]]
        avg_rt = float(np.mean(all_rts))

        svc_row = services_df[services_df["service_name"] == sname]
        stype = svc_row["service_type"].values[0] if len(svc_row) > 0 else latest.get("service_type", "")
        sla_cfg = sla_config.get(stype, {"sla_threshold": 200, "target_availability": 99.0})

        summary.append({
            "service_name": sname,
            "service_type": stype,
            "sla_threshold": latest.get("sla_threshold", sla_cfg["sla_threshold"]),
            "target_availability": latest.get("target_availability", sla_cfg["target_availability"]),
            "avg_response_time": round(avg_rt, 1),
            "achievement_rate": round(latest["achievement_rate"], 2),
            "week_avg_achievement": round(avg_achievement, 2),
            "is_achieved": latest["is_achieved"],
            "consecutive_days": consecutive_days
        })

    return pd.DataFrame(summary)


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

        if st.button("📊 SLA 达成率统计", use_container_width=True, type="secondary", key="sidebar_sla_stats_btn"):
            st.session_state["page"] = "sla_stats"
            st.rerun()

        if st.button("⚙️ SLA 配置管理", use_container_width=True, type="secondary", key="sidebar_sla_cfg_btn"):
            st.session_state["page"] = "sla_config"
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

    sla_summary_df = compute_sla_summary()
    st.subheader("🎯 SLA 服务等级协议概览")

    if not sla_summary_df.empty:
        total_sla_services = len(sla_summary_df)
        achieved_services = len(sla_summary_df[sla_summary_df["is_achieved"] == True])
        not_achieved_services = total_sla_services - achieved_services
        overall_sla_rate = sla_summary_df["achievement_rate"].mean()

        sla_col1, sla_col2, sla_col3 = st.columns([2, 1, 2])

        with sla_col1:
            ov_label = "🟢 优秀" if overall_sla_rate >= 99 else ("🟡 良好" if overall_sla_rate >= 95 else "🔴 需改进")
            sla_color = "#10B981" if overall_sla_rate >= 99 else ("#F59E0B" if overall_sla_rate >= 95 else "#EF4444")

            fig_overall = go.Figure(go.Indicator(
                mode="gauge+number",
                value=overall_sla_rate,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": f"整体 SLA 达成率 {ov_label}", "font": {"size": 16}},
                gauge={
                    "axis": {"range": [None, 100], "tickwidth": 1},
                    "bar": {"color": sla_color},
                    "bgcolor": "white",
                    "borderwidth": 2,
                    "bordercolor": "#E5E7EB",
                    "steps": [
                        {"range": [0, 95], "color": "#FEE2E2"},
                        {"range": [95, 99], "color": "#FEF3C7"},
                        {"range": [99, 99.9], "color": "#DBEAFE"},
                        {"range": [99.9, 100], "color": "#D1FAE5"}
                    ]
                },
                number={
                    "suffix": "%",
                    "font": {"size": 40, "color": sla_color},
                    "valueformat": ".2f"
                }
            ))
            fig_overall.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor="white",
                plot_bgcolor="#F9FAFB"
            )
            st.plotly_chart(fig_overall, use_container_width=True)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📊 查看 SLA 详情", use_container_width=True, type="primary", key="home_sla_stats_btn"):
                    st.session_state["page"] = "sla_stats"
                    st.rerun()
            with col_btn2:
                if st.button("⚙️ 配置 SLA 阈值", use_container_width=True, type="secondary", key="home_sla_cfg_btn"):
                    st.session_state["page"] = "sla_config"
                    st.rerun()

        with sla_col2:
            st.markdown(f"""
            <div style="padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); height: 280px;">
                <div style="font-size: 14px; color: #6B7280; margin-bottom: 16px;">
                    📋 SLA 服务概况
                </div>
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 32px; font-weight: 700; color: #1F2937;">
                        {total_sla_services}
                    </div>
                    <div style="font-size: 13px; color: #6B7280;">
                        服务总数
                    </div>
                </div>
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-size: 13px; color: #10B981;">✅ 已达标</span>
                        <span style="font-size: 24px; font-weight: 700; color: #10B981;">{achieved_services}</span>
                    </div>
                </div>
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-size: 13px; color: #EF4444;">❌ 未达标</span>
                        <span style="font-size: 24px; font-weight: 700; color: #EF4444;">{not_achieved_services}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with sla_col3:
            top3_services = sla_summary_df.sort_values("achievement_rate", ascending=False).head(3)
            top3_items = []
            for rank_idx, (_, svc) in enumerate(top3_services.iterrows()):
                rank = rank_idx + 1
                medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else "🥉")
                rate_color = "#10B981" if svc["achievement_rate"] >= 99 else ("#F59E0B" if svc["achievement_rate"] >= 95 else "#EF4444")
                top3_items.append(f"""
                <div style="
                    padding: 10px 14px;
                    margin-bottom: {10 if rank_idx < 2 else 0}px;
                    background-color: #F9FAFB;
                    border-radius: 8px;
                    border-left: 4px solid {rate_color};
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 16px;">{medal}</span>
                            <span style="font-size: 14px; font-weight: 600; margin-left: 6px;">{svc['service_name']}</span>
                        </div>
                        <div style="font-size: 16px; font-weight: 700; color: {rate_color};">
                            {svc['achievement_rate']:.2f}%
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #6B7280; margin-top: 2px;">
                        {svc['service_type']} · 连续达标 {svc['consecutive_days']} 天
                    </div>
                </div>
                """)
            top3_html = "".join(top3_items)
            st.markdown(f"""
            <div style="padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-height: 280px;">
                <div style="font-size: 14px; color: #6B7280; margin-bottom: 16px;">
                    🏆 SLA 达成率排名 Top 3
                </div>
                {top3_html}
            </div>
            """, unsafe_allow_html=True)

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


def render_sla_config_page():
    sla_config = load_sla_config()

    with st.sidebar:
        st.header("⚙️ SLA 配置")

        if st.button("← 返回监控首页", use_container_width=True, key="sla_cfg_back_btn"):
            st.session_state["page"] = "dashboard"
            st.rerun()

        if st.button("📊 SLA 统计页面", use_container_width=True, type="secondary", key="go_to_sla_stats"):
            st.session_state["page"] = "sla_stats"
            st.rerun()

        st.divider()
        st.subheader("📤 配置导入导出")

        if st.button("📥 导出配置 JSON", use_container_width=True, key="export_sla_btn"):
            json_str = export_sla_config_to_json(sla_config)
            st.session_state["sla_export_data"] = json_str
            st.success("✅ 配置已准备好导出！")

        if "sla_export_data" in st.session_state:
            st.download_button(
                label="💾 下载配置文件",
                data=st.session_state["sla_export_data"],
                file_name=f"sla_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                key="download_sla_cfg"
            )

        st.divider()
        st.subheader("📥 导入配置")
        uploaded_file = st.file_uploader("选择 JSON 配置文件", type=["json"], key="sla_upload")
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode("utf-8")
                imported_cfg, error = import_sla_config_from_json(content)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.success(f"✅ 成功解析 {len(imported_cfg)} 个服务类型配置")
                    if st.button("✅ 确认导入并覆盖", use_container_width=True, type="primary", key="confirm_import_sla"):
                        save_sla_config(imported_cfg)
                        st.success("🎉 配置已成功导入！")
                        del st.session_state["sla_export_data"]
                        st.cache_data.clear()
                        st.rerun()
            except Exception as e:
                st.error(f"❌ 读取文件失败: {str(e)}")

        st.divider()
        if st.button("🔄 恢复默认配置", use_container_width=True, key="reset_sla_default"):
            save_sla_config(DEFAULT_SLA_CONFIG.copy())
            st.success("✅ 已恢复默认配置！")
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption(f"💾 SLA 配置文件：{SLA_CONFIG_JSON}")
        st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.title("⚙️ SLA 服务等级协议配置")
    st.markdown("为每种服务类型设定 SLA 标准阈值和目标可用性，支持配置导入导出")
    st.divider()

    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric(label="📋 服务类型总数", value=f"{len(sla_config)} 种")
    with col_stats2:
        all_thresholds = [v["sla_threshold"] for v in sla_config.values()]
        avg_th = np.mean(all_thresholds)
        st.metric(label="📏 平均响应时间标准", value=f"{avg_th:.0f} ms")
    with col_stats3:
        all_targets = [v["target_availability"] for v in sla_config.values()]
        avg_target = np.mean(all_targets)
        st.metric(label="🎯 平均目标可用性", value=f"{avg_target:.2f}%")

    st.divider()

    col_actions1, col_actions2 = st.columns([3, 1])
    with col_actions1:
        st.subheader("📋 SLA 阈值配置表")
    with col_actions2:
        if st.button("💾 保存所有修改", use_container_width=True, type="primary", key="save_all_sla_cfg"):
            save_sla_config(sla_config)
            st.success("✅ 所有配置已保存！")
            st.cache_data.clear()
            st.rerun()

    config_df = pd.DataFrame([
        {
            "服务类型": stype,
            "响应时间标准 (ms)": cfg["sla_threshold"],
            "目标可用性 (%)": cfg["target_availability"]
        }
        for stype, cfg in sla_config.items()
    ])
    st.dataframe(config_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("✏️ 逐项调整配置")

    sorted_types = sorted(sla_config.keys())
    for stype in sorted_types:
        current = sla_config[stype]
        with st.expander(f"📌 {stype}", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_threshold = st.number_input(
                    "响应时间 SLA 标准 (ms)",
                    min_value=1,
                    max_value=10000,
                    value=int(current["sla_threshold"]),
                    key=f"sla_th_{stype}",
                    help=f"{stype} 的平均响应时间应小于此值才算达标"
                )
            with col2:
                new_target = st.number_input(
                    "目标可用性 (%)",
                    min_value=50.0,
                    max_value=100.0,
                    value=float(current["target_availability"]),
                    step=0.01,
                    format="%.2f",
                    key=f"sla_target_{stype}",
                    help="在统计周期内请求响应达标比例的目标值"
                )
            with col3:
                st.markdown("<div style='visibility:hidden;'>_</div>", unsafe_allow_html=True)
                if st.button("💾 保存此项", key=f"save_sla_{stype}", use_container_width=True):
                    sla_config[stype]["sla_threshold"] = new_threshold
                    sla_config[stype]["target_availability"] = new_target
                    save_sla_config(sla_config)
                    st.success(f"✅ {stype} 配置已保存！")
                    st.cache_data.clear()
                    st.rerun()

            if new_threshold != current["sla_threshold"] or new_target != current["target_availability"]:
                sla_config[stype]["sla_threshold"] = new_threshold
                sla_config[stype]["target_availability"] = new_target

            st.markdown(f"""
            <div style="margin-top: 8px; padding: 12px; background-color: #EFF6FF; border-radius: 6px; font-size: 13px;">
                <strong>💡 配置说明：</strong><br>
                该服务类型下的所有服务，在统计周期内响应时间 ≤ <strong>{new_threshold} ms</strong> 的请求比例 ≥ 
                <strong>{new_target:.2f}%</strong>，即为 SLA 达标。
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        st.caption(f"💾 SLA 配置持久化存储于：{SLA_CONFIG_JSON}")
    with col_footer2:
        st.caption(f"🔧 技术栈：Streamlit + Plotly | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def render_sla_stats_page():
    sla_summary_df = compute_sla_summary()
    all_trends = get_last_7_days_sla()
    sla_config = load_sla_config()

    with st.sidebar:
        st.header("📊 SLA 统计")

        if st.button("← 返回监控首页", use_container_width=True, key="sla_stats_back_btn"):
            st.session_state["page"] = "dashboard"
            st.rerun()

        if st.button("⚙️ SLA 配置页面", use_container_width=True, type="secondary", key="go_to_sla_cfg"):
            st.session_state["page"] = "sla_config"
            st.rerun()

        st.divider()
        st.subheader("🔍 筛选选项")

        all_service_types = ["全部"] + sorted(sla_summary_df["service_type"].unique().tolist())
        selected_type = st.selectbox("服务类型", all_service_types, key="sla_stats_type_filter")

        status_options = ["全部", "已达标", "未达标"]
        selected_status = st.selectbox("达标状态", status_options, key="sla_stats_status_filter")

        st.divider()
        st.subheader("📈 显示选项")
        show_gauge = st.checkbox("显示仪表盘图表", value=True, key="sla_show_gauge")
        show_trend = st.checkbox("显示 7 天趋势卡片", value=True, key="sla_show_trend")
        show_table = st.checkbox("显示详细数据表格", value=True, key="sla_show_table")

        st.divider()
        st.caption(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.caption("💡 提示：SLA 数据为模拟生成")

    st.title("📊 SLA 服务等级协议统计")
    st.markdown("统计各服务 SLA 达成情况，包含仪表盘、趋势分析和详细数据")
    st.divider()

    filtered_df = sla_summary_df.copy()
    if selected_type != "全部":
        filtered_df = filtered_df[filtered_df["service_type"] == selected_type]
    if selected_status != "全部":
        is_achieved = selected_status == "已达标"
        filtered_df = filtered_df[filtered_df["is_achieved"] == is_achieved]

    col_stats1, col_stats2, col_stats3, col_stats4, col_stats5 = st.columns(5)
    total_services = len(filtered_df)
    achieved_count = len(filtered_df[filtered_df["is_achieved"] == True]) if total_services > 0 else 0
    not_achieved_count = total_services - achieved_count
    overall_achievement = filtered_df["achievement_rate"].mean() if total_services > 0 else 0
    overall_avg_rt = filtered_df["avg_response_time"].mean() if total_services > 0 else 0
    avg_consecutive = filtered_df["consecutive_days"].mean() if total_services > 0 else 0

    with col_stats1:
        st.metric(label="📦 服务总数", value=f"{total_services} 个")
    with col_stats2:
        ach_color = "normal" if achieved_count == total_services else ("off" if achieved_count > 0 else "inverse")
        st.metric(label="✅ 已达标服务", value=f"{achieved_count} 个", delta_color=ach_color)
    with col_stats3:
        st.metric(label="❌ 未达标服务", value=f"{not_achieved_count} 个", delta_color="inverse" if not_achieved_count > 0 else "normal")
    with col_stats4:
        ov_label = "🟢 优秀" if overall_achievement >= 99 else ("🟡 良好" if overall_achievement >= 95 else "🔴 需改进")
        st.metric(label=f"🎯 整体达成率 {ov_label}", value=f"{overall_achievement:.2f}%")
    with col_stats5:
        st.metric(label="🔥 平均连续达标", value=f"{avg_consecutive:.0f} 天")

    st.divider()

    if show_gauge and total_services > 0:
        st.subheader("🎯 各服务 SLA 达成率仪表盘")

        services_to_show = filtered_df.sort_values("achievement_rate", ascending=False)
        num_services = len(services_to_show)
        cols_per_row = 4
        num_rows = (num_services + cols_per_row - 1) // cols_per_row

        for row_idx in range(num_rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                svc_idx = row_idx * cols_per_row + col_idx
                if svc_idx >= num_services:
                    break
                svc = services_to_show.iloc[svc_idx]
                with cols[col_idx]:
                    rate = svc["achievement_rate"]
                    target = svc["target_availability"]
                    is_ok = svc["is_achieved"]

                    if rate >= 99.9:
                        color = "#10B981"
                    elif rate >= 99:
                        color = "#3B82F6"
                    elif rate >= 95:
                        color = "#F59E0B"
                    else:
                        color = "#EF4444"

                    fig = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=rate,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": f"{svc['service_name']}", "font": {"size": 14}},
                        delta={
                            "reference": target,
                            "relative": False,
                            "increasing": {"color": "#10B981"},
                            "decreasing": {"color": "#EF4444"},
                            "valueformat": ".2f"
                        },
                        gauge={
                            "axis": {"range": [None, 100], "tickwidth": 1},
                            "bar": {"color": color},
                            "bgcolor": "white",
                            "borderwidth": 2,
                            "bordercolor": "#E5E7EB",
                            "steps": [
                                {"range": [0, 95], "color": "#FEE2E2"},
                                {"range": [95, 99], "color": "#FEF3C7"},
                                {"range": [99, 99.9], "color": "#DBEAFE"},
                                {"range": [99.9, 100], "color": "#D1FAE5"}
                            ],
                            "threshold": {
                                "line": {"color": "#6B7280", "width": 3},
                                "thickness": 0.8,
                                "value": target
                            }
                        },
                        number={
                            "suffix": "%",
                            "font": {"size": 28, "color": color},
                            "valueformat": ".2f"
                        }
                    ))
                    fig.update_layout(
                        height=260,
                        margin=dict(l=10, r=10, t=40, b=10),
                        paper_bgcolor="white",
                        plot_bgcolor="#F9FAFB"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    status_badge = "✅ 达标" if is_ok else "❌ 未达标"
                    badge_color = "#10B981" if is_ok else "#EF4444"
                    st.markdown(f"""
                    <div style="text-align: center; margin-top: -20px; margin-bottom: 20px;">
                        <span style="padding: 3px 10px; border-radius: 12px; background-color: {badge_color}; color: white; font-size: 12px; font-weight: 600;">
                            {status_badge}
                        </span>
                        <span style="margin-left: 6px; font-size: 12px; color: #6B7280;">
                            标准: {svc['sla_threshold']:.0f}ms | 目标: {target}%
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()

    if show_trend and total_services > 0:
        st.subheader("📈 最近 7 天 SLA 达成率趋势")

        trend_services = filtered_df.sort_values("achievement_rate", ascending=False).head(6)
        num_trend = len(trend_services)
        tcols_per_row = 3
        trows = (num_trend + tcols_per_row - 1) // tcols_per_row

        for trow in range(trows):
            tcols = st.columns(tcols_per_row)
            for tcol in range(tcols_per_row):
                tidx = trow * tcols_per_row + tcol
                if tidx >= num_trend:
                    break
                svc_row = trend_services.iloc[tidx]
                sname = svc_row["service_name"]
                trend_data = all_trends.get(sname, {"dates": [], "data": []})

                if trend_data["data"]:
                    dates = trend_data["dates"]
                    rates = [d["achievement_rate"] for d in trend_data["data"]]
                    targets = [d["target_availability"] for d in trend_data["data"]]
                    display_dates = [d[5:] for d in dates]

                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=display_dates,
                        y=rates,
                        mode="lines+markers",
                        name="实际达成率",
                        line=dict(color="#3B82F6", width=3),
                        marker=dict(size=8, color="#3B82F6"),
                        fill="tozeroy",
                        fillcolor="rgba(59, 130, 246, 0.1)"
                    ))
                    fig_trend.add_trace(go.Scatter(
                        x=display_dates,
                        y=targets,
                        mode="lines",
                        name="目标值",
                        line=dict(color="#EF4444", width=2, dash="dash")
                    ))
                    fig_trend.update_layout(
                        title=f"📈 {sname}",
                        height=260,
                        margin=dict(l=40, r=20, t=50, b=40),
                        yaxis=dict(range=[max(80, min(rates) - 2), 100.5], title="达成率 (%)"),
                        xaxis=dict(title="日期"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                        plot_bgcolor="#F9FAFB",
                        paper_bgcolor="white"
                    )
                    fig_trend.add_hline(
                        y=svc_row["target_availability"],
                        line_dash="dash",
                        line_color="#EF4444",
                        opacity=0.7
                    )
                    with tcols[tcol]:
                        st.plotly_chart(fig_trend, use_container_width=True)
                        st.markdown(f"""
                        <div style="text-align: center; margin-top: -10px; margin-bottom: 20px; font-size: 13px;">
                            🔥 连续达标 <strong style="color: {'#10B981' if svc_row['consecutive_days'] >= 3 else '#F59E0B'};">{svc_row['consecutive_days']}</strong> 天
                            &nbsp;|&nbsp; 周均 <strong>{svc_row['week_avg_achievement']:.2f}%</strong>
                        </div>
                        """, unsafe_allow_html=True)

        st.divider()

    if show_table:
        st.subheader("📋 SLA 详情数据")

        if filtered_df.empty:
            st.info("暂无符合筛选条件的数据")
        else:
            display_df = filtered_df.copy()
            display_df["达标状态"] = display_df["is_achieved"].apply(lambda x: "✅ 已达标" if x else "❌ 未达标")
            display_df = display_df[[
                "service_name", "service_type", "sla_threshold",
                "target_availability", "avg_response_time",
                "achievement_rate", "week_avg_achievement",
                "consecutive_days", "达标状态"
            ]]
            display_df.columns = [
                "服务名称", "服务类型", "SLA 标准值(ms)",
                "目标可用性(%)", "实际平均值(ms)",
                "达成率(%)", "周均达成率(%)",
                "连续达标天数", "达标状态"
            ]

            def color_sla_status(val):
                if "已达标" in str(val):
                    return "background-color: #D1FAE5; color: #065F46; font-weight: 600;"
                elif "未达标" in str(val):
                    return "background-color: #FEE2E2; color: #991B1B; font-weight: 600;"
                return ""

            def color_rate(val):
                if val >= 99.9:
                    return "background-color: #D1FAE5; color: #065F46; font-weight: 600;"
                elif val >= 99:
                    return "background-color: #DBEAFE; color: #1E40AF; font-weight: 600;"
                elif val >= 95:
                    return "background-color: #FEF3C7; color: #92400E; font-weight: 600;"
                else:
                    return "background-color: #FEE2E2; color: #991B1B; font-weight: 600;"

            styled_df = display_df.style \
                .applymap(color_sla_status, subset=["达标状态"]) \
                .applymap(color_rate, subset=["达成率(%)", "周均达成率(%)"])

            st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)

            col_exp1, col_exp2 = st.columns([1, 4])
            with col_exp1:
                csv_data = display_df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 导出 CSV",
                    data=csv_data,
                    file_name=f"sla_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    st.divider()
    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        st.caption(f"💾 SLA 历史数据：{SLA_HISTORY_JSON}")
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
    elif st.session_state["page"] == "sla_config":
        render_sla_config_page()
    elif st.session_state["page"] == "sla_stats":
        render_sla_stats_page()
    else:
        render_dashboard_page()


if __name__ == "__main__":
    main()
