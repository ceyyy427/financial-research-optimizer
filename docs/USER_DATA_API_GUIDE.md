# 用户自带数据 API 接口

Finathink 提供一个供应商无关的数据接入合同。用户自行选择数据服务、取得访问权限并填写接口地址；平台保存连接配置、执行字段映射和清洗，然后把统一记录交给研究流程。来源名称是用户声明的元信息，不表示 Finathink 已核验数据的真实性、完整性或授权。

## 配置流程

1. 打开本地应用的“User data connections”页面。
2. 填写连接 ID、名称、用户 API 地址、认证方式、字段映射和记录路径。
3. 认证方式支持 `no_auth`、`bearer` 和 `api_key_header`。其他方式会被明确拒绝。
4. 保存配置只保存连接合同和凭证引用，不自动下载数据。正常本地应用将 API Key 写入操作系统密钥链；测试可注入进程内 `InMemoryDataCredentialStore`，不会写入用户密钥链。页面、日志、报告、checkpoint、模型上下文和状态响应都不会回显 API Key。
5. 使用独立的“试连”操作，并提供有界的研究请求；试连响应只返回状态、记录数、质量问题数和时间可用性状态。

密钥链引用使用固定前缀加随机不透明标识，不包含用户连接 ID。macOS 写入密钥链时通过子进程标准输入传递密钥值，不把密钥放进 `security` 命令参数。接口地址的查询参数会按大小写和分隔符规范化检查，拒绝 `api_key`、`access_token`、`client_secret`、`credential_ref`、`authorization`、`password`、`secret`、`token`、`key` 等凭证字段及其边界变体；普通字段（例如 `monkey`）仍可使用。

字段映射是一个明确的 JSON 对象，例如：

```json
{
  "instrument": "ticker",
  "timestamp": "time",
  "open": "open_price",
  "high": "high_price",
  "low": "low_price",
  "close": "price",
  "volume": "volume"
}
```

平台不会执行用户提供的 Python、SQL、表达式或转换脚本。JSON 响应应当是记录数组，或在配置的 `records_path`（例如 `data`）下提供记录数组。记录会被转换到统一字段，缺失字段、非数值、无效时间和重复键会附加为质量问题。

正常本地应用会把脱敏的连接合同持久化到本地数据目录的 JSON 文件，并在重启后恢复连接。文件只包含地址、字段映射、分页路径和不透明凭证引用，不包含 API Key；API Key 只进入操作系统密钥链。读取配置本身不会解析凭证、发起网络请求或下载数据。

## 请求和网络边界

单次请求超时为 15 秒，最多重试 2 次，响应最多 5 MiB、10,000 条记录、20 页。默认 `BoundedHttpTransport` 只发起 GET，禁止重定向，并在连接前后检查 DNS 解析结果，拒绝 URL 中的凭证、片段、本机、私网、链路本地和云元数据目标；重定向和分页不得改变来源。凭证不会跨来源转发。

缺少 `available_at`、发布时间或修订时间时，数据的 PIT 可用性保持 `UNKNOWN`。平台不会根据模型或响应内容补造 PIT 结论。

## 本地接口

- `GET /settings/data-connections`：本地设置页面。
- `GET /api/data/connections`：只返回脱敏连接状态。
- `POST /api/data/connections`：保存连接配置，需要本地会话 CSRF token。
- `POST /api/data/connections/<connection_id>/test`：显式试连，需要本地会话 CSRF token。

研究入口 `ResearchOrchestrator.run_from_connection(connection_id, request)` 也属于显式动作。它先读取已保存合同，再解析密钥链中的凭证并获取一次有界的 `DataBatch`，然后把统一记录交给既有的研究、因子、风控和纸面决策流程；失败会返回 `DATA_UNAVAILABLE`、`DATA_INVALID` 或 `NO_DATA_AVAILABLE` 等 typed failure。连接器保持供应商无关，不下载或安装任何供应商 SDK。

这些写入和试连入口只绑定本地应用。默认离线启动时不会访问外部服务；测试使用注入的 mock transport。真实数据服务和真实 API Key 由用户自行配置，不是离线验收的前置条件。
