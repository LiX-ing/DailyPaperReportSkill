# DailyPaperReportSkill

本项目包含两部分：
- `paper-daily-mvp/`：执行引擎（检索、总结、输出、推送）
- `skill-package/paper-daily-skill/`：可安装的 Skill 封装

## 1) 快速安装 Skill

```bash
cd /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp/skill-package
./install_skill.sh
```

安装后 Skill 目录：
- `~/.codex/skills/paper-daily-skill/`

## 2) 核心配置（以 Skill 目录为准）

### `~/.codex/skills/paper-daily-skill/config/credentials.yaml`

```yaml
llm:
  provider: compat_http
  model: deepseek-chat
  api_key: <YOUR_KEY>
  base_url: https://api.deepseek.com
  api_style: chat
```

### `~/.codex/skills/paper-daily-skill/config/skill.yaml`

```yaml
output:
  md_dir: output/md
  feishu_card_dir: output/feishu_cards
  formats:
    - markdown
    - feishu_card_json

dedup:
  enabled: true
  skip_if_generated: true

webhook:
  enabled: true
  url: https://open.feishu.cn/open-apis/bot/v2/hook/xxxx

schedule:
  enabled: true
  domain: ai
  source: openalex
  query: ""
  run_time: "19:00"
  timezone: "Asia/Shanghai"
```

## 3) 一条命令控制（推荐）

自然语言改配置 + 重装系统定时 + 可选立即执行：

```bash
python /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp/scripts/skill_ctl.py \
  "每天19点给我一个论文" \
  --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml \
  --run-now --verbose
```

停止定时任务：

```bash
python /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp/scripts/skill_ctl.py \
  "停止定时任务" \
  --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml
```

## 4) 手动执行一轮

```bash
cd /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp
python scripts/run_from_skill_config.py --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml --verbose
```

## 5) 本机定时任务

跨平台安装器：

```bash
python scripts/install_scheduler.py --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml
```

- macOS: 自动安装 `launchd`
- Linux: 打印 `cron` 安装命令
- Windows: 打印 `schtasks` 命令

## 6) GitHub Actions（CI/CD）

- `ci.yml`：push/PR 自动跑测试（CI）
- `daily.yml`：定时日报（CD-like 运行任务）

### 为什么你看到 CI 绿但 CD 没跑？

`daily.yml` 不会因为 push 触发，只会：
1. 到 cron 时间触发
2. 手动 `Run workflow` 触发

### 需要配置的 GitHub Secrets / Variables

Repository **Secrets**:
- `SKILL_AUTH_TOKEN`
- `FEISHU_WEBHOOK_URL`

Repository **Variables**:
- `SKILL_MODEL`（如 `deepseek-chat`）
- `SKILL_BASE_URL`（如 `https://api.deepseek.com`）

## 7) 验证

```bash
cd /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp
python -m unittest discover -s tests -v
```
