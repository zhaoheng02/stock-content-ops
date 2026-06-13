# X Content Ops

这是一个“X 账号监控 → GPT/规则筛选 → 高价值案例库 → 中文多平台成稿”的商业化 MVP。

当前已经落地：
- 读取 500 个 X 账号清单，并通过 X API v2 采集最近帖子。
- 服务端数据源配置、运行记录和 X 数据源采集入口。
- 本地规则筛选，或使用 OpenAI Responses API 做 GPT 筛选。
- 统一人设生成四类草稿：小红书图文、视频号文案、公众号长文、抖音脚本。
- 导出人工审核队列：`manifest.json` + 每个平台 Markdown 草稿。
- 无外部依赖，Python 3.9+ 可直接运行。

## 快速试跑

```bash
python3 -m unittest discover -s tests
python3 -m content_ops run --source data/fixtures/sample_posts.json --out dist --min-score 70
```

运行后查看：

```bash
ls dist
cat dist/daily-manifest.json
```

## 接入真实 X 监控

先复制环境变量样例并填入密钥：

```bash
cp .env.example .env
```

加载环境变量后采集账号帖子：

```bash
set -a && source .env && set +a
python3 -m content_ops collect-x \
  --accounts config/x_accounts.example.csv \
  --out data/inbox/x_posts.json \
  --max-results-per-account 5
```

再跑筛选生成：

```bash
python3 -m content_ops run \
  --source data/inbox/x_posts.json \
  --out dist \
  --min-score 70 \
  --limit 20 \
  --use-gpt
```

如果不加 `--use-gpt`，会走本地确定性评分，适合离线测试和成本控制。

## 服务端数据源模块

数据源配置会写入本地运行态目录，只保存凭据文件路径和密钥名称，不保存密钥值。默认从 `/Users/bytedance/personal.config` 读取 `X_BEARER_TOKEN`。

创建或更新一个 X 数据源：

```bash
python3 -m content_ops sources save \
  --id x \
  --name "X / Twitter" \
  --targets "@openai,@levelsio" \
  --cadence-minutes 30 \
  --min-score 70
```

导入示例数据源，包含通过 Airtap 找到的 5 个 X 账号：

```bash
python3 -m content_ops sources import --file config/data_sources.example.json
```

查看当前数据源：

```bash
python3 -m content_ops sources list
```

也可以把数据源和运行记录放到 Supabase。先在 Supabase SQL Editor 执行 `docs/supabase_schema.sql`，再执行 `docs/supabase_seed_sources.sql` 写入示例数据源。然后设置：

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
python3 -m content_ops sources --repo supabase list
```

运行一次采集并写入 inbox：

```bash
python3 -m content_ops sources run x --out data/inbox
python3 -m content_ops sources runs --source-id x
```

没有 X API token 时，可以用确定性的 sample 模式验证完整链路：

```bash
python3 -m content_ops sources run x-growth-ai --out data/inbox --mode sample
```

前端数据源页默认使用 Sample 运行模式，适合本地演示；切到 Live 后会走真实 X API token。

本地 API 服务：

```bash
python3 -m content_ops serve --host 127.0.0.1 --port 8787
curl http://127.0.0.1:8787/api/sources
curl -X POST http://127.0.0.1:8787/api/source-runs \
  -H 'Content-Type: application/json' \
  --data '{"source_id":"x-growth-ai","out":"data/inbox","mode":"sample"}'
```

采集输出可继续进入筛选生成流程：

```bash
python3 -m content_ops run --source data/inbox/<采集文件>.json --out dist --min-score 70
```

每日正式运行可以用：

```bash
scripts/run_daily.sh
```

也可以指定批次名：

```bash
scripts/run_daily.sh 2026-06-08
```

## 前端 UI 原型

当前 UI 在 `web/` 目录。主页、数据源、线索池、创作、发布、账号、数据、审批、团队、素材十个页面均已接入真实后端（Supabase + serverless API），无 mock 数据。

```bash
cd web
yarn install
yarn dev --port 5174
```

本地访问：

```text
http://localhost:5174/
```

已覆盖的页面包括：主页、数据源、线索池、创作、发布、账号、数据、审批、团队、素材。

## 账号清单

账号 CSV 格式：

```csv
handle,category,priority,notes
openai,ai_tools,1,AI platform signals
levelsio,indie_dev,1,independent developer business cases
```

`priority` 为 1-5，1 代表最高优先级。真实商业化运行时建议维护 500 个账号，并按以下池子分层：

- AI 工具与模型公司
- AI 创业者与产品负责人
- 独立开发者
- B2B SaaS 创始人和增长负责人
- 出海产品、支付、合规、获客相关账号
- 少量健康长寿、财经账号作为候补选题池

## 输出格式

每个高价值案例会导出：

- `xiaohongshu`：小红书图文
- `video_account`：视频号口播文案
- `wechat_article`：公众号长文
- `douyin_script`：抖音短视频脚本

所有草稿默认状态都是 `needs_review`。商业化发布前必须人工审核来源、事实、平台风控和版权风险。

## 技术边界

- X 采集使用官方 API v2，不使用浏览器私有接口或绕过登录机制。
- OpenAI 使用 Responses API，默认模型由 `OPENAI_MODEL` 控制。
- 本项目不会保存真实密钥，`.env` 已被 `.gitignore` 排除。

## 部署到 Vercel

前端为 Vite 静态站点，后端 API 改为 Vercel Python serverless 函数（`api/*.py`），数据存储使用 Supabase。仓库已与 GitHub 连接，推送到 `main` 即自动部署。

1. 在 Supabase SQL Editor 执行 `docs/supabase_schema.sql` 建表（含 `source_posts`），再按顺序执行 `docs/supabase_schema_v2.sql`（drafts / publish_accounts / assets / team_members / proxies / publish_metrics）、`docs/supabase_schema_v3.sql`（异步 Airtap 运行状态）、`docs/supabase_schema_v4.sql`（监控账号头像与增量水位）。
2. 仓库导入 Vercel，框架预设选 “Other”。构建配置见 `vercel.json`：
   - Build Command: `bash build.sh`（用 `yarn install --frozen-lockfile` + `vite build`）
   - Output Directory: `web/dist`
3. 在 Vercel 项目的 Environment Variables 配置：
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. 部署后，前端通过同源 API 访问后端：`/api/sources`、`/api/source-runs`、`/api/source-accounts`、`/api/source-posts`、`/api/generate`（生成并落库草稿），以及 `/api/drafts`、`/api/accounts`、`/api/assets`、`/api/team`、`/api/proxies`、`/api/analytics`（支持 GET/POST/PATCH/DELETE）。

构建踩坑记录（保持现状即可，勿回退）：

- 用 `yarn` 而非 `npm`：Vercel 构建机上 `npm install`/`npm ci` 会崩在 “Exit handler never called!”。
- `web/yarn.lock` 必须解析自公网 `registry.npmjs.org`，不能含内网 `bnpm.byted.org`（构建机访问不到）。`web/.yarnrc` 已锁定公网源。
- 每个 `api/*.py` 必须**直接定义** `class handler(...)`（Vercel 用 AST 识别入口），不能用 `handler = build_handler()` 这类赋值，否则函数会被丢弃、路由 404。公共逻辑放在 `content_ops/vercel_handler.py` 的 `ContentOpsHandler`，各路由 `class handler(ContentOpsHandler): pass`。

本地开发：在 `web/.env` 设置 `VITE_API_BASE_URL=http://127.0.0.1:8787`，并运行 `python3 -m content_ops serve`。生产环境前端默认走同源相对路径 `/api/*`。
