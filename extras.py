# -*- coding: utf-8 -*-
# Add-on for app.py: profile, Google login, delete account, faster login/images, working print + CSV.
import os, re, io, csv, time, uuid, secrets
from urllib.parse import urlencode
from flask import request, session, redirect, url_for, render_template_string, abort, Response
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
import httpx

G = {}
GID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GSEC = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
PBKDF = "pbkdf2:sha256:150000"      # scrypt is very slow on Render's free CPU
PROF, SIGN = {}, {}

NEW = {  # key: (ku, ar, en)
 "profile": ("پرۆفایل", "الملف الشخصي", "Profile"),
 "p_name": ("ناوی تەواو", "الاسم الكامل", "Full name"),
 "p_phone": ("ژمارەی تەلەفۆن", "رقم الهاتف", "Phone number"),
 "p_email": ("ئیمەیڵ", "البريد الإلكتروني", "Email"),
 "p_id": ("ئایدی (ناوی بەکارهێنەر)", "المعرّف (اسم المستخدم)", "ID (username)"),
 "p_rm_photo": ("سڕینەوەی وێنە", "حذف الصورة", "Remove photo"),
 "p_first": ("پرۆفایلەکەت تەواو بکە", "أكمل ملفك الشخصي", "Complete your profile"),
 "p_skip": ("دواتر", "لاحقاً", "Later"),
 "p_pw": ("گۆڕینی وشەی نهێنی", "تغيير كلمة المرور", "Change password"),
 "p_pw_set": ("دانانی وشەی نهێنی", "تعيين كلمة مرور", "Set a password"),
 "p_pw_old": ("وشەی نهێنی ئێستا", "كلمة المرور الحالية", "Current password"),
 "p_pw_new": ("وشەی نهێنی نوێ", "كلمة المرور الجديدة", "New password"),
 "g_btn": ("بەردەوامبوون بە گووگڵ", "المتابعة عبر Google", "Continue with Google"),
 "g_link": ("بەستنەوەی گووگڵ", "ربط حساب Google", "Link Google account"),
 "g_linked": ("گووگڵ بەستراوەتەوە", "تم ربط Google", "Google linked"),
 "g_fail": ("چوونەژوورەوە بە گووگڵ سەرکەوتوو نەبوو", "فشل الدخول عبر Google", "Google sign-in failed"),
 "g_used": ("ئەم گووگڵە بۆ بەکارهێنەرێکی تر بەکارهاتووە", "حساب Google مرتبط بمستخدم آخر", "This Google account is linked to another user"),
 "e_pw": ("وشەی نهێنی ئێستا هەڵەیە", "كلمة المرور الحالية خاطئة", "Current password is wrong"),
 "e_photo": ("وێنەکە زۆر گەورەیە یان جۆرەکەی هەڵەیە", "الصورة كبيرة جداً أو غير مدعومة", "Photo too big or unsupported"),
 "e_email": ("ئیمەیڵ هەڵەیە یان پێشتر بەکارهاتووە", "البريد غير صالح أو مستخدم", "Email invalid or already used"),
 "del_me": ("سڕینەوەی هەژمارەکەم بۆ هەمیشە", "حذف حسابي نهائياً", "Delete my account permanently"),
 "del_me_desc": ("هەموو هەژمارەکان، تۆمارەکان و وێنەکانت دەسڕدرێنەوە و ناگەڕێتەوە. بۆ دڵنیابوون ناوی بەکارهێنەرەکەت بنووسە:",
                 "سيتم حذف كل الحسابات والسجلات والصور ولا يمكن التراجع. للتأكيد اكتب اسم المستخدم:",
                 "All accounts, entries and photos will be deleted forever. To confirm, type your username:"),
 "del_bad": ("ناوی بەکارهێنەر هەڵەیە", "اسم المستخدم غير صحيح", "Username does not match"),
 "csv": ("داگرتن CSV", "تنزيل CSV", "Download CSV"),
 "print_ios": ("ئەگەر پرینت لە بەرنامەکەدا کارناکات، CSV دابگرە یان لاپەڕەکە لە Safari بکەرەوە.",
               "إذا لم تعمل الطباعة داخل التطبيق، نزّل CSV أو افتح الصفحة في Safari.",
               "If printing does not work inside the app, download the CSV or open this page in Safari."),
}

CSS_EXTRA = """.av{width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,var(--acc),#8E6BBE);display:grid;place-items:center;font-weight:800;overflow:hidden;flex:none;border:1px solid var(--edge);color:#fff}
.av img{width:100%;height:100%;object-fit:cover}.av.big{width:92px;height:92px;font-size:36px}
.who{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--tx)}
.avwrap{display:flex;gap:16px;align-items:center;margin-bottom:6px}
a.btn{display:block;text-align:center;text-decoration:none}.gbtn{margin-top:12px}
"""

PROFILE = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{t('profile')}}</title>{{css|safe}}</head>
<body><div class="blob"></div><div class="wrap">
<div class="top"><a class="pill" href="/">&larr; {{t('back')}}</a><h2 class="ttl">{{t('profile')}}</h2></div>
{% if first %}<div class="glass sec"><b>{{t('p_first')}}</b></div>{% endif %}
{% if m %}<div class="glass sec" style="border-color:{{'var(--in)' if m[0]=='ok' else 'var(--ex)'}}">{{t(m[1])}}</div>{% endif %}
<form class="glass sec" id="pf" method="post" action="/profile" enctype="multipart/form-data">
{% if first %}<input type="hidden" name="first" value="1">{% endif %}
<div class="avwrap"><div class="av big" id="avp">{% if p.avatar %}<img src="/img/{{p.avatar}}" alt="">{% else %}{{(p.full_name or p.username or '?')[:1]|upper}}{% endif %}</div>
<div><input type="file" name="avatar" id="avf" accept="image/*"><label class="chk"><input type="checkbox" name="rm_avatar" value="1"><span>{{t('p_rm_photo')}}</span></label></div></div>
<label>{{t('p_name')}}</label><input name="full_name" value="{{p.full_name or ''}}" maxlength="60" autocomplete="name">
<label>{{t('p_phone')}}</label><input name="phone" value="{{p.phone or ''}}" inputmode="tel" maxlength="20" autocomplete="tel" dir="ltr">
<label>{{t('p_id')}}</label><input name="username" value="{{p.username}}" required maxlength="30" autocapitalize="none" dir="ltr">
<label>{{t('p_email')}}</label><input name="email" type="email" value="{{p.email or ''}}" {{'readonly' if p.google_id}} dir="ltr">
<button class="btn">{{t('save')}}</button>
{% if first %}<a class="btn ghost" href="/profile/skip">{{t('p_skip')}}</a>{% endif %}
</form>
{% if p.google_id %}<div class="glass sec"><h3>Google</h3><b>&#10003; {{t('g_linked')}}</b><br><small dir="ltr">{{p.email}}</small></div>
{% elif gid and 'WalletApp' not in request.headers.get('User-Agent','') %}<div class="glass sec"><h3>Google</h3><a class="btn ghost" href="/auth/google?link=1">G &nbsp;{{t('g_link')}}</a></div>{% endif %}
<form class="glass sec" method="post" action="/profile/password"><h3>{{t('p_pw') if p.has_pw!=False else t('p_pw_set')}}</h3>
{% if p.has_pw!=False %}<label>{{t('p_pw_old')}}</label><input type="password" name="old" autocomplete="current-password" required>{% endif %}
<label>{{t('p_pw_new')}}</label><input type="password" name="new" minlength="4" autocomplete="new-password" required>
<button class="btn">{{t('save')}}</button></form>
<form class="glass sec danger" method="post" action="/account/delete" onsubmit="return confirm('{{t('confirm_check')}}')"><h3>{{t('del_me')}}</h3><p>{{t('del_me_desc')}}</p>
<input name="confirm_user" required autocapitalize="none" dir="ltr" placeholder="{{p.username}}"><button class="btn red">{{t('yes_delete')}}</button></form>
<a class="mini red" href="/logout">{{t('logout')}}</a>
</div>
<script>
const f=document.getElementById('pf'),av=document.getElementById('avf');
function shrink(file){return new Promise(res=>{const im=new Image(),u=URL.createObjectURL(file);
 im.onload=()=>{const k=Math.min(1,400/Math.max(im.width,im.height)),c=document.createElement('canvas');c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);
  c.getContext('2d').drawImage(im,0,0,c.width,c.height);URL.revokeObjectURL(u);c.toBlob(b=>res(b),'image/jpeg',0.8)};im.onerror=()=>res(null);im.src=u})}
av.onchange=()=>{const x=av.files[0];if(x)document.getElementById('avp').innerHTML='<img src="'+URL.createObjectURL(x)+'">'};
f.onsubmit=async e=>{const x=av.files[0];if(!x)return;e.preventDefault();const fd=new FormData(f),b=await shrink(x);if(b)fd.set('avatar',b,'a.jpg');
 const r=await fetch('/profile',{method:'POST',body:fd});location.href=r.url};
</script></body></html>"""


def x_fmt(v, cur, L="en"):
    try: v = float(v or 0)
    except (TypeError, ValueError): v = 0.0
    r = round(v, 0 if cur == "IQD" else 2)
    s = f"{abs(r):,.0f}" if cur == "IQD" else f"{abs(r):,.2f}"
    sign = "-" if r < 0 else ""
    if cur == "USD": return f"{sign}${s}"
    return f"{sign}{s} " + ("IQD" if L == "en" else "د.ع")


def x_prof(uid, fresh=False):
    c = PROF.get(uid)
    if c and not fresh and c[1] > time.time(): return c[0]
    try:
        r = sb.table("users").select("id,username,full_name,phone,email,google_id,avatar,has_pw").eq("id", uid).limit(1).execute().data
        row = r[0] if r else None          # None = this user no longer exists in the database
    except Exception as ex:
        app.logger.error("profile read failed (did you run migration.sql?): %s", ex); row = {}
    PROF[uid] = (row, time.time() + 90)
    return row


def x_gate():
    if "uid" not in session or request.endpoint in (None, "static", "health", "sw", "logout"): return
    p = x_prof(session["uid"])
    if p is None:                          # stale cookie: user was deleted / database was reset
        lg = session.get("lang"); session.clear()
        if lg: session["lang"] = lg
        return redirect(url_for("login"))
    if request.method == "GET" and request.endpoint == "index" and not session.get("skip_prof"):
        if p and not (p.get("full_name") or "").strip():
            return redirect(url_for("x_profile", first=1))


def x_after(resp):
    if request.endpoint in ("login", "register") and request.method == "GET": session.pop("gerr", None)
    return resp


def x_skip():
    session["skip_prof"] = 1
    return redirect(url_for("index"))


def x_save_avatar(uid, fl):
    ext = os.path.splitext(fl.filename or "")[1].lower()
    data = fl.read()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp") or len(data) > 4 * 1024 * 1024: return None, "e_photo"
    path = f"{uid}/av_{uuid.uuid4().hex}{ext}"
    sb.storage.from_(BUCKET).upload(path, data, {"content-type": fl.mimetype or "image/jpeg"})
    return path, None


def x_profile():
    uid = session["uid"]
    if request.method == "POST":
        f, err = request.form, None
        p = x_prof(uid, True) or {}
        upd = {"full_name": f.get("full_name", "").strip()[:60] or None,
               "phone": re.sub(r"[^\d+ ]", "", f.get("phone", "").translate(DIG))[:20].strip() or None}
        un = f.get("username", "").strip().lower()
        if un and un != p.get("username"):
            if len(un) < 3 or len(un) > 30 or re.search(r"\s", un): err = "short"
            elif find_user(un): err = "taken"
            else: upd["username"] = un
        if not p.get("google_id"):
            em = f.get("email", "").strip().lower()[:120]
            if em and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em): err = err or "e_email"
            else: upd["email"] = em or None
        old_av, fl = p.get("avatar"), request.files.get("avatar")
        if not err and f.get("rm_avatar"): upd["avatar"] = None
        if not err and fl and fl.filename:
            try:
                new, err = x_save_avatar(uid, fl)
                if new: upd["avatar"] = new
            except Exception as ex:
                app.logger.error("avatar upload: %s", ex); err = "err"
        if not err:
            try:
                sb.table("users").update(upd, returning=MIN).eq("id", uid).execute()
                if "username" in upd: session["user"] = upd["username"]
                if "avatar" in upd and old_av: drop_imgs([old_av])
            except Exception as ex:
                app.logger.error("profile save: %s", ex); err = "e_email" if "email" in str(ex) else "err"
        session["pmsg"] = ("err", err) if err else ("ok", "saved")
        PROF.pop(uid, None)
        if not err and f.get("first"): return redirect(url_for("index"))
        return redirect(url_for("x_profile"))
    p = x_prof(uid, True) or {"username": session["user"]}
    return render_template_string(PROFILE, p=p, m=session.pop("pmsg", None), first=request.args.get("first"),
                                  css=G["CSS"], gid=bool(GID))


def x_password():
    uid, f = session["uid"], request.form
    try: row = sb.table("users").select("pw,has_pw").eq("id", uid).limit(1).execute().data[0]
    except Exception as ex:
        app.logger.error("pw read: %s", ex); session["pmsg"] = ("err", "err"); return redirect(url_for("x_profile"))
    new = f.get("new", "")
    if len(new) < 4: msg = ("err", "short")
    elif row.get("has_pw", True) and not G["check_password_hash"](row["pw"], f.get("old", "")): msg = ("err", "e_pw")
    else:
        sb.table("users").update({"pw": G["generate_password_hash"](new), "has_pw": True}, returning=MIN).eq("id", uid).execute()
        msg = ("ok", "saved")
    session["pmsg"] = msg
    PROF.pop(uid, None)
    return redirect(url_for("x_profile"))


def x_delete_me():
    uid = session["uid"]
    p = x_prof(uid, True) or {}
    if request.form.get("confirm_user", "").strip().lower() != (p.get("username") or session.get("user")):
        session["pmsg"] = ("err", "del_bad"); return redirect(url_for("x_profile"))
    imgs = [r["img"] for r in sb.table("tx").select("img").eq("user_id", uid).execute().data if r.get("img")]
    if p.get("avatar"): imgs.append(p["avatar"])
    sb.table("users").delete().eq("id", uid).execute()      # accounts + entries cascade
    drop_imgs(imgs); PROF.pop(uid, None)
    lg = session.get("lang"); session.clear()
    if lg: session["lang"] = lg
    return redirect(url_for("login"))


# ---------------------------------------------------------------- Google
def x_g_start():
    if not GID: abort(404)
    session["gst"] = uuid.uuid4().hex
    session["gmode"] = "link" if (request.args.get("link") and "uid" in session) else "login"
    q = urlencode(dict(client_id=GID, redirect_uri=url_for("x_g_cb", _external=True), response_type="code",
                       scope="openid email profile", state=session["gst"], prompt="select_account"))
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + q)


def x_g_cb():
    mode, st = session.pop("gmode", "login"), session.pop("gst", None)
    def fail(key="g_fail"):
        if mode == "link": session["pmsg"] = ("err", key); return redirect(url_for("x_profile"))
        session["gerr"] = key; return redirect(url_for("login"))
    if not GID or not st or request.args.get("state") != st or "code" not in request.args: return fail()
    try:
        tk = httpx.post("https://oauth2.googleapis.com/token", timeout=15, data=dict(
            code=request.args["code"], client_id=GID, client_secret=GSEC,
            redirect_uri=url_for("x_g_cb", _external=True), grant_type="authorization_code"))
        tk.raise_for_status()
        u = httpx.get("https://openidconnect.googleapis.com/v1/userinfo", timeout=15,
                      headers={"Authorization": "Bearer " + tk.json()["access_token"]}).json()
    except Exception as ex:
        app.logger.error("google token/userinfo: %s", ex); return fail()
    gid = str(u.get("sub") or "")
    email = (u.get("email") or "").lower() if u.get("email_verified") else ""
    if not gid: return fail()
    try:
        found = sb.table("users").select("id,username").eq("google_id", gid).limit(1).execute().data
        if mode == "link" and "uid" in session:
            uid = session["uid"]
            if found and found[0]["id"] != uid: return fail("g_used")
            upd = {"google_id": gid}
            if email and not (x_prof(uid, True) or {}).get("email"): upd["email"] = email
            sb.table("users").update(upd, returning=MIN).eq("id", uid).execute()
            PROF.pop(uid, None); session["pmsg"] = ("ok", "g_linked")
            return redirect(url_for("x_profile"))
        row = found[0] if found else None
        if not row:
            base = re.sub(r"[^a-z0-9_.]", "", email.split("@")[0])[:20] or "user"
            if len(base) < 3: base += "user"
            un = base
            while find_user(un): un = f"{base}{secrets.randbelow(9999)}"
            lg = session.get("lang")
            row = sb.table("users").insert({"username": un, "pw": G["generate_password_hash"](secrets.token_urlsafe(16)),
                "has_pw": False, "google_id": gid, "email": email or None,
                "full_name": (u.get("name") or "")[:60] or None}).execute().data[0]
            sb.table("accounts").insert({"user_id": row["id"], "name": T[lg if lg in T else "ku"]["acc_default"],
                                         "currency": "IQD"}, returning=MIN).execute()
            try:
                pic = u.get("picture")
                r = httpx.get(pic, timeout=6) if pic else None
                if r is not None and r.status_code == 200 and len(r.content) < 2 * 1024 * 1024:
                    path = f"{row['id']}/av_{uuid.uuid4().hex}.jpg"
                    sb.storage.from_(BUCKET).upload(path, r.content, {"content-type": r.headers.get("content-type", "image/jpeg")})
                    sb.table("users").update({"avatar": path}, returning=MIN).eq("id", row["id"]).execute()
            except Exception as ex:
                app.logger.warning("google avatar: %s", ex)
    except Exception as ex:
        app.logger.error("google login: %s", ex); return fail()
    lg = session.get("lang"); session.clear(); session.permanent = True
    session.update(uid=row["id"], user=row["username"])
    if lg: session["lang"] = lg
    return redirect(url_for("index"))


# ---------------------------------------------------------------- images (cached signed links = much faster)
def x_img(owner, name):
    if owner != session["uid"]: abort(404)
    p = f"{owner}/{name}"
    c = SIGN.get(p)
    if not c or c[1] < time.time():
        r = sb.storage.from_(BUCKET).create_signed_url(p, 3600)
        url = r.get("signedURL") or r.get("signedUrl")
        if not url: abort(404)
        SIGN[p] = c = (url, time.time() + 3000)
    resp = redirect(c[0]); resp.headers["Cache-Control"] = "private, max-age=600"
    return resp


# ---------------------------------------------------------------- print + CSV
def x_report(uid, s, e):
    try:
        rep = sb.rpc("report", {"p_user": uid, "p_from": s.isoformat(), "p_to": e.isoformat()}).execute().data
        if not isinstance(rep, list): raise ValueError("report() returned %r" % type(rep))
    except Exception as ex:
        app.logger.warning("report rpc failed, computing in python: %s", ex)
        accs = sb.table("accounts").select("id,name,currency,opening").eq("user_id", uid).order("id").execute().data
        rows, i = [], 0
        while True:
            part = sb.table("tx").select("account_id,type,amount,date").eq("user_id", uid).range(i, i + 999).execute().data
            rows += part; i += 1000
            if len(part) < 1000: break
        a0, a1, rep = s.isoformat(), e.isoformat(), []
        for a in accs:
            inc = exp = net = 0.0
            for r in rows:
                if r["account_id"] != a["id"]: continue
                v = float(r["amount"]); net += v if r["type"] == "income" else -v
                if a0 <= r["date"] <= a1:
                    if r["type"] == "income": inc += v
                    else: exp += v
            o = float(a.get("opening") or 0)
            rep.append(dict(id=a["id"], name=a["name"], currency=a["currency"], opening=o, inc=inc, exp=exp, bal=o + net))
    for a in rep:
        for k in ("inc", "exp", "bal", "opening"): a[k] = float(a.get(k) or 0)
    return rep


def x_print():
    uid, L = session["uid"], lang()
    kind = request.args.get("kind", "statement")
    if kind not in ("statement", "income", "expense", "grand"): kind = "statement"
    s, e, key = get_period()
    rep = x_report(uid, s, e)
    plabel = T[L]["all_time"] if key == "all" else (s.isoformat() if s == e else f"{s.isoformat()} \u2192 {e.isoformat()}")
    now = (datetime.now(TZ) if TZ else datetime.now()).strftime("%Y-%m-%d %H:%M")
    p = x_prof(uid) or {}
    base = dict(kind=kind, rep=rep, plabel=plabel, now=now, user=p.get("full_name") or session["user"], inc=[], exp=[],
                tots={}, acc=None, cur="IQD", csv_url="/export.csv?" + request.query_string.decode())
    if kind == "grand":
        for a in rep:
            c = base["tots"].setdefault(a["currency"], dict(inc=0, exp=0, bal=0))
            c["inc"] += a["inc"]; c["exp"] += a["exp"]; c["bal"] += a["bal"]
        return render_template_string(G["PRINT"], **base)
    try: aid = int(request.args.get("acc") or session.get("acc") or 0)
    except ValueError: aid = 0
    acc = next((a for a in rep if a["id"] == aid), rep[0] if rep else None)
    if not acc: abort(404)
    q = (sb.table("tx").select("id,type,amount,label,note,date").eq("user_id", uid).eq("account_id", acc["id"])
         .gte("date", s.isoformat()).lte("date", e.isoformat()))
    if kind in ("income", "expense"): q = q.eq("type", kind)
    rows = q.order("date").order("id").limit(5000).execute().data
    for r in rows: r["amount"] = float(r["amount"])
    base.update(acc=acc, cur=acc["currency"], inc=[r for r in rows if r["type"] == "income"],
                exp=[r for r in rows if r["type"] == "expense"])
    return render_template_string(G["PRINT"], **base)


def x_csv():
    uid = session["uid"]
    s, e, key = get_period()
    kind = request.args.get("kind", "statement")
    try: aid = int(request.args.get("acc") or session.get("acc") or 0)
    except ValueError: aid = 0
    names = {a["id"]: (a["name"], a["currency"]) for a in sb.table("accounts").select("id,name,currency").eq("user_id", uid).execute().data}
    q = (sb.table("tx").select("date,type,amount,label,note,account_id").eq("user_id", uid)
         .gte("date", s.isoformat()).lte("date", e.isoformat()))
    if kind != "grand": q = q.eq("account_id", aid)
    if kind in ("income", "expense"): q = q.eq("type", kind)
    rows = q.order("date").order("id").limit(5000).execute().data
    safe = lambda x: ("'" + x) if x[:1] in ("=", "+", "-", "@") else x
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["date", "type", "account", "currency", "amount", "label", "note"])
    for r in rows:
        n, c = names.get(r["account_id"], ("", ""))
        w.writerow([r["date"], r["type"], safe(n), c, r["amount"], safe(r.get("label") or ""), safe(r.get("note") or "")])
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=wallet.csv"})


# ---------------------------------------------------------------- cases: many kinds (court, property, vehicle, company ...)
CTYPES = ("court", "property", "vehicle", "company", "other")
CT_T = {  # type name (ku, ar, en)
 "court": ("دادگا", "محكمة", "Court"),
 "property": ("خانوو و زەوی", "عقار وأراضي", "Property"),
 "vehicle": ("سەیارە", "مركبة", "Vehicle"),
 "company": ("کاروباری کۆمپانیا", "أعمال شركة", "Company"),
 "other": ("تر", "أخرى", "Other"),
}
_SELL = ("فرۆشیار / خاوەن", "البائع / المالك", "Seller / owner")
_BUY = ("کڕیار", "المشتري", "Buyer")
LB = {  # per type: (client label, party label, subject label), each (ku, ar, en)
 "court": (("ناوی کڕیار (موەکیل)", "اسم الموكّل", "Client name"), ("لایەنی بەرانبەر", "الطرف الآخر", "Opposing party"),
           ("بابەتی دۆسیە", "موضوع القضية", "Case subject")),
 "property": (_SELL, _BUY, ("ناونیشان / ژمارەی پارچە", "العنوان / رقم القطعة", "Address / plot number")),
 "vehicle": (_SELL, _BUY, ("جۆر و ژمارەی پلاک", "النوع ورقم اللوحة", "Model and plate number")),
 "company": (("کۆمپانیا / کڕیار", "الشركة / العميل", "Company / client"),
             ("لایەنی تر / هاوبەش", "الطرف الآخر / الشريك", "Other party / partner"),
             ("جۆری کار", "نوع العمل", "Type of work")),
 "other": (("کڕیار", "العميل", "Client"), ("لایەنی تر", "الطرف الآخر", "Other party"), ("بابەت", "الموضوع", "Subject")),
}
EXTRA_T = {
 "case_no2": ("ژمارە / ڕیفرێنس", "الرقم / المرجع", "Number / reference"),
 "court2": ("شوێن / دەزگا", "الجهة / المكان", "Office / place"),
 "fee2": ("بڕی ڕێککەوتوو (نرخ / کۆمیسیۆن)", "المبلغ المتفق عليه (السعر / العمولة)", "Agreed amount (price / commission)"),
 "due": ("بەرواری کۆتایی / وادە", "تاريخ الاستحقاق", "Due date"),
 "memo": ("تێبینی دۆسیە", "ملاحظات", "Case notes"),
 "search": ("گەڕان...", "بحث...", "Search..."),
 "cases_t": ("دۆسیە و مامەڵەکان", "القضايا والمعاملات", "Cases and deals"),
}

def x_case_fields():
    f = request.form
    ct = f.get("case_type", "court")
    if ct not in CTYPES: ct = "other"
    due = f.get("due", "").strip()
    try: datetime.strptime(due, "%Y-%m-%d")
    except ValueError: due = None
    return {"name": f.get("name", "").strip()[:80], "client": f.get("client", "").strip()[:80],
            "case_no": f.get("case_no", "").strip()[:40], "court": f.get("court", "").strip()[:80],
            "fee": num(f.get("fee")), "case_type": ct, "subject": f.get("subject", "").strip()[:120],
            "party": f.get("party", "").strip()[:80], "memo": f.get("memo", "").strip()[:1000], "due": due}

SEL_HOME = """<input type="hidden" name="case_type" id="ctype" value="court"><div class="chips" id="ctsel">{% for k in ['court','property','vehicle','company','other'] %}<button type="button" class="pill {{'on' if k=='court'}}" data-sel="{{k}}" onclick="setCT('{{k}}')">{{t('ct_'+k)}}</button>{% endfor %}</div>"""
SEL_CASE = """{% set ct0 = c.case_type or 'court' %}<input type="hidden" name="case_type" id="ctype" value="{{ct0}}"><div class="chips" id="ctsel">{% for k in ['court','property','vehicle','company','other'] %}<button type="button" class="pill {{'on' if k==ct0}}" data-sel="{{k}}" onclick="setCT('{{k}}')">{{t('ct_'+k)}}</button>{% endfor %}</div>"""
JS_CT = """function setCT(t){$('ctype').value=t;document.querySelectorAll('#ctsel .pill').forEach(p=>p.classList.toggle('on',p.dataset.sel===t));
 $('l-client').textContent=TX['lb_'+t+'_client'];$('l-party').textContent=TX['lb_'+t+'_party'];$('l-subject').textContent=TX['lb_'+t+'_subject'];
 $('l-no').textContent=t==='court'?TX.case_no:TX.case_no2;$('l-court').textContent=t==='court'?TX.court:TX.court2;$('l-fee').textContent=t==='court'?TX.fee:TX.fee2}
"""
JS_FILTER = """let CFs='all',CFt='all';
function applyCF(){const q=($('csearch')?$('csearch').value:'').trim().toLowerCase();
 document.querySelectorAll('#caselist .cc').forEach(e=>e.style.display=((CFs==='all'||e.dataset.st===CFs)&&(CFt==='all'||e.dataset.ct===CFt)&&(!q||e.textContent.toLowerCase().indexOf(q)>-1))?'':'none');
 document.querySelectorAll('#cfilter .pill').forEach(p=>p.classList.toggle('on',p.dataset.f===CFs));
 document.querySelectorAll('#tfilter .pill').forEach(p=>p.classList.toggle('on',p.dataset.t===CFt))}
function filterCases(st){CFs=st;applyCF()}
function filterType(t){CFt=t;applyCF()}
"""
TFILTER = """<div class="chips" id="tfilter"><button class="pill on" data-t="all" onclick="filterType('all')">{{t('all')}}</button>{% for k in ['court','property','vehicle','company','other'] %}<button class="pill" data-t="{{k}}" onclick="filterType('{{k}}')">{{t('ct_'+k)}}</button>{% endfor %}</div><input id="csearch" oninput="applyCF()" placeholder="{{t('search')}}" autocomplete="off" style="margin-bottom:12px">"""

def x_cases_patch():
    for i, lg in enumerate(("ku", "ar", "en")):
        for t, v in CT_T.items(): T[lg]["ct_" + t] = v[i]
        for t, (c, p, s) in LB.items():
            T[lg]["lb_%s_client" % t], T[lg]["lb_%s_party" % t], T[lg]["lb_%s_subject" % t] = c[i], p[i], s[i]
        for k, v in EXTRA_T.items(): T[lg][k] = v[i]
    g = G
    g["case_fields"] = x_case_fields
    P = x_patch
    # --- home: new-case form, type chips, search, cards
    P("HOME", """<label>{{t('case_name')}}</label><input name="name" required maxlength="80" autocomplete="off">""",
      SEL_HOME + """<label>{{t('case_name')}}</label><input name="name" required maxlength="80" autocomplete="off">""")
    P("HOME", """<label>{{t('client')}}</label><input name="client" maxlength="80" autocomplete="off">""",
      """<label id="l-client">{{t('lb_court_client')}}</label><input name="client" maxlength="80" autocomplete="off"><label id="l-party">{{t('lb_court_party')}}</label><input name="party" maxlength="80" autocomplete="off"><label id="l-subject">{{t('lb_court_subject')}}</label><input name="subject" maxlength="120" autocomplete="off">""")
    P("HOME", """<label>{{t('case_no')}}</label><input name="case_no" maxlength="40" autocomplete="off">""",
      """<label id="l-no">{{t('case_no')}}</label><input name="case_no" maxlength="40" autocomplete="off">""")
    P("HOME", """<label>{{t('court')}}</label><input name="court" maxlength="80" autocomplete="off">""",
      """<label id="l-court">{{t('court')}}</label><input name="court" maxlength="80" autocomplete="off">""")
    P("HOME", """<label>{{t('fee')}}</label><input name="fee" inputmode="decimal" placeholder="0" autocomplete="off">""",
      """<label id="l-fee">{{t('fee')}}</label><input name="fee" inputmode="decimal" placeholder="0" autocomplete="off"><label>{{t('due')}}</label><input type="date" name="due"><label>{{t('memo')}}</label><textarea name="memo" rows="2" maxlength="1000"></textarea>""")
    P("HOME", """<button class="pill" data-f="closed" onclick="filterCases('closed')">{{t('status_closed')}}</button></div>""",
      """<button class="pill" data-f="closed" onclick="filterCases('closed')">{{t('status_closed')}}</button></div>""" + TFILTER)
    P("HOME", """<a class="glass cc" data-st="{{c.status}}" href="/case/{{c.id}}">""",
      """<a class="glass cc" data-st="{{c.status}}" data-ct="{{c.case_type or 'court'}}" href="/case/{{c.id}}">""")
    P("HOME", """<small>{{c.client}}{% if c.case_no %} &middot; {{c.case_no}}{% endif %}</small>""",
      """<small>{{t('ct_'+(c.case_type or 'court'))}}{% if c.client %} &middot; {{c.client}}{% endif %}{% if c.subject %} &middot; {{c.subject}}{% endif %}{% if c.case_no %} &middot; {{c.case_no}}{% endif %}{% if c.due %} &middot; {{c.due}}{% endif %}</small>""")
    P("HOME", """function setCaseCur(c){$('ccur').value=c;['IQD','USD'].forEach(k=>$('cc-'+k).classList.toggle('on',k===c))}""",
      """function setCaseCur(c){$('ccur').value=c;['IQD','USD'].forEach(k=>$('cc-'+k).classList.toggle('on',k===c))}\n""" + JS_CT + JS_FILTER)
    P("HOME", """<div class="sv on" id="s-menu"><h2 class="ptitle">{{t('tab_settings')}}</h2>""",
      """<div class="sv on" id="s-menu"><h2 class="ptitle">{{t('tab_settings')}}</h2><a class="glass menu" href="/profile" style="text-decoration:none"><span>{{t('profile')}}</span><i>&rsaquo;</i></a>""")
    # --- case page: show + edit
    P("CASE", """<h1 class="cn">{{c.name}}</h1>""",
      """<div class="badge" style="display:inline-block;margin-top:8px;background:var(--soft);color:var(--tx)">{{t('ct_'+(c.case_type or 'court'))}}</div><h1 class="cn">{{c.name}}</h1>""")
    P("CASE", """{% if c.client %}<div><span>{{t('client')}}</span><b>{{c.client}}</b></div>{% endif %}""",
      """{% set ct = c.case_type or 'court' %}{% if c.subject %}<div><span>{{t('lb_'+ct+'_subject')}}</span><b>{{c.subject}}</b></div>{% endif %}{% if c.client %}<div><span>{{t('lb_'+ct+'_client')}}</span><b>{{c.client}}</b></div>{% endif %}{% if c.party %}<div><span>{{t('lb_'+ct+'_party')}}</span><b>{{c.party}}</b></div>{% endif %}""")
    P("CASE", """{% if c.case_no %}<div><span>{{t('case_no')}}</span><b>{{c.case_no}}</b></div>{% endif %}""",
      """{% if c.case_no %}<div><span>{{t('case_no') if ct=='court' else t('case_no2')}}</span><b>{{c.case_no}}</b></div>{% endif %}""")
    P("CASE", """{% if c.court %}<div><span>{{t('court')}}</span><b>{{c.court}}</b></div>{% endif %}</div></div>""",
      """{% if c.court %}<div><span>{{t('court') if ct=='court' else t('court2')}}</span><b>{{c.court}}</b></div>{% endif %}{% if c.due %}<div><span>{{t('due')}}</span><b>{{c.due}}</b></div>{% endif %}{% if c.memo %}<div><span>{{t('memo')}}</span><b style="white-space:pre-wrap">{{c.memo}}</b></div>{% endif %}</div></div>""")
    P("CASE", """<div class="glass"><span>{{t('fee')}}</span><b>{{fm(c.fee,cur)}}</b></div>""",
      """<div class="glass"><span>{{t('fee') if ct=='court' else t('fee2')}}</span><b>{{fm(c.fee,cur)}}</b></div>""")
    P("CASE", """<label>{{t('case_name')}}</label><input name="name" required maxlength="80" value="{{c.name}}" autocomplete="off">""",
      SEL_CASE + """<label>{{t('case_name')}}</label><input name="name" required maxlength="80" value="{{c.name}}" autocomplete="off">""")
    P("CASE", """<label>{{t('client')}}</label><input name="client" maxlength="80" value="{{c.client}}" autocomplete="off">""",
      """<label id="l-client">{{t('lb_'+ct0+'_client')}}</label><input name="client" maxlength="80" value="{{c.client}}" autocomplete="off"><label id="l-party">{{t('lb_'+ct0+'_party')}}</label><input name="party" maxlength="80" value="{{c.party or ''}}" autocomplete="off"><label id="l-subject">{{t('lb_'+ct0+'_subject')}}</label><input name="subject" maxlength="120" value="{{c.subject or ''}}" autocomplete="off">""")
    P("CASE", """<label>{{t('case_no')}}</label><input name="case_no" maxlength="40" value="{{c.case_no}}" autocomplete="off">""",
      """<label id="l-no">{{t('case_no') if ct0=='court' else t('case_no2')}}</label><input name="case_no" maxlength="40" value="{{c.case_no}}" autocomplete="off">""")
    P("CASE", """<label>{{t('court')}}</label><input name="court" maxlength="80" value="{{c.court}}" autocomplete="off">""",
      """<label id="l-court">{{t('court') if ct0=='court' else t('court2')}}</label><input name="court" maxlength="80" value="{{c.court}}" autocomplete="off">""")
    P("CASE", """<label>{{t('fee')}}</label><input name="fee" inputmode="decimal" value="{{fee_v}}" autocomplete="off">""",
      """<label id="l-fee">{{t('fee') if ct0=='court' else t('fee2')}}</label><input name="fee" inputmode="decimal" value="{{fee_v}}" autocomplete="off"><label>{{t('due')}}</label><input type="date" name="due" value="{{c.due or ''}}"><label>{{t('memo')}}</label><textarea name="memo" rows="2" maxlength="1000">{{c.memo or ''}}</textarea>""")
    P("CASE", """setType('expense');showL((function(){""",
      JS_CT + """setCT({{ (c.case_type or 'court')|tojson }});setType('expense');showL((function(){""")
    # --- print
    P("PRINT", """{% if acc.client %}<div><span>{{t('client')}}</span><b>{{acc.client}}</b></div>{% endif %}""",
      """{% set ct = acc.case_type or 'court' %}{% if acc.subject %}<div><span>{{t('lb_'+ct+'_subject')}}</span><b>{{acc.subject}}</b></div>{% endif %}{% if acc.client %}<div><span>{{t('lb_'+ct+'_client')}}</span><b>{{acc.client}}</b></div>{% endif %}{% if acc.party %}<div><span>{{t('lb_'+ct+'_party')}}</span><b>{{acc.party}}</b></div>{% endif %}""")
    P("PRINT", """{% if acc.case_no %}<div><span>{{t('case_no')}}</span><b>{{acc.case_no}}</b></div>{% endif %}""",
      """{% if acc.case_no %}<div><span>{{t('case_no') if ct=='court' else t('case_no2')}}</span><b>{{acc.case_no}}</b></div>{% endif %}""")
    P("PRINT", """{% if acc.court %}<div><span>{{t('court')}}</span><b>{{acc.court}}</b></div>{% endif %}""",
      """{% if acc.court %}<div><span>{{t('court') if ct=='court' else t('court2')}}</span><b>{{acc.court}}</b></div>{% endif %}{% if acc.due %}<div><span>{{t('due')}}</span><b>{{acc.due}}</b></div>{% endif %}{% if acc.memo %}<div><span>{{t('memo')}}</span><b>{{acc.memo}}</b></div>{% endif %}""")
    P("PRINT", """<div class="box"><div><small>{{t('fee')}}</small>""",
      """<div class="box"><div><small>{{t('fee') if ct=='court' else t('fee2')}}</small>""")

# ---------------------------------------------------------------- wiring
def x_patch(name, old, new):
    s = G[name]
    if old not in s: app.logger.warning("extras: patch not applied in %s: %.50s", name, old); return
    G[name] = s.replace(old, new, 1)


def init(g):
    global G
    G = g
    app = g["app"]      # the Flask app (never the module "app")
    keep = {"G", "GID", "GSEC", "PBKDF", "PROF", "SIGN", "NEW", "CSS_EXTRA", "PROFILE", "init"}
    for k, v in g.items():
        if k not in keep and not k.startswith("x_") and not k.startswith("__"):
            globals()[k] = v      # force: app, sb, T, DIG ... always come from app.py
    for k, (a, b, c) in NEW.items():
        T["ku"][k], T["ar"][k], T["en"][k] = a, b, c
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)   # correct https redirect URL on Render

    # faster password check: new hashes use pbkdf2; old scrypt hashes are upgraded silently on next login
    orig_chk, orig_gen = g["check_password_hash"], g["generate_password_hash"]
    def gen(p, **k): return orig_gen(p, method=PBKDF)
    def chk(h, p):
        ok = orig_chk(h, p)
        if ok and h.startswith("scrypt"):
            POOL.submit(lambda: sb.table("users").update({"pw": gen(p)}, returning=MIN).eq("pw", h).execute())
        return ok
    g["generate_password_hash"], g["check_password_hash"] = gen, chk
    g["fmt"] = x_fmt

    # stopgap: an old dashboard() SQL function in Supabase has no "cases" key -> do not crash, show it empty
    try:
        orig_rpc = sb.rpc
        def rpc(fn, params=None, *a, **k):
            q = orig_rpc(fn, params, *a, **k)
            if fn == "dashboard":
                ex = q.execute
                def execute(*a2, **k2):
                    r = ex(*a2, **k2)
                    if isinstance(r.data, dict):
                        if "cases" not in r.data: app.logger.warning("dashboard() has no 'cases': run schema.sql in Supabase")
                        r.data.setdefault("cases", [])
                    return r
                q.execute = execute
            return q
        sb.rpc = rpc
    except Exception as ex:
        app.logger.warning("rpc wrapper not installed: %s", ex)

    app.before_request(x_gate)
    app.after_request(x_after)
    app.context_processor(lambda: dict(me=(x_prof(session["uid"]) if "uid" in session else {}) or {}, gid=bool(GID)))
    lr = g["login_required"]
    app.add_url_rule("/profile", "x_profile", lr(x_profile), methods=["GET", "POST"])
    app.add_url_rule("/profile/skip", "x_skip", lr(x_skip))
    app.add_url_rule("/profile/password", "x_password", lr(x_password), methods=["POST"])
    app.add_url_rule("/account/delete", "x_delete_me", lr(x_delete_me), methods=["POST"])
    app.add_url_rule("/auth/google", "x_g_start", x_g_start)
    app.add_url_rule("/auth/google/callback", "x_g_cb", x_g_cb)
    app.add_url_rule("/export.csv", "x_csv", lr(x_csv))
    # keep the app's own print page (it knows about cases); only fall back to ours if it crashes
    orig_print = app.view_functions["print_view"]
    def safe_print(*a, **k):
        try: return orig_print(*a, **k)
        except HTTPException: raise
        except Exception as ex:
            app.logger.warning("print_view failed (%s), using fallback", ex)
            return lr(x_print)()
    app.view_functions["print_view"] = safe_print
    app.view_functions["img"] = lr(x_img)

    x_patch("CSS", "</style>", CSS_EXTRA + "</style>")
    x_patch("CSS", '<link rel="manifest"', '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="manifest"')
    x_patch("AUTH", "{% if err %}", "{% if session.get('gerr') %}<div class=\"err\">{{t(session.get('gerr'))}}</div>{% endif %}{% if err %}")
    x_patch("AUTH", "<button class=\"btn\">{{t(mode)}}</button>",
            "<button class=\"btn\">{{t(mode)}}</button>{% if gid and 'WalletApp' not in request.headers.get('User-Agent','') %}<a class=\"btn ghost gbtn\" href=\"/auth/google\">G &nbsp;{{t('g_btn')}}</a>{% endif %}")
    x_patch("HOME", "<div><small>{{t('hi')}}</small><b>{{user}}</b></div>",
            "<a class=\"who\" href=\"/profile\">{% if me.avatar %}<span class=\"av\"><img src=\"/img/{{me.avatar}}\" alt=\"\"></span>{% else %}<span class=\"av\">{{((me.full_name or user)[:1])|upper}}</span>{% endif %}"
            "<div><small>{{t('hi')}}</small><b>{{me.full_name or user}}</b></div></a>")
    x_patch("HOME", "<a class=\"mini red\" href=\"/logout\">", "<a class=\"mini\" href=\"/profile\">{{t('profile')}}</a> <a class=\"mini red\" href=\"/logout\">")
    x_patch("HOME", "chart.umd.min.js\"></script>", "chart.umd.min.js\" defer></script>")
    x_patch("HOME", "setType('expense');setTab(tab,true);if(MSG)toast(MSG,1);",
            "setType('expense');setTab(tab,true);if(MSG)toast(MSG,1);addEventListener('DOMContentLoaded',function(){if(tab==='charts')boot()});")
    x_patch("PRINT", "<button onclick=\"print()\">&#128424; {{t('print_btn')}}</button>",
            "<a href=\"{{csv_url or ('/export.csv?' ~ request.query_string.decode())}}\">&#11015; {{t('csv')}}</a><button onclick=\"try{window.print()}catch(e){}\">&#128424; {{t('print_btn')}}</button>")
    x_patch("PRINT", "</body></html>",
            "<p class=\"noprint meta\" id=\"ph\" style=\"display:none\">{{t('print_ios')}}</p>"
            "<script>if(navigator.standalone||matchMedia('(display-mode: standalone)').matches)document.getElementById('ph').style.display='block'</script></body></html>")
    x_cases_patch()