# Диагностическая модель сервопривода

Python-пакет `servo_diagnostic_model` обрабатывает записанную телеметрию сервопривода. Он разбивает запись на окна, извлекает признаки и оценивает физические риски, признаки статистического отклонения и качество данных. Для каждого окна модель возвращает Health Score (0–100), Anomaly Score (0–1), диагностическое состояние, объяснение и рекомендации.

Модель работает с файлами и объектами Python. Для первого запуска стенд не нужен.

## Установка

Нужны Git и Python 3.12. Команды ниже рассчитаны на Bash, включая Git Bash на Windows.

```bash
git clone https://github.com/teru1337/servo-diagnostic-model.git
cd servo-diagnostic-model

# Git Bash на Windows
py -3.12 -m venv .venv
source .venv/Scripts/activate
```

На Linux или macOS вместо двух последних команд используй:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Из корня репозитория установи зависимости. NumPy и pandas используются в расчётах и обработке данных, matplotlib — в инструментах визуализации, pytest — в тестах.

```bash
python -m pip install numpy pandas matplotlib pytest
python -m pytest -q
```

## Первый запуск без стенда

Вставь блок целиком. Он создаёт временный CSV с синтетической телеметрией и печатает результат для первого окна.

```bash
python - <<'PY'
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from servo_diagnostic_model.api.diagnostic_service import diagnose_csv

config = Path("servo_diagnostic_model/config")
config_paths = [str(config / f"{name}.json") for name in ("limits", "weights", "thresholds")]

with TemporaryDirectory() as directory:
    path = Path(directory) / "demo.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("t", "device_id", "statusword", "velocity", "current_A",
                         "torque_Nm", "dc_bus_voltage", "drive_temp", "error_code"))
        writer.writerows((i / 10, "demo", 4, 100, 1.0, 0.5, 310, 35, 0)
                         for i in range(61))
    results = diagnose_csv(str(path), *config_paths)
    print(f"Диагностических окон: {len(results)}")
    print(json.dumps(results[0], ensure_ascii=False, indent=2, allow_nan=False))
PY
```

## Работа со своей телеметрией

1. Подготовь CSV с отметками времени `t` или `ts` и как минимум тремя распознаваемыми диагностическими каналами. Проверь имена, единицы измерения и параметры оборудования по [схеме телеметрии](markdowns/02_TELEMETRY_SCHEMA.md) и [описанию конфигурации](markdowns/11_CONFIGS_AND_CONSTANTS.md). Для непрерывной диагностики используй запись одного привода на файл.
2. Вызови `diagnose_csv(csv_path, limits_path, weights_path, thresholds_path)` с путём к записи и конфигурации. Для статистической оценки передай пятым аргументом `normal_profile_path`. Без профиля модель выполняет физическую диагностику и отмечает статистический компонент как недоступный.
3. Проверь список результатов. Пустой список может означать ошибки валидации или отсутствие окон нужной длины. Диагностические состояния: `normal`, `observation`, `warning`, `critical`, `unknown`. Ненулевой код ошибки или активный флаг ошибки либо отказа переводит окно в `critical`.

Модель возвращает JSON-совместимый словарь для каждого окна. В нём есть границы окна и идентификатор устройства, оценки и состояния, рассчитанные признаки, отдельные риски, основные причины, рекомендации и сведения о качестве данных.

### Обучение профиля нормы

Используй отдельные записи исправного привода. Для обучения и оценки отбирай целые сеансы, чтобы окна одной записи не попали в обе выборки.

```bash
python -m servo_diagnostic_model.api.profile_service \
  data/normal_01.csv data/normal_02.csv data/normal_profile.json
```

Последний позиционный аргумент — путь выходного JSON. При большом числе файлов используй `--manifest data/normal_manifest.csv` перед выходным путём. В манифесте требуется колонка `path`. Относительные пути к CSV указывай от текущего рабочего каталога. Полный список параметров покажет команда `python -m servo_diagnostic_model.api.profile_service --help`.

## Структура проекта

| Каталог | Назначение |
| --- | --- |
| [api](servo_diagnostic_model/api/) | Диагностика окон, обработка CSV и обучение профиля нормы |
| [data](servo_diagnostic_model/data/) и [features](servo_diagnostic_model/features/) | Подготовка телеметрии, валидация, нарезка окон и извлечение признаков |
| [model](servo_diagnostic_model/model/) и [recommendations](servo_diagnostic_model/recommendations/) | Физические риски, статистический профиль, оценка состояния и рекомендации |
| [config](servo_diagnostic_model/config/) | Пределы оборудования, веса и пороги. Перед применением к своему приводу проверь их значения |
| [evaluation](servo_diagnostic_model/evaluation/) и [artifacts](artifacts/) | Сценарии оценки и сохранённые результаты предыдущих запусков |
| [tests](tests/) | Проверки модели, обработки данных и API |

Для разработки начни с [архитектуры](markdowns/04_CODE_ARCHITECTURE.md), [правил проекта](AGENTS.md) и [методики оценки](markdowns/12_TESTING_AND_EVALUATION.md). Для параметров лабораторной оценки выполни `python -m servo_diagnostic_model.evaluation.lab_validation --help`.

## Границы применения

Модель анализирует телеметрию и помогает интерпретировать отклонения. Для защитного отключения используй штатные системы безопасности оборудования. Статистическое отклонение отражает расхождение с профилем нормы. Для подтверждения обнаружения конкретного дефекта нужны записи с независимо подтверждённой неисправностью. Пороговые значения и профиль нормы необходимо проверять на целевом приводе и в его рабочих режимах.

Каталог с локальными измерениями в корне репозитория исключён из Git. Сохраняй новые CSV и рабочие профили отдельно от версионируемых примеров.
