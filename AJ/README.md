# AJ — Team lead & Mac mini hub

You own infrastructure, integration testing, README coordination, and merges to `main`.

| Area | Path |
|------|------|
| Mac mini scripts | `mac-mini/` |
| Connection tests | `scripts/connect-services.sh` |
| Team bus | `README.md` (update Changelog after every push) |
| Your notes | `AJ/notes/` |

## Daily commands
```bash
git pull origin main
./scripts/connect-services.sh          # verify Apify + n8n
cd mac-mini && ./sync-from-github.sh   # after teammate pushes
```
