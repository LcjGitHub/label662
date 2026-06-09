import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


def get_trace_status_color(status):
    if status == "成功":
        return "#10B981"
    elif status == "超时":
        return "#F59E0B"
    elif status == "失败":
        return "#EF4444"
    return "#6B7280"


def get_error_type_color(error_type):
    if error_type == "无":
        return "#10B981"
    error_colors = {
        "连接超时": "#F59E0B",
        "服务不可用": "#EF4444",
        "权限错误": "#8B5CF6",
        "参数错误": "#F59E0B",
        "内部错误": "#EF4444",
        "数据库错误": "#DC2626",
        "网络错误": "#F97316"
    }
    return error_colors.get(error_type, "#6B7280")


def compute_trace_summary(traces):
    if not traces:
        return {
            "total_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "timeout_count": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "p95_response_time": 0.0,
            "p99_response_time": 0.0,
            "max_response_time": 0.0,
            "error_types": {}
        }

    total = len(traces)
    success = len([t for t in traces if t.get("status") == "成功"])
    failure = len([t for t in traces if t.get("status") == "失败"])
    timeout = len([t for t in traces if t.get("status") == "超时"])
    rts = [float(t.get("response_time_ms", 0)) for t in traces]
    rts_sorted = sorted(rts)

    error_types = {}
    for t in traces:
        if t.get("error_type", "无") != "无":
            et = t.get("error_type", "未知错误")
            error_types[et] = error_types.get(et, 0) + 1

    p95_idx = int(len(rts_sorted) * 0.95) if len(rts_sorted) > 0 else 0
    p99_idx = int(len(rts_sorted) * 0.99) if len(rts_sorted) > 0 else 0

    return {
        "total_count": total,
        "success_count": success,
        "failure_count": failure,
        "timeout_count": timeout,
        "success_rate": round(success / total * 100, 2) if total > 0 else 0.0,
        "avg_response_time": round(sum(rts) / total, 2) if total > 0 else 0.0,
        "p95_response_time": rts_sorted[p95_idx] if p95_idx < len(rts_sorted) else (rts_sorted[-1] if rts_sorted else 0.0),
        "p99_response_time": rts_sorted[p99_idx] if p99_idx < len(rts_sorted) else (rts_sorted[-1] if rts_sorted else 0.0),
        "max_response_time": max(rts) if rts else 0.0,
        "error_types": error_types
    }


def build_trace_chain(all_traces, trace_id):
    if not all_traces:
        return []

    chain = []
    try:
        chain = [t for t in all_traces if t.get("trace_id") == trace_id]
        if chain:
            chain.sort(key=lambda x: (int(x.get("depth", 0) or 0), float(x.get("start_time_ms", 0) or 0)))
            return chain
    except Exception:
        pass

    target = next((t for t in all_traces if t.get("trace_id") == trace_id), None)
    if not target:
        return []

    chain = [target]
    visited = {trace_id}

    def _safe_parse_ts(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now()

    current = target
    for _ in range(5):
        try:
            parent = next((t for t in all_traces if t.get("target_service_id") == current.get("source_service_id")
                           and t.get("trace_id") not in visited
                           and abs((_safe_parse_ts(t.get("timestamp", "")) -
                                    _safe_parse_ts(current.get("timestamp", ""))).total_seconds()) < 300), None)
            if parent:
                chain.insert(0, parent)
                visited.add(parent.get("trace_id"))
                current = parent
            else:
                break
        except Exception:
            break

    current = target
    for _ in range(5):
        try:
            child = next((t for t in all_traces if t.get("source_service_id") == current.get("target_service_id")
                          and t.get("trace_id") not in visited
                          and abs((_safe_parse_ts(t.get("timestamp", "")) -
                                   _safe_parse_ts(current.get("timestamp", ""))).total_seconds()) < 300), None)
            if child:
                chain.append(child)
                visited.add(child.get("trace_id"))
                current = child
            else:
                break
        except Exception:
            break

    return chain


def build_trace_tree(all_traces, trace_id):
    chain = build_trace_chain(all_traces, trace_id)
    if not chain:
        return []

    span_map = {}
    for t in chain:
        sid = t.get("span_id") or t.get("trace_id")
        if sid:
            span_map[sid] = {**t, "children": []}

    roots = []
    for sid, node in span_map.items():
        pid = node.get("parent_span_id", "")
        if pid and pid in span_map:
            span_map[pid]["children"].append(node)
        else:
            roots.append(node)

    for root in roots:
        try:
            root["children"].sort(key=lambda x: float(x.get("start_time_ms", 0) or 0))
        except Exception:
            pass

    return roots


def get_trace_tree_flat(tree, level=0, result=None):
    if result is None:
        result = []
    for node in tree:
        try:
            node_copy = dict(node)
            node_copy["_level"] = level
            children = node_copy.pop("children", [])
            result.append(node_copy)
            if children:
                get_trace_tree_flat(children, level + 1, result)
        except Exception:
            continue
    return result


def filter_traces_by_service(traces, service_id, direction="both"):
    if not traces:
        return []
    if direction == "inbound":
        return [t for t in traces if t.get("target_service_id") == service_id]
    elif direction == "outbound":
        return [t for t in traces if t.get("source_service_id") == service_id]
    else:
        return [t for t in traces if t.get("source_service_id") == service_id or t.get("target_service_id") == service_id]


def render_trace_timeline(all_traces, trace_id):
    chain = build_trace_chain(all_traces, trace_id)
    if not chain:
        return None

    if len(chain) == 1:
        return None

    try:
        root_start = min(float(t.get("start_time_ms", 0) or 0) for t in chain)
    except Exception:
        root_start = 0

    timeline_data = []
    for t in chain:
        try:
            offset = float(t.get("start_time_ms", 0) or 0) - root_start
            duration = float(t.get("duration_ms", t.get("response_time_ms", 0)) or 0)
            color = get_trace_status_color(t.get("status", "成功"))
            label = f"{t.get('source_service_name', 'N/A')} → {t.get('target_service_name', 'N/A')}"
            timeline_data.append({
                "Span": label,
                "Start (ms)": round(offset, 2),
                "Duration (ms)": round(duration, 2),
                "Status": t.get("status", "未知"),
                "Color": color,
                "Depth": int(t.get("depth", 0) or 0),
                "Method": t.get("method", ""),
                "Endpoint": t.get("endpoint", ""),
                "HTTPStatus": str(t.get("http_status_code", "")),
                "ErrorType": t.get("error_type", "无"),
            })
        except Exception:
            continue

    if not timeline_data:
        return None

    df = pd.DataFrame(timeline_data)
    df = df.sort_values("Start (ms)")

    fig = go.Figure()
    statuses_shown = set()
    for _, row in df.iterrows():
        showlegend = row["Status"] not in statuses_shown
        if showlegend:
            statuses_shown.add(row["Status"])
        extra_hover = ""
        if row.get("ErrorType", "无") != "无":
            extra_hover = f"<br>错误类型: {row['ErrorType']}"
        fig.add_trace(go.Bar(
            x=[row["Duration (ms)"]],
            y=[row["Span"]],
            orientation="h",
            base=[row["Start (ms)"]],
            marker_color=row["Color"],
            name=row["Status"],
            legendgroup=row["Status"],
            showlegend=showlegend,
            hovertemplate=(
                f"<b>{row['Span']}</b><br>"
                f"状态: {row['Status']}<br>"
                f"方法: {row['Method']}<br>"
                f"端点: {row['Endpoint']}<br>"
                f"HTTP: {row['HTTPStatus']}<br>"
                f"开始偏移: {row['Start (ms)']:.1f} ms<br>"
                f"持续时间: {row['Duration (ms)']:.1f} ms"
                + extra_hover + "<extra></extra>"
            ),
            opacity=0.85
        ))

    fig.update_layout(
        title="调用链路时间线",
        barmode="overlay",
        height=max(320, 60 + len(df) * 32),
        xaxis_title="时间偏移 (毫秒)",
        yaxis_title="调用段 (Span)",
        showlegend=True,
        legend_title="调用状态",
        margin=dict(l=20, r=20, t=50, b=40),
        bargap=0.2
    )
    fig.update_xaxes(type="linear")
    return fig


def render_trace_waterfall(all_traces, trace_id):
    chain = build_trace_chain(all_traces, trace_id)
    if len(chain) < 2:
        return None

    try:
        chain_sorted = sorted(chain, key=lambda x: (int(x.get("depth", 0) or 0), float(x.get("start_time_ms", 0) or 0)))
    except Exception:
        chain_sorted = chain

    measures = []
    values = []
    labels = []
    colors = []

    for t in chain_sorted:
        try:
            label = f"{t.get('source_service_name', '?')}→{t.get('target_service_name', '?')}"
            labels.append(label)
            rt = float(t.get("response_time_ms", t.get("duration_ms", 0)) or 0)
            values.append(round(rt, 2))
            measures.append("relative")
            colors.append(get_trace_status_color(t.get("status", "成功")))
        except Exception:
            continue

    if not values:
        return None

    fig = go.Figure(go.Waterfall(
        name="响应时间",
        orientation="v",
        measure=measures,
        x=labels,
        textposition="outside",
        text=[f"{v:.0f}ms" for v in values],
        y=values,
        connector={"line": {"color": "rgb(127, 127, 127)"}},
        decreasing={"marker": {"color": "#10B981"}},
        increasing={"marker": {"color": "#3B82F6"}},
        totals={"marker": {"color": "#8B5CF6"}}
    ))

    try:
        for i in range(len(fig.data[0]["x"])):
            fig.data[0]["marker"]["color"][i] = colors[i]
    except Exception:
        pass

    fig.update_layout(
        title="调用瀑布图 (响应时间累加)",
        height=380,
        xaxis_title="调用链路阶段",
        yaxis_title="响应时间 (毫秒)",
        margin=dict(l=20, r=20, t=50, b=80),
        showlegend=False
    )
    fig.update_xaxes(tickangle=-20)
    return fig


def render_status_distribution(filtered_traces):
    status_counts = {}
    for t in filtered_traces:
        st_name = t.get("status", "未知")
        status_counts[st_name] = status_counts.get(st_name, 0) + 1
    if not status_counts:
        return None

    fig_pie = px.pie(
        values=list(status_counts.values()),
        names=list(status_counts.keys()),
        color=list(status_counts.keys()),
        color_discrete_map={
            "成功": "#10B981",
            "超时": "#F59E0B",
            "失败": "#EF4444"
        },
        hole=0.4,
        title="调用状态占比"
    )
    fig_pie.update_layout(height=320)
    return fig_pie


def render_error_distribution(global_summary):
    err_data = global_summary.get("error_types", {}) if isinstance(global_summary, dict) else {}
    if not err_data:
        return None

    err_df = pd.DataFrame([
        {"错误类型": k, "数量": v} for k, v in sorted(err_data.items(), key=lambda x: -x[1])
    ])

    all_error_types = ["连接超时", "服务不可用", "权限错误", "参数错误", "内部错误", "数据库错误", "网络错误"]
    color_map = {et: get_error_type_color(et) for et in all_error_types}

    fig_err = px.bar(
        err_df,
        x="数量",
        y="错误类型",
        orientation="h",
        title="各错误类型发生次数",
        color="错误类型",
        color_discrete_map=color_map,
    )
    fig_err.update_layout(height=320, showlegend=False)
    return fig_err
