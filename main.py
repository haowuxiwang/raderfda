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

        # 对于 enforcement 数据，添加日期过滤
        if endpoint_type == "enforcement":
            date_str = start_date.strftime("%Y%m%d")
            params["search"] = (
                f"report_date:[{date_str}+TO+{end_date.strftime('%Y%m%d')}]"
            )
            params["limit"] = 100  # enforcement 数据可能较少，增加限制

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
    """格式化消息内容"""
    try:
        if not data or "results" not in data:
            logger.warning(f"{report_type} 数据为空或格式不正确")
            return None

        results = data["results"]
        total = len(results)

        if total == 0:
            logger.info(f"{report_type} 没有新数据")
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

        formatted_text = "\n".join(text_lines)
        logger.info(f"成功格式化 {report_type} 消息")
        return formatted_text
    except Exception as e:
        logger.error(f"格式化 {report_type} 消息时出错: {str(e)}", exc_info=True)
        return None


def send_to_feishu(total_titles, timestamp, report_type, text):
    """发送消息到飞书"""
    if not FEISHU_WEBHOOK:
        logger.error("飞书 Webhook URL 未配置")
        return False

    payload = {
        "total_count": total_titles,
        "timestamp": timestamp,
        "report_type": report_type,
        "message_content": text,
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


def send_error_notification(error_message):
    """发送错误通知到飞书"""
    if not FEISHU_WEBHOOK:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "total_count": "0",
        "timestamp": timestamp,
        "report_type": "系统错误",
        "message_content": f"⚠️ FDA 数据推送任务执行失败\n\n错误信息:\n{error_message}",
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

        # 定义要获取的数据类型
        report_types = [
            ("enforcement", "警告信"),
            ("drugs", "药品不良事件"),
            ("label", "药品标签"),
        ]

        for endpoint_type, report_name in report_types:
            logger.info(f"\n{'='*40}")
            logger.info(f"📡 正在处理 {report_name} 数据...")
            logger.info(f"{'='*40}")

            try:
                data = get_recent_fda_data(endpoint_type)

                if data:
                    text = format_message(data, report_name)
                    if text:
                        total = len(data.get("results", []))
                        if send_to_feishu(
                            total_titles=str(total),
                            timestamp=timestamp,
                            report_type=report_name,
                            text=text,
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
