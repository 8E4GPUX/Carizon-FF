# Git + VSCode 操作流程指南

> 适用对象：需要使用 Git 进行版本控制、配合 VSCode 进行代码管理的开发人员
> 本文档介绍 Git 的基本操作流程，不绑定特定项目

---

## 目录

1. [环境准备](#1-环境准备)
2. [VSCode 中操作 Git](#2-vscode-中操作-git)
3. [常用 Git 命令（终端执行）](#3-常用-git-命令终端执行)
4. [代码上传流程](#4-代码上传流程)
5. [代码下载/同步流程](#5-代码下载同步流程)
6. [新建分支与功能开发](#6-新建分支与功能开发)
7. [常见问题](#7-常见问题)

---

## 1. 环境准备

### 1.1 安装 Git

从官网下载安装：https://git-scm.com/

安装完成后，打开终端验证：
```bash
git --version
```

首次使用需配置用户名和邮箱：
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

### 1.2 安装 VSCode

从官网下载安装：https://code.visualstudio.com/

### 1.3 克隆仓库到本地

```bash
# 将远程仓库克隆到本地（仓库地址由项目负责人提供）
git clone <仓库地址>

# 进入项目目录
cd <项目目录>
```

---

## 2. VSCode 中操作 Git

### 2.1 打开项目

**方式一：命令行打开**
```bash
code <项目目录路径>
```

**方式二：VSCode 菜单**
1. 打开 VSCode
2. `文件` → `打开文件夹...`
3. 选择项目目录

### 2.2 源代码管理面板（Git 可视化操作）

![VSCode 源代码管理面板](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/overview.png)

**打开方式**：
- 快捷键：`Ctrl + Shift + G`
- 或点击左侧活动栏的「源代码管理」图标（第三个，分支形状）

**面板功能说明**：

| 区域 | 说明 |
|------|------|
| **更改** | 已修改但未暂存的文件（M 标记） |
| **暂存的更改** | 已 `git add` 待提交的文件（A 标记） |
| **消息输入框** | 顶部输入提交信息 |
| **✓ 提交** | 提交暂存的更改 |
| **... 更多操作** | 推送、拉取、分支管理等 |

### 2.3 常用 VSCode Git 操作

#### 查看文件变更（Diff）

![VSCode Diff 视图](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/diff.png)

- 在「更改」列表中点击文件 → 右侧打开 Diff 视图
- 左侧：原文件，右侧：修改后文件
- 红色背景 = 删除行，绿色背景 = 新增行

#### 暂存/取消暂存

- 点击文件右侧的 `+` → 暂存该文件
- 点击文件右侧的 `-` → 取消暂存
- 点击「更改」标题旁的 `+` → 暂存所有文件

#### 提交代码

1. 在消息输入框输入提交信息（如 `fix: 修复登录超时问题`）
2. 点击 `✓ 提交` 按钮
3. 或点击 `✓ 提交` 旁的下拉箭头 → `提交并推送`

#### 推送/拉取

- 点击底部状态栏的「同步更改」按钮（循环箭头图标）
- 或点击源代码管理面板的 `...` → `推送` / `拉取`

### 2.4 分支管理

**创建/切换分支**：

1. 点击 VSCode 左下角状态栏的分支名称（如 `main`）
2. 顶部弹出分支选择框
3. 选择已有分支切换，或输入新分支名创建

![VSCode 分支切换](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/gitbranches.png)

---

## 3. 常用 Git 命令（终端执行）

### 3.1 在哪里输入命令

**方式一：VSCode 内置终端**
- 快捷键：`` Ctrl + ` ``（反引号）
- 或 `终端` → `新建终端`
- 确保终端路径在项目目录下

![VSCode 终端](https://code.visualstudio.com/assets/docs/terminal/basics/integrated-terminal.png)

**方式二：系统终端**
- Windows：PowerShell / CMD
- macOS：终端
- Linux：终端

```bash
# 先进入项目目录
cd <项目目录路径>
```

### 3.2 常用命令速查表

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
| `git add <文件>` | 暂存指定文件 | `git add src/index.js` |
| `git add .` | 暂存所有变更 | `git add .` |
| `git commit -m "信息"` | 提交暂存内容 | `git commit -m "fix: 修复连接超时"` |
| `git commit -am "信息"` | 暂存+提交一步完成（仅跟踪过的文件） | `git commit -am "feat: 新增用户模块"` |

#### 远程同步

| 命令 | 说明 | 示例 |
|------|------|------|
| `git push` | 推送到远程 | `git push origin main` |
| `git pull` | 拉取远程更新 | `git pull origin main` |
| `git fetch` | 获取远程信息（不合并） | `git fetch origin` |
| `git remote -v` | 查看远程仓库地址 | `git remote -v` |

#### 分支操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `git branch` | 查看本地分支 | `git branch` |
| `git branch -a` | 查看所有分支（含远程） | `git branch -a` |
| `git checkout -b <分支>` | 创建并切换分支 | `git checkout -b feature/login` |
| `git checkout <分支>` | 切换分支 | `git checkout main` |
| `git merge <分支>` | 合并分支到当前分支 | `git merge feature/login` |

#### 撤销/回退

| 命令 | 说明 | 示例 |
|------|------|------|
| `git restore <文件>` | 撤销未暂存的修改 | `git restore src/index.js` |
| `git restore --staged <文件>` | 取消暂存 | `git restore --staged src/index.js` |
| `git reset --soft HEAD~1` | 撤销上次提交（保留修改） | `git reset --soft HEAD~1` |
| `git reset --hard HEAD~1` | 撤销上次提交（丢弃修改） | `git reset --hard HEAD~1` |

### 3.3 提交信息规范

推荐使用约定式提交（Conventional Commits），格式统一、便于追溯：

```
<类型>: <简短描述>
```

**常用类型**：

| 类型 | 使用场景 | 示例 |
|------|----------|------|
| `feat` | 新功能 | `feat: 新增用户登录功能` |
| `fix` | 修复 Bug | `fix: 修复页面白屏问题` |
| `docs` | 文档变更 | `docs: 更新API使用说明` |
| `test` | 测试相关 | `test: 添加登录单元测试` |
| `chore` | 构建/工具链 | `chore: 升级依赖版本` |
| `refactor` | 重构 | `refactor: 重构数据查询逻辑` |
| `style` | 代码格式 | `style: 格式化代码缩进` |

---

## 4. 代码上传流程

### 4.1 首次上传（新文件）

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
   git add src/components/Button.jsx
   ```

3. **提交到本地仓库**
   ```bash
   git commit -m "feat: 新增按钮组件"
   ```

4. **推送到远程仓库**
   ```bash
   git push origin main
   ```

### 4.2 日常上传流程

```bash
# 1. 先拉取最新代码（避免冲突）
git pull origin main

# 2. 修改代码...

# 3. 查看变更
git status
git diff

# 4. 暂存并提交
git add .
git commit -m "fix: 修复XX问题"

# 5. 推送到远程
git push origin main
```

### 4.3 VSCode 可视化上传

1. 修改文件后，打开源代码管理面板（`Ctrl + Shift + G`）
2. 查看「更改」列表中的文件
3. 点击文件可查看 Diff
4. 点击文件旁的 `+` 暂存
5. 顶部输入提交信息
6. 点击 `✓ 提交`
7. 点击底部状态栏的「同步更改」推送

---

## 5. 代码下载/同步流程

### 5.1 首次克隆（新电脑）

```bash
# 克隆仓库（仓库地址由项目负责人提供）
git clone <仓库地址>

# 进入目录
cd <项目目录>
```

### 5.2 拉取最新代码

```bash
# 方式一：拉取并自动合并
git pull origin main

# 方式二：先获取再手动合并
git fetch origin
git merge origin/main
```

### 5.3 VSCode 中同步

- 点击底部状态栏的「同步更改」按钮（循环箭头图标）
- 或使用快捷键：`Ctrl + Shift + G` → `...` → `拉取`

---

## 6. 新建分支与功能开发

### 6.1 分支命名规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `feature/` | 新功能 | `feature/user-login` |
| `fix/` | 修复 | `fix/timeout-error` |
| `docs/` | 文档 | `docs/api-guide` |
| `refactor/` | 重构 | `refactor/database-layer` |
| `hotfix/` | 紧急修复 | `hotfix/crash-on-startup` |

### 6.2 分支开发流程

```bash
# 1. 确保在主分支且代码最新
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature/user-login

# 3. 开发、提交...
git add .
git commit -m "feat: 新增用户登录功能"

# 4. 推送到远程
git push origin feature/user-login

# 5. 合并回主分支
git checkout main
git merge feature/user-login
git push origin main

# 6. 可选：删除功能分支
git branch -d feature/user-login
```

---

## 7. 常见问题

### 7.1 Git 相关

**Q: 推送被拒绝（push rejected）**
```bash
# 原因：远程有本地没有的提交
# 解决：先拉取再推送
git pull origin main --rebase
git push origin main
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

![VSCode 冲突解决](https://code.visualstudio.com/assets/docs/sourcecontrol/overview/merge-editor-overview.png)

**Q: 想撤销未提交的修改**
```bash
git restore <文件名>        # 撤销单个文件
git restore .               # 撤销所有修改
```

**Q: 想修改上次提交信息**
```bash
git commit --amend -m "新的提交信息"
```

**Q: 不小心把不该提交的文件暂存了**
```bash
git restore --staged <文件名>   # 取消暂存，保留修改
```

### 7.2 其他常见问题

**Q: 提示「fatal: not a git repository」**
```bash
# 当前目录不是 Git 仓库
# 确认是否在正确的项目目录下
pwd          # 查看当前路径（Linux/macOS）
cd           # 切换到项目目录
```

**Q: 如何查看某次提交的具体修改**
```bash
git show <提交ID>            # 查看某次提交的详情
git log -p                   # 查看所有提交的详细 diff
```

**Q: 想暂存当前工作去处理其他事**
```bash
git stash                    # 暂存当前修改
git stash pop                # 恢复暂存的修改
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
│ git stash          暂存当前工作               │
└─────────────────────────────────────────────┘
```

### B. 相关链接

| 资源 | 地址 |
|------|------|
| Git 官网下载 | https://git-scm.com/ |
| VSCode 下载 | https://code.visualstudio.com/ |
| Git 官方文档 | https://git-scm.com/doc |
| 约定式提交规范 | https://www.conventionalcommits.org/ |

---

> **文档版本**：v1.0
> **适用场景**：通用 Git + VSCode 操作指南，不绑定特定项目
