# luci-app-openflux

**Languages:** [English](#english) · [Русский](#russian)

---

<a id="english"></a>
## English

LuCI application for running the [OpenFlux](https://github.com/p1neappleXpress/OpenFlux)
client on OpenWrt. It keeps any number of tunnel profiles in UCI and runs
**exactly one selected profile**, exposing a local SOCKS5 port that a proxy
manager (Mihomo/SSClash, sing-box, etc.) can use as a regular upstream proxy.

The package contains only shell scripts, LuCI JavaScript and an empty UCI
config. No servers, rooms or keys are bundled — you add your own profiles in
the web UI.

### Features

- **Master switch** — when disabled, nothing is started and no RAM is used;
  the client binary is not even unpacked.
- **Multiple profiles, one process** — profiles are just UCI sections, so you
  can keep as many as you like without paying RAM for each one.
- **Editable encryption key** — stored in UCI (plain text, see Security) and
  written to `/tmp/openflux-<section>.key` with mode `600` on start.
- **Per-profile SOCKS5 port** — point your proxy manager at any of them.
- **Status, start/stop/restart and log** on the same page.
- **Binary from flash or gzip archive** — keep a compressed client in flash
  and let the service unpack it to `/tmp` on start (useful on routers with
  small overlay).

### Requirements

- OpenWrt 23.05 or newer with LuCI (tested on 24.10, `aarch64_cortex-a53`)
- ~12 MB free flash for the compressed client (or ~29 MB for the raw binary)
- ~100 MB free RAM while the client is running
- `luci-base` (declared as a dependency)

### Installation

1. Download `luci-app-openflux_<version>_all.ipk` from the **Releases** page of
   this repository (or build it yourself, see [Build](#build)) and copy it to
   the router:

   ```sh
   scp luci-app-openflux_1.0.0_all.ipk root@192.168.1.1:/tmp/
   ```

2. Install it (the package is architecture-independent and contains no
   binaries):

   ```sh
   opkg update
   opkg install /tmp/luci-app-openflux_1.0.0_all.ipk
   ```

   In LuCI the same is available at **System → Software → Upload Package**.

3. Install the OpenFlux client itself — see [Client binary](#client-binary).

4. Reload LuCI in the browser (`Ctrl+F5`) and open **Services → OpenFlux**.

### Client binary

The package does **not** ship the client. It is downloaded separately from the
upstream OpenFlux releases:

- Releases: <https://github.com/p1neappleXpress/OpenFlux/releases>
- Latest build: <https://github.com/p1neappleXpress/OpenFlux/releases/latest>

Pick the asset that matches the router's CPU:

| Router CPU | `uname -m` | Asset |
|---|---|---|
| ARM64 (most modern routers) | `aarch64` | `openflux-linux-arm64` |
| x86-64 | `x86_64` | `openflux-linux-amd64` |
| 32-bit ARM | `armv7l` | `openflux-linux-arm` |

Check on the router:

```sh
uname -m
opkg print-architecture | awk 'END { print $2 }'
```

#### 1. Download

On the router (ARM64 example; replace the asset name for other CPUs):

```sh
cd /tmp
uclient-fetch -O openflux-arm64 \
  https://github.com/p1neappleXpress/OpenFlux/releases/latest/download/openflux-linux-arm64
```

If `uclient-fetch` is not installed, install it or use `wget`:

```sh
opkg update
opkg install uclient-fetch        # or: opkg install wget-ssl
```

If GitHub is not reachable from the router (or you prefer a browser),
download `openflux-linux-arm64` on your PC and copy it over:

```powershell
scp openflux-linux-arm64 root@192.168.1.1:/tmp/openflux-arm64
```

Optionally verify the checksum against the release's `SHA256SUMS.txt`:

```sh
cd /tmp
uclient-fetch -O SHA256SUMS.txt \
  https://github.com/p1neappleXpress/OpenFlux/releases/latest/download/SHA256SUMS.txt
sha256sum openflux-arm64
grep openflux-linux-arm64 SHA256SUMS.txt
```

#### 2. Install it — compressed in flash (recommended)

The raw client is ~28–29 MB, which usually does not fit in a router's overlay.
The service can keep it gzipped in flash (~11–12 MB) and unpack it to RAM on
every start:

```sh
gzip -9 -c /tmp/openflux-arm64 > /root/openflux-arm64.gz
chmod 600 /root/openflux-arm64.gz
ls -lh /root/openflux-arm64.gz     # expect ~11-12 MB
rm /tmp/openflux-arm64
```

Then in **Services → OpenFlux** set:

- *Client binary* — `/usr/bin/openflux` (the file does not have to exist; it is
  only used as a hint that no raw binary is installed)
- *Compressed binary (optional)* — `/root/openflux-arm64.gz`

Or from the shell:

```sh
uci set openflux.main.binary='/usr/bin/openflux'
uci set openflux.main.archive='/root/openflux-arm64.gz'
uci commit openflux
/etc/init.d/openflux restart
```

On start the init script runs the equivalent of

```sh
gzip -dc /root/openflux-arm64.gz > /tmp/openflux && chmod +x /tmp/openflux
```

so the archive stays in flash and survives reboots, while the unpacked copy
lives in RAM and disappears on reboot (and is recreated on the next start).
Nothing is unpacked at all while the master switch is off.

#### 3. Alternative — raw binary in flash

Only if you have ~29 MB free in the overlay (`df -h /overlay`):

```sh
mv /tmp/openflux-arm64 /usr/bin/openflux
chmod +x /usr/bin/openflux
```

Set *Client binary* to `/usr/bin/openflux` and leave *Compressed binary* empty.

### Usage

1. **Services → OpenFlux**.
2. Add a profile: *Name*, *Transport*, *Link / room*, *SOCKS5* address,
   *Encryption key*.
3. Pick it under *Active profile*, enable *Enable service* and press
   **Save & Apply**.
4. The service restarts with that profile and listens on its SOCKS5 port.

Verify from a shell:

```sh
logread -e openflux                         # service messages
netstat -ln | grep 1081                     # SOCKS port is listening
curl --socks5-hostname 127.0.0.1:1081 https://ifconfig.me
```

The exit node's IP should be printed. On the router the running client is
`/tmp/openflux` (see [Files on the router](#files-on-the-router)).

#### Using it from Mihomo

```yaml
proxies:
  - name: openflux
    type: socks5
    server: 127.0.0.1
    port: 1081
    udp: true

proxy-groups:
  - name: Auto
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 120
    proxies:
      - openflux
```

If you keep several profiles with different SOCKS ports, add one proxy entry
per port. Only the active profile answers; the others simply fail health
checks until you switch.

### Build

Without the OpenWrt SDK (Python 3 only, any OS):

```sh
python3 build-ipk.py
# -> dist/luci-app-openflux_1.0.0_all.ipk
```

With the SDK/feed:

```sh
mkdir -p package/luci-app-openflux
cp -r . package/luci-app-openflux
make package/luci-app-openflux/compile V=s
```

Bump `VERSION` (and `PKG_RELEASE` if needed) before releasing.

#### Releases

A tag builds and publishes the package automatically:

```sh
git tag v1.0.0
git push origin v1.0.0
```

The `build` workflow runs `build-ipk.py` and attaches
`luci-app-openflux_1.0.0_all.ipk` to the GitHub release, so users can install it
straight from the **Releases** page. The same file is also available as a
workflow artifact. `dist/` and `*.ipk` are ignored by git — only the sources
are committed.

### Layout

```
root/etc/config/openflux                                  UCI defaults
root/etc/init.d/openflux                                  procd service
root/usr/share/luci/menu.d/luci-app-openflux.json         menu entry
root/usr/share/rpcd/acl.d/luci-app-openflux.json          ACL
root/www/luci-static/resources/view/openflux/overview.js  LuCI view
build-ipk.py                                              standalone ipk builder
Makefile                                                  SDK build
```

### Files on the router

| Path | What |
|---|---|
| `/etc/config/openflux` | UCI config: master switch, active profile, your profiles and keys (mode `600`) |
| `/etc/init.d/openflux` | procd init script (`/etc/init.d/openflux start\|stop\|restart\|enable\|disable`) |
| `/usr/bin/openflux` | Raw client binary — only if you chose the direct layout |
| `/root/openflux-arm64.gz` | Gzipped client in flash — only if you chose the compressed layout |
| `/tmp/openflux` | Running copy, unpacked from the archive on start |
| `/tmp/openflux-<section>.key` | Per-profile key file, written on start (mode `600`) |
| `/www/luci-static/resources/view/openflux/overview.js` | LuCI page |
| `/usr/share/luci/menu.d/luci-app-openflux.json` | Menu entry |
| `/usr/share/rpcd/acl.d/luci-app-openflux.json` | ACL for the page |

Typical compressed setup:

```sh
ls -lh /root/openflux-arm64.gz    # ~11-12 MB, in flash, survives reboot
ls -lh /tmp/openflux              # ~28-29 MB, in RAM, recreated on start
pidof openflux
uci show openflux
```

### Troubleshooting

- **`client binary not found` in the log** — neither `/usr/bin/openflux` nor the
  archive exists, or the archive path is wrong. Check `uci get
  openflux.main.archive` and `ls -l` that path.
- **`no profile with a URL configured`** — add a profile and select it under
  *Active profile*; an empty profile is skipped.
- **Client starts but returns `encryption key differs`** — the key must match
  the exit node byte-for-byte. Copy it with `cat` and do not trim it.
- **`gzip: write error: No space left on device`** — the overlay is full; the
  compressed archive needs ~12 MB. Check `df -h /overlay`.
- **Page missing after install** — reload with `Ctrl+F5`; if it still does not
  appear, run `rm -rf /tmp/luci-* && /etc/init.d/uhttpd restart`.

### Security

- Encryption keys are stored **in plain text** in `/etc/config/openflux`.
  The package sets the file mode to `600` on install, but anyone with root
  access to the router can read them. Do not publish your config.
- The UI shows the key so it can be edited; hide your screen when doing so.
- Prefer HTTPS links and keep the router firmware up to date.

### Notes

- Exactly one profile runs at a time. This is intentional: each client
  process needs ~60–70 MB RSS, which matters on a router.
- The key must match the exit node exactly. Copy it via `cat`, not through a
  terminal that may wrap lines.
- For `cupsonline` transports the room string expires eventually. If rooms
  return 404, recreate them on the exit node and update the profile.
- This is an unofficial UI wrapper, not affiliated with the OpenFlux author.
  OpenFlux itself is distributed under its own license and disclaimer.

### License

MIT — see [LICENSE](LICENSE).

---

<a id="russian"></a>
## Русский

**Languages:** [English](#english) · **Русский**

LuCI-приложение для запуска клиента [OpenFlux](https://github.com/p1neappleXpress/OpenFlux)
на OpenWrt. Хранит любое число профилей туннеля в UCI и запускает
**ровно один выбранный профиль**, открывая локальный SOCKS5-порт, который
менеджер прокси (Mihomo/SSClash, sing-box и т. п.) использует как обычный
вышестоящий прокси.

В пакете только shell-скрипты, JavaScript для LuCI и пустой конфиг UCI.
Никаких серверов, комнат и ключей внутри нет — свои профили вы добавляете
в веб-интерфейсе.

### Возможности

- **Главный выключатель** — когда выключен, ничего не запускается и память
  не расходуется; бинарник клиента даже не распаковывается.
- **Много профилей, один процесс** — профили это просто секции UCI, их можно
  держать сколько угодно, не платя RAM за каждый.
- **Ключ шифрования можно править** — хранится в UCI (открытым текстом, см.
  «Безопасность») и при старте пишется в `/tmp/openflux-<section>.key`
  с правами `600`.
- **Свой SOCKS5-порт у каждого профиля** — направьте менеджер прокси на
  любой из них.
- **Статус, старт/стоп/перезапуск и лог** на той же странице.
- **Бинарник из flash или gzip-архива** — держите сжатый клиент во flash, а
  сервис распакует его в `/tmp` при старте (полезно на роутерах с маленьким
  overlay).

### Требования

- OpenWrt 23.05 или новее с LuCI (проверено на 24.10, `aarch64_cortex-a53`)
- ~12 МБ свободного flash под сжатый клиент (или ~29 МБ под несжатый)
- ~100 МБ свободной RAM, пока клиент запущен
- `luci-base` (прописан в зависимостях)

### Установка

1. Скачайте `luci-app-openflux_<version>_all.ipk` со страницы **Releases**
   этого репозитория (или соберите сами, см. [Сборка](#ru-build)) и
   скопируйте на роутер:

   ```sh
   scp luci-app-openflux_1.0.0_all.ipk root@192.168.1.1:/tmp/
   ```

2. Установите (пакет не зависит от архитектуры и не содержит бинарников):

   ```sh
   opkg update
   opkg install /tmp/luci-app-openflux_1.0.0_all.ipk
   ```

   То же самое в LuCI: **System → Software → Upload Package**.

3. Установите сам клиент OpenFlux — см. [Клиент OpenFlux](#ru-client).

4. Перезагрузите LuCI в браузере (`Ctrl+F5`) и откройте
   **Services → OpenFlux**.

<a id="ru-client"></a>
### Клиент OpenFlux

Пакет **не содержит** клиент. Он скачивается отдельно из upstream-релизов
OpenFlux:

- Релизы: <https://github.com/p1neappleXpress/OpenFlux/releases>
- Последняя сборка: <https://github.com/p1neappleXpress/OpenFlux/releases/latest>

Выберите ассет под процессор роутера:

| Процессор роутера | `uname -m` | Ассет |
|---|---|---|
| ARM64 (большинство современных) | `aarch64` | `openflux-linux-arm64` |
| x86-64 | `x86_64` | `openflux-linux-amd64` |
| 32-битный ARM | `armv7l` | `openflux-linux-arm` |

Проверить на роутере:

```sh
uname -m
opkg print-architecture | awk 'END { print $2 }'
```

#### 1. Скачать

На роутере (пример для ARM64; для других CPU подставьте своё имя ассета):

```sh
cd /tmp
uclient-fetch -O openflux-arm64 \
  https://github.com/p1neappleXpress/OpenFlux/releases/latest/download/openflux-linux-arm64
```

Если `uclient-fetch` нет, поставьте его или используйте `wget`:

```sh
opkg update
opkg install uclient-fetch        # или: opkg install wget-ssl
```

Если GitHub с роутера недоступен (или удобнее браузером), скачайте
`openflux-linux-arm64` на ПК и скопируйте:

```powershell
scp openflux-linux-arm64 root@192.168.1.1:/tmp/openflux-arm64
```

При желании сверьте контрольную сумму с `SHA256SUMS.txt` из релиза:

```sh
cd /tmp
uclient-fetch -O SHA256SUMS.txt \
  https://github.com/p1neappleXpress/OpenFlux/releases/latest/download/SHA256SUMS.txt
sha256sum openflux-arm64
grep openflux-linux-arm64 SHA256SUMS.txt
```

#### 2. Установить — сжатым во flash (рекомендуется)

Несжатый клиент занимает ~28–29 МБ и обычно не влезает в overlay роутера.
Сервис умеет держать его в gzip во flash (~11–12 МБ) и распаковывать в RAM
при каждом старте:

```sh
gzip -9 -c /tmp/openflux-arm64 > /root/openflux-arm64.gz
chmod 600 /root/openflux-arm64.gz
ls -lh /root/openflux-arm64.gz     # ожидается ~11-12 МБ
rm /tmp/openflux-arm64
```

Затем в **Services → OpenFlux** укажите:

- *Client binary* — `/usr/bin/openflux` (файл может отсутствовать; путь нужен
  лишь как признак, что несжатого бинарника нет)
- *Compressed binary (optional)* — `/root/openflux-arm64.gz`

Или из консоли:

```sh
uci set openflux.main.binary='/usr/bin/openflux'
uci set openflux.main.archive='/root/openflux-arm64.gz'
uci commit openflux
/etc/init.d/openflux restart
```

При старте init-скрипт выполняет примерно это:

```sh
gzip -dc /root/openflux-arm64.gz > /tmp/openflux && chmod +x /tmp/openflux
```

таким образом архив остаётся во flash и переживает перезагрузку, а
распакованная копия живёт в RAM и исчезает при ребуте (и создаётся заново
при следующем старте). Пока главный выключатель выключен, распаковки нет
вообще.

#### 3. Альтернатива — несжатый бинарник во flash

Только если в overlay есть ~29 МБ свободно (`df -h /overlay`):

```sh
mv /tmp/openflux-arm64 /usr/bin/openflux
chmod +x /usr/bin/openflux
```

Укажите *Client binary* = `/usr/bin/openflux`, а *Compressed binary*
оставьте пустым.

### Использование

1. **Services → OpenFlux**.
2. Добавьте профиль: *Name*, *Transport*, *Link / room*, адрес *SOCKS5*,
   *Encryption key*.
3. Выберите его в *Active profile*, включите *Enable service* и нажмите
   **Save & Apply**.
4. Сервис перезапустится с этим профилем и начнёт слушать его SOCKS5-порт.

Проверка из консоли:

```sh
logread -e openflux                         # сообщения сервиса
netstat -ln | grep 1081                     # SOCKS-порт слушается
curl --socks5-hostname 127.0.0.1:1081 https://ifconfig.me
```

Должен вывестись IP выходной ноды. На роутере запущенный клиент — это
`/tmp/openflux` (см. [Файлы на роутере](#ru-paths)).

#### Использование из Mihomo

```yaml
proxies:
  - name: openflux
    type: socks5
    server: 127.0.0.1
    port: 1081
    udp: true

proxy-groups:
  - name: Auto
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 120
    proxies:
      - openflux
```

Если профилей несколько и у них разные SOCKS-порты, добавьте по записи на
каждый порт. Отвечает только активный профиль; остальные просто проваливают
health-check, пока вы не переключитесь.

<a id="ru-build"></a>
### Сборка

Без OpenWrt SDK (только Python 3, любая ОС):

```sh
python3 build-ipk.py
# -> dist/luci-app-openflux_1.0.0_all.ipk
```

С SDK/фидом:

```sh
mkdir -p package/luci-app-openflux
cp -r . package/luci-app-openflux
make package/luci-app-openflux/compile V=s
```

Перед релизом поднимите `VERSION` (и при необходимости `PKG_RELEASE`).

#### Релизы

Тег собирает и публикует пакет автоматически:

```sh
git tag v1.0.0
git push origin v1.0.0
```

Workflow `build` запускает `build-ipk.py` и прикрепляет
`luci-app-openflux_1.0.0_all.ipk` к GitHub-релизу, так что пакет можно
поставить прямо со страницы **Releases**. Тот же файл доступен как артефакт
workflow. `dist/` и `*.ipk` игнорируются git — в репозитории только
исходники.

### Структура репозитория

```
root/etc/config/openflux                                  UCI defaults
root/etc/init.d/openflux                                  procd service
root/usr/share/luci/menu.d/luci-app-openflux.json         menu entry
root/usr/share/rpcd/acl.d/luci-app-openflux.json          ACL
root/www/luci-static/resources/view/openflux/overview.js  LuCI view
build-ipk.py                                              standalone ipk builder
Makefile                                                  SDK build
```

<a id="ru-paths"></a>
### Файлы на роутере

| Путь | Что это |
|---|---|
| `/etc/config/openflux` | Конфиг UCI: главный выключатель, активный профиль, профили и ключи (права `600`) |
| `/etc/init.d/openflux` | procd init-скрипт (`/etc/init.d/openflux start\|stop\|restart\|enable\|disable`) |
| `/usr/bin/openflux` | Несжатый бинарник клиента — только при прямом варианте |
| `/root/openflux-arm64.gz` | Сжатый клиент во flash — только при сжатом варианте |
| `/tmp/openflux` | Рабочая копия, распаковывается из архива при старте |
| `/tmp/openflux-<section>.key` | Файл ключа профиля, создаётся при старте (права `600`) |
| `/www/luci-static/resources/view/openflux/overview.js` | Страница LuCI |
| `/usr/share/luci/menu.d/luci-app-openflux.json` | Пункт меню |
| `/usr/share/rpcd/acl.d/luci-app-openflux.json` | ACL для страницы |

Типичная настройка со сжатым клиентом:

```sh
ls -lh /root/openflux-arm64.gz    # ~11-12 МБ, во flash, переживает ребут
ls -lh /tmp/openflux              # ~28-29 МБ, в RAM, создаётся при старте
pidof openflux
uci show openflux
```

### Если что-то не работает

- **`client binary not found` в логе** — нет ни `/usr/bin/openflux`, ни
  архива, либо путь к архиву неверный. Проверьте
  `uci get openflux.main.archive` и `ls -l` по этому пути.
- **`no profile with a URL configured`** — добавьте профиль и выберите его
  в *Active profile*; пустой профиль пропускается.
- **Клиент стартует, но пишет `encryption key differs`** — ключ должен
  совпадать с выходной нодой байт в байт. Копируйте через `cat` и не
  обрезайте.
- **`gzip: write error: No space left on device`** — overlay переполнен;
  сжатому архиву нужно ~12 МБ. Проверьте `df -h /overlay`.
- **После установки нет страницы** — перезагрузите с `Ctrl+F5`; если не
  помогло, выполните `rm -rf /tmp/luci-* && /etc/init.d/uhttpd restart`.

### Безопасность

- Ключи шифрования хранятся **открытым текстом** в `/etc/config/openflux`.
  При установке пакет ставит файлу права `600`, но любой с root-доступом к
  роутеру их прочитает. Не публикуйте свой конфиг.
- Интерфейс показывает ключ, чтобы его можно было править; не показывайте
  экран посторонним.
- Предпочитайте HTTPS-ссылки и держите прошивку роутера обновлённой.

### Примечания

- Одновременно работает ровно один профиль. Это осознанно: каждый процесс
  клиента занимает ~60–70 МБ RSS, что для роутера существенно.
- Ключ должен точно совпадать с выходной нодой. Копируйте его через `cat`,
  а не через терминал, который может перенести строку.
- Для транспорта `cupsonline` строка комнаты со временем протухает. Если
  комнаты отвечают 404, создайте их заново на выходной ноде и обновите
  профиль.
- Это неофициальная обёртка, не связанная с автором OpenFlux. Сам OpenFlux
  распространяется по собственной лицензии и с собственным дисклеймером.

### Лицензия

MIT — см. [LICENSE](LICENSE).
