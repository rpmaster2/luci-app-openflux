# luci-app-openflux

LuCI application for running the [OpenFlux](https://github.com/p1neappleXpress/OpenFlux)
client on OpenWrt. It keeps any number of tunnel profiles in UCI and runs
**exactly one selected profile**, exposing a local SOCKS5 port that a proxy
manager (Mihomo/SSClash, sing-box, etc.) can use as a regular upstream proxy.

The package contains only shell scripts, LuCI JavaScript and an empty UCI
config. No servers, rooms or keys are bundled — you add your own profiles in
the web UI.

## Features

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

## Requirements

- OpenWrt 23.05 or newer with LuCI (tested on 24.10, `aarch64_cortex-a53`)
- The OpenFlux client binary for your architecture, downloaded separately
  from the upstream releases page
- `luci-base` (declared as a dependency)

## Installation

```sh
opkg install luci-app-openflux_1.0.0_all.ipk
```

Then reload LuCI in the browser (`Ctrl+F5`) and open **Services → OpenFlux**.

### Client binary

The package does not ship the client. Download the build matching your
router's CPU from the upstream releases and use one of two layouts:

1. **Direct** — put the executable at `/usr/bin/openflux`:

   ```sh
   chmod +x /usr/bin/openflux
   ```

   Leave *Compressed binary* empty in the UI.

2. **Compressed in flash** — the uncompressed client is ~28 MB, which may not
   fit on a small overlay. Store it gzipped and let it be unpacked to RAM:

   ```sh
   gzip -9 -c /usr/bin/openflux > /root/openflux.gz
   ```

   Set *Client binary* to a non-existent path (e.g. `/usr/bin/openflux`) and
   *Compressed binary* to `/root/openflux.gz`. On start the service unpacks it
   to `/tmp/openflux`; this survives reboots because the archive stays in
   flash.

## Usage

1. **Services → OpenFlux**.
2. Add a profile: name, transport, link/room, SOCKS5 address, encryption key.
3. Pick it in **Active profile** and press **Save & Apply**.
4. The service restarts with that profile and listens on its SOCKS5 port.

Verify from a shell:

```sh
curl --socks5-hostname 127.0.0.1:1081 https://ifconfig.me
```

The exit node's IP should be printed.

### Using it from Mihomo

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

## Build

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

## Layout

```
root/etc/config/openflux                                  UCI defaults
root/etc/init.d/openflux                                  procd service
root/usr/share/luci/menu.d/luci-app-openflux.json         menu entry
root/usr/share/rpcd/acl.d/luci-app-openflux.json          ACL
root/www/luci-static/resources/view/openflux/overview.js  LuCI view
build-ipk.py                                              standalone ipk builder
Makefile                                                  SDK build
```

## Security

- Encryption keys are stored **in plain text** in `/etc/config/openflux`.
  The package sets the file mode to `600` on install, but anyone with root
  access to the router can read them. Do not publish your config.
- The UI shows the key so it can be edited; hide your screen when doing so.
- Prefer HTTPS links and keep the router firmware up to date.

## Notes

- Exactly one profile runs at a time. This is intentional: each client
  process needs ~60–70 MB RSS, which matters on a router.
- The key must match the exit node exactly. Copy it via `cat`, not through a
  terminal that may wrap lines.
- For `cupsonline` transports the room string expires eventually. If rooms
  return 404, recreate them on the exit node and update the profile.
- This is an unofficial UI wrapper, not affiliated with the OpenFlux author.
  OpenFlux itself is distributed under its own license and disclaimer.

## License

MIT — see [LICENSE](LICENSE).
