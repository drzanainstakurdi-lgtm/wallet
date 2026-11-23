"""
Gives your EXISTING website users a login in the Flutter app (their data stays the same).

Why is this needed? The website stores passwords in its own table, in a format Supabase Auth
cannot read. So you (the admin) choose an app password for each old user here, once.
Run it on your own computer. The service key never goes into the app.

    pip install httpx python-dotenv
    python tools/link_legacy_users.py

It reads SUPABASE_URL and SUPABASE_SERVICE_KEY from the environment or from a .env file
(you can point it at your Flask project's .env with:  python tools/link_legacy_users.py ../wallet-dana-main/.env).
"""
import getpass
import os
import re
import sys

import httpx
from dotenv import load_dotenv

DOMAIN = "wallet-dana.app"  # must match usernameDomain in lib/config.dart

load_dotenv(sys.argv[1] if len(sys.argv) > 1 else ".env")
URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

r = httpx.get(f"{URL}/rest/v1/users", headers=H, timeout=30,
              params={"select": "id,username,display_name", "auth_id": "is.null", "order": "id"})
r.raise_for_status()
users = r.json()
print(f"{len(users)} website users have no app login yet.\n")

for u in users:
    name = u["username"]
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", name):
        print(f"- {name!r}: skipped (the app only supports a-z, 0-9 . _ - in usernames)")
        continue
    pw = getpass.getpass(f"App password for '{name}' (min 6 chars, Enter = skip): ")
    if not pw:
        continue
    if len(pw) < 6:
        print("  too short, skipped")
        continue
    a = httpx.post(f"{URL}/auth/v1/admin/users", headers=H, timeout=30,
                   json={"email": f"{name}@{DOMAIN}", "password": pw, "email_confirm": True})
    if a.status_code >= 300:
        print("  failed:", a.text)
        continue
    auth_id = a.json()["id"]
    p = httpx.patch(f"{URL}/rest/v1/users", headers=H, timeout=30, params={"id": f"eq.{u['id']}"},
                    json={"auth_id": auth_id})
    print("  linked" if p.status_code < 300 else f"  link failed: {p.text}")
print("\nDone.")
