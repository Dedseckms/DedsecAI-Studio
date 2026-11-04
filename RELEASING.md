# Выпуск DedsecAI Studio

Каждый релиз сохраняет оформление v0.4.1: баннер Studio, русское описание, таблица Windows / Arch Linux / Debian и Ubuntu, шесть пакетов, SHA-256, снимок приложения, изменения и фактически выполненные проверки.

1. Обновить версию в `common.py`, `build.py`, `packaging/PKGBUILD`, `installers/windows-setup.nsi` и ссылки README.
2. Переписать раздел «Что нового» в `packaging/release-notes.md` под текущий выпуск. Оставить маркеры `@VERSION@` и `@COMMIT@` для сборщика.
3. Проверить CI в main. Создать и отправить тег `vX.Y.Z`.

Workflow Release собирает EXE, Windows ZIP, Arch tar.gz и pacman, Debian tar.gz и DEB. Публикация разрешена только после тестов Ubuntu и Windows, реального запуска панели и тихой установки собранного EXE в Windows. Release notes формируются из общего шаблона; файлы и SHA256SUMS формируются из одной сборки.

Оформление установщика хранится в `installers/artwork`. Для обновления ресурсов: `python installers/create-artwork.py` (Pillow). Иконка содержит размеры 16–256 пикселей. Полная установка с загрузкой Python/runtime/Pi и визуальная проверка страниц должны отдельно указываться в результатах проверки.
