# OTA 部署工具 - Bug 修复跟踪

> 创建日期：2026-06-10  
> 最后更新：2026-06-10  
> 跟踪状态：🔴 待修复

---

## Bug 汇总表

| Bug ID | 严重程度 | 状态 | 标题 | 指派 |
|--------|---------|------|------|------|
| BUG-001 | 🔴 严重 | 🆕 待修复 | 导入路径错误导致程序无法启动 | 研发 |
| BUG-002 | 🔴 严重 | 🆕 待修复 | main.py 导入拼写错误 | 研发 |
| BUG-003 | 🟡 中等 | 🆕 待修复 | 板端 SSH 认证方式不灵活 | 研发 |
| BUG-004 | 🟡 中等 | 🆕 待修复 | 传输进度回调参数不一致 | 研发 |
| BUG-005 | 🟢 轻微 | 🆕 待修复 | 日志文件名硬编码 | 研发 |

---

## 详细 Bug 描述

### BUG-001: 导入路径错误

**严重程度**: 🔴 严重（阻塞）

**问题描述**:
所有 Python 文件中使用了中文路径作为模块导入路径，导致程序无法启动。

**影响范围**: 所有模块

**涉及文件**:
- main.py
- core/deployment_engine.py
- core/ssh_client.py
- core/board_operator.py
- core/transfer_manager.py
- core/rollback_manager.py
- core/package_classifier.py
- config/config_manager.py
- ui/main_window.py
- ui/log_viewer.py
- ui/settings_dialog.py

**错误示例**:
```python
# 当前代码（错误）
from 研发包部署.ota_deploy_tool.研发专用.utils.logger import get_logger
```

**修复方案**:
```python
# 修复后（正确）
from utils.logger import get_logger
```

**验收标准**:
- [ ] 所有模块导入路径修复
- [ ] 程序可以正常启动
- [ ] 无 ModuleNotFoundError

---

### BUG-002: main.py 导入拼写错误

**严重程度**: 🔴 严重（阻塞）

**问题描述**:
main.py 第 13 行 `from PyQt5.QtCore import Qtl` 中 `Qtl` 应为 `Qt`

**影响范围**: 程序入口

**涉及文件**: main.py

**错误代码**:
```python
# 第 13 行
from PyQt5.QtCore import Qtl  # 错误：Qtl 不存在
```

**修复方案**:
```python
from PyQt5.QtCore import Qt  # 正确
```

**验收标准**:
- [ ] 第 13 行修复为 `Qt`
- [ ] 程序可以正常启动

---

### BUG-003: 板端 SSH 认证方式不灵活

**严重程度**: 🟡 中等

**问题描述**:
板端 SSH 连接使用固定用户名 `user`，无密码认证。如果板端需要密钥认证或不同用户名，将无法连接。

**影响范围**: 板端连接

**涉及文件**:
- core/deployment_engine.py (第 444-452 行)
- config/config_manager.py

**当前代码**:
```python
def _create_board_client(self) -> SSHClient:
    return SSHClient(
        hostname=self._config.get("板端_IP", ""),
        username="user",  # 固定
        password="",      # 固定
        ...
    )
```

**修复方案**:
1. 在配置中添加板端用户名和密码
2. 支持密钥认证

```python
# config_manager.py DEFAULT_CONFIG 添加:
"板端_用户名": "user",
"板端_密码": "",
"板端_密钥文件": "",

# deployment_engine.py 修改:
def _create_board_client(self) -> SSHClient:
    return SSHClient(
        hostname=self._config.get("板端_IP", ""),
        username=self._config.get("板端_用户名", "user"),
        password=self._config.get("板端_密码", ""),
        key_file=self._config.get("板端_密钥文件", ""),
        ...
    )
```

**验收标准**:
- [ ] 配置中可设置板端用户名
- [ ] 配置中可设置板端密码
- [ ] 支持密钥认证（可选）

---

### BUG-004: 传输进度回调参数不一致

**严重程度**: 🟡 中等

**问题描述**:
TransferManager 的进度回调是 3 参数 `(current, total, message)`，但 DeploymentEngine 设置的是 2 参数 `(percent, message)`

**影响范围**: 进度显示

**涉及文件**:
- core/transfer_manager.py (第 41 行)
- core/deployment_engine.py (第 229 行)

**当前代码**:
```python
# transfer_manager.py
def _report_progress(self, current: int, total: int, message: str = ""):
    if self._progress_callback:
        self._progress_callback(current, total, message)  # 3 参数

# deployment_engine.py
self._transfer_mgr.set_progress_callback(self._progress_callback)
# 但 progress_callback 期望 2 参数: (percent, message)
```

**修复方案**:
统一为 2 参数格式，在 TransferManager 中计算百分比：

```python
# transfer_manager.py
def _report_progress(self, current: int, total: int, message: str = ""):
    if self._progress_callback:
        percent = int(current * 100 / total) if total > 0 else 0
        self._progress_callback(percent, message)  # 2 参数
```

**验收标准**:
- [ ] 进度回调参数统一
- [ ] 进度显示正常

---

### BUG-005: 日志文件名硬编码

**严重程度**: 🟢 轻微

**问题描述**:
日志文件名格式硬编码为 `deploy_YYYYMMDD.log`，无法自定义

**影响范围**: 日志功能

**涉及文件**: utils/logger.py (第 37 行)

**当前代码**:
```python
log_file = os.path.join(log_dir, f"deploy_{datetime.now().strftime('%Y%m%d')}.log")
```

**修复方案**:
将文件名格式加入配置或作为参数传入：

```python
def init(self, log_dir: str = None, log_prefix: str = "deploy"):
    ...
    log_file = os.path.join(log_dir, f"{log_prefix}_{datetime.now().strftime('%Y%m%d')}.log")
```

**验收标准**:
- [ ] 可自定义日志文件名前缀

---

## 修复进度

### 版本 v2.0.1 (计划)

- [ ] BUG-001: 导入路径修复
- [ ] BUG-002: main.py 拼写修复

### 版本 v2.1.0 (计划)

- [ ] BUG-003: 板端认证配置化
- [ ] BUG-004: 进度回调统一
- [ ] BUG-005: 日志文件名可配置

---

## 测试验证

| Bug ID | 修复版本 | 测试日期 | 测试人员 | 结果 |
|--------|---------|---------|---------|------|
| BUG-001 | - | - | - | ⏸️ 待测试 |
| BUG-002 | - | - | - | ⏸️ 待测试 |
| BUG-003 | - | - | - | ⏸️ 待测试 |
| BUG-004 | - | - | - | ⏸️ 待测试 |
| BUG-005 | - | - | - | ⏸️ 待测试 |

---

## 备注

- P0 级别 Bug 必须在发版前修复
- 修复后需要产品进行回归测试
- 测试通过后才能合并到主分支
