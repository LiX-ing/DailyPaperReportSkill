# 顶会顶刊配置维护说明

## 文件位置
- 配置文件：`config/venues.yaml`

## 修改目标
你可以随时修改下列内容：
- 新增/删除领域
- 领域下新增/删除 venue 缩写
- 维护 `venue_aliases`（缩写对应全称/别名）
- 调整筛选参数（如 `default_year_window`）

## 推荐维护原则
1. 优先使用标准简称（例如 `ICML`, `NeurIPS`, `ICSE`）。
2. 一个 venue 一行，方便 diff。
3. 每次修改后更新 `updated_at`。
4. 若同一会议有多个写法（如 `FSE`, `ESEC/FSE`），可以都保留。

## 你当前关心的模板领域
- `ai`
- `data_mining`
- `machine_learning`
- `software_engineering`

## OpenAlex 匹配建议
当前实现优先读取 `venue_aliases` 做 venue 名称关键词匹配（大小写不敏感）。
- 如果发现漏召回：在 `venue_aliases` 里为该缩写增加全称或常见别名
- 如果发现误召回：删除过于泛化的别名，保留更精确的全称

## 示例
```yaml
domains:
  software_engineering:
    description: Software Engineering
    venues:
      - ICSE
      - FSE
      - ASE
      - TSE
      - TOSEM

venue_aliases:
  ICSE:
    - International Conference on Software Engineering
  TSE:
    - IEEE Transactions on Software Engineering
```
