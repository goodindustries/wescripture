# Dev server on lucky

The reader is served from the **lucky** VM rather than the laptop, so QA and the
reader suite hit a real network instead of localhost.

## Where it runs

| | |
|---|---|
| Host | `lucky` — Ubuntu VM, `192.168.64.3`, user `agent` |
| Reached via | ProxyJump through `lucky-host` (192.168.12.235) |
| Checkout | `~/wescripture` on the VM, cloned from GitHub (depth 1) |
| Server | `python3 -m http.server 8091 --bind 0.0.0.0`, detached with nohup |
| Log | `~/ws-server.log` on the VM |

The VM sits on lucky-host's private 192.168.64.x network, so it is not
reachable from the laptop directly. A tunnel maps it onto the port everything
already points at:

```bash
ssh -F ~/Classified/dinosaur/ssh/ubuntu-agent-config \
    -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -L 127.0.0.1:8091:127.0.0.1:8091 lucky-vm
```

With that up, `http://localhost:8091/library/` is served by lucky and
`./tests/reader/run.sh` needs no changes.

## Refresh it after a push

One connection, everything in it:

```bash
ssh -F ~/Classified/dinosaur/ssh/ubuntu-agent-config lucky-vm '
  cd ~/wescripture && git fetch --quiet origin && git reset --hard --quiet origin/main
  pkill -f "http.server 8091"; sleep 1
  nohup python3 -m http.server 8091 --bind 0.0.0.0 > ~/ws-server.log 2>&1 &
  echo "$(git log --oneline -1)"'
```

## Notes

- **`library/supabase-config.json` is gitignored**, so the clone does not have
  it. Sign-in, notes and the feed are inert there; the feed shows "Feed
  unavailable", which is the state we built for.
- **Bound to the LAN only.** Nothing is tunnelled out. lucky already runs
  cloudflared for `api.meetmaxx.co`; exposing this publicly is a separate call.
- **Use `lucky-vm`, not `lucky`, for commands.** `Host lucky` carries
  `LocalForward 18790` with `ExitOnForwardFailure yes` for the MCP tunnel, so it
  aborts if that port is already taken.
- **Do not open SSH connections in bursts.** `lucky2` (a different machine, a
  Mac) is currently wedged in exactly that state: it accepts TCP and completes
  authentication, then resets every session. Its own config warns about this —
  macOS sshd MaxStartups. It needs Remote Login toggled or a reboot.

## What serving over a network exposed

Localhost hid two things that a real connection makes obvious.

- Tapping a verse takes **~3.1s** to open the pane, because `openVerseDiscovery`
  awaits `verse_discovery.json` — **14.5MB**.
- A single page load pulls **~24MB** of JSON: `verse_discovery.json` 14.5MB,
  `entities/people.json` 2.5MB, `entities/scripture_people.json` 2.0MB,
  `source_toc.json` 1.5MB, `source_links.json` 1.4MB, `source_citations.json`
  1.4MB, `entities/topics.json` 1.3MB.

The design brief asks for reading that "feels instant on a mid-range phone".
Sharding `verse_discovery.json` per chapter — the layout `library/translations/`
already uses — is the obvious fix and belongs in the next round.
