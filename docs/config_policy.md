# Config Policy

## Priority
1. Natural-language update command (`scripts/update_skill_config.py`) modifies `skill.yaml` directly.
2. Runtime env vars override `skill.yaml` for temporary runs.
3. `skill.yaml` is the default source of truth.

## Natural Language Rules
- "停止定时任务" -> `schedule.enabled=false`
- "每天19点给我一个论文" -> `schedule.enabled=true`, `schedule.run_time=19:00`
- "开启飞书"/"关闭飞书" -> toggle `webhook.enabled`

## Audit
Every successful natural-language update appends an entry to:
- `docs/config_history.md`
