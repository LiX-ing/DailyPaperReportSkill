# 架构说明（面向可扩展）

## 流程阶段
1. 论文检索（OpenAlex）
2. 领域/venue 过滤
3. 去重（SQLite）
4. 中文翻译与总结（LLM provider 适配层）
5. Markdown 报告输出

## API Key 使用阶段
- 仅阶段 4 需要 LLM API key（当 provider 非 `local`）。
- 其余阶段均不依赖 LLM key。

## 扩展点
- 数据源扩展：在 `src/openalex_client.py` 同层新增 `openreview_client.py` 等。
- LLM 扩展：在 `src/llm.py` 增加 provider 客户端类，并接入 `build_llm_client`。
- 输出扩展：在 `src/report.py` 之外新增 push 适配（飞书/邮件/Telegram）。
- 领域配置扩展：维护 `config/venues.yaml`。

## 兼容策略
- 新环境变量：`LLM_*`
- 向后兼容：保留读取 `OPENAI_*`
