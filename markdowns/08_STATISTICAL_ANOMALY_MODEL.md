# 08_STATISTICAL_ANOMALY_MODEL.md

# Статистическая модель аномалий

## 1. Назначение документа

Этот документ описывает статистическую часть диагностической модели.

Coding agent должен реализовать модуль, который сравнивает текущее окно телеметрии с профилем нормальной работы и выдаёт `Anomaly Score`.

Статистическая модель не должна использовать готовые ML-модели из:

```text
sklearn
tensorflow
pytorch
keras
xgboost
lightgbm
catboost
```

Разрешается использовать:

```text
Python standard library
numpy
pandas
json
statistics
```

---

## 2. Зачем нужна статистическая модель

Физическая модель ищет близость к паспортным пределам.

Но не все проблемы сразу выглядят как превышение предела.

Пример:

```text
Ток не превышает номинальный предел, но для режима удержания он стал в 3 раза выше обычного.
```

Физическая модель может сказать:

```text
risk_current низкий
```

Статистическая модель должна сказать:

```text
поведение нетипично для нормального режима
```

---

## 3. Место в pipeline

```text
TelemetryWindow
    ↓
extract_features()
    ↓
features
    ↓
calculate_physical_risks()
    ↓
fit/load normal profile
    ↓
calculate_anomaly_score(features, profile)
    ↓
anomaly_score
    ↓
Health Score + classifier
```

---

## 4. Основная идея

Статистическая модель строит профиль нормальной работы.

Профиль содержит типичные значения признаков:

- медиана;
- MAD;
- среднее;
- стандартное отклонение;
- min;
- max;
- количество наблюдений.

Для нового окна модель сравнивает текущие признаки с профилем и считает, насколько они отклонились.

---

## 5. Почему median и MAD

Обычное среднее и стандартное отклонение чувствительны к выбросам.

Для телеметрии это проблема, потому что даже нормальная запись может содержать:

- случайные скачки;
- шум;
- короткие переходные процессы;
- пропуски;
- единичные выбросы.

Поэтому базовый метод должен использовать:

```text
median
MAD
```

MAD:

```text
MAD = median(|x_i - median(x)|)
```

---

## 6. Что такое normal profile

Normal profile — это JSON-совместимая структура, описывающая нормальное поведение.

Пример:

```json
{
  "global": {
    "current_rms": {
      "median": 0.071,
      "mad": 0.005,
      "mean": 0.073,
      "std": 0.006,
      "min": 0.06,
      "max": 0.09,
      "count": 56
    },
    "voltage_std": {
      "median": 0.26,
      "mad": 0.03,
      "mean": 0.27,
      "std": 0.04,
      "min": 0.18,
      "max": 0.34,
      "count": 56
    }
  },
  "by_motion_phase": {
    "holding": {
      "current_rms": {
        "median": 0.055,
        "mad": 0.004,
        "count": 45
      }
    },
    "moving": {
      "current_rms": {
        "median": 0.11,
        "mad": 0.015,
        "count": 8
      }
    }
  }
}
```

---

## 7. Какие признаки включать в статистический профиль

Не все признаки нужно включать.

### 7.1. Включить

Рекомендуемые признаки:

```text
velocity_mean
velocity_std
abs_velocity_max

current_rms
current_abs_max
current_std

torque_rms
torque_abs_max
torque_std

voltage_mean
voltage_std
voltage_range

temp_mean
temp_slope

current_to_torque_ratio
current_at_low_speed
torque_at_low_speed

motion_ratio
hold_ratio
```

---

### 7.2. Не включать

Не включать в статистический профиль:

```text
window_start
window_end
sample_count
device_id
statusword raw
error_code raw
error_flag
fault_flag
warning_flag
unique_error_codes
data_quality_notes
```

Причина:

- служебные поля не являются нормальными числовыми признаками;
- error/fault лучше обрабатывать физическими правилами;
- строки и списки не подходят для robust z-score.

---

### 7.3. Осторожно включать

Признаки температуры:

```text
temp_mean
temp_max
temp_slope
```

Температура может быть почти постоянной в коротких сессиях. Тогда MAD будет 0.

Нужно корректно обрабатывать `MAD=0`.

---

## 8. Разделение по режимам

Статистический профиль должен поддерживать два уровня:

1. Глобальный профиль.
2. Профиль по фазам движения.

Фазы:

```text
holding
moving
acceleration
braking
stopped
mixed
unknown
```

---

### 8.1. Почему нужно разделение по фазам

Один и тот же ток может быть нормальным в движении и подозрительным при удержании.

Пример:

```text
current_rms = 0.2 A
```

В разгоне:

```text
может быть нормально
```

В удержании:

```text
может быть признаком механической нагрузки
```

Поэтому если есть профиль для конкретной фазы, нужно использовать его.

---

### 8.2. Приоритет выбора профиля

При расчёте anomaly score:

```text
1. Если есть profile["by_motion_phase"][motion_phase] и там достаточно данных:
    использовать фазовый профиль.
2. Иначе:
    использовать global profile.
3. Если нет никакого профиля:
    anomaly_score = 0.0, available=False.
```

---

## 9. Минимальное количество окон для профиля

Нельзя строить профиль по одному окну.

Рекомендуемые пороги:

```json
{
  "min_windows_for_global_profile": 10,
  "min_windows_for_phase_profile": 5
}
```

Если данных меньше:

- профиль можно создать;
- но пометить его как ненадёжный;
- при расчёте anomaly score использовать осторожность.

---

## 10. Модуль `statistical_profile.py`

### 10.1. Функция `fit_normal_profile`

```python
def fit_normal_profile(
    feature_rows: list[dict],
    feature_names: list[str] | None = None,
    min_count: int = 5
) -> dict:
    ...
```

Вход:

```python
feature_rows
```

Список словарей признаков, полученных из нормальной телеметрии.

---

### 10.2. Алгоритм

```text
1. Если feature_names не передан:
    выбрать числовые признаки автоматически.
2. Для каждого признака:
    собрать все валидные значения.
3. Если значений достаточно:
    посчитать median, mad, mean, std, min, max, count.
4. Сформировать global profile.
5. Разделить feature_rows по motion_phase.
6. Для каждой фазы повторить расчёт.
7. Вернуть profile.
```

---

### 10.3. Псевдокод

```python
def fit_normal_profile(feature_rows, feature_names=None, min_count=5):
    if feature_names is None:
        feature_names = infer_numeric_feature_names(feature_rows)

    profile = {
        "meta": {
            "version": "0.1",
            "min_count": min_count,
            "feature_names": feature_names
        },
        "global": {},
        "by_motion_phase": {}
    }

    profile["global"] = calculate_feature_stats(
        feature_rows=feature_rows,
        feature_names=feature_names,
        min_count=min_count
    )

    rows_by_phase = group_by_motion_phase(feature_rows)

    for phase, rows in rows_by_phase.items():
        profile["by_motion_phase"][phase] = calculate_feature_stats(
            feature_rows=rows,
            feature_names=feature_names,
            min_count=min_count
        )

    return profile
```

---

## 11. Расчёт статистик признака

Функция:

```python
def calculate_feature_stats(values: list[float]) -> dict:
    ...
```

Выход:

```python
{
    "median": 0.071,
    "mad": 0.005,
    "mean": 0.073,
    "std": 0.006,
    "min": 0.060,
    "max": 0.090,
    "count": 56
}
```

---

### 11.1. MAD

```python
def calculate_mad(values: list[float]) -> float:
    median_value = median(values)
    deviations = [abs(x - median_value) for x in values]
    return median(deviations)
```

---

### 11.2. Обработка MAD = 0

Если `MAD = 0`, robust z-score нельзя считать обычным способом.

Варианты:

1. Использовать `eps`.
2. Использовать `std`.
3. Если и `std=0`, считать любое отличие от медианы подозрительным.

Рекомендуемая логика:

```text
scale = mad

если scale == 0 или None:
    scale = std

если scale == 0 или None:
    scale = eps
```

Где:

```text
eps = 1e-9
```

---

## 12. Сохранение и загрузка профиля

### 12.1. `save_profile`

```python
def save_profile(profile: dict, path: str) -> None:
    ...
```

Сохраняет JSON.

---

### 12.2. `load_profile`

```python
def load_profile(path: str) -> dict:
    ...
```

Загружает JSON.

Если файла нет:

```python
return None
```

или выбросить `FileNotFoundError`.

Рекомендация:

- для низкоуровневой функции выбрасывать ошибку;
- в `diagnostic_service` обрабатывать отсутствие профиля мягко.

---

## 13. Модуль `anomaly_score.py`

### 13.1. Назначение

Считает Anomaly Score для одного окна.

Функция:

```python
def calculate_anomaly_score(
    features: dict,
    profile: dict | None = None,
    thresholds: dict | None = None
) -> dict:
    ...
```

Выход:

```python
{
    "anomaly_score": 0.14,
    "feature_scores": {
        "current_rms": 0.10,
        "voltage_std": 0.04
    },
    "profile_used": "by_motion_phase.holding",
    "available": True
}
```

Если профиля нет:

```python
{
    "anomaly_score": 0.0,
    "feature_scores": {},
    "profile_used": None,
    "available": False
}
```

---

## 14. Robust Z-score

### 14.1. Формула

```text
z = abs(value - median) / scale
```

где:

```text
scale = max(MAD, eps)
```

или fallback на std.

---

### 14.2. Перевод z-score в риск

```text
feature_anomaly = clamp(z / robust_z_limit)
```

Рекомендуемый порог:

```text
robust_z_limit = 5.0
```

Если `z=0`:

```text
feature_anomaly = 0
```

Если `z>=5`:

```text
feature_anomaly = 1
```

---

### 14.3. Функция

```python
def robust_feature_score(value: float, stats: dict, z_limit: float = 5.0) -> float:
    ...
```

---

## 15. Веса статистических признаков

Не все статистические признаки одинаково важны.

Рекомендуемые веса:

```json
{
  "current_rms": 1.0,
  "current_abs_max": 0.8,
  "current_std": 0.6,

  "torque_rms": 1.0,
  "torque_abs_max": 0.8,
  "torque_std": 0.6,

  "voltage_mean": 0.6,
  "voltage_std": 1.0,
  "voltage_range": 0.8,

  "temp_mean": 0.5,
  "temp_slope": 1.0,

  "velocity_std": 0.8,
  "abs_velocity_max": 0.5,

  "current_to_torque_ratio": 0.8,
  "current_at_low_speed": 1.0,
  "torque_at_low_speed": 0.8,

  "motion_ratio": 0.4
}
```

В первой версии можно использовать одинаковые веса.

---

## 16. Итоговый Anomaly Score

Формула:

```text
anomaly_score = weighted_mean(feature_scores)
```

где:

```text
weighted_mean = sum(score_i * weight_i) / sum(weight_i)
```

Также можно ограничить сверху:

```text
anomaly_score = clamp(anomaly_score)
```

---

## 17. Альтернативная агрегация

Иногда одна очень сильная аномалия важнее среднего.

Можно использовать гибрид:

```text
mean_score = weighted_mean(feature_scores)
max_score = max(feature_scores)

anomaly_score = 0.7 * mean_score + 0.3 * max_score
```

Для первой версии статистической модели рекомендуется именно этот вариант.

---

## 18. Псевдокод `calculate_anomaly_score`

```python
def calculate_anomaly_score(features, profile=None, thresholds=None):
    if profile is None:
        return {
            "anomaly_score": 0.0,
            "feature_scores": {},
            "profile_used": None,
            "available": False
        }

    z_limit = thresholds.get("robust_z_limit", 5.0) if thresholds else 5.0
    motion_phase = features.get("motion_phase", "unknown")

    selected_profile, profile_name = select_profile_for_phase(profile, motion_phase)

    if not selected_profile:
        return {
            "anomaly_score": 0.0,
            "feature_scores": {},
            "profile_used": None,
            "available": False
        }

    feature_scores = {}

    for feature_name, stats in selected_profile.items():
        value = features.get(feature_name)

        if value is None:
            continue

        if not is_valid_number(value):
            continue

        score = robust_feature_score(value, stats, z_limit)
        feature_scores[feature_name] = score

    if not feature_scores:
        return {
            "anomaly_score": 0.0,
            "feature_scores": {},
            "profile_used": profile_name,
            "available": False
        }

    mean_score = weighted_mean(feature_scores)
    max_score = max(feature_scores.values())

    anomaly_score = clamp(0.7 * mean_score + 0.3 * max_score)

    return {
        "anomaly_score": anomaly_score,
        "feature_scores": feature_scores,
        "profile_used": profile_name,
        "available": True
    }
```

---

## 19. Как обучать normal profile

В этом проекте слово "обучать" не означает ML-обучение нейросети.

Это означает:

```text
посчитать статистику нормальной работы
```

Порядок:

```text
1. Взять нормальную сессию телеметрии.
2. Разбить на окна.
3. Посчитать признаки для каждого окна.
4. Передать feature_rows в fit_normal_profile().
5. Сохранить normal_profile.json.
```

---

## 20. Нормальные данные

Normal profile должен строиться только по нормальным данным.

Если в данных есть:

- error_code != 0;
- fault_flag=True;
- явные синтетические аномалии;
- плохое качество данных;

такие окна нужно исключать из профиля.

Функция:

```python
def filter_normal_feature_rows(feature_rows: list[dict]) -> list[dict]:
    ...
```

Пример условий:

```text
error_flag == False
fault_flag == False
missing_ratio < 0.1
invalid_ratio < 0.1
```

---

## 21. Что делать при малом количестве данных

Если данных мало:

- профиль всё равно можно создать;
- но добавить `profile["meta"]["reliable"] = False`;
- при расчёте anomaly score можно уменьшить влияние статистики.

Пример:

```text
если profile_reliable == False:
    anomaly_score = anomaly_score * 0.5
```

Но для первой версии можно просто добавить meta-поле.

---

## 22. Drift и переобучение профиля

В первой версии не нужно реализовывать автоматическое обновление профиля.

Но код должен позволять позже:

- пересчитать профиль;
- сохранить новую версию;
- сравнить старый и новый профиль.

Добавить в meta:

```json
{
  "created_at": "2026-06-10T12:00:00",
  "source": "normal_session",
  "version": "0.1"
}
```

---

## 23. Unit-тесты

### 23.1. MAD

Проверить:

```text
values = [1, 1, 1]
mad = 0
```

---

### 23.2. Robust score normal

Если value == median:

```text
score = 0
```

---

### 23.3. Robust score high

Если value сильно отличается:

```text
score > 0
```

---

### 23.4. Clamp

Если z очень большой:

```text
score = 1
```

---

### 23.5. No profile

Если profile=None:

```text
anomaly_score=0
available=False
```

---

### 23.6. Phase profile

Если есть профиль для `holding`, должен использоваться он.

---

### 23.7. Global fallback

Если фазового профиля нет, используется `global`.

---

### 23.8. Save/load profile

Сохранённый профиль должен загружаться без потери данных.

---

## 24. Acceptance criteria

Статистическая модель считается готовой, если:

1. Есть `fit_normal_profile(feature_rows)`.
2. Профиль содержит `global`.
3. Профиль содержит `by_motion_phase`.
4. Для числовых признаков считаются median, MAD, mean, std, min, max, count.
5. Профиль можно сохранить в JSON.
6. Профиль можно загрузить из JSON.
7. Есть `calculate_anomaly_score(features, profile)`.
8. Если профиля нет, модель не падает.
9. Anomaly Score находится в диапазоне 0..1.
10. Feature scores находятся в диапазоне 0..1.
11. Используется robust z-score.
12. MAD=0 обрабатывается корректно.
13. Есть fallback с фазового профиля на global.
14. Есть unit-тесты.
