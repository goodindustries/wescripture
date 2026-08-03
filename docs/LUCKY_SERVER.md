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

## What serving over a network exposed, and what it cost

Localhost hid a payload problem that a real connection made obvious, and fixing
it is what the numbers below measure. Both columns were taken on this box, same
methodology, by checking out each commit in turn.

| | before | after |
|---|---|---|
| Time until scripture is on screen | 3,854 ms | **1,678 ms** |
| Transferred to reach that point | 13.1 MB | **1.4 MB** |
| Tap a verse, cold | 4,899 ms | **219 ms** |
| Tap a verse, warm | 160 ms | 144 ms |

Three changes did it:

1. `verse_discovery.json` (14.5MB) became `library/discovery/<chapter>.json`
   shards, ~10kB each, so opening a verse no longer waits on the whole corpus.
2. The sources corpus (4.3MB) and the full entity records (5.3MB) left the
   blocking boot fetch. Only the small `*_index` name maps stay, which is all a
   chapter needs to linkify.
3. Both bundles warm 250ms after first paint, so the window where a fast tap
   waits for them is small and shrinking it cost nothing.

The remaining ~12MB still transfers, just behind the reading experience rather
than in front of it. Trimming it further means shrinking the entity and source
corpora themselves, which is a data question, not a loading one.
