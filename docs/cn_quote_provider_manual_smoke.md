# A股 / ETF Provider 本地手动试跑说明

## 1. 设计目标

`scripts/run_cn_quote_provider_smoke.py` 用于本地手动验证 A股 / ETF provider 接入链路是否能跑通。脚本默认不联网、不请求真实行情、不读取真实 `user_config`，也不接入日报、周报、Discord 或 Web UI。

该脚本只负责 CLI 参数、显式开关校验、安全提示和控制台输出；dry-run、local-only 与 real-provider 路径分别复用现有 provider 模块。CI / GitHub Actions 中禁止真实 provider 请求。

## 2. 默认 dry-run

不传 `--real` 时，脚本默认等价于 dry-run：只验证请求计划和安全边界，不请求真实行情，不保存真实价格、涨跌幅、成交额或净值。

默认输出会明确包含：

- `data_mode`
- `data_status`
- `source_status`
- `has_real_market_data=false`
- `allow_commit_to_repo=false`

## 3. local-only 模式

`--local-only` 使用本地 fixture 路径验证字段映射，不联网，不请求真实 provider，也不会把 fixture 结果标记为真实行情。

local-only 结果仅用于确认本地结构和字段契约，不能作为真实行情或交易依据。

## 4. real 模式

`--real` 仅限用户本地手动运行。真实 provider 路径必须同时满足：

- CLI 参数包含 `--real`
- `CN_QUOTE_ENABLE_REAL_PROVIDER=1`
- `CN_QUOTE_NETWORK_ENABLED=1`
- `CN_QUOTE_ALLOW_REAL_REQUEST=1`
- 当前不是 CI 环境（`CI=true` 或 `GITHUB_ACTIONS=true` 都会阻断）
- provider config 中 `network_enabled=true`
- provider config 中 `provider_enabled=true`
- provider config 中 `allow_real_request=true`
- `allow_commit_to_repo=false`
- `cache_scope=local_only`

任一条件不满足时，脚本返回 `provider_policy_blocked` 或 `disabled_by_default`，并说明缺少的条件。

## 5. 安全边界

- 不写 public repo。
- 不写 `data/history`。
- 不写 `config`。
- 不保存真实行情、真实价格、真实涨跌幅、真实成交额、真实净值或真实估算净值。
- 不保存 Token、API Key、Webhook、cookie、authorization、bearer、password 或 secret。
- 真实结果只打印到控制台。
- 输出默认脱敏。
- CI 环境禁止真实 provider 请求。

## 6. 示例命令

Dry-run 示例（默认不请求真实行情）：

```bash
python scripts/run_cn_quote_provider_smoke.py --provider akshare --code 000001 --type stock --market CN --dry-run
```

local-only 示例（使用本地 fixture，不联网）：

```bash
python scripts/run_cn_quote_provider_smoke.py --provider local_fixture --code 000001 --type stock --market CN --local-only
```

real 示例（仅限本地手动运行，不要在 CI 中执行）：

```bash
CN_QUOTE_ENABLE_REAL_PROVIDER=1 CN_QUOTE_NETWORK_ENABLED=1 CN_QUOTE_ALLOW_REAL_REQUEST=1 python scripts/run_cn_quote_provider_smoke.py --provider akshare --code 000001 --type stock --market CN --real --no-save
```

> 注意：real 示例仅限本地手动运行。不要把真实输出提交到仓库，也不要把真实价格、涨跌幅、成交额或任何密钥粘贴进 issue / PR / 文档。

## 7. 后续路线

- P5-Q5：A股 / ETF provider 本地真实请求结果审计。
- P5-R：场外基金真实净值 provider 接入评估。
