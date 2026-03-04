# Базова інструкція запуску звітності (додаток)

## 1. Підготовка перед першим запуском
1. Встановіть залежності: `python3 -m pip install -r requirements.txt`.
2. Встановіть браузер: `playwright install chromium`.
3. Створіть `.env` з `.env.example` і внесіть доступи до `nz.ua`.
4. Скопіюйте `config/nz_selectors.example.json` у `config/nz_selectors.json`.
5. Оновіть у `config/nz_selectors.json` URL і селектори під ваш інтерфейс.
6. Одноразово збережіть авторизовану сесію:
```bash
PYTHONPATH=src python3 -m school_attendance.cli bootstrap-session --timeout-seconds 300
```
Після відкриття браузера виконайте ручний вхід і поверніться в термінал.

## 2. Щоденний запуск (автоматичний)
```bash
PYTHONPATH=src python3 -m school_attendance.cli run-daily --run-date YYYY-MM-DD
```

Рекомендований час запуску: `06:00-06:20`.

## 3. Dry-run для перевірки локально
```bash
PYTHONPATH=src python3 -m school_attendance.cli run-daily \
  --dry-run --skip-collect \
  --run-date YYYY-MM-DD \
  --raw-file /шлях/до/attendance.csv
```

## 4. Що генерується
- `data/raw/<date>/` — сирі файли з `nz.ua`.
- `data/normalized/<date>/attendance.csv` — нормалізовані дані.
- `data/processed/<date>/incidents.csv` — інциденти "втік".
- `out/<date>/summary.json`, `detail.csv`, `report.md` — фінальний пакет.

## 5. Контрольні точки часу
- До `06:30`: готовий ранковий пакет.
- До `10:00`: первинна валідація інцидентів класними керівниками.
- До `12:00`: фінальні статуси інцидентів.

## 6. Fallback при неповних даних
1. Позначте випуск як "попередній".
2. Надішліть попередній пакет до `06:30`.
3. Після уточнення даних переформуйте і надішліть оновлення до `09:00`.

## 7. Чек перед відправкою
- Вірний `run-date`.
- Періоди 7/30/семестр пораховані.
- Інциденти "втік" відповідають правилу `1+`.
- Файли `summary.json`, `detail.csv`, `report.md` сформовані.
