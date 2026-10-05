# 用户自带数据 API 接口

Finathink 提供一个供应商无关的数据接入合同。用户自行选择数据服务、取得访问权限并填写接口地址；平台保存连接配置、执行字段映射和清洗，然后把统一记录交给研究流程。来源名称是用户声明的元信息，不表示 Finathink 已核验数据的真实性、完整性或授权。

## 配置流程

1. 打开本地应用的“User data connections”页面。
2. 填写连接 ID、名称、用户 API 地址、认证方式、字段映射和记录路径。
3. 认证方式支持 `no_auth`、`bearer` 和 `api_key_header`。其他方式会被明确拒绝。
4. 保存配置只保存连接合同和凭证引用，不自动下载数据。API Key 只进入进程内本地凭证存储，页面、日志、报告、checkpoint、模型上下文和状态响应都不会回显它。
5. 使用独立的“试连”操作，并提供有界的研究请求；试连响应只返回状态、记录数、质量问题数和时间可用性状态。

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

## 请求和网络边界

单次请求超时为 15 秒，最多重试 2 次，响应最多 5 MiB、10,000 条记录、20 页。连接器校验 HTTP/HTTPS 地址，拒绝 URL 中的凭证、片段、本机、私网、链路本地和云元数据目标；重定向和分页不得改变来源。凭证不会跨来源转发。

缺少 `available_at`、发布时间或修订时间时，数据的 PIT 可用性保持 `UNKNOWN`。平台不会根据模型或响应内容补造 PIT 结论。

## 本地接口

- `GET /settings/data-connections`：本地设置页面。
- `GET /api/data/connections`：只返回脱敏连接状态。
- `POST /api/data/connections`：保存连接配置，需要本地会话 CSRF token。
- `POST /api/data/connections/<connection_id>/test`：显式试连，需要本地会话 CSRF token。

这些写入和试连入口只绑定本地应用。默认离线启动时不会访问外部服务；测试使用注入的 mock transport。真实数据服务和真实 API Key 由用户自行配置，不是离线验收的前置条件。
