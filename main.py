import requests
import json
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"fda_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 飞书 Webhook URL - 从环境变量读取（必须配置）
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

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
            logger.error(f"未知的端点类型: {endpoint_type}")
            return None

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 构建查询参数
        params = {"limit": 10}

        # 对于 enforcement 数据，不添加日期过滤，直接获取最新的
        # 因为日期过滤可能导致查询失败
        if endpoint_type == "enforcement":
            params["limit"] = 100  # 获取更多数据

        logger.info(f"正在请求 {endpoint_type} 数据，参数: {params}")
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        logger.info(
            f"成功获取 {endpoint_type} 数据，共 {len(data.get('results', []))} 条记录"
        )
        return data
    except requests.exceptions.Timeout:
        logger.error(f"获取 {endpoint_type} 数据超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 {endpoint_type} 数据请求失败: {str(e)}")
        return None
    except Exception as e:
        logger.error(
            f"获取 {endpoint_type} 数据时发生未知错误: {str(e)}", exc_info=True
        )
        return None


def format_message(data, report_type):
    """格式化消息内容 - 参考 trendrader 风格"""
    try:
        if not data or "results" not in data:
            logger.warning(f"{report_type} 数据为空或格式不正确")
            return None

        results = data["results"]
        total = len(results)

        if total == 0:
            logger.info(f"{report_type} 没有新数据")
            return None

        # 根据类型选择 emoji
        emoji_map = {"药品不良事件": "⚠️", "警告信": "🚨", "药品标签": "💊"}
        emoji = emoji_map.get(report_type, "📊")

        # 构建消息文本
        text_lines = [f"{emoji} FDA {report_type} 最新数据更新"]
        text_lines.append(f"共 {total} 条记录")
        text_lines.append("")  # 空行

        for i, item in enumerate(results[:10], 1):  # 显示前10条
            if report_type == "药品不良事件":
                # 获取药品名称
                patient = item.get("patient", {})
                drugs = patient.get("drug", [])
                if drugs:
                    drug_name = drugs[0].get("medicinalproduct", "未知药品")
                else:
                    drug_name = "未知药品"

                # 获取严重性
                serious = item.get("serious", "未知")
                reaction = (
                    item.get("patient", {})
                    .get("reaction", [{}])[0]
                    .get("reactionmeddrapt", "")
                )

                text_lines.append(f"{i}. {drug_name}")
                if reaction:
                    text_lines.append(f"   反应: {reaction}")

            elif report_type == "警告信":
                # 产品描述
                product = item.get("product_description", "未知产品")[:80]
                # 召回原因
                reason = item.get("reason_for_recall", "未说明")[:50]
                # 召回日期
                recall_date = item.get("report_date", "")
                # 分类
                classification = item.get("classification", "")

                text_lines.append(f"{i}. {product}")
                text_lines.append(f"   原因: {reason}")
                if recall_date:
                    text_lines.append(f"   日期: {recall_date}")
                if classification:
                    text_lines.append(f"   级别: Class {classification}")

            elif report_type == "药品标签":
                # 品牌名称
                openfda = item.get("openfda", {})
                brand_names = openfda.get("brand_name", [])
                brand_name = brand_names[0] if brand_names else "未知"

                # 通用名称
                generic_names = openfda.get("generic_name", [])
                generic_name = generic_names[0] if generic_names else ""

                # 制造商
                manufacturers = openfda.get("manufacturer_name", [])
                manufacturer = manufacturers[0] if manufacturers else ""

                text_lines.append(f"{i}. {brand_name}")
                if generic_name:
                    text_lines.append(f"   通用名: {generic_name}")
                if manufacturer:
                    text_lines.append(f"   制造商: {manufacturer[:40]}")

            text_lines.append("")  # 每条记录后空行

        formatted_text = "\n".join(text_lines)
        logger.info(f"成功格式化 {report_type} 消息")
        return formatted_text
    except Exception as e:
        logger.error(f"格式化 {report_type} 消息时出错: {str(e)}", exc_info=True)
        return None


def format_message_with_links(data, report_type):
    """格式化消息内容 - 带链接的富文本格式"""
    try:
        if not data or "results" not in data:
            logger.warning(f"{report_type} 数据为空或格式不正确")
            return None

        results = data["results"]
        total = len(results)

        if total == 0:
            logger.info(f"{report_type} 没有新数据")
            return None

        # 构建富文本内容
        content_blocks = []

        # 标题行
        content_blocks.append([{"tag": "text", "text": f"共 {total} 条记录\n\n"}])

        for i, item in enumerate(results[:10], 1):  # 显示前10条
            block = []

            if report_type == "药品不良事件":
                patient = item.get("patient", {})
                drugs = patient.get("drug", [])
                drug_name = (
                    drugs[0].get("medicinalproduct", "未知药品")
                    if drugs
                    else "未知药品"
                )
                reactions = patient.get("reaction", [])
                reaction = reactions[0].get("reactionmeddrapt", "") if reactions else ""

                search_url = f"https://open.fda.gov/apis/drug/event/"

                block.append({"tag": "text", "text": f"{i}. "})
                block.append({"tag": "a", "text": drug_name, "href": search_url})
                if reaction:
                    block.append({"tag": "text", "text": f"\n   反应: {reaction}"})
                block.append({"tag": "text", "text": "\n\n"})

            elif report_type == "警告信":
                product = item.get("product_description", "未知产品")[:80]
                reason = item.get("reason_for_recall", "未说明")[:50]
                recall_date = item.get("report_date", "")
                classification = item.get("classification", "")
                enforcement_url = f"https://open.fda.gov/apis/drug/enforcement/"

                block.append({"tag": "text", "text": f"{i}. "})
                block.append({"tag": "a", "text": product, "href": enforcement_url})
                block.append({"tag": "text", "text": f"\n   原因: {reason}"})
                if recall_date:
                    block.append({"tag": "text", "text": f"\n   日期: {recall_date}"})
                if classification:
                    block.append(
                        {"tag": "text", "text": f"\n   级别: Class {classification}"}
                    )
                block.append({"tag": "text", "text": "\n\n"})

            elif report_type == "药品标签":
                openfda = item.get("openfda", {})
                brand_names = openfda.get("brand_name", [])
                brand_name = brand_names[0] if brand_names else "未知"
                generic_names = openfda.get("generic_name", [])
                generic_name = generic_names[0] if generic_names else ""
                manufacturers = openfda.get("manufacturer_name", [])
                manufacturer = manufacturers[0] if manufacturers else ""
                label_url = f"https://open.fda.gov/apis/drug/label/"

                block.append({"tag": "text", "text": f"{i}. "})
                block.append({"tag": "a", "text": brand_name, "href": label_url})
                if generic_name:
                    block.append(
                        {"tag": "text", "text": f"\n   通用名: {generic_name}"}
                    )
                if manufacturer:
                    block.append(
                        {"tag": "text", "text": f"\n   制造商: {manufacturer[:40]}"}
                    )
                block.append({"tag": "text", "text": "\n\n"})

            content_blocks.append(block)

        logger.info(f"成功格式化 {report_type} 消息（富文本格式）")
        return content_blocks
    except Exception as e:
        logger.error(f"格式化 {report_type} 消息时出错: {str(e)}", exc_info=True)
        return None


def send_to_feishu(total_titles, timestamp, report_type, text):
    """发送消息到飞书 - 使用富文本格式支持链接"""
    if not FEISHU_WEBHOOK:
        logger.error("飞书 Webhook URL 未配置")
        return False

    # 使用富文本格式，支持链接
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"{report_type} - {total_titles} 条记录",
                    "content": [
                        [{"tag": "text", "text": f"⏰ 更新时间: {timestamp}\n\n{text}"}]
                    ],
                }
            }
        },
    }

    try:
        logger.info(f"正在发送 {report_type} 消息到飞书...")
        response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        logger.info(f"✅ 成功发送 {report_type} 消息到飞书，响应: {result}")
        return True
    except requests.exceptions.Timeout:
        logger.error(f"❌ 发送 {report_type} 消息超时")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 发送 {report_type} 消息失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(
            f"❌ 发送 {report_type} 消息时发生未知错误: {str(e)}", exc_info=True
        )
        return False


def send_to_feishu_rich(total_titles, timestamp, report_type, content_blocks):
    """发送富文本消息到飞书 - 支持链接"""
    if not FEISHU_WEBHOOK:
        logger.error("飞书 Webhook URL 未配置")
        return False

    # 根据类型选择 emoji
    emoji_map = {"药品不良事件": "⚠️", "警告信": "🚨", "药品标签": "💊"}
    emoji = emoji_map.get(report_type, "📊")

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"{emoji} {report_type} - {total_titles} 条",
                    "content": content_blocks,
                }
            }
        },
    }

    try:
        logger.info(f"正在发送 {report_type} 富文本消息到飞书...")
        response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        logger.info(f"✅ 成功发送 {report_type} 消息到飞书，响应: {result}")
        return True
    except requests.exceptions.Timeout:
        logger.error(f"❌ 发送 {report_type} 消息超时")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 发送 {report_type} 消息失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(
            f"❌ 发送 {report_type} 消息时发生未知错误: {str(e)}", exc_info=True
        )
        return False


def send_error_notification(error_message):
    """发送错误通知到飞书"""
    if not FEISHU_WEBHOOK:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "⚠️ 系统错误",
                    "content": [
                        [
                            {"tag": "text", "text": f"时间: {timestamp}\n\n"},
                            {"tag": "text", "text": f"错误信息:\n{error_message}"},
                        ]
                    ],
                }
            }
        },
    }

    try:
        requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        logger.info("已发送错误通知到飞书")
    except Exception as e:
        logger.error(f"发送错误通知失败: {str(e)}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 开始执行 FDA 数据推送任务")
    logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    success_count = 0
    fail_count = 0
    errors = []

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 定义要获取的数据类型 - 先获取容易成功的
        report_types = [
            ("label", "药品标签"),
            ("drugs", "药品不良事件"),
            ("enforcement", "警告信"),
        ]

        for endpoint_type, report_name in report_types:
            logger.info(f"\n{'='*40}")
            logger.info(f"📡 正在处理 {report_name} 数据...")
            logger.info(f"{'='*40}")

            try:
                data = get_recent_fda_data(endpoint_type)

                if data:
                    content_blocks = format_message_with_links(data, report_name)
                    if content_blocks:
                        total = len(data.get("results", []))
                        if send_to_feishu_rich(
                            total_titles=str(total),
                            timestamp=timestamp,
                            report_type=report_name,
                            content_blocks=content_blocks,
                        ):
                            success_count += 1
                        else:
                            fail_count += 1
                            errors.append(f"{report_name}: 发送失败")
                    else:
                        logger.info(f"{report_name}: 无新数据需要推送")
                else:
                    fail_count += 1
                    error_msg = f"{report_name}: 获取数据失败"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            except Exception as e:
                fail_count += 1
                error_msg = f"{report_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"处理 {report_name} 时发生错误: {str(e)}", exc_info=True)

        # 输出执行摘要
        logger.info("\n" + "=" * 60)
        logger.info("📊 执行摘要")
        logger.info("=" * 60)
        logger.info(f"✅ 成功: {success_count} 个")
        logger.info(f"❌ 失败: {fail_count} 个")

        if errors:
            logger.warning("\n失败详情:")
            for error in errors:
                logger.warning(f"  - {error}")

        logger.info("\n✨ 任务执行完成！")
        logger.info("=" * 60)

        # 如果有失败，发送错误通知
        if fail_count > 0:
            error_summary = "\n".join(errors)
            send_error_notification(error_summary)

    except Exception as e:
        logger.critical(f"任务执行过程中发生严重错误: {str(e)}", exc_info=True)
        send_error_notification(f"任务执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    main()
