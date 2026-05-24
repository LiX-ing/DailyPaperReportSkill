---
name: paper-daily-skill
description: Run the local paper daily pipeline, generate detailed markdown + optional Feishu card webhook, and summarize results for the user.
---

# Paper Daily Skill

## When to Use
Use this skill when user asks to:
- generate today's paper daily report
- run one-off constrained paper query (year/venue/topic)
- verify pipeline output paths or webhook delivery status

## Default Run
Run cache-first daily generation for domain `ai`:
```bash
$HOME/.codex/skills/paper-daily-skill/scripts/run_paper_daily.sh ai openalex
```

## Constraint Run
If user gives constraints, pass the full user text as query:
```bash
$HOME/.codex/skills/paper-daily-skill/scripts/run_paper_daily.sh ai openalex "<user_query>"
```

## Webhook Behavior
- Controlled by `ENABLE_FEISHU_WEBHOOK` (env) and `config/skill.yaml` (`webhook.enabled`).
- If disabled or missing `FEISHU_WEBHOOK_URL`, generation still succeeds.
- Webhook failure is non-blocking.

## Output Files
- Markdown: `<project_root>/output/md/`
- Feishu card JSON: `<project_root>/output/feishu_cards/`

After running, read the latest markdown report and return concise Chinese summary.

## Validation
If user asks for validation, run:
```bash
cd <project_root> && python -m unittest discover -s tests -v
```

## References
- `references/usage.md`
- `scripts/run_paper_daily.sh`


## Config
- Skill config file: `~/.codex/skills/paper-daily-skill/config/skill.yaml`
- Skill credentials: `~/.codex/skills/paper-daily-skill/config/credentials.yaml`
- Local runtime override: `~/.codex/skills/paper-daily-skill/config/local.env` (optional, path only)
- Feishu webhook env: `FEISHU_WEBHOOK_URL`
- Feishu switch: `ENABLE_FEISHU_WEBHOOK=true/false` (overrides config)

- You can also set webhook URL in `config/skill.yaml` as `webhook.url` (env still overrides).


## One-Command Control
Use unified controller for natural language scheduling:
```bash
python scripts/skill_ctl.py "每天19点给我一个论文" --skill-config "$HOME/.codex/skills/paper-daily-skill/config/skill.yaml" --run-now --verbose
```


## Natural Language Scheduling
For requests like "每天19点给我一个论文" or "停止定时任务", run:
```bash
python scripts/skill_ctl.py "<user_request>" --skill-config "$HOME/.codex/skills/paper-daily-skill/config/skill.yaml" --run-now --verbose
```
Do not use default report flow for schedule-edit intents.
