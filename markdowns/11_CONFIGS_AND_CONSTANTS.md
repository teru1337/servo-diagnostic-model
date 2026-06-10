# 11_CONFIGS_AND_CONSTANTS.md

# Конфигурации и константы модели

## 1. Назначение документа

Этот документ описывает конфигурационные файлы проекта `servo_diagnostic_model`.

Coding agent должен вынести числовые пределы, веса, пороги и настройки модели в отдельные JSON-файлы.

Нельзя жёстко зашивать все значения прямо в код.

Причина:

- модель должна легко адаптироваться под другой сервопривод;
- веса Health Score должны настраиваться без переписывания функций;
- пороги классификации должны быть прозрачными;
- паспортные ограничения могут отличаться для разных связок привода и двигателя;
- для статьи и отчёта важно показать, какие параметры использовались.

---

## 2. Основные конфигурационные файлы

В проекте должны быть файлы:

```text
config/
├── limits.json
├── weights.json
├── thresholds.json
└── feature_weights.json
```

Минимально обязательные:

```text
limits.json
weights.json
thresholds.json
```

Опциональный, но желательный:

```text
feature_weights.json
```

---

## 3. Общий принцип

Конфигурации должны загружаться в `diagnostic_service.py`.

Пример:

```python
limits = load_json("config/limits.json")
weights = load_json("config/weights.json")
thresholds = load_json("config/thresholds.json")
```

Код модели должен получать конфиги как аргументы:

```python
calculate_physical_risks(features, limits)
calculate_health_score(risks, weights)
classify_state(health_score, anomaly_score, risks, thresholds, features)
```

---

## 4. Файл `limits.json`

### 4.1. Назначение

`limits.json` содержит физические, паспортные и инженерные пределы.

Он нужен для расчёта физических рисков:

- ток;
- момент;
- скорость;
- DC-шина;
- температура;
- качество данных.

---

### 4.2. Пример полной структуры

```json
{
  "device": {
    "device_id": "servo_1",
    "drive_model": "Delta ASDA-B3-E",
    "motor_model": "unknown",
    "description": "Default limits for ServoAI diagnostic MVP"
  },

  "current": {
    "rated_current_A": 4.27,
    "max_current_A": 12.8,
    "warning_ratio": 0.75,
    "critical_ratio": 1.0
  },

  "torque": {
    "rated_torque_Nm": 2.39,
    "max_torque_Nm": 8.36,
    "warning_ratio": 0.75,
    "critical_ratio": 1.0
  },

  "velocity": {
    "max_velocity_rpm": 6000,
    "warning_ratio": 0.75,
    "critical_ratio": 1.0,
    "stop_threshold_rpm": 10,
    "motion_threshold_rpm": 10
  },

  "voltage": {
    "dc_bus_min_safe": 280,
    "dc_bus_max_safe": 340,
    "dc_bus_min_critical": 240,
    "dc_bus_max_critical": 380,
    "voltage_std_limit": 5.0,
    "voltage_range_limit": 20.0
  },

  "temperature": {
    "temp_safe": 55,
    "temp_warning": 70,
    "temp_critical": 85,
    "temp_slope_limit": 0.2
  },

  "data_quality": {
    "missing_ratio_limit": 0.3,
    "invalid_ratio_limit": 0.2,
    "time_gap_count_limit": 3,
    "min_samples_per_window": 10,
    "flatline_tolerance": 1e-9
  },

  "motion": {
    "accel_threshold_rpm_s": 50,
    "velocity_stability_threshold_rpm": 50,
    "low_speed_threshold_rpm": 10
  }
}
```

---

## 5. Упрощённая структура `limits.json`

Если coding agent хочет начать проще, можно использовать плоскую структуру.

```json
{
  "rated_current_A": 4.27,
  "max_current_A": 12.8,

  "rated_torque_Nm": 2.39,
  "max_torque_Nm": 8.36,

  "max_velocity_rpm": 6000,

  "dc_bus_min_safe": 280,
  "dc_bus_max_safe": 340,
  "dc_bus_min_critical": 240,
  "dc_bus_max_critical": 380,
  "voltage_std_limit": 5.0,

  "temp_safe": 55,
  "temp_warning": 70,
  "temp_critical": 85,
  "temp_slope_limit": 0.2,

  "missing_ratio_limit": 0.3,
  "invalid_ratio_limit": 0.2,
  "time_gap_count_limit": 3,

  "velocity_stop_threshold_rpm": 10,
  "velocity_motion_threshold_rpm": 10,
  "accel_threshold_rpm_s": 50,
  "velocity_stability_threshold_rpm": 50,
  "low_speed_threshold_rpm": 10
}
```

Рекомендация:

- для первой реализации использовать плоскую структуру;
- позже можно перейти к вложенной.

---

## 6. Важное предупреждение по числам

Числа в `limits.json` являются стартовыми значениями для MVP.

Их нужно уточнить под конкретную связку:

- модель сервопривода;
- модель двигателя;
- номинальный ток;
- номинальный момент;
- максимальный момент;
- диапазон DC-шины;
- температурные ограничения.

Если точных значений нет, coding agent должен:

1. использовать значения по умолчанию;
2. явно записывать это в `debug`;
3. не делать вид, что пределы являются окончательными.

---

## 7. Правила отсутствующих лимитов

Если лимит отсутствует, модель не должна падать.

Пример:

```python
rated_current_A = limits.get("rated_current_A")
```

Если `rated_current_A is None`, то:

- риск тока по RMS нельзя корректно рассчитать;
- нужно использовать доступные альтернативы;
- если альтернатив нет, вернуть `risk_current = 0.0`;
- повысить `data_quality` или добавить warning в debug.

---

## 8. Файл `weights.json`

### 8.1. Назначение

`weights.json` содержит веса рисков для расчёта Health Score.

Пример:

```json
{
  "error": 0.25,
  "statusword": 0.15,
  "temperature": 0.18,
  "current": 0.16,
  "torque": 0.14,
  "voltage": 0.14,
  "statistical_anomaly": 0.08,
  "velocity": 0.03,
  "data_quality": 0.02
}
```

---

## 9. Логика весов

Вес показывает важность риска в итоговом Health Score.

Например:

| Риск                  | Почему важен                                          |
| --------------------- | ----------------------------------------------------- |
| `error`               | Ненулевой код ошибки должен резко ухудшать состояние  |
| `statusword`          | Fault/Warning отражают состояние привода              |
| `temperature`         | Перегрев опасен для силовой части                     |
| `current`             | RMS-ток связан с нагрузкой и нагревом                 |
| `torque`              | Момент отражает механическую нагрузку                 |
| `voltage`             | DC-шина важна для OV/UV и питания                     |
| `statistical_anomaly` | Ранние отклонения от нормального профиля              |
| `velocity`            | Скорость важна, но сама по себе редко главная причина |
| `data_quality`        | Плохие данные снижают уверенность                     |

---

## 10. Требования к весам

1. Все веса должны быть неотрицательными.
2. Сумма весов не обязана равняться 1.
3. При расчёте Health Score веса должны нормироваться автоматически.
4. Отсутствующий вес означает, что риск не участвует в расчёте.
5. Если все веса равны 0, Health Score должен вернуть безопасную ошибку или `0`.

---

## 11. Альтернативный вариант весов для Version 0.1

Если статистическая модель ещё не реализована:

```json
{
  "error": 0.3,
  "statusword": 0.18,
  "temperature": 0.18,
  "current": 0.16,
  "torque": 0.14,
  "voltage": 0.14,
  "velocity": 0.04,
  "data_quality": 0.03
}
```

`statistical_anomaly` можно добавить позже.

---

## 12. Файл `thresholds.json`

### 12.1. Назначение

`thresholds.json` содержит пороги:

- оконной обработки;
- классификации состояния;
- Anomaly Score;
- Robust Z-score;
- рекомендаций.

---

### 12.2. Полная структура

```json
{
  "windowing": {
    "window_seconds": 5,
    "window_step_seconds": 1,
    "min_samples_per_window": 10
  },

  "health": {
    "health_normal": 85,
    "health_observation": 70,
    "health_warning": 50
  },

  "anomaly": {
    "anomaly_observation": 0.3,
    "anomaly_warning": 0.5,
    "anomaly_critical": 0.75,
    "robust_z_limit": 5.0,
    "min_windows_for_global_profile": 10,
    "min_windows_for_phase_profile": 5
  },

  "risks": {
    "risk_observation": 0.5,
    "risk_warning": 0.75,
    "risk_critical": 0.9
  },

  "recommendations": {
    "max_recommendations": 3,
    "min_risk_for_recommendation": 0.5,
    "min_risk_for_main_cause": 0.3
  },

  "debug": {
    "include_features": true,
    "include_debug": true,
    "round_digits": 3
  }
}
```

---

## 13. Упрощённая структура `thresholds.json`

Для первой реализации можно использовать плоскую структуру:

```json
{
  "window_seconds": 5,
  "window_step_seconds": 1,
  "min_samples_per_window": 10,

  "health_normal": 85,
  "health_observation": 70,
  "health_warning": 50,

  "anomaly_observation": 0.3,
  "anomaly_warning": 0.5,
  "anomaly_critical": 0.75,
  "robust_z_limit": 5.0,

  "risk_observation": 0.5,
  "risk_warning": 0.75,
  "risk_critical": 0.9,

  "max_recommendations": 3,
  "min_risk_for_recommendation": 0.5,
  "min_risk_for_main_cause": 0.3,

  "include_features": true,
  "include_debug": true,
  "round_digits": 3
}
```

---

## 14. Файл `feature_weights.json`

### 14.1. Назначение

Этот файл нужен для статистической модели аномалий.

Он задаёт веса признаков при расчёте Anomaly Score.

Пример:

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
  "temp_max": 0.6,
  "temp_slope": 1.0,

  "velocity_std": 0.8,
  "abs_velocity_max": 0.5,

  "current_to_torque_ratio": 0.8,
  "current_at_low_speed": 1.0,
  "torque_at_low_speed": 0.8,

  "motion_ratio": 0.4,
  "hold_ratio": 0.4
}
```

---

## 15. Конфигурация normal profile

Normal profile не является обычной ручной конфигурацией. Он создаётся программно.

Файл:

```text
config/normal_profile.json
```

Пример:

```json
{
  "meta": {
    "version": "0.1",
    "created_at": "2026-06-10T12:00:00",
    "source": "normal_telemetry_session",
    "reliable": true,
    "min_count": 5
  },
  "global": {
    "current_rms": {
      "median": 0.071,
      "mad": 0.005,
      "mean": 0.073,
      "std": 0.006,
      "min": 0.06,
      "max": 0.09,
      "count": 56
    }
  },
  "by_motion_phase": {
    "holding": {},
    "moving": {},
    "acceleration": {},
    "braking": {}
  }
}
```

---

## 16. Модуль загрузки конфигураций

Создать файл:

```text
config_loader.py
```

или:

```text
api/diagnostic_service.py
```

с функциями:

```python
def load_json_config(path: str) -> dict:
    ...
```

```python
def load_model_configs(
    limits_path: str,
    weights_path: str,
    thresholds_path: str,
    feature_weights_path: str | None = None
) -> dict:
    ...
```

---

## 17. Поведение при отсутствии конфига

Если отсутствует `limits.json`:

- в CLI можно выбросить ошибку;
- в тестах можно использовать default config.

Если отсутствует `weights.json`:

- использовать default weights;
- добавить warning.

Если отсутствует `thresholds.json`:

- использовать default thresholds;
- добавить warning.

Если отсутствует `normal_profile.json`:

- статистическую модель отключить;
- `anomaly_score = 0.0`;
- `available = False`.

---

## 18. Default configs в коде

Желательно создать:

```text
config/defaults.py
```

Пример:

```python
DEFAULT_LIMITS = {
    "rated_current_A": 4.27,
    "max_current_A": 12.8,
    "rated_torque_Nm": 2.39,
    "max_torque_Nm": 8.36,
    "max_velocity_rpm": 6000,
    "dc_bus_min_safe": 280,
    "dc_bus_max_safe": 340,
    "dc_bus_min_critical": 240,
    "dc_bus_max_critical": 380,
    "voltage_std_limit": 5.0,
    "temp_safe": 55,
    "temp_warning": 70,
    "temp_critical": 85,
    "temp_slope_limit": 0.2
}
```

```python
DEFAULT_WEIGHTS = {
    "error": 0.25,
    "statusword": 0.15,
    "temperature": 0.18,
    "current": 0.16,
    "torque": 0.14,
    "voltage": 0.14,
    "statistical_anomaly": 0.08,
    "velocity": 0.03,
    "data_quality": 0.02
}
```

```python
DEFAULT_THRESHOLDS = {
    "window_seconds": 5,
    "window_step_seconds": 1,
    "min_samples_per_window": 10,
    "health_normal": 85,
    "health_observation": 70,
    "health_warning": 50,
    "anomaly_observation": 0.30,
    "anomaly_warning": 0.50,
    "anomaly_critical": 0.75,
    "robust_z_limit": 5.0,
    "max_recommendations": 3,
    "min_risk_for_main_cause": 0.30
}
```

---

## 19. Валидация конфигураций

Нужно реализовать проверки.

### 19.1. `validate_limits`

```python
def validate_limits(limits: dict) -> list[str]:
    ...
```

Проверить:

- токи > 0;
- моменты > 0;
- max > rated;
- critical temperature > safe temperature;
- max velocity > 0;
- voltage critical min < voltage safe min;
- voltage critical max > voltage safe max.

---

### 19.2. `validate_weights`

```python
def validate_weights(weights: dict) -> list[str]:
    ...
```

Проверить:

- все веса числа;
- все веса >= 0;
- сумма весов > 0.

---

### 19.3. `validate_thresholds`

```python
def validate_thresholds(thresholds: dict) -> list[str]:
    ...
```

Проверить:

- `health_warning < health_observation < health_normal`;
- `anomaly_observation < anomaly_warning < anomaly_critical`;
- window_seconds > 0;
- window_step_seconds > 0;
- min_samples_per_window > 0.

---

## 20. Пример использования конфигов

```python
from servo_diagnostic_model.config_loader import load_json_config

limits = load_json_config("config/limits.json")
weights = load_json_config("config/weights.json")
thresholds = load_json_config("config/thresholds.json")

results = diagnose_csv(
    csv_path="data/telemetry.csv",
    limits=limits,
    weights=weights,
    thresholds=thresholds
)
```

---

## 21. Где использовать значения

| Конфиг                 | Где используется                                      |
| ---------------------- | ----------------------------------------------------- |
| `limits.json`          | physical risks, motion phase, data quality            |
| `weights.json`         | health_score                                          |
| `thresholds.json`      | windowing, classifier, anomaly score, recommendations |
| `feature_weights.json` | statistical anomaly model                             |
| `normal_profile.json`  | anomaly score                                         |

---

## 22. Требования к округлению

Внутри расчётов не округлять слишком рано.

Округлять только в финальном результате.

Пример:

```python
round_digits = thresholds.get("round_digits", 3)
```

Применять к:

- `health_score`;
- `anomaly_score`;
- risks;
- selected features.

---

## 23. Unit-тесты конфигов

### 23.1. Load valid JSON

Проверить, что корректный JSON загружается.

---

### 23.2. Missing file

Проверить поведение при отсутствующем файле.

---

### 23.3. Invalid JSON

Проверить, что некорректный JSON обрабатывается.

---

### 23.4. Validate limits

Проверить, что неправильные пределы дают warnings/errors.

---

### 23.5. Validate weights

Проверить, что отрицательные веса недопустимы.

---

### 23.6. Validate thresholds

Проверить порядок порогов.

---

## 24. Acceptance criteria

Конфигурации считаются готовыми, если:

1. Есть `limits.json`.
2. Есть `weights.json`.
3. Есть `thresholds.json`.
4. Конфиги загружаются через функцию.
5. Есть default configs.
6. Отсутствие optional normal profile не ломает модель.
7. Веса не зашиты жёстко в Health Score.
8. Пределы не зашиты жёстко в physical risks.
9. Пороги классификации не зашиты жёстко в classifier.
10. Есть валидация limits.
11. Есть валидация weights.
12. Есть валидация thresholds.
13. Есть unit-тесты на загрузку и валидацию.
