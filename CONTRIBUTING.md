# Помочь DedsecAI Studio

Спасибо за интерес к проекту. Подойдут исправления, улучшения интерфейса, документация и отчёты с других компьютеров.

## С чего начать

1. Посмотри [открытые задачи](https://github.com/Dedseckms/DedsecAI-Studio/issues).
2. Для заметной новой функции сначала опиши сценарий в issue.
3. Создай ветку, внеси изменение и открой pull request с кратким описанием результата и проверок.

## Локальный запуск

Для самого веб-приложения достаточно Python 3.10+ и стандартной библиотеки. Создай отдельный каталог данных, чтобы разработка не меняла твою обычную установку:

```bash
git clone https://github.com/Dedseckms/DedsecAI-Studio.git
cd DedsecAI-Studio
DEDSECAI_HOME=/tmp/dedsecai-dev python3 cli.py serve
```

Windows PowerShell:

```powershell
$env:DEDSECAI_HOME = Join-Path $env:TEMP "dedsecai-dev"
python cli.py serve
```

Адрес: `http://127.0.0.1:1236`. Для второго одновременно работающего экземпляра задай также отдельные `DEDSECAI_PANEL_PORT`, `DEDSECAI_SERVER_PORT` и `DEDSECAI_IMAGE_PORT`.

## Проверки

```bash
DEDSECAI_HOME=/tmp/dedsecai-tests python3 -m unittest discover -s tests -v
python3 build.py
```

В PowerShell сначала задай `$env:DEDSECAI_HOME` на отдельную тестовую папку, затем выполни `python -m unittest discover -s tests -v` и `python build.py`.

CI проверяет Python-код и сборку на Ubuntu и Windows. Unit tests не скачивают веса. Проверку конкретной модели описывай отдельно: имя и квантовка, движок, GPU/VRAM, RAM и результат.

## Что полезно в pull request

- Конкретный сценарий до и после изменения.
- Скриншоты для интерфейса и проверка узкого экрана.
- Проверки, которые подтверждают исправление.
- Объяснение новых зависимостей, если они нужны.

Не включай в коммит веса, базы переписки, личные конфиги или ключи. Примеры и скриншоты делай на демонстрационных данных. Код Studio распространяется под [MIT](LICENSE); сторонние компоненты — на своих условиях, см. [NOTICE.md](NOTICE.md).
