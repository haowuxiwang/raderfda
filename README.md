# FDA 数据飞书推送机器人

通过 GitHub Actions 定期获取 OpenFDA 的药品、警告信、指南信息，并推送到飞书群聊。

## 功能特性

- 📊 自动获取 FDA 最新数据
  - 药品不良事件
  - 警告信（召回信息）
  - 药品标签信息
- 🤖 自动推送到飞书机器人
- ⏰ 每天定时运行（北京时间上午 9:00 和下午 2:00）
- 🔧 支持手动触发
- 🔐 环境变量安全管理 Webhook
- 📝 完整的日志记录
- ⚠️ 错误自动通知

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

### 2. 配置 GitHub Secrets（推荐）

为了安全起见，建议将飞书 Webhook URL 配置为 GitHub Secret：

1. 进入 GitHub 仓库
2. 点击 `Settings` > `Secrets and variables` > `Actions`
3. 点击 `New repository secret`
4. Name: `FEISHU_WEBHOOK`
5. Value: 你的飞书 Webhook URL
6. 点击 `Add secret`

如果不配置 Secret，代码会使用默认的 Webhook URL（已在代码中设置）。

### 3. 本地测试（可选）

在上传到 GitHub 之前，可以先本地测试：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行脚本
python main.py
```

查看 `logs/` 目录下的日志文件了解执行详情。

### 4. 手动触发测试

1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择 `FDA 数据推送` workflow
4. 点击 `Run workflow` 按钮

### 5. 查看运行日志

- **GitHub Actions 日志**: 在 Actions 页面查看每次运行的控制台输出
- **下载详细日志**: 在 Actions 运行详情页面，可以下载 `fda-logs` 文件（保留 7 天）

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── fda_notification.yml  # GitHub Actions 配置
├── logs/                          # 日志目录（自动创建）
├── main.py                        # 主程序
├── requirements.txt               # Python 依赖
├── .gitignore                     # Git 忽略文件
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
  - cron: '0 1 * * *'  # UTC 1:00 = 北京时间 9:00
  - cron: '0 6 * * *'  # UTC 6:00 = 北京时间 14:00
```

时区说明：GitHub Actions 使用 UTC 时间，北京时间 = UTC + 8 小时

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

## 错误处理

- 任务执行失败时会自动发送错误通知到飞书
- 所有错误都会记录在日志文件中
- 日志文件会上传到 GitHub Actions Artifacts（保留 7 天）

## 注意事项

- OpenFDA API 有速率限制（每分钟 240 次请求，无需 API Key）
- GitHub Actions 免费版每月有 2000 分钟的运行时间限制
- 确保飞书 Webhook 地址正确且有效
- 建议使用 GitHub Secrets 管理敏感信息
- 日志文件按日期命名，便于追踪历史记录

## License

MIT
