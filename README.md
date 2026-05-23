# Paper Daily MVP

一个可运行的最小版本（MVP）：每天从指定领域顶会顶刊中挑 1 篇近两年论文，输出中文简洁版摘要。

## MVP 是什么？
MVP（Minimum Viable Product）= 最小可行产品。
它不是“完整功能”，而是“用最少功能先跑通核心价值”。

本项目核心价值：
- 自动选论文（按领域 + 顶会顶刊 + 年份）
- 自动生成中文简版（优先 abstract 翻译复用）
- 每天稳定产出 1 篇

## 功能现状
- 数据源：`openalex`（默认）/ `semantic_scholar`（替代）
- LLM 适配层：`local` / `openai` / `openai_compatible`
- Prompt 模板外置：`prompts/zh_summary_prompt.txt`
- 领域与 venue 配置：`config/venues.yaml`
- Skill 运行配置：`config/skill.yaml`（输出路径、输出格式、去重策略）
- 查询规划：`query_planner.py`（自然语言解析成 domain/year/venue/keywords）
- 相关性排序：`scorer.py`（对候选论文按查询意图打分）
- 数据源能力层：`source_capabilities.py`（声明各 source 的查询能力）
- 去重：SQLite（`data/seen_papers.db`）
- 输出：Markdown（`output/YYYY-MM-DD-paper.md`）
- 规则：优先翻译 abstract；若 abstract 过短，输出占位提示（后续可接 PDF 全文总结）
- 落盘规则：默认命中即写入 Markdown，除非显式 `--no-save` 或 query 中明确要求不保存

## 快速开始

1. 安装依赖

```bash
cd paper-daily-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果你要启用 OpenAI 或 OpenAI 兼容接口（例如很多第三方网关），再安装：

```bash
pip install -r requirements-openai.txt
```

2. 配置环境变量（可选但推荐）

```bash
cp .env.example .env
```

- 若配置 `LLM_API_KEY` 且 `LLM_PROVIDER` 非 `local`，会调用对应模型生成中文总结。
- 未配置时，使用本地规则生成基础中文结果。
- 推荐配置 `OPENALEX_EMAIL` 作为 OpenAlex API 请求标识。
- 推荐优先使用项目配置或本机 `SKILL_*` 变量：
  - `SKILL_BASE_URL`
  - `SKILL_AUTH_TOKEN`
  - `SKILL_MODEL`
- 若本机 shell 配置也没有，可在 `config/credentials.yaml` 中配置一份凭证（安装后可手动填写）。

通用配置（推荐）：

```env
LLM_PROVIDER=local
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_BASE_URL=
PAPER_SOURCE=openalex
VERIFY_SSL=true
OPENALEX_API_KEY=
OPENALEX_EMAIL=you@example.com
SEMANTIC_SCHOLAR_API_KEY=
FEISHU_WEBHOOK_URL=
```

`LLM_PROVIDER` 可选值：
- `local`：不调用任何模型 API（无需 key）
- `openai`：调用 OpenAI（需要 `LLM_API_KEY`）
- `openai_compatible`：调用 OpenAI 兼容接口（需要 `LLM_API_KEY`，常配 `LLM_BASE_URL`）

如果 `provider=local` 但检测到 `SKILL_BASE_URL + SKILL_AUTH_TOKEN`（或兼容变量），会自动切到 `openai_compatible`。

LLM 配置优先级（高 -> 低）：
- `config/credentials.yaml`（项目内，最推荐）
- `SKILL_*`（环境变量 / `~/.zhsrc` / `~/.zshrc`）
- `LLM_*` / `OPENAI_*` / `ANTHROPIC_*`（兼容）

OpenAlex 相关：
- `OPENALEX_API_KEY`：推荐配置，用于 API 额度与计费管理
- `OPENALEX_EMAIL`：可选联系邮箱参数（`mailto`），用于礼貌请求标识
- `VERIFY_SSL`：默认 `true`；若本地代理导致 TLS EOF，可临时设为 `false` 排查

飞书推送相关：
- `FEISHU_WEBHOOK_URL`：可选。配置后会在生成 `feishu_card_json` 后自动发送 webhook。

3. 运行

```bash
python -m src.main --domain ai
```

切换到 Semantic Scholar：

```bash
python -m src.main --domain ai --source semantic_scholar
```

切换到 OpenReview：

```bash
python -m src.main --domain ai --source openreview
```

离线/演示模式（不访问 OpenAlex）：

```bash
python -m src.main --domain ai --dry-run
```

可选参数：

```bash
python -m src.main --domain machine_learning --year-window 2
```

自然语言约束检索（自动识别年份/会议/领域）：

```bash
python -m src.main --domain ai --source openalex --query "给我一篇2026年AAAI发表的论文"
```

自然语言主题检索（如 multimodal，会做相关性排序）：

```bash
python -m src.main --domain ai --query "给我一篇2025~2026年multimodal顶会论文"
```

临时问答不落盘（显式关闭写文件）：

```bash
python -m src.main --domain ai --query "给我一篇ICML论文，不保存"
# 或
python -m src.main --domain ai --query "给我一篇ICML论文" --no-save
```

指定自定义 prompt 模板：

```bash
python -m src.main --domain ai --prompt-template prompts/zh_summary_prompt.txt
```

排查匹配问题（打印抓取数和匹配数）：

```bash
python -m src.main --domain ai --verbose
```

OpenAlex TLS 报错排查（仅排查用途）：

```bash
VERIFY_SSL=false python -m src.main --domain ai --source openalex --verbose
```

`--verbose` 会额外打印：
- 当前数据源
- SSL 校验状态
- 抓取候选数量
- venue 匹配数量

当 `--source openalex` 且匹配为 0 时，程序会自动尝试 `semantic_scholar` 作为回退源。

## API Key 用在哪些阶段

1. 论文检索阶段（OpenAlex）：不需要 LLM key，只使用公开 API。  
2. 论文筛选/去重阶段：不需要 key，本地逻辑。  
3. 中文翻译与总结阶段：需要 LLM key（仅当 `LLM_PROVIDER` 不是 `local`）。  
4. 报告输出阶段：不需要 key，本地写 Markdown。  

结论：当前流程里，只有“中文翻译与总结”这一步会用你的模型 API key。

## 目录

- `src/main.py` 主入口
- `src/openalex_client.py` OpenAlex 拉取
- `src/query_planner.py` 查询意图规划
- `src/scorer.py` 候选论文相关性打分
- `src/source_capabilities.py` source 能力声明
- `src/llm.py` LLM 适配层（provider 抽象）
- `src/prompt_loader.py` Prompt 模板加载
- `src/summarizer.py` 中文翻译与总结
- `src/storage.py` 去重存储
- `src/report.py` 报告输出
- `prompts/zh_summary_prompt.txt` 总结 Prompt 模板
- `config/venues.yaml` 顶会顶刊配置
- `config/skill.yaml` 输出与运行配置（md/json 路径、输出格式、生成去重策略）
- `docs/venues_maintenance.md` 配置维护文档
- `.github/workflows/daily.yml` GitHub Actions 示例

## 配置职责分离

- `config/venues.yaml`：检索语义配置（domain、venues、alias、selection 策略）
- `config/skill.yaml`：运行配置（输出目录、输出格式、生成历史去重策略）
- `config/credentials.yaml`：可选凭证配置（当本机环境未设置时使用）

`config/skill.yaml` 默认示例：

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
  enabled: false
  url: ""
```

Webhook 开关与地址优先级（高 -> 低）：
- 开关: 环境变量 `ENABLE_FEISHU_WEBHOOK=true/false` > `config/skill.yaml` 的 `webhook.enabled` > 默认 `false`
- 地址: 环境变量 `FEISHU_WEBHOOK_URL` > `config/skill.yaml` 的 `webhook.url`

## 本地生成一篇真实报告（非 dry-run）

1. 安装依赖

```bash
cd /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-openai.txt
```

2. 配置 `.env`（示例）

```env
LLM_PROVIDER=openai
LLM_API_KEY=你的真实key
LLM_MODEL=gpt-4.1-mini
OPENALEX_API_KEY=你的openalex key
OPENALEX_EMAIL=you@example.com
```

如果你用 OpenAI 兼容平台：

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的key
LLM_BASE_URL=https://你的兼容网关/v1
LLM_MODEL=对应模型名
OPENALEX_API_KEY=你的openalex key
OPENALEX_EMAIL=you@example.com
```

3. 验证 OpenAlex 连通性

```bash
curl -I https://api.openalex.org/works
```

返回 `200` 或 `301/302` 即通常可用；若报 DNS/连接错误，先处理网络问题。

4. 运行真实模式

```bash
python -m src.main --domain ai
```

5. 查看输出

报告会生成在 `output/`，例如 `output/2026-04-16-ai-paper.md`。

## 下一步建议
- 增加 PDF 抓取与全文总结（作为 abstract 不足时的 fallback）
- 增加推送（邮箱/飞书/Telegram/Notion）
- 增加质量评分（过滤弱摘要）


兼容网关推荐：`provider: compat_http`（不依赖 openai SDK，直接 HTTP 调用 `/chat/completions`）。

## 定时任务（跨平台）

- 安装/生成调度配置：
```bash
python scripts/install_scheduler.py --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml
```

- macOS 会自动安装 launchd。
- Linux/Windows 会打印可执行命令（cron/schtasks）。

## 自然语言改配置

```bash
python scripts/update_skill_config.py "我想让你停止定时任务" --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml
python scripts/update_skill_config.py "每天19点给我一个论文" --skill-config ~/.codex/skills/paper-daily-skill/config/skill.yaml
```

每次成功修改会记录到：
- `docs/config_history.md`
