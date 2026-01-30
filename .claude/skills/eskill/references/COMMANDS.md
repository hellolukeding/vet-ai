# Eskill Command Reference

Complete reference for all eskill commands with syntax, options, and examples.

## Global Options

These options can be used with any command:

```
-g, --global    Use global skill directory (~/.eskill/skills/)
                instead of local (./.claude/skills/)
```

---

## install (alias: add)

Install a skill from a Git repository URL.

### Syntax

```bash
eskill install [options] <url>
eskill add [options] <url>
```

### Arguments

- `url` - GitHub or GitLab repository URL

### Options

```
-a, --agent <name>    Target agent (claude, cursor, windsurf)
                      Default: auto-detected or claude

-l, --link           Use symbolic link instead of copying
                      Only applies to global installations

-f, --force          Force overwrite if skill already exists
```

### Examples

```bash
# Basic installation
eskill install https://github.com/owner/skill-repo

# Install globally
eskill install -g https://github.com/owner/skill-repo

# Install with symlink
eskill install -l -g https://github.com/owner/skill-repo

# Force reinstall
eskill install -f https://github.com/owner/skill-repo

# Install for specific agent
eskill install -a cursor https://github.com/owner/skill-repo

# Short alias
eskill add https://github.com/owner/skill-repo
```

---

## list (alias: ls)

List installed skills.

### Syntax

```bash
eskill list [options]
eskill ls [options]
```

### Options

```
-a, --agent <name>    Target agent (claude, cursor, windsurf)
                      Default: auto-detected or claude
```

### Output Format

```
已安装的技能 (./.claude/skills/):

  • skill-name@author [🔗 软链]
    版本: v1.0.0

  • another-skill [📥 GitHub]
    版本: #a1b2c3d

总计: 2 个技能
```

### Examples

```bash
# List local skills
eskill list

# List global skills
eskill list -g

# List for specific agent
eskill list -a windsurf
```

---

## remove (alias: rm, uninstall)

Remove an installed skill.

### Syntax

```bash
eskill remove [options] <name>
eskill rm [options] <name>
eskill uninstall [options] <name>
```

### Arguments

- `name` - Skill name (with optional @author suffix)

### Options

```
-a, --agent <name>    Target agent (claude, cursor, windsurf)
                      Default: auto-detected or claude
```

### Examples

```bash
# Remove local skill
eskill remove pdf-tool

# Remove global skill
eskill remove -g pdf-tool

# Remove with author specification
eskill remove pdf-tool@username

# Use short alias
eskill rm pdf-tool
```

---

## link

Link a global skill to the local project.

### Syntax

```bash
eskill link <name>
```

### Arguments

- `name` - Skill name with author (name@author format)

### Examples

```bash
# Link a global skill
eskill link pdf-tool@username
```

---

## upload

Upload a local skill to the global repository.

### Syntax

```bash
eskill upload <name>
```

### Arguments

- `name` - Skill name with author (name@author format)

### Examples

```bash
# Upload local skill to global
eskill upload my-skill@username
```

---

## update

Update installed skills to their latest versions.

### Syntax

```bash
eskill update [options] [name]
```

### Arguments

- `name` - Skill name (optional, updates all if not specified)
  - Use "all" to explicitly update all skills

### Options

```
-f, --force          Force update even if version matches
```

### Examples

```bash
# Update all skills
eskill update

# Update specific skill
eskill update pdf-tool

# Force update
eskill update -f pdf-tool

# Update all explicitly
eskill update all

# Update global skills
eskill update -g
```

---

## search

Search for skills in the SkillsMP marketplace.

**Note:** Requires API key configuration (`eskill config set-api-key`)

### Syntax

```bash
eskill search [options] <query>
```

### Arguments

- `query` - Search keywords or phrases

### Options

```
-p, --page <number>     Page number (default: 1)
-l, --limit <number>    Results per page, max 100 (default: 20)
-s, --sort <by>         Sort by: stars or recent (default: stars)
--ai                    Use AI semantic search
```

### Examples

```bash
# Basic search
eskill search pdf

# Search with pagination
eskill search pdf --page 2
eskill search pdf -p 2

# Sort by recent
eskill search pdf --sort recent

# AI semantic search
eskill search "document processing" --ai

# Limit results
eskill search pdf --limit 50

# Combine options
eskill search pdf --page 2 --limit 50 --sort recent
```

### Output Format

Search results display:
- Skill name and author
- Description
- Star count
- Updated date
- Installation command example

---

## config

Manage eskill configuration.

### Syntax

```bash
eskill config <action>
```

### Actions

#### set-api-key

Set the SkillsMP API key (required for search).

```bash
eskill config set-api-key
```

Prompts for API key input interactively.

Get API key from: https://skillsmp.com/docs/api

#### status

Display current configuration status.

```bash
eskill config status
```

Shows:
- API key configuration status
- Global and local skill directories
- Currently configured agent

### Examples

```bash
# Set API key
eskill config set-api-key

# Check status
eskill config status
```

---

## cleanup

Remove eskill data (skills and/or configuration).

### Syntax

```bash
eskill cleanup [options]
```

### Options

```
-a, --all      Remove ALL data including:
               - API key configuration
               - Global and local skills
               - All eskill metadata

               (Without --all, only removes skills)
```

### Examples

```bash
# Remove local skills only
eskill cleanup

# Remove global skills only
eskill cleanup -g

# Remove everything (skills + config)
eskill cleanup --all
```

**Warning:** `--all` permanently deletes all eskill data including API keys.

---

## agents (alias: list-agents)

List supported AI agents and their skill directories.

### Syntax

```bash
eskill agents
eskill list-agents
```

### Output Format

```
Supported Agents:

  • claude        - Claude
    .claude/skills/

  • cursor        - Cursor
    .cursor/skills/

  • windsurf      - Windsurf
    .windsurf/skills/
```

---

## completion

Generate shell auto-completion scripts.

### Syntax

```bash
eskill completion [options]
```

### Options

```
-s, --shell <type>    Shell type: bash or zsh (default: bash)
```

### Examples

```bash
# Generate bash completion
eskill completion --shell bash > ~/.bash_completion
source ~/.bash_completion

# Generate zsh completion
eskill completion --shell zsh > ~/.zsh_completion
source ~/.zsh_completion

# Add to ~/.bashrc for persistence
echo 'source ~/.bash_completion' >> ~/.bashrc

# Add to ~/.zshrc for persistence
echo 'source ~/.zsh_completion' >> ~/.zshrc
```

---

## Internal Commands

These commands are used internally by eskill for auto-completion:

- `_list_skills` - List all skill names
- `_list_local_skills` - List local skill names
- `_list_global_skills` - List global skill names

---

## Exit Codes

- `0` - Success
- `1` - Error (invalid input, command failed, etc.)

---

## Environment Variables

Eskill respects these environment variables:

- `HOME` - User home directory (for global skills)
- `PATH` - System path for executable location
