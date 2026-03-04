# Звітність відвідуваності школи

Репозиторій містить документи та робочі шаблони для щоденної ранкової звітності по відсутніх учнях на основі даних з `nz.ua`.

## Що тут є
- Єдині правила формування звітів для адміністрації.
- Шаблон щоденного звіту (PDF структура + CSV поля).
- Правило інциденту "втік з уроків" (`1+`).
- SOP, ескалації, KPI пілоту на 30 днів.

## Швидкий старт
1. Переконайтесь, що у відповідального є доступ до `nz.ua` і таблиці зведення.
2. Відкрийте [базову інструкцію запуску](docs/ops/attendance/start-guide.md).
3. Зберіть дані відвідуваності за 7/30/семестр.
4. Оновіть зведення та перевірте інциденти "втік" за правилом `1+`.
5. Сформуйте PDF і надішліть директору до `06:30`.

## Щоденний цикл роботи
- `08:30-09:00`: збір і зведення даних.
- до `09:15`: доставка звіту.
- до `10:00`: первинна перевірка інцидентів класними керівниками.
- до `12:00`: фінальні статуси інцидентів.

## Структура документації
- Політика звітності: [`docs/ops/attendance/attendance-policy.md`](docs/ops/attendance/attendance-policy.md)
- Щоденний SOP: [`docs/ops/attendance/daily-sop.md`](docs/ops/attendance/daily-sop.md)
- Матриця ескалацій: [`docs/ops/attendance/escalation-matrix.md`](docs/ops/attendance/escalation-matrix.md)
- Шаблон звіту: [`docs/templates/attendance/daily-report-template.md`](docs/templates/attendance/daily-report-template.md)
- Поля експорту: [`docs/templates/attendance/daily-report-columns.csv`](docs/templates/attendance/daily-report-columns.csv)

## Правило "втік з уроків"
Інцидент фіксується, якщо учень після факту присутності в поточний день має `1+` пропущених уроків без офіційної причини.

## KPI пілоту на 30 днів
- `>=95%` звітів доставлено до `06:30`.
- Розбіжність з первинними даними `<=2%`.
- `100%` інцидентів мають статус до `12:00`.
- Неопрацьовані інциденти на кінець дня `<=5%`.

## Повна документація
- Дизайн рішення: [`docs/plans/2026-03-04-attendance-reporting-design.md`](docs/plans/2026-03-04-attendance-reporting-design.md)
- План впровадження: [`docs/plans/2026-03-04-attendance-reporting-implementation-plan.md`](docs/plans/2026-03-04-attendance-reporting-implementation-plan.md)
- Базова інструкція запуску: [`docs/ops/attendance/start-guide.md`](docs/ops/attendance/start-guide.md)
