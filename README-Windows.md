# School Attendance on Windows

Коротка інструкція для запуску на Windows 10/11.

## 1) Передумови

- Встановлений `Git`
- Встановлений `Python 3.10+` (з опцією "Add Python to PATH")

Перевірка:

```powershell
git --version
python --version
```

## 2) Клонування і перехід в проєкт

```powershell
git clone https://github.com/yuratrotskyi/school_attendance.git
cd school_attendance
```

## 3) Рекомендований старт по кліку

Після клонування можна просто запустити:

```powershell
.\windows\first-setup.cmd
```

Що зробить цей файл:

- створить `.venv`, якщо її ще нема
- встановить `pip`-залежності
- встановить `playwright chromium`
- створить `.env` з `.env.example`, якщо його ще нема
- створить `config\nz_selectors.json` з шаблону, якщо його ще нема
- відкриє браузер для `bootstrap-session`

Після цього можна користуватись двома launcher-файлами:

- `windows\run-daily.cmd`
- `windows\run-attendance-10plus.cmd`

І винести їх ярликами на робочий стіл.

## 4) Віртуальне середовище

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Якщо PowerShell блокує активацію:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 5) Встановлення залежностей

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## 6) Налаштування конфігів

```powershell
Copy-Item .env.example .env
Copy-Item config\nz_selectors.example.json config\nz_selectors.json
```

Відкрий `.env` і заповни потрібні змінні (`NZ_LOGIN`, `NZ_PASSWORD` тощо).

## 7) Перший вхід (збереження сесії)

```powershell
$env:PYTHONPATH = "src"
python -m school_attendance.cli bootstrap-session --timeout-seconds 300
```

Що робити:

- у відкритому браузері увійти в `nz.ua`
- пройти Cloudflare, якщо з’явиться
- після успішного входу повернутись в термінал і натиснути `Enter`

## 8) Щоденний запуск

```powershell
$env:PYTHONPATH = "src"
python -m school_attendance.cli run-daily
```

## 9) Запуск по кліку з ярлика

У репозиторії є 2 готові launcher-файли:

- `windows\run-daily.cmd`
- `windows\run-attendance-10plus.cmd`

Що вони роблять:

- переходять у папку проєкту
- активують `.venv`
- ставлять `PYTHONPATH=src`
- запускають потрібну команду
- залишають вікно відкритим після завершення

Як зробити кнопки на робочому столі:

1. Відкрий папку `school_attendance\windows`
2. Для `run-daily.cmd` натисни правою кнопкою:
   `Надіслати -> Робочий стіл (створити ярлик)`
3. Те саме зроби для `run-attendance-10plus.cmd`
4. За бажанням перейменуй ярлики на:
   - `Щоденний звіт`
   - `10+ днів підряд`

## 10) Де дивитись результати

- `out\YYYY-MM-DD\report.md`
- `out\YYYY-MM-DD\student-absence-summary.csv`
- `out\YYYY-MM-DD\summary.json`
- `data\normalized\YYYY-MM-DD\attendance.csv`

## 11) Якщо сесія протухла

Повтори крок 6 (`bootstrap-session`), потім знову крок 7.

## 12) Варіант для CMD

```cmd
py -3 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python -m playwright install chromium
set PYTHONPATH=src
python -m school_attendance.cli bootstrap-session --timeout-seconds 300
python -m school_attendance.cli run-daily
```
