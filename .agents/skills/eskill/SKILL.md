---
name: eskill
description: skill统一管理 CLI 工具，当用户需要安装、管理、搜索、更新、删除或使用skill时使用此技能，而不是直接操作skill文件夹。
---

# Eskill - AI Agent 技能管理器

Eskill 是 AI agents (Codex, Cursor, Windsurf) 的统一技能管理工具。它支持从 Git 仓库安装技能、管理本地/全局技能集合、搜索 SkillsMP 市场，以及保持技能更新。

## 安装

```bash
npm install -g eskill
```

## 核心概念

### 技能位置

**本地技能**（默认）：`./.Codex/skills/`
- 项目特定的技能
- 仅在当前项目中可用

**全局技能**（`-g` 标志）：`~/.eskill/skills/`
- 在所有项目间共享
- 必须链接到特定项目才能使用

### 技能来源

技能可以来自不同的来源：
- 🔗 **软链接** - 指向全局技能的软链接
- 📋 **复制** - 从全局仓库复制
- 📥 **GitHub** - 直接从 GitHub 下载
- 👤 **本地** - 用户创建的本地技能

## 快速开始

### 安装技能

**从 Git URL：**
```bash
# GitHub 或 GitLab 仓库
eskill install https://github.com/owner/skill-repo
eskill install https://gitlab.com/owner/skill-repo

# 简写格式（搜索后）
eskill install pdf-tool@username
```

**安装选项：**
```bash
# 安装到全局目录
eskill install -g https://github.com/owner/skill-repo

# 使用符号链接而不是复制
eskill install -l https://github.com/owner/skill-repo

# 强制覆盖已存在的技能
eskill install -f https://github.com/owner/skill-repo

# 为特定的 agent 安装 (Codex, cursor, windsurf)
eskill install -a cursor https://github.com/owner/skill-repo
```

### 列出技能

```bash
# 列出本地技能
eskill list

# 列出全局技能
eskill list -g

# 列出特定 agent 的技能
eskill list -a windsurf
```

输出显示：
- 技能名称和作者（如果适用）
- 版本或 commit 哈希
- 来源类型（symlink、copied、GitHub、local）

### 搜索技能

搜索 SkillsMP 市场（需要 API key）：

```bash
# 基本搜索
eskill search pdf

# 分页搜索
eskill search pdf --page 2
eskill search pdf -p 2

# 按最近更新排序（而不是按星标）
eskill search pdf --sort recent

# AI 语义搜索
eskill search "文档处理" --ai

# 限制结果数量
eskill search pdf --limit 50
```

### 更新技能

```bash
# 更新所有技能
eskill update

# 更新特定技能
eskill update pdf-tool

# 强制更新即使版本匹配
eskill update -f pdf-tool

# 更新全局技能
eskill update -g
```

### 删除技能

```bash
# 删除本地技能
eskill remove pdf-tool

# 删除全局技能
eskill remove -g pdf-tool

# 备选命令：uninstall 或 rm
eskill uninstall pdf-tool
eskill rm pdf-tool
```

## 高级用法

### 链接全局技能

将全局技能链接到本地项目：

```bash
eskill link pdf-tool@username
```

从 `~/.eskill/skills/` 创建软链接到 `./.Codex/skills/`。

### 上传到全局仓库

将本地技能上传到全局仓库：

```bash
eskill upload pdf-tool@username
```

### 配置

**设置 SkillsMP API Key**（搜索所需）：

```bash
eskill config set-api-key
```

从以下地址获取 API key：https://skillsmp.com/docs/api

**检查配置状态：**

```bash
eskill config status
```

### 支持的 Agents

列出所有支持的 AI agents：

```bash
eskill agents
```

目前支持的：
- **Codex**（默认）- `.Codex/skills/`
- **cursor** - `.cursor/skills/`
- **windsurf** - `.windsurf/skills/`

### Shell 自动补全

为 bash/zsh 生成补全脚本：

```bash
# Bash
eskill completion --shell bash > ~/.bash_completion
source ~/.bash_completion

# Zsh
eskill completion --shell zsh > ~/.zsh_completion
source ~/.zsh_completion
```

添加到 `~/.bashrc` 或 `~/.zshrc` 以持久化。

### 清理

**删除所有已安装的技能：**

```bash
eskill cleanup        # 仅本地技能
eskill cleanup -g     # 仅全局技能
```

**删除所有内容**（技能 + 配置）：

```bash
eskill cleanup --all
```

## 命令参考

详细的命令语法、选项和示例，请参见 [COMMANDS.md](references/COMMANDS.md)。

## 技能目录结构

技能具有以下结构：

```
skill-name/
├── SKILL.md           # 技能元数据和说明
├── pyproject.toml     # Python 依赖（如果使用脚本）
├── .python-version    # Python 版本（如果使用脚本）
├── scripts/           # 可执行的 Python 脚本
├── references/        # 参考文档
└── assets/            # 模板、图片等
```

## 常见工作流程

### 查找并安装技能

1. **搜索**技能：
   ```bash
   eskill search pdf
   ```

2. **安装**所需技能：
   ```bash
   eskill install pdf-tool@username
   ```

3. **验证**安装：
   ```bash
   eskill list
   ```

### 设置全局技能

1. **全局安装**：
   ```bash
   eskill install -g https://github.com/owner/useful-skill
   ```

2. **链接到项目**：
   ```bash
   cd /path/to/project
   eskill link useful-skill@owner
   ```

3. **验证**链接：
   ```bash
   eskill list
   ```

### 保持技能更新

```bash
# 检查当前版本
eskill list

# 更新所有技能
eskill update

# 更新特定技能
eskill update useful-skill
```

## 故障排除

**安装后找不到技能：**
- 检查是否使用了全局标志：`eskill list -g`
- 链接全局技能：`eskill link skill-name@author`

**搜索不工作：**
- 验证 API key：`eskill config status`
- 设置 API key：`eskill config set-api-key`

**权限错误：**
- 全局安装可能需要 sudo
- 考虑使用不带 `-g` 的本地安装

## 最佳实践

1. 使用**全局技能**存放跨项目的可复用工具
2. 使用**本地技能**存放项目特定功能
3. **定期更新**技能以获取最新功能
4. 在构建自定义技能前先**搜索 SkillsMP**
5. **链接全局技能**以避免在项目中重复
