# 12_TESTING_AND_EVALUATION.md

# Тестирование и оценка качества модели

## 1. Назначение документа

Этот документ описывает, как тестировать и оценивать проект `servo_diagnostic_model`.

Coding agent должен реализовать unit-тесты, интеграционные тесты и базовые инструменты оценки качества диагностической модели.

Тестирование нужно не только для проверки кода, но и для подтверждения, что модель ведёт себя инженерно корректно.

---

## 2. Виды тестирования

В проекте нужно предусмотреть:

1. Unit-тесты.
2. Интеграционные тесты.
3. Тесты на нормальной телеметрии.
4. Тесты на синтетических аномалиях.
5. Проверку метрик качества.
6. Проверку стабильности JSON-выхода.
7. Проверку устойчивости к плохим данным.

---

## 3. Папка тестов

Структура:

```text
tests/
├── test_loader.py
├── test_validator.py
├── test_windowing.py
├── test_features.py
├── test_physical_risks.py
├── test_statistical_profile.py
├── test_anomaly_score.py
├── test_health_score.py
├── test_classifier.py
├── test_recommendations.py
├── test_diagnostic_service.py
└── test_bad_data.py
```

---

## 4. Инструмент тестирования

Использовать:

```text
pytest
```

Запуск:

```bash
pytest
```

Запуск с подробным выводом:

```bash
pytest -v
```

---

## 5. Unit-тесты data pipeline

### 5.1. `test_load_csv_success`

Проверить, что CSV загружается.

Минимальный тестовый CSV:

```csv
t,velocity,current_A,torque_Nm,dc_bus_voltage,drive_temp,statusword,error_code
0.0,0,0.05,0.01,305,37,7,0
0.1,10,0.06,0.02,305,37,7,0
```

Ожидание:

```text
DataFrame не пустой.
Колонки прочитаны.
```

---

### 5.2. `test_load_csv_file_not_found`

Вызвать loader на несуществующем файле.

Ожидание:

```text
FileNotFoundError
```

---

### 5.3. `test_normalize_column_names`

Вход:

```text
Timestamp, Speed, Current_A, Temp
```

Ожидание:

```text
ts, velocity, current_A, drive_temp
```

---

### 5.4. `test_parse_time_from_t`

Вход содержит `t`.

Ожидание:

```text
t приведён к float.
```

---

### 5.5. `test_parse_time_from_ts`

Вход содержит `ts`, но не содержит `t`.

Ожидание:

```text
создана колонка t;
первое значение t = 0.
```

---

### 5.6. `test_validate_missing_time`

Если нет ни `t`, ни `ts`, validator должен вернуть critical error.

---

### 5.7. `test_estimate_sampling_rate`

Вход:

```text
t = [0.0, 0.1, 0.2, 0.3]
```

Ожидание:

```text
sampling_rate ≈ 10 Hz
```

---

### 5.8. `test_make_windows`

Вход:

```text
duration = 10 s
window = 5 s
step = 1 s
```

Ожидание:

```text
будет несколько перекрывающихся окон.
```

---

## 6. Unit-тесты feature engineering

### 6.1. `test_rms_positive_values`

Вход:

```python
values = [1, 1, 1]
```

Ожидание:

```python
rms = 1
```

---

### 6.2. `test_rms_negative_values`

Вход:

```python
values = [-1, 1]
```

Ожидание:

```python
rms = 1
```

---

### 6.3. `test_rms_empty`

Вход:

```python
values = []
```

Ожидание:

```python
rms is None
```

---

### 6.4. `test_slope_linear_growth`

Вход:

```python
times = [0, 1, 2]
values = [10, 20, 30]
```

Ожидание:

```python
slope = 10
```

---

### 6.5. `test_velocity_features`

Проверить:

```text
velocity_mean
velocity_max
velocity_min
abs_velocity_max
velocity_rms
```

---

### 6.6. `test_temperature_slope`

Если температура растёт линейно, `temp_slope > 0`.

---

### 6.7. `test_error_flag`

Если в окне есть `error_code != 0`, признак `error_flag=True`.

---

### 6.8. `test_motion_phase_stopped`

Если скорость во всех точках около нуля, фаза:

```text
stopped или holding
```

---

### 6.9. `test_motion_phase_moving`

Если скорость стабильная и выше порога, фаза:

```text
moving
```

---

## 7. Unit-тесты physical risks

### 7.1. `test_current_risk_normal`

```python
features = {
    "current_rms": 1.0,
    "current_abs_max": 2.0,
    "current_unit": "A"
}

limits = {
    "rated_current_A": 4.0,
    "max_current_A": 8.0
}
```

Ожидание:

```text
risk_current = 0.25
```

или близко к этому, если используется max из RMS и peak.

---

### 7.2. `test_current_risk_clamped`

Если ток сильно выше предела, риск не должен быть больше 1.

---

### 7.3. `test_voltage_low_risk`

Если `voltage_min < dc_bus_min_safe`, риск напряжения > 0.

---

### 7.4. `test_voltage_critical_low`

Если `voltage_min <= dc_bus_min_critical`, риск напряжения = 1.

---

### 7.5. `test_temperature_safe`

Если `temp_max <= temp_safe`, риск температуры = 0.

---

### 7.6. `test_temperature_critical`

Если `temp_max >= temp_critical`, риск температуры = 1.

---

### 7.7. `test_error_risk`

Если `error_flag=True`, риск ошибки = 1.

---

### 7.8. `test_statusword_fault_risk`

Если `fault_flag=True`, риск statusword = 1.

---

## 8. Unit-тесты statistical anomaly model

### 8.1. `test_calculate_mad`

Вход:

```python
values = [1, 1, 2, 2, 100]
```

Ожидание:

```text
MAD считается без падения.
```

---

### 8.2. `test_robust_score_zero`

Если value равен median, score = 0.

---

### 8.3. `test_robust_score_clamped`

Если value очень далеко от median, score = 1.

---

### 8.4. `test_no_profile`

Если profile отсутствует:

```python
anomaly_score = 0.0
available = False
```

---

### 8.5. `test_fit_normal_profile`

Передать список feature rows.

Ожидание:

```text
profile содержит global.
profile содержит статистики признаков.
```

---

### 8.6. `test_phase_profile`

Если feature rows имеют `motion_phase`, profile содержит `by_motion_phase`.

---

## 9. Unit-тесты Health Score

### 9.1. `test_health_score_all_zero_risks`

Если все риски 0:

```text
health_score = 100
```

---

### 9.2. `test_health_score_all_one_risks`

Если все риски 1:

```text
health_score = 0
```

---

### 9.3. `test_health_score_range`

Health Score всегда должен быть:

```text
0 <= score <= 100
```

---

### 9.4. `test_hard_limit_error`

Если `error_flag=True`, Health Score не выше 40.

---

### 9.5. `test_missing_weight`

Если у риска нет веса, расчёт не падает.

---

## 10. Unit-тесты classifier

### 10.1. `test_classifier_normal`

Условия:

```python
health_score = 95
anomaly_score = 0.1
error_flag = False
fault_flag = False
```

Ожидание:

```text
state = normal
```

---

### 10.2. `test_classifier_observation`

Условия:

```python
health_score = 80
anomaly_score = 0.1
```

Ожидание:

```text
state = observation
```

---

### 10.3. `test_classifier_warning`

Условия:

```python
health_score = 60
```

Ожидание:

```text
state = warning
```

---

### 10.4. `test_classifier_critical_by_health`

Условия:

```python
health_score = 40
```

Ожидание:

```text
state = critical
```

---

### 10.5. `test_classifier_critical_by_error`

Условия:

```python
features["error_flag"] = True
```

Ожидание:

```text
state = critical
```

---

### 10.6. `test_classifier_critical_by_fault`

Условия:

```python
features["fault_flag"] = True
```

Ожидание:

```text
state = critical
```

---

## 11. Unit-тесты recommendations

### 11.1. `test_recommendation_normal`

Если `state=normal`, вернуть рекомендацию:

```text
Продолжить мониторинг.
```

---

### 11.2. `test_recommendation_error`

Если `error_flag=True`, вернуть critical-рекомендацию.

---

### 11.3. `test_recommendation_voltage`

Если `risks["voltage"] >= 0.75`, вернуть рекомендацию по питанию/DC-шине.

---

### 11.4. `test_recommendation_temperature`

Если `risks["temperature"] >= 0.75`, вернуть рекомендацию по охлаждению.

---

### 11.5. `test_recommendation_mechanical`

Если `risks["current"] >= 0.75`, вернуть рекомендацию по механике.

---

### 11.6. `test_recommendation_limit`

Количество рекомендаций не должно превышать `max_recommendations`.

---

## 12. Интеграционные тесты

### 12.1. `test_diagnose_csv_normal`

Вход: нормальная CSV-телеметрия.

Ожидание:

```text
результат является list;
в каждом результате есть health_score;
state не critical;
recommendations есть.
```

---

### 12.2. `test_diagnose_csv_with_error`

В CSV есть участок с `error_code != 0`.

Ожидание:

```text
окна с error_code != 0 имеют state = critical.
```

---

### 12.3. `test_diagnose_csv_bad_data`

В CSV есть пропуски.

Ожидание:

```text
модель не падает;
data_quality risk повышается.
```

---

## 13. Синтетические аномалии

Создать модуль:

```text
evaluation/synthetic_anomalies.py
```

Он должен генерировать искусственные отклонения на основе нормальной телеметрии.

---

## 14. Виды синтетических аномалий

### 14.1. Перегрузка по току

Функция:

```python
def inject_current_overload(df, start_t, end_t, multiplier=3.0):
    ...
```

Логика:

```text
на участке start_t..end_t умножить current_A на multiplier
```

Ожидаемая реакция:

```text
risk_current растёт;
Health Score падает;
state становится warning или critical.
```

---

### 14.2. Рост температуры

Функция:

```python
def inject_temperature_ramp(df, start_t, end_t, final_temp):
    ...
```

Логика:

```text
добавить линейный рост drive_temp до final_temp
```

Ожидаемая реакция:

```text
risk_temperature растёт;
temp_slope > 0;
recommendation по охлаждению.
```

---

### 14.3. Просадка DC-шины

Функция:

```python
def inject_voltage_drop(df, start_t, end_t, drop_value):
    ...
```

Логика:

```text
dc_bus_voltage -= drop_value
```

Ожидаемая реакция:

```text
risk_voltage растёт;
recommendation по питанию.
```

---

### 14.4. Перенапряжение DC-шины

Функция:

```python
def inject_voltage_spike(df, start_t, end_t, spike_value):
    ...
```

Логика:

```text
dc_bus_voltage += spike_value
```

Ожидаемая реакция:

```text
risk_voltage растёт;
recommendation по тормозному резистору/DC-шине.
```

---

### 14.5. Ошибка привода

Функция:

```python
def inject_error_code(df, start_t, end_t, error_code):
    ...
```

Ожидаемая реакция:

```text
error_flag=True;
state=critical;
recommendation по error_code.
```

---

### 14.6. Потеря данных

Функция:

```python
def inject_data_gap(df, start_t, end_t):
    ...
```

Логика:

```text
удалить строки на участке
```

Ожидаемая реакция:

```text
time_gap_count растёт;
data_quality risk растёт.
```

---

### 14.7. Вибрации скорости

Функция:

```python
def inject_velocity_oscillation(df, start_t, end_t, amplitude, frequency_hz):
    ...
```

Логика:

```text
velocity += amplitude * sin(2*pi*f*t)
```

Ожидаемая реакция:

```text
velocity_std растёт;
statistical_anomaly растёт;
возможно recommendation по motion_instability.
```

---

## 15. Разметка синтетических аномалий

При генерации аномалий нужно создать колонку:

```text
label
```

Допустимые значения:

```text
normal
current_overload
temperature_ramp
voltage_drop
voltage_spike
error_code
data_gap
velocity_oscillation
```

Если аномалия наложена на участок:

```text
label = anomaly_type
```

В остальных точках:

```text
label = normal
```

---

## 16. Метрики качества

Создать модуль:

```text
evaluation/metrics.py
```

---

### 16.1. Accuracy

```text
accuracy = correct_predictions / total_predictions
```

---

### 16.2. Precision

```text
precision = TP / (TP + FP)
```

Показывает, насколько часто тревоги были реальными.

---

### 16.3. Recall

```text
recall = TP / (TP + FN)
```

Показывает, сколько аномалий модель нашла.

---

### 16.4. F1-score

```text
F1 = 2 * precision * recall / (precision + recall)
```

---

### 16.5. False Alarm Rate

```text
false_alarm_rate = false_alarms / normal_windows
```

---

### 16.6. Detection Delay

Задержка обнаружения:

```text
detection_delay = first_detected_anomaly_time - anomaly_start_time
```

Для проекта это важная метрика, потому что модель должна находить отклонения достаточно быстро.

---

### 16.7. Calculation Time

Измерить время обработки:

```text
time per window
time per full session
```

---

## 17. Бинарная оценка аномалий

Для метрик нужно перевести состояние модели в binary prediction.

Пример:

```python
def state_to_binary_anomaly(state: str) -> int:
    if state in ["warning", "critical"]:
        return 1
    return 0
```

Или более мягкий вариант:

```python
if state in ["observation", "warning", "critical"]:
    return 1
```

Для первой оценки лучше:

```text
warning/critical = anomaly
normal/observation = normal
```

---

## 18. Оценка по окнам

Каждое окно должно получить label.

Если в окне есть хотя бы одна точка с аномальным label:

```text
window_label = anomaly
```

Иначе:

```text
window_label = normal
```

---

## 19. Графики

Создать модуль:

```text
evaluation/plots.py
```

Графики:

1. Health Score во времени.
2. Anomaly Score во времени.
3. Риски во времени.
4. Температура + пределы.
5. DC-шина + пределы.
6. Ток + пределы.
7. State timeline.

---

## 20. Минимальные графики для статьи

Обязательно подготовить:

```text
health_score_over_time.png
anomaly_score_over_time.png
risks_over_time.png
telemetry_with_anomaly.png
```

---

## 21. Acceptance criteria

Тестирование и evaluation считаются готовыми, если:

1. Есть pytest-тесты для data pipeline.
2. Есть pytest-тесты для features.
3. Есть pytest-тесты для physical risks.
4. Есть pytest-тесты для Health Score.
5. Есть pytest-тесты для classifier.
6. Есть pytest-тесты для recommendations.
7. Есть интеграционный тест `diagnose_csv`.
8. Есть модуль синтетических аномалий.
9. Можно создать current overload.
10. Можно создать temperature ramp.
11. Можно создать voltage drop/spike.
12. Можно создать error_code anomaly.
13. Есть базовые метрики precision/recall/F1.
14. Есть расчёт detection delay.
15. Есть хотя бы базовые графики.
16. Модель не падает на плохих данных.
