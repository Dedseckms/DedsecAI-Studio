<p align="center">
  <img src="assets/readme/banner.svg" width="100%" alt="DedsecAI Studio — локальные модели, код, изображения и память" />
</p>

<p align="center">
  <strong>Локальная AI-мастерская под твой компьютер.</strong><br />
  Общайся с моделями, пиши код в Pi и создавай изображения в одном интерфейсе.
</p>

<p align="center">
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/latest"><img src="https://img.shields.io/github/v/release/Dedseckms/DedsecAI-Studio?include_prereleases&amp;style=for-the-badge&amp;label=RELEASE&amp;color=7fffc1&amp;labelColor=101b21" alt="Последняя версия" /></a>
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Dedseckms/DedsecAI-Studio/ci.yml?branch=main&amp;style=for-the-badge&amp;label=CI&amp;labelColor=101b21" alt="Статус проверок Linux и Windows" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/LICENSE-MIT-7fffc1?style=for-the-badge&amp;labelColor=101b21" alt="Код Studio: лицензия MIT" /></a>
  <a href="#installation"><img src="https://img.shields.io/badge/PYTHON-3.10%2B-8fbaff?style=for-the-badge&amp;labelColor=101b21" alt="Python 3.10 или новее" /></a>
</p>

<p align="center">
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/stargazers"><img src="https://img.shields.io/github/stars/Dedseckms/DedsecAI-Studio?style=flat-square&amp;label=Stars&amp;color=7fffc1&amp;labelColor=101b21" alt="Звёзды GitHub" /></a>
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/forks"><img src="https://img.shields.io/github/forks/Dedseckms/DedsecAI-Studio?style=flat-square&amp;label=Forks&amp;color=7fffc1&amp;labelColor=101b21" alt="Форки GitHub" /></a>
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases"><img src="https://img.shields.io/github/downloads/Dedseckms/DedsecAI-Studio/total?style=flat-square&amp;label=Downloads&amp;color=7fffc1&amp;labelColor=101b21" alt="Скачивания файлов релизов" /></a>
</p>

<p align="center">
  <a href="#download">Скачать</a> · <a href="#screenshots">Скриншоты</a> · <a href="#installation">Установка</a> · <a href="#guide">Руководство</a> · <a href="https://github.com/Dedseckms/DedsecAI-Studio/issues/new/choose">Предложить улучшение</a>
</p>

<a id="download"></a>

## Скачать и запустить

<p align="center">
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/DedsecAI-Studio-0.4.1-Setup.exe"><img src="assets/readme/windows.svg" width="240" alt="Скачать Windows EXE" /></a>
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/dedsecai-studio-0.4.1-1-any.pkg.tar.zst"><img src="assets/readme/arch.svg" width="240" alt="Скачать пакет Arch Linux" /></a>
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/dedsecai-studio_0.4.1_all.deb"><img src="assets/readme/debian.svg" width="240" alt="Скачать пакет Debian или Ubuntu" /></a>
</p>

<p align="center">
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/tag/v0.4.1">Все варианты, ZIP и tar.gz</a> · <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/SHA256SUMS">SHA-256</a> · <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/tag/v0.4.1">Что нового в v0.4.1</a>
</p>

Ранняя версия проекта. EXE не подписан; полная приёмочная установка GUI на Windows/Debian ещё не завершена. Для скачивания движков и весов нужен интернет. Модели и личная переписка в установщики не входят.

<a id="screenshots"></a>

## Внутри Studio

<a href="assets/readme/companion.webp"><img src="assets/readme/companion.webp" width="100%" alt="Собеседник: отдельный список чатов, переписка с кодом и поле ввода" /></a>

<p align="center"><sub>Реальный интерфейс с демонстрационной перепиской. Личные чаты в скриншоты не включены. Нажми на изображение, чтобы открыть его полностью.</sub></p>

<table>
  <tr>
    <td width="50%"><a href="assets/readme/dashboard.webp"><img src="assets/readme/dashboard.webp" alt="Панель управления моделями и оборудованием" /></a></td>
    <td width="50%"><a href="assets/readme/images.webp"><img src="assets/readme/images.webp" alt="Мастерская изображений с каталогом Uncensored-сборок" /></a></td>
  </tr>
  <tr>
    <td align="center"><strong>Модели и ресурсы ПК</strong><br /><sub>Контекст, профили, замеры и управление сервером.</sub></td>
    <td align="center"><strong>Мастерская изображений</strong><br /><sub>Каталог, Hugging Face, компоненты и галерея.</sub></td>
  </tr>
</table>

<details>
<summary><strong>Ещё экраны: память и мобильный вид</strong></summary>
<br />
<table>
  <tr>
    <td width="72%" valign="top"><a href="assets/readme/memory.webp"><img src="assets/readme/memory.webp" alt="Редактируемая локальная память собеседника" /></a></td>
    <td width="28%" valign="top"><a href="assets/readme/mobile.webp"><img src="assets/readme/mobile.webp" alt="Собеседник на узком экране" /></a></td>
  </tr>
</table>
</details>

## Одна мастерская — разные задачи

| 💬 Собеседник | 🧠 Личная память |
| :--- | :--- |
| История на диске, поиск, независимая прокрутка чатов и сообщений, удаление и восстановление. | Редактируемые факты и предпочтения, доступные моделям между разговорами. |
| **🧩 Свои модели** | **🎨 Изображения** |
| GGUF, Hugging Face, свои файлы, квантовки и настраиваемый контекст. | SD Turbo, SDXL, Qwen Image; загрузка, компоненты, генерация и корзина галереи. |
| **⌨️ Код в терминале** | **📊 Под твой компьютер** |
| Открытие Pi в выбранной папке проекта и общий профиль модели с веб-чатом. | CPU, RAM, GPU/VRAM, объяснение ограничений и реальные замеры скорости. |

### Что уже есть

- **Два движка:** llama.cpp для текста и vision, stable-diffusion.cpp для генерации изображений.
- **Контроль памяти:** видно, какой движок работает и какая модель загружена; есть отдельные кнопки выгрузки.
- **Удобные загрузки:** «Мои модели», «Каталог» и Hugging Face. Можно только скачать или скачать и запустить.
- **Qwen Image 2.1:** совместимые энкодер и VAE подключаются автоматически.
- **Свой стиль:** терминальное оформление, анимации, обои и режим уменьшенного движения.
- **Локальные данные:** история, вложения, галерея и факты хранятся на компьютере.

В каталоге есть сборки с меткой **Uncensored**. Это обозначение автора весов, а не гарантия поведения или универсальной совместимости. Vision анализирует картинки в чате; генерация изображений находится в отдельной мастерской.

<a id="installation"></a>

## Начать за несколько минут

| Система | Что делать |
| :--- | :--- |
| **Windows** | Запусти [EXE](https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/DedsecAI-Studio-0.4.1-Setup.exe), выбери компоненты и открой Studio из меню Пуск. |
| **Arch Linux** | Установи [пакет](https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/dedsecai-studio-0.4.1-1-any.pkg.tar.zst) через `sudo pacman -U ./dedsecai-studio-0.4.1-1-any.pkg.tar.zst`. |
| **Debian / Ubuntu** | Установи [DEB](https://github.com/Dedseckms/DedsecAI-Studio/releases/download/v0.4.1/dedsecai-studio_0.4.1_all.deb) через `sudo apt install ./dedsecai-studio_0.4.1_all.deb`. |

После установки открой Studio → настрой движок → выбери модель. В нативных Linux-пакетах движки и Pi устанавливаются из раздела **«Система»**; скриптовые установщики могут настроить их сразу.

**Адрес панели:** `http://127.0.0.1:1236` · **CLI:** `dedsecai web`

<details>
<summary><strong>Запуск из исходников</strong></summary>

```bash
git clone https://github.com/Dedseckms/DedsecAI-Studio.git
cd DedsecAI-Studio
python3 cli.py init
python3 cli.py web
```

Нужен Python 3.10+. Движок, Pi и веса настраиваются отдельно через интерфейс. На Windows команда Python может называться `python`.
</details>

<a id="guide"></a>

## Руководство и подробности

<details>
<summary><strong>Открыть полное руководство: установка, модели, память, фильтры и сборка</strong></summary>

## Установка

### Windows

Запустите `DedsecAI-Studio-0.4.1-Setup.exe` — мастер установки с выбором llama.cpp, Pi и автозапуска. Альтернатива: распакуйте Windows ZIP и запустите `installers\install-windows.cmd`.
Нужен Python 3.10+ с Tcl/Tk. При отсутствии подходящего Python/Tk/FTS5 установщик скачивает официальный Python 3.14.10, проверяет SHA-256 и Authenticode издателя и устанавливает его для текущего пользователя. winget не требуется.
Устанавливается готовый Vulkan runtime llama.cpp (либо CPU: PowerShell `-Backend cpu`), затем Pi и Node.js при необходимости.
В меню Пуск появляется DedsecAI Studio, сервер панели запускается при входе. Для отключения: `-NoAutostart`.
Windows CUDA: укажите собственный проверенный llama-server через `DEDSECAI_LLAMA_SERVER`; автоматический Windows-установщик использует Vulkan/CPU.

### Arch Linux

Распакуйте Arch архив: `bash installers/install-arch.sh`.
Для существующего llama-server достаточно Python/Tk; иначе ставятся инструменты сборки и Vulkan.
Вариант без сборки runtime: `bash installers/install-arch.sh --skip-runtime`.
Для нативного пакета есть `packaging/PKGBUILD`; готовность пакета зависит от наличия makepkg/fakeroot у сборщика.

### Debian / Ubuntu

Распакуйте Debian архив: `bash installers/install-debian.sh`.
Либо установите DEB: `sudo apt install ./dedsecai-studio_0.4.1_all.deb` и откройте приложение из меню.
DEB ставит приложение; runtime/Pi настраиваются кнопками в разделе «Система».
Скриптовый установщик ставит зависимости и настраивает runtime/Pi сразу.
Сборка llama.cpp из исходников использует glibc целевой системы — архив Ubuntu runtime не подставляется в старый Debian.
Драйвер видеокарты и Vulkan ICD должен быть установлен отдельно. Установщик не заменяет видеодрайверы.

### Общие параметры

`installers/install.py --skip-runtime --skip-pi --no-autostart --no-open` — установить только приложение.
`python cli.py setup-runtime --backend auto|cpu|vulkan|cuda` — настройка движка.
`python cli.py setup-pi` — отдельная установка Pi (Node >=22.19, пакет Pi закреплён на 1.1.0).
`python cli.py web` — открыть приложение, `python cli.py serve` — сервер переднего плана.
`python cli.py init --migrate` — перенести данные старого Qwen Studio, сохранив оригиналы.

## Железо и модели

Оценки не являются гарантией загрузки или точной скорости. Итоговый расход зависит от архитектуры, KV, вычислительных буферов, драйвера и других приложений.
На Windows карты NVIDIA, AMD и Intel определяются через DXGI, с отдельным учётом выделенной видеопамяти и разделяемой RAM. NVIDIA дополнительно сообщает датчики через nvidia-smi. Если занятая память неизвестна, интерфейс показывает прочерк.
NVIDIA определяется через nvidia-smi, AMD в Linux — через sysfs. Неизвестная/разделяемая память не выдаётся за гарантированную VRAM.
Загруженный GGUF уточняет архитектуру и параметры кэша. MLA/SSM/hybrid оцениваются приблизительно.
Измеренная скорость привязана к профилю и отпечатку оборудования, не переносится на другой компьютер.
Kimi K2 — сотни ГиБ весов. MoE active parameters не заменяют полный размер. Не подходящие ПК варианты отмечаются явно.
У каждого GGUF своя лицензия и требования к версии llama.cpp. Каталог подтверждает наличие файлов, а не качество всех моделей.
Для закрытых Hugging Face репозиториев задайте `HF_TOKEN` и примите условия в источнике.
Для текстовых и vision-моделей нужен GGUF. Для генерации stable-diffusion.cpp принимает совместимые GGUF/safetensors/ckpt и отдельные энкодеры/VAE по рецепту. Один diffusion GGUF обычно не включает все компоненты.

## Чаты собеседника

Переписка и список чатов прокручиваются независимо в пределах окна; поле ввода остаётся снизу. На узком экране список открывается кнопкой «Чаты». Обновление ответа сохраняет позицию чтения, когда вы прокрутили историю вверх.
У чата есть кнопка «×» для удаления с подтверждением. Чат перемещается в корзину, скрывается из истории и поиска и может быть восстановлен вместе с вложениями. Отдельно сохранённые записи «Памяти» остаются доступными. Перед удалением чата с текущим ответом нужно остановить генерацию.

## Мастерская изображений и GPU

Общая верхняя панель показывает модели, о которых сообщают работающие API, и расход VRAM процессов NVIDIA, когда драйвер отдаёт эти данные. Выбранная в каталоге модель не считается загруженной. Общая занятая VRAM включает рабочий стол и другие приложения; она не приписывается целиком нейросети. Для каждого движка есть отдельная кнопка выгрузки.

В «Изображениях» разделены «Мои модели», «Каталог» и поиск Hugging Face. Можно скачать модель, не переключая работающего собеседника, или скачать и сразу запустить. Встроенный каталог содержит SD Turbo, SD 1.5, SDXL Turbo и Qwen Image 2.1 Uncensored Q4/Q5/Q6/Q8. Uncensored — метка автора, не гарантия отсутствия отказов или определённого содержания. Поиск исключает явно размеченные энкодеры/LoRA; форматы MLX/NVFP4 и split-веса не предлагаются как самостоятельные модели для этого runtime. Совместимость произвольной сторонней сборки всё равно зависит от архитектуры и компонентов.

У картинки есть «Сохранить» и «Удалить». Удаление требует подтверждения и перемещает PNG в локальную корзину; вкладка «Корзина» восстанавливает файл и запись галереи. Отдельная блокировка защищает индекс при одновременной генерации и удалении. Модель записывается в метаданные новых изображений; у старых неизвестная модель не угадывается. Ваши картинки не удаляются при обновлении.

Если после генерации вы работали в текстовом чате, следующая генерация загружает последний выбранный генератор. Переключение освобождает другой движок. Оба серверных API остаются на loopback.

## Контекст и картинки

В Обзоре нажмите «Изменить контекст», либо «Настроить» на карточке модели. Предел берётся из GGUF; выбранное окно может не поместиться в память ПК. Интерфейс показывает приблизительный KV-кэш, а не гарантию запуска. Активная модель перезапустится; Pi получит новый размер окна при следующем запуске.
Vision-модель и её проектор должны соответствовать друг другу. При импорте Hugging Face выбирайте mmproj; у локальной модели укажите полный путь в профиле. До четырёх PNG/JPEG/WebP до 6 МиБ сохраняются вместе с сообщением. Для картинок резервируется дополнительный контекст. Точное число image-токенов зависит от модели.

Во вкладке «Изображения» выберите SD Turbo, SD 1.5 или SDXL Turbo и нажмите «Скачать и запустить». Движок, рецепт и основной файл подключаются автоматически. Каталог показывает объём загрузки и ориентир по GPU вашего ПК. Ссылка не требуется.
Свой GGUF/safetensors/ckpt можно добавить кнопкой «Выбрать файл с компьютера». Известные типы распознаются автоматически; для составных моделей подбираются однозначно подходящие компоненты из библиотеки, а недостающие перечисляются явно. Для Qwen Image 2.1 и Turbo недостающие Qwen3-VL-8B Q4_K_M и VAE 2.1 скачиваются и подключаются автоматически по закреплённым ревизиям и SHA-256. В карточке указан дополнительный объём. Полный VAE не скачивается, если уже выбран подходящий TAE. Проверяются также группы «нужен хотя бы один компонент», например VAE/TAE.
Рецепт, компоненты и прямые ссылки остаются в свёрнутых дополнительных настройках. Из каталога импортированный image-GGUF можно подключить кнопкой «В изображения»: создаётся hard link, оригинал сохраняется. При импорте между разными дисками файл копируется после проверки свободного места; оригинал сохраняется. Рецепты берутся из закреплённого runtime.
Скорость генератора проверяется реальным изображением после загрузки всех компонентов. Автозамеры можно прервать кнопкой остановки. Запуск генератора освобождает текстовую модель; запуск текстовой модели останавливает генератор. Image-runtime устанавливается отдельно кнопкой: x64 Windows и Linux, CPU/Vulkan.

## Автоматическая память

По умолчанию новые сообщения проверяются на прямые утверждения об имени, месте проживания, работе, языке ответов и предпочтениях. Сохраняются слова пользователя с источником сообщения, а не догадки модели. Вопросы, примеры и сообщения с очевидными секретами пропускаются; это эвристика, а не распознавание всех личных данных. Память можно отключить или исправить во вкладке «Память». Исправленную вручную запись автообновление не перезаписывает. Изменения автоматических записей сохраняются в истории БД.
Память общая для моделей. Это не обучение весов и не полное понимание всей биографии; сложный факт можно добавить через «Запомни: …» или вручную. Старые сообщения задним числом автоматически не обрабатываются.

## Фильтры

Режим «Без фильтров приложения» отключает проверки Studio, но не удаляет обученные отказы из весов.
Списки тем/слов — эвристика: возможны пропуски и ложные срабатывания; стопроцентный тематический запрет не обещается.
При ограничениях ответ буферизуется, проверяется и только затем показывается. Запрещённый запрос не добавляется в чат.
Политики действуют только в веб-собеседнике. Прямой API llama.cpp и Pi обходят эти проверки.
Изменение правил не стирает историю или память и применяется к следующим сообщениям.

## Данные и перенос

Linux: `${XDG_DATA_HOME:-~/.local/share}/dedsecai-studio`; Windows: `%LOCALAPPDATA%\DedsecAI Studio`.
Переменная `DEDSECAI_HOME` меняет каталог данных; код установки хранится в `app/`, данные отдельно.
`config/`, `state/`, `models/`, `image-models/`, `gallery/`, `companion/companion.sqlite3` — настройки, журналы, модели и переписка.
Локальный импорт ссылается на файл в исходной папке. При переносе ПК путь нужно выбрать заново.
Панель доступна только на loopback; действия проверяют Host, Origin и CSRF-токен. Прямой llama.cpp API слушает loopback отдельно.
Старые файлы не удаляются при миграции. Перед обновлением пользовательской установки создаётся копия кода.

## Сборка и проверка

`python build.py` создаёт ZIP Windows, tar.gz Arch/Debian, DEB и SHA256SUMS в dist/.
`python -m unittest discover -s tests -v` — проверки без загрузки весов.
Полные приёмочные проверки Windows и Debian в этой Linux-среде не выполнялись. Скрипты/формат пакетов проверяются здесь, а запуск на целевой ОС требует отдельного тестирования.
Установщики не подписаны Authenticode и не содержат веса, токены, личные настройки или переписку.
Сборка llama.cpp/скачивание runtime и Pi требует интернета. На слабом ПК сборка занимает заметное время.

Источники: https://github.com/leejet/stable-diffusion.cpp, https://github.com/ggml-org/llama.cpp, https://huggingface.co, https://nodejs.org, https://github.com/earendil-works/pi.

## Windows EXE

Это настоящий Unicode NSIS online-установщик, не переименованный ZIP. Компоненты llama.cpp, Pi/Node и автозапуск включены по умолчанию и отключаются в мастере.
Архитектуры: Windows 10/11 x64 или ARM64. Сам загрузчик NSIS x86 работает через системную совместимость; скачиваемые Python/Node/llama выбираются под ОС.
Нужен интернет. Python/движок/Pi скачиваются по необходимости, веса моделей отдельно.
Мастер создаёт запись в «Установленных приложениях» и удаление программы с подтверждением. Удаление сохраняет модели, историю, память и скачанные runtimes.
Журнал установки: `%LOCALAPPDATA%\DedsecAI Studio\state\windows-setup.log`.
EXE не подписан Authenticode. Полная установка на настоящей Windows пока не проверена.
Сборка EXE: `python installers/build-windows.py --makensis /путь/к/makensis` (NSIS 3; при переносимой Linux-сборке задайте NSISDIR).

</details>

## Вместе делаем Studio удобнее

Нашёл ошибку или придумал улучшение? [Создай issue](https://github.com/Dedseckms/DedsecAI-Studio/issues/new/choose). Хочешь помочь кодом — начни с [CONTRIBUTING.md](CONTRIBUTING.md).

<p align="center">
  <a href="https://github.com/Dedseckms/DedsecAI-Studio/stargazers">⭐ Поддержать проект звездой</a> · <a href="https://github.com/Dedseckms/DedsecAI-Studio/releases/latest">↓ Последний релиз</a> · <a href="LICENSE">MIT</a> · <a href="NOTICE.md">Сторонние компоненты</a>
</p>

<p align="center"><sub>Сделано для локальной работы. Модели выбираешь ты.</sub></p>
