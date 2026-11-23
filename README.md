# Златоуст

Личный тренажёр публичных выступлений. Записываете минуту речи на камеру и получаете разбор: темп, паузы, слова-паразиты, интонация, громкость, дикция по тексту, взгляд в камеру, мимика, осанка и жесты. Всё работает у вас на компьютере, записи никуда не уходят.

## Установка (Windows 11)

Нужны Git и интернет на время установки. Видеокарта NVIDIA необязательна, но с ней разбор в несколько раз быстрее.

```powershell
git clone https://github.com/AntonTikhomirov/zlatoust.git
cd zlatoust
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Скрипт сам поставит `uv`, Python 3.12, все библиотеки строго по `uv.lock`, скачает модели (около 3,5 ГБ) и создаст ярлык «Златоуст» на рабочем столе. Повторный запуск ничего не сломает.

Запуск: ярлык на рабочем столе. Откроется отдельное окно. Закрыли окно — приложение завершилось. Если что-то не так, запустите `scripts\start.bat`: там видны сообщения. Журнал лежит в `%LOCALAPPDATA%\Zlatoust\zlatoust.log`.

Обновление: `powershell -ExecutionPolicy Bypass -File scripts\update.ps1`.

## Разбор с ИИ (необязательно)

Метрики и оценки всегда считает программа. Советы пишет один из трёх вариантов, выбор в «Настройках»:

- **По правилам** — по умолчанию, бесплатно, офлайн.
- **Ollama** — локальная модель на видеокарте. Установите [Ollama](https://ollama.com) и выполните `ollama pull qwen2.5:7b`.
- **Claude API** — ключ с console.anthropic.com. Подписка Claude Pro ключа не даёт, API оплачивается отдельно: около $0,05 за разбор на Opus 5.5, около $0,002 на Haiku 5.5.

Если ИИ недоступен, отчёт всё равно будет — по правилам.

## Где данные

`%LOCALAPPDATA%\Zlatoust`: `recordings\` (видео), `zlatoust.sqlite3` (история и отчёты), `models\`, `settings.json` (там же ключ API, в репозиторий он не попадает).

## Разработка

```bash
uv sync                      # окружение
uv run pytest                # тесты
uv run python -m zlatoust --server   # только ядро на 127.0.0.1:8765
cd frontend && npm install && npm run dev   # интерфейс с горячей перезагрузкой
cd frontend && npm run build # собрать frontend/dist (он лежит в репозитории, чтобы установка не требовала Node)
```

Устройство и решения — в [docs/architecture.md](docs/architecture.md). Граф знаний проекта (graphify) — в [graphify-out/](graphify-out/GRAPH_REPORT.md).
