# FDA 数据飞书推送机器人

通过 GitHub Actions 定期获取 OpenFDA 的药品、警告信、指南信息，并推送到飞书群聊。

## 功能特性

- 📊 自动获取 FDA 最新数据
  - 药品不良事件
  - 警告信（召回信息）
  - 药品标签信息
- 🤖 自动推送到飞书机器人
- ⏰ 每天定时运行（北京时间上午 9:00）
- 🔧 支持手动触发

## 快速开始

### 1. 创建 GitHub 仓库

在 GitHub 上创建一个新仓库，然后将代码推送上去：

```bash
git init
git add .
git commit -m "Initial commit: FDA 飞书推送机器人"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

### 2. 配置说明

飞书 Webhook 已经硬编码在 `main.py` 中，如果需要修改，请编辑：

```python
FEISHU_WEBHOOK = "你的飞书 Webhook URL"
```

### 3. 手动触发测试

1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择 `FDA 数据推送` workflow
4. 点击 `Run workflow` 按钮

### 4. 查看运行日志

在 Actions 页面可以查看每次运行的详细日志。

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── fda_notification.yml  # GitHub Actions 配置
├── main.py                        # 主程序
├── requirements.txt               # Python 依赖
└── README.md                      # 项目说明
```

## 飞书消息格式

消息包含以下字段：
- `total_titles`: 总新闻数
- `timestamp`: 时间戳
- `report_type`: 类型（警告信/药品不良事件/药品标签）
- `text`: 详细内容

## 自定义配置

### 修改运行时间

编辑 `.github/workflows/fda_notification.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 时间，对应北京时间 9:00
```

### 修改数据获取天数

编辑 `main.py` 中的 `days` 参数：

```python
data = get_recent_fda_data(endpoint_type, days=7)  # 获取最近 7 天的数据
```

## OpenFDA API 说明

本项目使用以下 OpenFDA API 端点：
- 药品不良事件: `https://api.fda.gov/drug/event.json`
- 警告信: `https://api.fda.gov/drug/enforcement.json`
- 药品标签: `https://api.fda.gov/drug/label.json`

更多 API 信息请访问: https://open.fda.gov/

## 注意事项

- OpenFDA API 有速率限制（每分钟 240 次请求，无需 API Key）
- GitHub Actions 免费版每月有 2000 分钟的运行时间限制
- 确保飞书 Webhook 地址正确且有效

## License

MIT
