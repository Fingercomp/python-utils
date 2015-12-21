# python-utils
Небольшие программки на Python.

## Чат-клиенты
Копируют таковой на сайтах. Отправка/получение сообщений, всякое форматирование, плюшки, свистелки и прочее.

**Требования**:
* Python 3.4+
* PyGObject
* BeautifulSoup

**OS**:
* Windows
* *Linux*

**Инфа**:
* Если зажать [Ctrl] и кликнуть по нику слева от сообщения, он вставится в строку ввода.
* Если зажать [Alt] и кликнуть по этому же нику, то откроется профиль (доступно только для cc-chat)
* Клик по иконке в трее - переключить видимость окна.

### ffgs-chat
Служит для работы с чатиком на [FFGS](http://ffgs.ru/). Минимум костылей благодаря толковому API.
![Скрин окна](http://i.imgur.com/yLe0wr0l.jpg)

**Настройка**:
* Создайте файл `~/.local/share/python-utils/ffgs-chat.cfg`.
* Авторизуйтесь на сайте [FFGS](http://ffgs.ru/).
* Откройте список куков в браузере.
* Скопируйте значение PHPSESSID.
* Вставьте его в файл, в первую строку.
* Запустите клиент. Если всё сделано верно, у Вас появится строка ввода сообщения внизу.

### cc-chat
Работает с чатиком на [cc.ru](http://computercraft.ru/). В отличии от программы выше, здесь огромное число костылей: такой API.
Тем не менее, оно работает.
![Скрин окна](http://i.imgur.com/ZLgHa2k.png)
![Скрин окна с инфой](http://i.imgur.com/J0R9XV3.png)

**Настройка**:
* Запустите программу.
* Скопируйте путь к файлу, который отобразится в диалоге.
* Окроейте его в редакторе.
* Авторизуйтесь на сайте [cc.ru](http://computercraft.ru/).
* Откройте Инспектор.
* Перейдите на вкладку "Сеть".
* Нажмите кнопку [Обновить] на сайте под чатом.
* Отследите нужный запрос и откройте описание.
* Перейдите по ссылке запроса.
* Скопируйте всё между `secure_key=` и `&type`.
* Вставьте это в первую строку файла.
* Из заголовков (Headers) скопируйте Cookie.
* Вставьте это во вторую строку файла.
* Запустите клиент. Запуск без корректных данных невозможен!

## Мониторинг серверов mc-monitor
Небольшой индикатор в системном трее сообщит о состояниях игровых серверов. Кроме того, есть таймер, активирующийся через каждые 24 часа, для рестарта которого требуется выбрать пункт меню.

**Требования**:
* Python 3.4+
* PyGObject
* mcstatus

**OS**:
* Windows
* *Linux*

**Настройка**:
* Запустите программу в первый раз.
* Скопируйте путь к файлу.
* В него впишите список серверов для мониторинга. Формат `АДРЕС:ПОРТ=ИМЯ СЕРВЕРА`. По строке на каждый сервер. Перед `=` не должно быть пробелов!
* Запустите программу. если всё сделано правильно, никаких ошибок быть не должно.
* Если вас не устраивает интервал обновления, найдите строку `DELAY = 10` и замените число на желаемое (в секундах).
