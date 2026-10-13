# Sweet Cravings by Victoria — Baker order tracking app

A light-pink, Arial-font bakery order tracker with real account creation and login, and persistent orders stored separately for each account in SQLite.

## Start

1. Install Python 3.9 or later.
2. Extract this ZIP file into a folder.
3. Open a terminal in the extracted `bakery-tracker` folder.
4. Run `python server.py` (or `py server.py` on Windows).
5. Open **http://localhost:8765** in your browser. Do **not** open `index.html` directly.
6. The dashboard opens in **Guest mode** automatically. Use **Log in / Create account** whenever you want to register or sign in with your email and password (10+ characters).

No external Python packages are required. Accounts and orders persist in `bakery.sqlite3`, created automatically. Different users have separate order lists. Guest orders are stored in this browser using localStorage and are not automatically moved to an account. Export CSV before clearing browser data or switching devices. Passwords are stored as salted PBKDF2 hashes, not plaintext.

## Important

This is a **local development application**, not a publicly hosted service. Accounts are real in the local SQLite database, but only accessible while the server is running on this computer. For production/public internet use, add HTTPS, CSRF protections, login rate limiting, secure hosting, password recovery, and proper database backups. Keep `bakery.sqlite3` private and back it up regularly. Orders from the old browser-local version are not automatically imported.
