# 汉化术语表与判定规则

这份文档是 `zh-cn` 分支翻译用户可见文案时的**唯一事实源**：遇到新文案时先查这里的术语与规则，保证整份汉化用词一致。

维护者：本 fork 的汉化分支。适用范围：`src/wifit3/{ui,campaigns,setup}` 与 `errors.py`、`device/manager.py`
（也就是 `tools/i18n_audit.py` 扫描的同一片区域）。

---

## 1. 什么要译：用户可见文案

- **控件文本**：`Static` / `Label` / `Button` / `Checkbox` / `Switch`、
  `Select(options=[("显示文本", 值)])` 里的显示文本、`Input(placeholder=...)`、
  `DataTable.add_column(...)` 表头与 `add_row(...)` 的用户可读单元格、
  `Screen.TITLE` / `ModalScreen.TITLE` / `SUB_TITLE`、`border_title` / `border_subtitle`。
- **提示与消息**：`notify(...)`、toast、`BINDINGS` 的 `description=`（显示在 Footer）、`tooltip=`。
- **进 TUI 日志面板的行**：战役里 `self.log(...)` 写的进度行、`status_headlines()` /
  `status_under_card()` / `status_under_dash()` / `ineligible_reason()` 的返回文本。
- **弹窗文案**：确认安装/卸载、错误弹窗（`error_modals`、`setup_error`）、
  以及被弹窗直接渲染的 `WifiteError.title` / `.message`。
- **特权安装的状态行**：`ui.status(...)`、`SetupResult(message=...)`。
  注意 `BringupProgressModal` 会把状态行截断到 **58 字符**（`_STATUS_MAX`），所以状态文案保持简短
  （中文 ≤ 约 28 字）。
- **富文本标记里的可见文字**：`"[b]Capture[/b]"` 只译文字，标记原样保留。

## 2. 什么不译

| 类别 | 例子 | 原因 |
|---|---|---|
| 代码标识符、注释、docstring | — | 保持仓库既有风格 |
| CSS、widget `id=` / `classes=` | `"filter-text"`、`"ellipsis"`、`"1fr"` | 非文案，改了会坏样式/查找 |
| 字典键 / 配置键 / 状态串 | `"ssid"`、`"beacons"`、`"failed"` | 会被比较或持久化 |
| 枚举值 | `EncryptionType.OPEN = "OPEN"`、`CaptureKind.WEP_KEY = "wep_key"` | 同上 |
| `persist/vault.py` 的 `_KIND_LABELS` | `"Handshake"`、`"WEP Key"` | 同时是 `summary()` 的**字典键**，还被 `screen.py` / `vault_item.py` 当比较值；只汉化其**显示结果**（`WEP（3 个密钥）`） |
| 主题名、ANSI 调色键 | `"dark"`、`wifit3-logo-bars-primary` | 配置值 |
| `logger.*()` 与日志格式串 | `"campaign %r crashed in _loop()"`、`"%(asctime)s…"` | 只写 `wifit3.log`，不是界面渲染 |
| 富文本样式串、路径、命令 | `"black bold on cyan"`、`"/etc/udev/rules.d"`、`sudo apt install libudev1` | 非文案 / 要能直接复制执行 |
| udev / modprobe 规则文件内容 | `# wifit3 hands … to userland.` | 会被正则回读解析 |
| 数据哨兵 | `"<hidden>"`（parser 写入、models 比较） | 数据层值；界面占位另用 `‹隐藏›` |

**协议与厂商标识保留原样**：`SSID` `BSSID` `MAC` `AP` `RSSI` `dBm` `WPA` `WPA2` `WPA3`
`SAE` `OWE` `WEP` `EAPOL` `PMKID` `PSK` `WPS` `PBC` `PIN` `ARP` `PTW` `ICV` `CRC` `CSA` `BTM`
`USB` `VID:PID` `WinUSB` `UAC` `udev` `pkexec` `1k`/`11k`，以及 `wifit3`、`Hashcat`、
`PixieDust`、`ChopChop`、所有厂商/型号名（`ALFA AWUS1900`、`TP-Link Archer T2U` …）、
频段 `2.4G` / `5G` / `2.4 GHz`。

## 3. 术语表（统一用词）

| 英文 | 中文 | 备注 |
|---|---|---|
| Scanner / Focus / Splash | 扫描 / 聚焦 / 启动 | 屏幕标题 |
| Vault | 保险库 | |
| Preferences / Prefs | 偏好设置 | |
| Capture（名词/按钮） | 抓包 | |
| Handshake | 握手 | 紧凑标记 `✓HS` 不译 |
| PMKID harvest | PMKID 收集 | |
| Deauth / Deauthentication | 解除认证 | |
| Decloak | 解除隐藏 | |
| Reassociation / Association | 重关联 / 关联 | |
| Probe Response | 探测响应 | |
| Beacon | 信标 | |
| Inject / Injection | 注入 | |
| EvilTwin | 邪恶双胞胎 | 弹窗标题可用「邪恶双胞胎 (EvilTwin)」 |
| Fake AP | 伪造 AP | |
| Downgrade | 降级 | |
| Brute-force | 暴力破解 | |
| Wordlist | 字典 | |
| Cracked | 已破解 | |
| Silenced | 已静音 | |
| Channel | 信道 | 紧凑表头可保留 `CH` |
| Signal / Power | 信号 / 功率 | |
| Encryption | 加密 | |
| Vendor | 厂商 | |
| Clients | 客户端 | |
| Device / Adapter / Card | 网卡 | 统一指硬件 |
| Driver / Firmware | 驱动 / 固件 | |
| Bring-up | 初始化 | |
| Replug | 重新插拔 | |
| Locked / soft-lock / hard-lock | 已锁定 / 软锁定 / 硬锁定 | |
| Details | 详情 | |
| Not found | 未找到 | |
| Back to Splash | 返回启动页 | 弹窗按钮 |
| Live check | 存活检测 | |

## 4. 硬性保留规则（译错就出 bug）

1. **Rich 标记原样**：`[bold green]`、`[black bold on cyan]`、`[/]`、`[u]`… 逐字保留；
   加速键下划线改写为中文首字（`[u]E[/u]ncryption` → `[u]加[/u]密`）。
2. **首尾空格原样**：拼接串（`"Key: "`、`" to clipboard"`）的空格必须保留。
3. **f-string 占位符原样**：`{name}`、`{n}`、`%s` 不动。
4. **转义原样**：`\n`、`\t`、`\\`。
5. **中文内引号**：用 `「」` 或 `“”`，避免与 Python 引号冲突。
6. **宽度敏感处**：若某字符串长度参与布局算术或被断言（如 `_LABEL_W`、定宽单元格），
   要么保持等宽短译、要么不改并在提交信息里说明。
7. **一改就全改**：改任何字面量前先全仓搜索；若它同时被当键/比较值用，**要么全部同步、要么不动**。
8. **禁止 em-dash**：`src/wifit3` 下不能出现 `—`（U+2014），`tests/test_style.py` 会拦。
9. **不写中文“破折号套破折号”**：需要并列用 `：`、`·`、`()`。

## 5. 风格

- 简洁：按钮/表头 2–5 字；Footer 键位说明 ≤ 6 字。
- 用中文全角标点（`：，。！？`）；中文与英文/数字之间**保留一个空格**（如 `已捕获 PMKID`、`信道 6`）。
- 短标签不加句号；完整句子用中文句号。
- 语气随原文（命令式仍命令式）。

## 6. 测试同步

- 只把断言里的英文字面量换成对应中文，**不放宽、不删除、不改语义**。
- 不改测试函数名、文件名、docstring。
- 若某字面量被测试当**值**钉住（例如 `Config` 持久化、枚举值），按 §4.7 处理。

## 7. 每次同步后的自检

```powershell
.\.venv\Scripts\python.exe tools\i18n_audit.py     # NEW 逐条判断：译 or 收进基线
.\.venv\Scripts\python.exe -m ruff check src/ tests/
.\.venv\Scripts\python.exe -m pytest
```
