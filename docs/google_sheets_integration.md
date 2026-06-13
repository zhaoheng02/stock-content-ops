# Google Sheets 审核后台接入

当前 MVP 已经导出 `daily-manifest.json` 和 Markdown 草稿。下一步可以把 manifest 同步到 Google Sheets，作为人工审核后台。

建议表字段：

- batch_name
- source_id
- account
- source_url
- score
- score_reasons
- platform
- draft_path
- reviewer
- status
- notes
- publish_url
- published_at

状态流：

- `needs_review`
- `approved`
- `rewrite_required`
- `rejected`
- `published`

需要的 Google 配置：

- Google Cloud OAuth client 或 service account
- 目标 Spreadsheet ID
- 可写入权限

真实凭证不要提交到 Git，放在 `.env` 或本机安全目录。

