# A股大阳包小阴筛选工具

这个工具会从 A 股非 ST 股票中筛选最近 3 个已完成交易日内出现“大阳包小阴”信号的股票，综合形态强度、成交量放大和财务表现排名，输出前 10，并为每只股票附最近 5 个交易日 K 线图。

> 仅用于量化筛选和研究，不构成投资建议。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如需运行测试：

```powershell
python -m pip install -r requirements-dev.txt
```

## Gmail API 邮件配置

本工具使用 Gmail API OAuth2 发送邮件，不需要 Gmail App Password。

1. 在 Google Cloud Console 创建 OAuth Client：
   - 类型选择 `Desktop app`
   - 下载 JSON
   - 保存为 `secrets/gmail_credentials.json`

2. 复制 `.env.example` 为 `.env`：

```powershell
Copy-Item .env.example .env
notepad .env
```

3. `.env` 默认内容：

```env
MAIL_FROM=riverhuang82@gmail.com
GMAIL_CREDENTIALS_FILE=secrets/gmail_credentials.json
GMAIL_TOKEN_FILE=secrets/gmail_token.json
```

4. 首次授权并生成 token：

```powershell
.\.venv\Scripts\python -m stock_filter_tool gmail-auth
```

无浏览器环境可用控制台授权码：

```powershell
.\.venv\Scripts\python -m stock_filter_tool gmail-auth --console
```

`secrets/` 和 `.env` 都已加入 `.gitignore`，不会上传到 GitHub。

## 运行示例

生成报告但不发邮件：

```powershell
.\.venv\Scripts\python -m stock_filter_tool run --top 10 --no-email --chart-days 5
```

生成报告并发送邮件：

```powershell
.\.venv\Scripts\python -m stock_filter_tool run --top 10 --days 3 --chart-days 5 --send-email
```

指定输出文件：

```powershell
.\.venv\Scripts\python -m stock_filter_tool run --top 10 --no-email --output reports/latest.html
```

调试时限制扫描股票数量：

```powershell
.\.venv\Scripts\python -m stock_filter_tool run --top 10 --no-email --limit 100
```

## 数据源策略

- 股票列表：优先使用东方财富公开列表接口，并在代码中忽略本机代理以规避部分代理断连；失败时退回 AkShare 的 A 股代码表。
- 历史 K 线：优先使用新浪日 K 接口，失败时使用腾讯前复权日 K 接口。
- 财务指标：继续使用 AkShare 财务接口，仅对技术候选池做财务重排，避免全市场逐只请求财务导致云任务超时。

## 输出

默认输出到 `reports/`：

- `latest.html`：HTML 报告，包含排名和 K 线图。
- `latest.md`：Markdown 报告。
- `charts/`：每只入选股票最近 5 个交易日 K 线图。

## 云端自动化部署

### GitHub Actions

仓库内置 `.github/workflows/scheduled-screen.yml`，支持手动触发和工作日定时触发。默认在北京时间 16:30 运行，适合等待 A 股收盘后筛选。

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 添加：

- `MAIL_FROM`
- `GMAIL_CREDENTIALS_JSON`
- `GMAIL_TOKEN_JSON`

其中 `GMAIL_CREDENTIALS_JSON` 是 OAuth desktop client JSON，`GMAIL_TOKEN_JSON` 是首次授权后生成的 `secrets/gmail_token.json` 内容。

### Docker

构建镜像：

```powershell
docker build -t stock-filter-code .
```

运行容器：

```powershell
docker run --rm `
  -e MAIL_FROM=riverhuang82@gmail.com `
  -e GMAIL_CREDENTIALS_JSON='<OAuth client JSON>' `
  -e GMAIL_TOKEN_JSON='<OAuth token JSON>' `
  stock-filter-code
```

云端任务建议：

- 在交易日收盘后运行，例如北京时间 16:30 之后。
- 使用平台 Secret 管理 Gmail OAuth JSON，不要把 `.env` 或 `secrets/` 上传。
- 允许任务访问公网，行情和财务数据需要请求公开接口。
- 保存 `reports/` 为任务产物，便于邮件失败时排查。
- 需要监控“未筛到股票”时可加 `--fail-on-empty`，让空结果返回退出码 `2`。
