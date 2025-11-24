import requests
import json
from datetime import datetime, timedelta
import os

# 飞书 Webhook URL
FEISHU_WEBHOOK = (
    "https://www.feishu.cn/flow/api/trigger-webhook/5c323f1d94ae652b0d3093860dbca0a2"
)

# OpenFDA API 端点
OPENFDA_ENDPOINTS = {
    "drugs": "https://api.fda.gov/drug/event.json",
    "enforcement": "https://api.fda.gov/drug/enforcement.json",
    "label": "https://api.fda.gov/drug/label.json",
}


def get_recent_fda_data(endpoint_type, days=7):
    """获取最近几天的 FDA 数据"""
    try:
        endpoint = OPENFDA_ENDPOINTS.get(endpoint_type)
        if not endpoint:
            return None

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 构建查询参数
        params = {"limit": 10}

        # 对于 enforcement 数据，添加日期过滤
        if endpoint_type == "enforcement":
            date_str = start_date.strftime("%Y%m%d")
            params["search"] = (
                f"report_date:[{date_str}+TO+{end_date.strftime('%Y%m%d')}]"
            )

        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        print(f"获取 {endpoint_type} 数据失败: {str(e)}")
        return None


def format_message(data, report_type):
    """格式化消息内容"""
    if not data or "results" not in data:
        return None

    results = data["results"]
    total = len(results)

    if total == 0:
        return None

    # 构建消息文本
    text_lines = [f"📊 FDA {report_type} 最新数据更新"]
    text_lines.append(f"共 {total} 条记录\n")

    for i, item in enumerate(results[:5], 1):  # 只显示前5条
        if report_type == "药品不良事件":
            drug_name = (
                item.get("patient", {})
                .get("drug", [{}])[0]
                .get("medicinalproduct", "未知药品")
            )
            text_lines.append(f"{i}. {drug_name}")
        elif report_type == "警告信":
            product = item.get("product_description", "未知产品")
            reason = item.get("reason_for_recall", "未说明")
            text_lines.append(f"{i}. {product[:50]}... - {reason[:30]}...")
        elif report_type == "药品标签":
            brand_name = (
                item.get("openfda", {}).get("brand_name", ["未知"])[0]
                if item.get("openfda", {}).get("brand_name")
                else "未知"
            )
            text_lines.append(f"{i}. {brand_name}")

    return "\n".join(text_lines)


def send_to_feishu(total_titles, timestamp, report_type, text):
    """发送消息到飞书"""
    payload = {
        "message_type": "text",
        "content": {
            "total_titles": total_titles,
            "timestamp": timestamp,
            "report_type": report_type,
            "text": text,
        },
    }

    try:
        response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ 成功发送 {report_type} 消息到飞书")
        return True
    except Exception as e:
        print(f"❌ 发送消息失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("🚀 开始获取 FDA 数据...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 定义要获取的数据类型
    report_types = [
        ("enforcement", "警告信"),
        ("drugs", "药品不良事件"),
        ("label", "药品标签"),
    ]

    for endpoint_type, report_name in report_types:
        print(f"\n📡 正在获取 {report_name} 数据...")
        data = get_recent_fda_data(endpoint_type)

        if data:
            text = format_message(data, report_name)
            if text:
                total = len(data.get("results", []))
                send_to_feishu(
                    total_titles=str(total),
                    timestamp=timestamp,
                    report_type=report_name,
                    text=text,
                )
        else:
            print(f"⚠️  未获取到 {report_name} 数据")

    print("\n✨ 任务完成！")


if __name__ == "__main__":
    main()
