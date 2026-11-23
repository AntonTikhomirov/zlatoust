## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. When the answer is under a Markdown heading, `graphify section "<heading>"` prints that section's text, so the .md need not be opened. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## Правила проекта Златоуст

- Язык интерфейса и текстов — только русский.
- Граф знаний проекта лежит в `graphify-out/` и коммитится в репозиторий. Перед вопросами об устройстве проекта сначала смотрите граф (`graphify query "..."`, `graphify-out/GRAPH_REPORT.md`).
- После каждого изменения приложения обновляйте граф: `/graphify . --update` (код и документы), затем коммитьте `graphify-out/` вместе с изменением. Облачные сессии эфемерны: установите CLI через `uv tool install graphifyy`.
- Решения и пороги описаны в `docs/architecture.md` — обновляйте его при изменении решений.
- Перед коммитом: `uv run pytest` и `cd frontend && npm run build` (собранный `frontend/dist` лежит в репозитории).
