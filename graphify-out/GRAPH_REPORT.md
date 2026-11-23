# Graph Report - zlatoust  (2026-11-23)

## Corpus Check
- 43 files · ~16,274 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .ico 1, .css 1)

## Summary
- 396 nodes · 793 edges · 20 communities (11 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84dbde73`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Клиент API интерфейса
- Анализ голоса (Praat)
- Зависимости фронтенда
- Распознавание речи Whisper
- Запуск окна и сервера
- HTTP API сессий
- Архитектура и решения
- Упражнения и LLM-разбор
- Конфиг TS приложения
- Конфиг TS сборки
- Оценки и пороги
- Корневой tsconfig
- Планы развития
- Пакет zlatoust
- scoring.py

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 27 edges
2. `analyze()` - 20 edges
3. `compilerOptions` - 19 edges
4. `compilerOptions` - 17 edges
5. `data_dir()` - 14 edges
6. `ReportView()` - 12 edges
7. `_connect()` - 11 edges
8. `react` - 11 edges
9. `Transcriber` - 10 edges
10. `Settings` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_settings_key_masked()` --calls--> `create_app()`  [INFERRED]
  tests/test_pipeline.py → backend/zlatoust/app.py
- `test_full_flow()` --calls--> `create_app()`  [INFERRED]
  tests/test_pipeline.py → backend/zlatoust/app.py
- `test_diction()` --calls--> `diction_compare()`  [INFERRED]
  tests/test_pipeline.py → backend/zlatoust/analysis/text.py
- `index.html #root (точка входа /src/main.tsx)` --implements--> `React + TypeScript интерфейс (MediaRecorder webm)`  [INFERRED]
  frontend/index.html → docs/architecture.md
- `frontend/dist` --conceptually_related_to--> `React + TypeScript интерфейс (MediaRecorder webm)`  [INFERRED]
  README.md → docs/architecture.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Варианты толкования** — readme_разбор_по_правилам, readme_ollama, readme_claude_api [EXTRACTED 1.00]
- **Конвейер анализа записи** — docs_architecture_pyav, docs_architecture_faster_whisper, docs_architecture_метрики_речи, docs_architecture_parselmouth, docs_architecture_mediapipe, docs_architecture_оценки [EXTRACTED 1.00]

## Communities (20 total, 9 thin omitted)

### Community 0 - "Клиент API интерфейса"
Cohesion: 0.09
Nodes (50): api, DictionOp, Exercise, fmtDate(), fmtTime(), Health, Improvement, Metrics (+42 more)

### Community 1 - "Анализ голоса (Praat)"
Cohesion: 0.06
Nodes (23): _db(), phrases_from_words(), prosody_metrics(), speech_metrics(), diction_compare(), edit_distance(), find_fillers(), levenshtein_ops() (+15 more)

### Community 2 - "Зависимости фронтенда"
Cohesion: 0.07
Nodes (36): dependencies, react@^19.1.0, react-dom@^19.1.0, devDependencies, eslint@^9.25.0, @eslint/js@^9.25.0, eslint-plugin-react-hooks@^5.2.0, eslint-plugin-react-refresh@^0.4.19 (+28 more)

### Community 3 - "Распознавание речи Whisper"
Cohesion: 0.12
Nodes (14): _add_cuda_dll_dirs(), cuda_available(), get_transcriber(), Transcriber, Transcript, Word, ensure_models(), models_ready() (+6 more)

### Community 4 - "Запуск окна и сервера"
Cohesion: 0.08
Nodes (19): _drain(), main(), _main(), start(), _server_running(), SettingsIn, _setup_logging(), _show_startup_error() (+11 more)

### Community 5 - "HTTP API сессий"
Cohesion: 0.11
Nodes (19): create_app(), create_session(), delete(), get_session(), list_sessions(), retry(), video(), _connect() (+11 more)

### Community 6 - "Архитектура и решения"
Cohesion: 0.07
Nodes (24): faster-whisper распознавание, MediaPipe Pose + Face, Praat/parselmouth (тон, громкость), PyAV (звук, кадры, ffmpeg внутри), React + TypeScript интерфейс (MediaRecorder webm), analysis/scoring.py пороги, SQLite + папка записей, Конвейер анализа (+16 more)

### Community 7 - "Упражнения и LLM-разбор"
Cohesion: 0.14
Nodes (16): get_settings(), put_settings(), test_llm(), pick_for_skill(), _call_anthropic(), _call_ollama(), Feedback, Improvement (+8 more)

### Community 8 - "Конфиг TS приложения"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+12 more)

### Community 9 - "Конфиг TS сборки"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+10 more)

### Community 18 - "scoring.py"
Cohesion: 0.33
Nodes (5): band(), fmt_t(), n(), _obs(), score()

## Knowledge Gaps
- **15 isolated node(s):** `zlatoust`, `Планы: установщик, диагностика, графики, Android`, `analysis/scoring.py пороги`, `index.html #root (точка входа /src/main.tsx)`, `scripts/start.bat` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 151 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `HTTP API сессий` to `Анализ голоса (Praat)`, `Распознавание речи Whisper`, `Запуск окна и сервера`, `Упражнения и LLM-разбор`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `.start()` and `test_full_flow()`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zlatoust`, `Планы: установщик, диагностика, графики, Android`, `analysis/scoring.py пороги` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Клиент API интерфейса` be split into smaller, more focused modules?**
  _Cohesion score 0.08755760368663594 - nodes in this community are weakly interconnected._
- **Why does `react` connect `Клиент API интерфейса` to `Зависимости фронтенда`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `analyze()` (e.g. with `Transcriber` and `.transcribe()`) actually correct?**
  _`analyze()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Анализ голоса (Praat)` be split into smaller, more focused modules?**
  _Cohesion score 0.061581920903954805 - nodes in this community are weakly interconnected._