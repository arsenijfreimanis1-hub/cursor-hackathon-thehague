# Web Automation (Helium)

When the task involves browser automation, scraping, or form filling:

1. Prefer **Helium** (`pip install helium`) over raw Selenium — simpler API:
   ```python
   from helium import start_chrome, go_to, click, write, S
   start_chrome(headless=True)
   go_to("https://example.com")
   write("query", into=S("#search"))
   click("Search")
   ```
2. Fall back to **Playwright** for complex SPAs or when Helium cannot find elements.
3. Always use **headless** mode unless the user explicitly needs to watch.
4. Respect `robots.txt` and rate limits; add delays between requests.
5. Store scraped data as JSON/CSV in the project `data/` dir, not stdout only.
6. Close the browser in a `finally` block.

## Jarvis integration

- William can run automation via `web.automate` tool (Helium wrapper).
- For build slices: put scripts in `scripts/` or `automation/` with a `requirements.txt` entry for `helium`.
- Acceptance: script runs without error and produces expected output file.

## Security

- Never store credentials in source; use env vars (`WEB_LOGIN_USER`, `WEB_LOGIN_PASS`).
- Do not automate login flows for banking or sensitive accounts without explicit user approval.
