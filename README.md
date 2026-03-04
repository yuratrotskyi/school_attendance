# Звітність відвідуваності школи

CLI-додаток і документація для щоденної автоматизації звітності по відвідуваності учнів на базі даних `nz.ua`.

## Що вміє додаток
- Автоматично збирати відвідуваність з журналів `https://nz.ua/journal/list` (гібридний режим, через Playwright).
- Нормалізувати CSV-дані в єдиний формат.
- Обчислювати KPI за `7 днів / 30 днів / семестр`.
- Виявляти інциденти "втік з уроків" за правилом `1+`.
- Формувати вихідні файли: `summary.json`, `detail.csv`, `report.md`.

## Вимоги
- `Python 3.9+`
- Для автоматичного збору: `playwright` + `chromium`

## Встановлення
1. Встановіть залежності:
   `python3 -m pip install -r requirements.txt`
2. Встановіть браузер для Playwright:
   `playwright install chromium`
3. Створіть `.env` на основі прикладу:
   `cp .env.example .env`
4. Заповніть `NZ_LOGIN`, `NZ_PASSWORD` у `.env`.
5. За потреби вкажіть шлях файлу сесії:
   `SESSION_STATE_PATH=config/nz_session_state.json`
6. Для nz.ua з Cloudflare залишайте:
   `NZ_HEADLESS=false` (щоб можна було пройти перевірку "Verify you are human")

## Налаштування селекторів nz.ua
1. Скопіюйте шаблон:
   `cp config/nz_selectors.example.json config/nz_selectors.json`
2. Актуалізуйте селектори під інтерфейс вашого акаунта `nz.ua`:
   - `journal_list`: список журналів і пагінація сторінок списку.
   - `journal_page`: таблиця учнів/відміток і пагінація сторінок всередині журналу.
3. Додайте в `.env`:
   `SELECTORS_PATH=config/nz_selectors.json`

### Правила мапінгу відміток у журналі
- `Н` => відсутній (`ABSENT`) і враховується у звітах.
- `ХВ` => ігнорується для метрик відсутності.
- Інші значення/порожня клітинка => присутність (`PRESENT`).

## Запуск
### 0) Одноразовий ручний вхід (рекомендовано для обходу Cloudflare)
```bash
PYTHONPATH=src python3 -m school_attendance.cli bootstrap-session \
  --timeout-seconds 300
```
Після запуску відкриється браузер. Увійдіть вручну в кабінет і поверніться в термінал, щоб зберегти сесію.

### 1) Dry-run (без логіну, локальний CSV)
```bash
PYTHONPATH=src python3 -m school_attendance.cli run-daily \
  --dry-run \
  --skip-collect \
  --run-date 2026-03-04 \
  --raw-file /шлях/до/attendance.csv
```

### 2) Автоматичний збір з `journal/list` + обробка
```bash
PYTHONPATH=src python3 -m school_attendance.cli run-daily \
  --run-date 2026-03-04
```
Якщо файл сесії валідний, додаток використає його автоматично і не робитиме повторний логін по паролю.

Якщо з'являється Cloudflare:
1. Запустіть `bootstrap-session` і пройдіть "Verify you are human" у відкритому браузері.
2. Після збереження сесії повторіть `run-daily`.
3. У разі повторної помилки дивіться `logs/artifacts/cloudflare-*.html`.

## Де шукати результати
- Raw: `data/raw/<date>/`
- Нормалізовані: `data/normalized/<date>/attendance.csv`
- Оброблені: `data/processed/<date>/incidents.csv`
- Фінальний пакет: `out/<date>/summary.json`, `out/<date>/detail.csv`, `out/<date>/report.md`

Raw-файл після автоматичного збору: `data/raw/<date>/attendance-journal.csv`.

## Правило "втік з уроків"
Інцидент фіксується, якщо учень після першої присутності у день має `1+` неповажний пропуск.

## Тести
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Документація
- Політика: [`docs/ops/attendance/attendance-policy.md`](docs/ops/attendance/attendance-policy.md)
- SOP: [`docs/ops/attendance/daily-sop.md`](docs/ops/attendance/daily-sop.md)
- Start guide: [`docs/ops/attendance/start-guide.md`](docs/ops/attendance/start-guide.md)
- Дизайн додатка: [`docs/plans/2026-03-04-nz-attendance-app-design.md`](docs/plans/2026-03-04-nz-attendance-app-design.md)
- План реалізації: [`docs/plans/2026-03-04-nz-attendance-app-implementation-plan.md`](docs/plans/2026-03-04-nz-attendance-app-implementation-plan.md)
- Дизайн джерела `journal/list`: [`docs/plans/2026-03-04-nz-journal-list-source-design.md`](docs/plans/2026-03-04-nz-journal-list-source-design.md)
- План реалізації `journal/list`: [`docs/plans/2026-03-04-nz-journal-list-source-implementation-plan.md`](docs/plans/2026-03-04-nz-journal-list-source-implementation-plan.md)
