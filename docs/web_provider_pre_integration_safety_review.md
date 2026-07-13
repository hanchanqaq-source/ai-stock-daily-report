# Web-P48 真实 provider 接入前安全复核

## 1. 定位

Web-P48 是“股票基金质量分析系统”在真实 provider 接入前的安全复核阶段。本阶段只复核 Web-P45～Web-P47.1 已完成的 mock-only provider candidate 链路，并补充静态与单元测试证据；不新增真实 provider client、API client、凭证配置、feature flag、页面入口或正式 runtime 接入。

日报 / 推送显示名称继续固定为“AI股票基金每日信息报告”。

## 2. 当前已完成链路

当前 mock-only 链路为：

```text
ProviderCandidatePayload
→ validateProviderCandidatePayload
→ normalizeProviderCandidatePayloadToDryRunInput
→ validateRealDailyReportDryRunInput
```

已完成内容：

- Web-P45：`ProviderCandidatePayload` mock-only fixture。
- Web-P46：candidate validator。
- Web-P47：candidate normalizer。
- Web-P47.1：candidate → validator → normalizer → dry-run validator 链路复核。

## 3. 安全复核项目

Web-P48 复核以下边界：

- 当前没有真实 provider client、真实 provider API 请求、真实行情接入或真实账户读取。
- provider candidate 仍只存在于 mock-only preview 范围，未进入页面、preview model 或正式 runtime。
- candidate validator 先于 normalization；任一 blocked 均不返回 `normalizedInput`。
- normalizer 后仍执行 dry-run validator，且 normalizer 不调用 adapter、不生成 `DailyReportViewModel`。
- 全链路固定 `fallbackMode: mock-only`，`canFallbackToMockOnly: true`。
- `sourceType` 仍为 `mock-only`，所有真实能力开关均保持 false。
- Web-P49 已新增默认关闭 feature flag；仍不存在启用真实 provider 的入口。
- CI / Web 测试不依赖真实 provider 凭证、真实账户或真实网络请求；本复核不读取 `.env`、token、webhook、API key 或 GitHub Secrets。

## 4. Go / No-Go 矩阵

| 项目 | 当前状态 | 结论 |
| --- | --- | --- |
| mock-only candidate fixture | 已完成 | Ready |
| candidate validator | 已完成 | Ready |
| normalizer | 已完成 | Ready |
| dry-run validator | 已完成 | Ready |
| mock-only fallback | 已测试 | Ready |
| runtime 隔离 | 已测试 | Ready |
| 默认关闭 feature flag | Web-P49 已实现，默认 disabled | Ready（仅 mock-only gate） |
| 凭证管理方案 | 尚未实现 | Not Ready |
| 真实只读权限确认 | 尚未完成 | Not Ready |
| provider client | 未实现 | Not Ready |
| 日志脱敏实现 | 仅有规则/设计 | Not Ready |
| CI 真实凭证隔离方案 | 未进入真实接入阶段 | Not Ready |
| 用户人工批准真实接入 | 未批准 | Not Ready |

## 5. 当前结论

- 真实 provider 接入：**NO-GO**。
- 当前不允许新增真实请求、凭证或账户读取。
- Web-P48 不授权任何真实 provider 请求，也不授权读取真实行情、真实账户、通知、AI、数据库或交易链路。
- 当前状态只证明 mock-only candidate、validator、normalizer、dry-run validator、blocked 传播、fallback 和 runtime 隔离边界仍成立。

## 6. 下一步条件

- 当前允许的下一阶段仅为 Web-P49：默认关闭的 provider dry-run feature flag。
- Web-P49 也不得连接真实 provider，不得读取真实凭证、账户或行情。
- 真实 provider 接入必须另外立项、单独设计、单独 PR，并再次获得用户人工确认。

## 7. Web-P49 provider dry-run feature flag 状态

Web-P49 已实现默认关闭的 provider dry-run feature flag，仅作为纯函数门禁回答“是否允许后续代码进入 mock-only provider dry-run 链路”。

边界确认：

- 默认状态为 `disabled`，`canRunMockOnlyCandidateChain=false`。
- 显式传入安全静态配置启用时只产生 `enabled-mock-only`，仅表示后续阶段可进入 mock-only candidate 链路。
- feature flag 未接入页面、preview model、正式 runtime、URL 参数、环境变量、浏览器存储或后端配置。
- feature flag 不调用 `validateProviderCandidatePayload`、`normalizeProviderCandidatePayloadToDryRunInput`、`validateRealDailyReportDryRunInput` 或 dry-run adapter。
- 任意真实 provider、真实账户读取、通知、交易或 AI 能力请求均返回 `blocked`，并保持 `fallbackMode: mock-only`。
- 真实 provider 接入结论仍为 **NO-GO**。
- 下一步 Web-P50 才复核 feature flag 门禁与 mock-only fallback 链路组合。

## Web-M1B mock-only gate 闭环补充

Web-M1B 已完成 provider dry-run mock-only gate 闭环：feature flag 默认仍为 `disabled`，只有显式安全的 `enabled-mock-only` 才会运行既有 candidate validator → normalizer → dry-run validator 链路。

该 gate 未接入页面、preview model、React runtime、API client 或后端接口；disabled、非法 feature flag、candidate blocked、dry-run blocked 和异常路径均不返回 `normalizedInput`，并固定回退 `mock-only`。

真实 provider 仍未接入，最终状态保持 **NO-GO**。下一阶段进入真实只读 provider 前仍需用户人工批准。
