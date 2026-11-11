# E-Wallet v2 (Flask + Supabase)

Multi-account wallet (IQD / USD), month and date-range filters, charts, 3 languages.

## Supabase
SQL Editor -> paste `schema.sql` -> Run.
Safe on a fresh project and also when upgrading v1: old entries move into a "Main" IQD account.

## Local (VS Code)
    python -m venv .venv
    .venv\Scripts\activate        (Mac/Linux: source .venv/bin/activate)
    pip install -r requirements.txt
    copy .env.example .env        (fill in the values)
    python app.py                 -> http://localhost:5000

## Deploy (Render.com)
Build: `pip install -r requirements.txt`   Start: `gunicorn app:app`
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, SECRET_KEY, PRODUCTION=1

Keep the service key on the server only. Never commit `.env`.

## Install on iPhone (Add to Home Screen)
Open the https link in **Safari** -> a banner explains the steps -> Share -> Add to Home Screen.
Name on the home screen: جزدانەکەم. Icons live in `static/icons` (regenerate with `python make_icons.py`).
Notes: the installed app keeps its own login (log in once inside it); PWA install needs https (Render gives it).

## Speed tips
- Choose the Render region closest to your Supabase project region (biggest single speed win).
- Render free sleeps after ~15 min idle: ping `https://YOUR-APP/health` every 5 min with a free monitor (UptimeRobot) or use a paid instance.
- Re-run `schema.sql` after updating (the dashboard function was upgraded to one call).

## v3 layout
Bottom floating tab bar: Home / Entries / (+) / Charts / Settings.
Settings: language, accounts, clear income or expenses (with confirmation), delete account, print, reset everything.
Print: account statement, income only, expenses only, grand total of all accounts (uses the Filter period).
**Re-run `schema.sql`** after updating (adds entry counts to the dashboard and the `report` function).

## v4: lawyer edition
- Light cream theme.
- Bottom bar: Home / Income / (+) / Expenses / Cases. Charts and Settings are in the top-right icons.
- Income and Expenses are separate pages. Settings is split into separate pages (language, accounts, clear data, office, danger).
- Cases: every legal matter has client, case number, court, agreed fee, status. Record money received and case expenses; print a case statement with the case name as the title.
- Print opens directly (auto print) and shows the office/lawyer name from Settings > Office. Printing was removed from Settings; it lives on Home, Income, Expenses and each Case.
- **Re-run `schema.sql`** (adds the case columns, `case_view`, and updates `dashboard` and `report`).

## v5
- Print: no repeated summary on top; lists first, one totals block at the bottom.
- Desktop (wide screens): sidebar on the side, two-column pages. Phone layout unchanged.
- Removed the "danger zone" (reset everything).
- Faster: stylesheet is cached by the browser (`/app.css`), pages are gzip-compressed, Chart.js loads only when the Charts page opens.
- No database change in this version (no need to re-run schema.sql).

## v6 features
- Edit any entry (pencil icon), search inside Income/Expenses.
- Monthly budget per account with progress bar and daily allowance.
- Recurring entries (salary, rent...) added automatically every month.
- Export to CSV (Excel/Numbers): one account + period, or everything as a backup.
- Change password.
- Cases: next hearing date, with a reminder card on Home for hearings in the next 7 days.
- **Re-run `schema.sql`** (new columns, `recurring` table, `run_recurring` function).

## Sharing, transfers and more (current build)
- Share a legal case (Cases > open the case > Share) or a personal account (Settings > Accounts) with another user by username.
  The other person gets an invitation on Home and must accept. Roles: view only, or can add entries. Only the owner can edit/delete the case or change sharing; anyone invited can leave.
- Transfer between two of your accounts (also IQD <-> USD with the amount received entered by you).
- Edit entries, search, CSV export/backup, monthly budget, recurring entries, change password, court hearing reminders.
- **Re-run `schema.sql`** after every update; it is safe to run again.

## v9
- Settings: icons on every row, a profile card at the top, separate Profile page (photo, display name, password, logout) and Print page (logo, office name, phone).
- Print and receipts show logo, office name and phone at the top.
- New case: "Start date" (defaults to today) plus the optional "Next hearing" date.
- Sharing: typing a username shows the person's photo and display name; the Share button stays disabled until the person is found.
- **Re-run `schema.sql`** (new columns: display_name, phone, avatar, logo, started).

## v10: case types and Google sign-in
- Cases can be: court case, property (house) sale/purchase, car sale/purchase, other matter. Each type has its own labels
  (deed number, address, plate number, car model...), the other party, the deal value, and a type filter in the list.
- Print: the totals row now appears only once, at the end of each table.
- **Google sign-in**: the button is on the login and register pages.
  1. Google Cloud Console > APIs & Services > Credentials > OAuth client ID (Web application).
  2. Authorized redirect URIs: `https://YOUR-DOMAIN/auth/google/callback` (add every domain you use, e.g. Vercel and Render, and `http://localhost:5000/auth/google/callback` for local tests).
  3. On your host (Vercel / Render) set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` and **redeploy** (changing variables does not apply until a new deploy).
  4. Open `https://YOUR-DOMAIN/auth/google/info`: it shows whether the keys are seen and the exact redirect URI to paste into Google.
  Optional: `PUBLIC_URL=https://YOUR-DOMAIN` forces the address used in the redirect.
- Google sign-in does not work inside an embedded WebView (the Capacitor iPhone app): Google blocks it. Use Safari / the home-screen web app, or ask for the in-app browser setup.
- **Re-run `schema.sql`** (new columns: case_type, party, price, google_id, email, google_only).

## v11: printing that works everywhere
- Print pages (reports and receipts) now never fail with "Internal Server Error" when the database has not been upgraded yet
  (before, a missing `phone`/`logo` column broke every print). Still re-run `schema.sql` to get logo and phone on the letterhead.
- **Print** button: opens the print dialog in a browser; inside the iPhone app (Capacitor) or the home-screen app, where the
  print dialog does not exist, it creates a PDF and opens the share sheet (Print / Save to Files / WhatsApp...).
- **PDF** button: creates an A4 PDF (pages never cut a table row in half) and shares or downloads it.
- The PDF is built in the browser (html2canvas + jsPDF loaded from jsDelivr), so the phone needs internet for that step.
