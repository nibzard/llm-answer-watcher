# Claude Code Hooks for LLM Answer Watcher

This project uses **Claude Code hooks** to automatically enforce code quality and maintain git commit hygiene. Hooks are shell commands that execute at specific points during development.

## Configured Hooks

### 1. **Ruff Linting Hook** 🔍

**Event**: `PostToolUse` (runs after Edit/Write operations)
**Matcher**: `Edit|Write`
**Purpose**: Automatically lint Python files after editing

**What it does**:
- Detects when a `.py` file is edited or created
- Runs `ruff check --fix --quiet` on the file
- Auto-fixes issues when possible
- Reports results after each edit

**Example output**:
```
🔍 Running ruff on llm_answer_watcher/config/loader.py...
✅ Ruff check passed
```

or

```
🔍 Running ruff on llm_answer_watcher/cli.py...
⚠️  Ruff found issues:
  llm_answer_watcher/cli.py:15:1: F401 'typing.Union' imported but unused
  llm_answer_watcher/cli.py:23:10: UP007 Use `X | Y` for union types
```

**Configuration**: See `ruff.toml` for linting rules

---

### 2. **Git Conventional Commit Reminder** 📝

**Event**: `Stop` (runs when Claude Code finishes responding)
**Matcher**: `*` (all tools)
**Purpose**: Remind about uncommitted changes and conventional commit format

**What it does**:
- Checks for uncommitted changes in git
- Displays count of modified files
- Shows conventional commit format examples
- Only activates if there are actual changes

**Example output**:
```
📝 Git Status: 5 file(s) modified
💡 Consider committing with conventional commit format:
   feat: add new feature
   fix: bug fix
   docs: documentation changes
   refactor: code refactoring
   test: add or update tests
   chore: maintenance tasks
```

**Conventional commit types**:
- `feat:` - New feature implementation
- `fix:` - Bug fix
- `docs:` - Documentation changes only
- `refactor:` - Code refactoring (no behavior change)
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks (dependencies, config)
- `style:` - Code style changes (formatting)
- `perf:` - Performance improvements
- `ci:` - CI/CD configuration changes

**Example commits**:
```bash
git commit -m "feat: implement config loader with Pydantic validation"
git commit -m "fix: prevent SQL injection in brand mention queries"
git commit -m "docs: add API documentation for LLM runner module"
git commit -m "test: add 80% coverage for mention detector"
git commit -m "refactor: extract retry logic to utils module"
git commit -m "chore: add ruff and pytest to dependencies"
```

---

## Hook Configuration

Hooks are defined in `.claude/hooks.json` and apply to this project only.

### Viewing Current Hooks

```bash
cat .claude/hooks.json | jq
```

### Testing Hooks

**Test ruff hook**:
1. Edit any Python file: `echo "import sys" > test.py`
2. Save the file (use Edit/Write tool)
3. Watch for ruff output

**Test git reminder**:
1. Make changes to files
2. Wait for Claude Code to finish responding
3. See git status reminder

---

## Customizing Hooks

### Disable a Hook Temporarily

Edit `.claude/hooks.json` and comment out the hook or change the matcher:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "DISABLED_Edit|Write",
        "hooks": [...]
      }
    ]
  }
}
```

### Add More Hooks

#### Example: pytest hook (run tests after editing test files)

```json
{
  "matcher": "Edit|Write",
  "hooks": [
    {
      "type": "command",
      "command": "file=$(jq -r '.tool_input.file_path // empty'); if [[ \"$file\" == *test_*.py ]]; then echo \"\\n🧪 Running pytest on $file...\"; pytest \"$file\" -v --tb=short; fi"
    }
  ]
}
```

#### Example: mypy type checking hook

```json
{
  "matcher": "Edit|Write",
  "hooks": [
    {
      "type": "command",
      "command": "file=$(jq -r '.tool_input.file_path // empty'); if [[ \"$file\" == *.py ]] && command -v mypy &> /dev/null; then echo \"\\n🔎 Running mypy on $file...\"; mypy \"$file\" --strict; fi"
    }
  ]
}
```

---

## Ruff Configuration

The project uses `ruff.toml` to enforce Python 3.12+ patterns:

**Key enforcements**:
- ✅ Modern type hints (`X | Y`, not `Union[X, Y]`)
- ✅ Timezone-aware datetimes (UTC required)
- ✅ Pathlib over `os.path`
- ✅ No shadowing builtins
- ✅ Import sorting (isort)
- ✅ Code simplification suggestions
- ✅ Unused variable detection

**Auto-fixes enabled**:
- Import sorting
- Quote normalization
- Modern syntax conversions (UP rules)
- Comprehension simplifications

**Manual review required**:
- Complex logic issues
- Potential bugs (flake8-bugbear)
- Performance concerns

---

## Benefits

### For Developers

- **Instant feedback**: Catch issues immediately after editing
- **Consistent style**: Ruff auto-fixes formatting
- **Prevent regressions**: Enforces Python 3.12+ patterns
- **Clean commits**: Reminder to use conventional format

### For AI Agents

- **Structured feedback**: Hooks provide deterministic validation
- **Clear rules**: ruff.toml defines exact standards
- **Automated fixes**: Reduces back-and-forth iterations
- **Quality gates**: Ensures production-ready code

### For the Project

- **Maintainability**: Consistent code style throughout
- **Documentation**: Git history is readable with conventional commits
- **Security**: Catches common vulnerabilities (SQL injection, etc.)
- **Performance**: Identifies inefficient patterns

---

## Troubleshooting

### Hook not running

**Check hook configuration**:
```bash
cat .claude/hooks.json | jq '.hooks'
```

**Verify matcher syntax**:
- Use `Edit|Write` for multiple tools
- Use `*` for all tools
- Tool names are case-sensitive

### Ruff errors persist

**Check ruff installation**:
```bash
which ruff
ruff --version
```

**Run manually**:
```bash
ruff check . --fix
```

**View configuration**:
```bash
cat ruff.toml
```

### Git reminder not showing

**Verify git repository**:
```bash
git status
```

**Check for uncommitted changes**:
```bash
git diff
git status --porcelain
```

---

## Advanced Usage

### Chain Multiple Hooks

You can run multiple commands in sequence:

```json
{
  "matcher": "Edit|Write",
  "hooks": [
    {
      "type": "command",
      "command": "ruff check file && mypy file && echo '✅ All checks passed'"
    }
  ]
}
```

### Conditional Logic

Use shell conditionals for complex behavior:

```json
{
  "type": "command",
  "command": "if [ condition ]; then action1; else action2; fi"
}
```

### JSON Parsing

Access tool parameters via `jq`:

```bash
file=$(jq -r '.tool_input.file_path')
command=$(jq -r '.tool_input.command')
old_string=$(jq -r '.tool_input.old_string')
```

---

## Security Considerations

**Hooks run with your shell permissions** - they can:
- Read/write files
- Execute commands
- Access environment variables
- Make network requests

**Best practices**:
- ✅ Review hooks before enabling
- ✅ Keep hooks in version control (`.claude/hooks.json`)
- ✅ Avoid secrets in hook commands
- ✅ Use quotes around file paths
- ❌ Don't run untrusted hook code
- ❌ Don't expose API keys in hooks

---

## Resources

- [Claude Code Hooks Documentation](https://docs.claude.com/en/docs/claude-code/hooks-guide)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Python 3.12+ Type Hints](https://docs.python.org/3/library/typing.html)

---

**Built for the LLM Answer Watcher project**

Hooks ensure production-ready code quality from the first commit. 🚀
