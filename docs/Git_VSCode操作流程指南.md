# CARIZON-OTA部署工具 — Git + VSCode 操作流程指南

> 适用项目：`Carizon-FF`（OTA 可视化无感部署工具）
> 远程仓库：https://github.com/8E4GPUX/Carizon-FF.git
> 本地路径：`c:\工具开发\Demo\研发包部署\ota_deploy_tool`

---

## 目录

1. [环境概览](#1-环境概览)
2. [Git 仓库结构](#2-git-仓库结构)
3. [VSCode 中操作 Git](#3-vscode-中操作-git)
4. [常用 Git 命令（终端执行）](#4-常用-git-命令终端执行)
5. [代码上传流程](#5-代码上传流程)
6. [代码下载/同步流程](#6-代码下载同步流程)
7. [新建分支与功能开发](#7-新建分支与功能开发)
8. [部署与运行](#8-部署与运行)
9. [常见问题](#9-常见问题)

---

## 1. 环境概览

### 1.1 项目架构

```
ota_deploy_tool/
├── .git/                    # Git 版本库（不要手动修改）
├── 研发专用/                 # 研发人员工作目录
│   ├── main.py              # 程序入口
│   ├── requirements.txt     # Python 依赖
│   ├── config/              # 配置文件（加密）
│   │   ├── config_manager.py
│   │   ├── package_mapping.json   # 包类型映射
│   │   ├── deploy_config.enc      # 加密部署配置
│   │   └── .config_key            # 加密密钥（不提交）
│   ├── core/                # 核心逻辑
│   │   ├── deployment_engine.py   # 部署引擎
│   │   ├── ssh_client.py          # SSH/SFTP 客户端
│   │   ├── transfer_manager.py    # 文件传输管理
│   │   ├── board_operator.py      # 板端操作
│   │   ├── rollback_manager.py    # 回滚管理
│   │   ├── package_classifier.py  # 包分类器
│   │   ├── deploy_history.py      # 部署历史
│   │   └── template_manager.py    # 模板管理
│   ├── ui/                  # 界面
│   │   ├── main_window.py         # 主窗口（网易云风格）
│   │   ├── settings_dialog.py     # 设置对话框
│   │   ├── log_viewer.py          # 日志查看器
│   │   └── theme_manager.py       # 主题管理
│   ├── utils/               # 工具
│   │   ├── logger.py
│   │   └── checksum.py
│   └── tests/               # 测试
├── 产品专用/                 # 产品文档
├── docs/                    # 需求文档
└── .gitignore               # Git 忽略规则
```

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| GUI 框架 | PyQt5 |
| SSH 通信 | paramiko |
| 配置加密 | cryptography (Fernet) |
| 版本控制 | Git + GitHub |
| 开发工具 | VSCode |

---

## 2. Git 仓库结构

### 2.1 远程仓库地址

```
https://github.com/8E4GPUX/Carizon-FF.git
```

![GitHub仓库页面](https://docs.github.com/assets/cb-20363/images/help/repository/repo-tabs-overview.png)

> **说明**：上图仅为示意，实际仓库地址为 `github.com/8E4GPUX/Carizon-FF`

### 2.2 分支说明

| 分支 | 说明 |
|------|------|
| `master` | 本地开发主分支 |
| `origin/master` | 远程 master 分支 |
| `origin/main` | 远程 main 分支（默认） |

### 2.3 版本历史（关键里程碑）

| 版本 | 提交信息 | 说明 |
|------|----------|------|
| v3.1 | `feat: v3.1 主题切换+包校验+配置历史` | 最新功能版 |
| v3.0 | `feat: v3.0 部署历史+模板管理` | 历史管理版 |
| v2.7 | `feat: UI优化v2.7 - QSplitter/表格/标题内移` | UI 大改版 |
| v2.5 | `feat: 完成P0/P1产品优化` | 基础功能版 |

---

## 3. VSCode 中操作 Git

### 3.1 打开项目

**方式一：命令行打开**
```bash
code "c:\工具开发\Demo\研发包部署\ota_deploy_tool"
```

**方式二：VSCode 菜单**
1. 打开 VSCode
2. `文件` → `打开文件夹...`
3. 选择 `c:\工具开发\Demo\研发包部署\ota_deploy_tool`

### 3.2 源代码管理面板（Git 可视化操作）

![VSCode 源代码管理面板](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/scm-viewlet.png)

**打开方式**：
- 快捷键：`Ctrl + Shift + G`
- 或点击左侧活动栏的「源代码管理」图标（第三个，分支形状）

**面板功能说明**：

| 区域 | 说明 |
|------|------|
| **更改** | 已修改但未暂存的文件（红色标记） |
| **暂存的更改** | 已 `git add` 待提交的文件（绿色标记） |
| **消息输入框** | 顶部输入提交信息 |
| **✓ 提交** | 提交暂存的更改 |
| **... 更多操作** | 推送、拉取、分支管理等 |

### 3.3 常用 VSCode Git 操作

#### 查看文件变更（Diff）

![VSCode Diff 视图](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/diff-editor.png)

- 在「更改」列表中点击文件 → 右侧打开 Diff 视图
- 左侧：原文件，右侧：修改后文件
- 红色背景 = 删除行，绿色背景 = 新增行

#### 暂存/取消暂存

- 点击文件右侧的 `+` → 暂存该文件
- 点击文件右侧的 `-` → 取消暂存
- 点击「更改」标题旁的 `+` → 暂存所有文件

#### 提交代码

1. 在消息输入框输入提交信息（如 `fix: 修复SSH连接超时问题`）
2. 点击 `✓ 提交` 按钮
3. 或点击 `✓ 提交` 旁的下拉箭头 → `提交并推送`

#### 推送/拉取

![VSCode 推送拉取](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/scm-viewlet.png)

- 点击底部状态栏的「同步更改」按钮（循环箭头图标）
- 或点击源代码管理面板的 `...` → `推送` / `拉取`

### 3.4 分支管理

**创建/切换分支**：

1. 点击 VSCode 左下角状态栏的分支名称（如 `master`）
2. 顶部弹出分支选择框
3. 选择已有分支切换，或输入新分支名创建

![VSCode 分支切换](https://code.visualstudio.com/assets/docs/sourcecontrol/branching/branch-picker.png)

---

## 4. 常用 Git 命令（终端执行）

### 4.1 在哪里输入命令

**方式一：VSCode 内置终端**
- 快捷键：`` Ctrl + ` ``（反引号）
- 或 `终端` → `新建终端`
- 确保终端路径在 `ota_deploy_tool` 目录下

![VSCode 终端](https://code.visualstudio.com/assets/docs/terminal/basics/terminal.png)

**方式二：Windows 终端 / PowerShell**
```bash
cd c:\工具开发\Demo\研发包部署\ota_deploy_tool
```

### 4.2 常用命令速查表

#### 基础操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git status` | 查看当前工作区状态 | `git status` |
| `git log --oneline` | 查看简洁提交历史 | `git log --oneline -10` |
| `git diff` | 查看未暂存的变更 | `git diff` |
| `git diff --cached` | 查看已暂存的变更 | `git diff --cached` |

#### 提交相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `git add <文件>` | 暂存指定文件 | `git add main.py` |
| `git add .` | 暂存所有变更 | `git add .` |
| `git commit -m "信息"` | 提交暂存内容 | `git commit -m "fix: 修复连接超时"` |
| `git commit -am "信息"` | 暂存+提交一步完成 | `git commit -am "feat: 新增主题切换"` |

#### 远程同步

| 命令 | 说明 | 示例 |
|------|------|------|
| `git push` | 推送到远程 | `git push origin master` |
| `git pull` | 拉取远程更新 | `git pull origin master` |
| `git fetch` | 获取远程信息（不合并） | `git fetch origin` |
| `git remote -v` | 查看远程仓库地址 | `git remote -v` |

#### 分支操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git branch` | 查看本地分支 | `git branch` |
| `git branch -a` | 查看所有分支（含远程） | `git branch -a` |
| `git checkout -b <分支>` | 创建并切换分支 | `git checkout -b feature/new-ui` |
| `git checkout <分支>` | 切换分支 | `git checkout master` |
| `git merge <分支>` | 合并分支 | `git merge feature/new-ui` |

#### 撤销/回退

| 命令 | 说明 | 示例 |
|------|------|------|
| `git restore <文件>` | 撤销未暂存的修改 | `git restore main.py` |
| `git restore --staged <文件>` | 取消暂存 | `git restore --staged main.py` |
| `git reset --soft HEAD~1` | 撤销上次提交（保留修改） | `git reset --soft HEAD~1` |
| `git reset --hard HEAD~1` | 撤销上次提交（丢弃修改） | `git reset --hard HEAD~1` |

### 4.3 提交信息规范

本项目使用约定式提交（Conventional Commits）：

```
<类型>: <简短描述>

类型:
  feat    - 新功能
  fix     - 修复
  docs    - 文档
  test    - 测试
  chore   - 杂项
  bugfix  - Bug 修复
  refactor- 重构
```

**示例**：
```
feat: v3.1 主题切换+包校验+配置历史
fix: 修复板端连接方式，通过工控机SSH隧道跳转
docs: 添加v3.1+新需求REQ-019~022
test: v3.0部署历史与模板管理测试报告
```

---

## 5. 代码上传流程

### 5.1 首次上传（新文件）

```mermaid
graph LR
    A[修改代码] --> B[git add .]
    B --> C[git commit -m "信息"]
    C --> D[git push]
```

**详细步骤**：

1. **确认状态**
   ```bash
   git status
   ```
   查看哪些文件被修改/新增

2. **暂存文件**
   ```bash
   git add .
   ```
   或只暂存特定文件：
   ```bash
   git add 研发专用/core/deployment_engine.py
   ```

3. **提交到本地仓库**
   ```bash
   git commit -m "feat: 新增XX功能"
   ```

4. **推送到远程 GitHub**
   ```bash
   git push origin master
   ```

### 5.2 日常上传流程

```bash
# 1. 先拉取最新代码（避免冲突）
git pull origin master

# 2. 修改代码...

# 3. 查看变更
git status
git diff

# 4. 暂存并提交
git add .
git commit -m "fix: 修复XX问题"

# 5. 推送到远程
git push origin master
```

### 5.3 VSCode 可视化上传

1. 修改文件后，打开源代码管理面板（`Ctrl + Shift + G`）
2. 查看「更改」列表中的文件
3. 点击文件可查看 Diff
4. 点击文件旁的 `+` 暂存
5. 顶部输入提交信息
6. 点击 `✓ 提交`
7. 点击底部状态栏的「同步更改」推送

---

## 6. 代码下载/同步流程

### 6.1 首次克隆（新电脑）

```bash
# 克隆仓库
git clone https://github.com/8E4GPUX/Carizon-FF.git

# 进入目录
cd Carizon-FF
```

### 6.2 拉取最新代码

```bash
# 方式一：拉取并自动合并
git pull origin master

# 方式二：先获取再手动合并
git fetch origin
git merge origin/master
```

### 6.3 VSCode 中同步

- 点击底部状态栏的「同步更改」按钮（循环箭头图标）
- 或使用快捷键：`Ctrl + Shift + G` → `...` → `拉取`

---

## 7. 新建分支与功能开发

### 7.1 分支命名规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `feature/` | 新功能 | `feature/theme-switch` |
| `fix/` | 修复 | `fix/ssh-timeout` |
| `docs/` | 文档 | `docs/api-guide` |
| `refactor/` | 重构 | `refactor/deploy-engine` |

### 7.2 分支开发流程

```bash
# 1. 确保在 master 分支且代码最新
git checkout master
git pull origin master

# 2. 创建功能分支
git checkout -b feature/theme-switch

# 3. 开发、提交...
git add .
git commit -m "feat: 新增主题切换功能"

# 4. 推送到远程
git push origin feature/theme-switch

# 5. 合并回 master
git checkout master
git merge feature/theme-switch
git push origin master

# 6. 可选：删除功能分支
git branch -d feature/theme-switch
```

---

## 8. 部署与运行

### 8.1 安装依赖

```bash
cd c:\工具开发\Demo\研发包部署\ota_deploy_tool\研发专用
pip install -r requirements.txt
```

依赖清单：
- `PyQt5>=5.15.0` — GUI 界面
- `paramiko>=2.8.0` — SSH/SFTP 通信
- `cryptography>=3.4.0` — 配置加密

### 8.2 运行程序

```bash
cd c:\工具开发\Demo\研发包部署\ota_deploy_tool\研发专用
python main.py
```

### 8.3 程序功能界面

![程序主界面示意](https://picsum.photos/800/500)

> 主界面采用网易云音乐暗色风格，包含：
> - **顶部导航栏**：Logo、版本号、连接状态
> - **信息卡片**：升级包数量、部署进度、当前状态、运行时间
> - **左侧面板**：升级包选择（支持拖拽）、部署进度表格
> - **右侧面板**：日志输出、操作按钮
> - **底部操作栏**：开始部署、停止、设置等

### 8.4 部署配置

程序启动后，通过 `设置` 按钮配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 工控机 IP | 工控机网络地址 | 自动检测 |
| 工控机 密码 | SSH 登录密码 | Carizon!@#2025 |
| 板端 IP | 板端网络地址 | 通过工控机跳转 |
| 板端 用户名 | SSH 登录用户 | root |
| SSH 超时 | 连接超时秒数 | 8s |
| 重启等待 | 设备重启等待时间 | 60~300s |

---

## 9. 常见问题

### 9.1 Git 相关

**Q: 推送被拒绝（push rejected）**
```bash
# 原因：远程有本地没有的提交
# 解决：先拉取再推送
git pull origin master --rebase
git push origin master
```

**Q: 冲突（merge conflict）**
```
# 出现 CONFLICT 提示时：
1. 打开冲突文件（VSCode 会高亮标记）
2. 选择保留哪个版本（当前/传入/两者都保留）
3. 保存文件
4. git add .
5. git commit
```

![VSCode 冲突解决](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/merge-conflict.png)

**Q: 想撤销未提交的修改**
```bash
git restore <文件名>        # 撤销单个文件
git restore .               # 撤销所有修改
```

**Q: 想修改上次提交信息**
```bash
git commit --amend -m "新的提交信息"
```

### 9.2 运行相关

**Q: 提示模块找不到**
```bash
# 确保在 研发专用 目录下运行
cd c:\工具开发\Demo\研发包部署\ota_deploy_tool\研发专用
python main.py
```

**Q: SSH 连接失败**
1. 检查工控机 IP 是否正确
2. 检查网络连通性：`ping <工控机IP>`
3. 检查密码是否正确
4. 查看日志文件：`研发专用/logs/`

**Q: 加密配置丢失**
```
config/.config_key 和 config/deploy_config.enc 被 .gitignore 排除
不会提交到 Git，换电脑后需要重新配置
```

---

## 附录

### A. Git 命令速查卡

```
┌─────────────────────────────────────────────┐
│              Git 常用命令速查                  │
├─────────────────────────────────────────────┤
│ git status         查看状态                   │
│ git add .          暂存所有                   │
│ git commit -m "msg" 提交                     │
│ git push           推送                      │
│ git pull           拉取                      │
│ git log --oneline  查看历史                   │
│ git branch         查看分支                   │
│ git checkout -b x  新建并切换分支              │
│ git merge x        合并分支 x                 │
│ git diff           查看变更                   │
│ git restore .      撤销修改                   │
└─────────────────────────────────────────────┘
```

### B. 提交类型参考

| 类型 | 使用场景 |
|------|----------|
| `feat` | 新功能（feature） |
| `fix` | 修复 bug |
| `docs` | 文档变更 |
| `test` | 测试相关 |
| `chore` | 构建/工具链 |
| `refactor` | 重构 |
| `bugfix` | Bug 修复 |
| `style` | 代码格式 |

### C. 相关链接

| 资源 | 地址 |
|------|------|
| GitHub 仓库 | https://github.com/8E4GPUX/Carizon-FF |
| VSCode 下载 | https://code.visualstudio.com/ |
| Git 下载 | https://git-scm.com/ |
| Python 下载 | https://www.python.org/ |

---

> **文档版本**：v1.0
> **最后更新**：2026-07-06
> **适用项目**：Carizon-FF (OTA 可视化无感部署工具)
