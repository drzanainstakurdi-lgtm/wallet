# -*- coding: utf-8 -*-
# جزدانی ئەلکترۆنی / المحفظة الإلكترونية / E-Wallet  (Flask + Supabase)
import os, re, uuid, json, calendar, gzip, hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, date
from functools import wraps
from dotenv import load_dotenv
from flask import (Flask, request, session, redirect, url_for,
                   render_template_string, abort, Response, send_from_directory, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
try:
    from postgrest.types import ReturnMethod
    MIN = ReturnMethod.minimal
except Exception:
    MIN = "minimal"

load_dotenv()
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Baghdad"))
except Exception:
    TZ = None

BUCKET = os.getenv("SUPABASE_BUCKET", "receipts")
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

POOL = ThreadPoolExecutor(4)   # background jobs (photo upload / cleanup)
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(days=90),
    SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=1),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("PRODUCTION") == "1",
)

# ---------------------------------------------------------------- texts
T = {
 "ku": dict(dir="rtl", app="جزدانەکەم", username="ناوی بەکارهێنەر", password="وشەی نهێنی",
  login="چوونەژوورەوە", register="دروستکردنی هەژمار", no_acc="هەژمارت نییە؟", has_acc="هەژمارت هەیە؟",
  logout="دەرچوون", balance="ماوەی ئەم هەژمارە", today="ئەمڕۆ", week="ئەم هەفتەیە", month="ئەم مانگە",
  income="داهات", expense="خەرجی", net="ماوە", add_in="داهاتی نوێ", add_ex="خەرجی نوێ",
  amount="بڕی پارە", src_in="سەرچاوە (لە کوێوە هات)", src_ex="بۆ چی خەرج کرا", note="تێبینی", photo="وێنە",
  date="بەروار", save="پاشەکەوتکردن", all="هەمووی", empty="هیچ تۆمارێک نییە لەم ماوەیەدا.",
  delete="سڕینەوە", confirm="دڵنیای لە سڕینەوە؟", bad="ناو یان وشەی نهێنی هەڵەیە",
  taken="ئەم ناوە پێشتر بەکارهاتووە", short="ناو لانیکەم ٣ و وشەی نهێنی ٤ پیت بێت", hi="بەخێربێیت",
  new_acc="هەژماری نوێ", acc_name="ناوی هەژمار", currency="دراو", opening="پارەی دەستپێک", create="دروستکردن",
  total_all="کۆی گشتی هەموو هەژمارەکان", month_pick="مانگ هەڵبژێرە", from_="لە بەرواری", to_="تا بەرواری",
  apply="پیشاندان", all_time="هەموو کات", chart_daily="داهات و خەرجی بەپێی ڕۆژ", chart_cat="دابەشبوون بەپێی جۆر",
  others="ئەوانی تر", del_acc="سڕینەوەی هەژمار", confirm_acc="هەژمارەکە لەگەڵ هەموو تۆمارەکانی دەسڕدرێتەوە. دڵنیایت؟",
  no_data="هیچ داتایەک نییە", history="تۆمارەکان", cur_IQD="دینار", cur_USD="دۆلار", acc_default="هەژماری سەرەکی",
  period="ماوەی هەڵبژێردراو", rate="ڕێژەی خەرجی",
  pwa_t="جزدانەکەم وەک بەرنامە دابمەزرێنە", pwa_1="دوگمەی هاوبەشکردن (Share) لە خوارەوەی شاشە دابگرە",
  pwa_2="«Add to Home Screen» هەڵبژێرە و پاشان «Add»", pwa_safari="بۆ دامەزراندن، ئەم لاپەڕەیە لە Safari بکەرەوە",
  pwa_btn="دامەزراندن", pwa_close="دواتر", off_t="ئینتەرنێت نییە", off_p="پەیوەندی ئینتەرنێتت بپشکنە و دووبارە هەوڵ بدەرەوە.", off_b="دووبارە هەوڵبدەرەوە", err="پاشەکەوت نەکرا، دووبارە هەوڵبدەرەوە"),
 "ar": dict(dir="rtl", app="محفظتي", username="اسم المستخدم", password="كلمة المرور",
  login="تسجيل الدخول", register="إنشاء حساب", no_acc="ليس لديك حساب؟", has_acc="لديك حساب؟",
  logout="خروج", balance="رصيد هذا الحساب", today="اليوم", week="هذا الأسبوع", month="هذا الشهر",
  income="الدخل", expense="المصروف", net="المتبقي", add_in="دخل جديد", add_ex="مصروف جديد",
  amount="المبلغ", src_in="المصدر (من أين جاء)", src_ex="على ماذا صُرف", note="ملاحظة", photo="صورة",
  date="التاريخ", save="حفظ", all="الكل", empty="لا توجد سجلات في هذه الفترة.",
  delete="حذف", confirm="هل تريد الحذف؟", bad="اسم المستخدم أو كلمة المرور غير صحيحة",
  taken="هذا الاسم مستخدم", short="الاسم 3 أحرف على الأقل وكلمة المرور 4", hi="أهلاً",
  new_acc="حساب جديد", acc_name="اسم الحساب", currency="العملة", opening="الرصيد الافتتاحي", create="إنشاء",
  total_all="المجموع الكلي لكل الحسابات", month_pick="اختر الشهر", from_="من تاريخ", to_="إلى تاريخ",
  apply="عرض", all_time="كل الأوقات", chart_daily="الدخل والمصروف يومياً", chart_cat="التوزيع حسب النوع",
  others="أخرى", del_acc="حذف الحساب", confirm_acc="سيتم حذف الحساب مع كل سجلاته. هل أنت متأكد؟",
  no_data="لا توجد بيانات", history="السجلات", cur_IQD="دينار", cur_USD="دولار", acc_default="الحساب الرئيسي",
  period="الفترة المحددة", rate="نسبة الصرف",
  pwa_t="ثبّت محفظتي كتطبيق", pwa_1="اضغط زر المشاركة (Share) أسفل الشاشة",
  pwa_2="اختر «إضافة إلى الشاشة الرئيسية» (Add to Home Screen) ثم «إضافة»", pwa_safari="افتح هذه الصفحة في Safari للتثبيت",
  pwa_btn="تثبيت", pwa_close="لاحقاً", off_t="لا يوجد اتصال بالإنترنت", off_p="تحقق من اتصالك وحاول مرة أخرى.", off_b="إعادة المحاولة", err="تعذّر الحفظ، حاول مرة أخرى"),
 "en": dict(dir="ltr", app="My Wallet", username="Username", password="Password",
  login="Log in", register="Create account", no_acc="No account?", has_acc="Have an account?",
  logout="Log out", balance="Account balance", today="Today", week="This week", month="This month",
  income="Income", expense="Expense", net="Left", add_in="New income", add_ex="New expense",
  amount="Amount", src_in="Source (where from)", src_ex="Spent on", note="Note", photo="Photo",
  date="Date", save="Save", all="All", empty="No entries in this period.",
  delete="Delete", confirm="Delete this entry?", bad="Wrong username or password",
  taken="Username already taken", short="Username 3+ chars, password 4+ chars", hi="Welcome",
  new_acc="New account", acc_name="Account name", currency="Currency", opening="Opening balance", create="Create",
  total_all="Grand total of all accounts", month_pick="Pick a month", from_="From date", to_="To date",
  apply="Show", all_time="All time", chart_daily="Income and expense by day", chart_cat="Breakdown by category",
  others="Others", del_acc="Delete account", confirm_acc="This deletes the account and all its entries. Sure?",
  no_data="No data", history="Entries", cur_IQD="Dinar", cur_USD="Dollar", acc_default="Main account",
  period="Selected period", rate="Spending rate",
  pwa_t="Install My Wallet as an app", pwa_1="Tap the Share button at the bottom of the screen",
  pwa_2="Choose Add to Home Screen, then Add", pwa_safari="Open this page in Safari to install",
  pwa_btn="Install", pwa_close="Later", off_t="No internet connection", off_p="Check your connection and try again.", off_b="Try again", err="Could not save, please try again"),
}

T["ku"].update(dict(
  tab_home="سەرەکی", tab_entries="تۆمارەکان", tab_charts="گرافیک", tab_settings="ڕێکخستن", filter="فلتەر",
  done="ئەنجام درا ✓", saved="پاشەکەوتکرا ✓", set_user="هەژماری من", set_lang="زمان", set_accounts="هەژمارەکان",
  set_clear="سڕینەوەی داتای ئەم هەژمارە", set_print="پرینت", set_danger="ناوچەی مەترسیدار",
  clear_btn="سڕینەوەی تۆمارەکان", entries_n="تۆمار", print_statement="کەشفی هەژمار (داهات و خەرجی)",
  print_income="تەنها داهات", print_expense="تەنها خەرجی", print_grand="کۆی گشتی هەموو هەژمارەکان",
  print_hint="ماوەی هەڵبژێردراو لە فلتەر بەکاردێت:", print_btn="پرینت", back="گەڕانەوە", generated="ڕێکەوتی دروستکردن",
  col_label="سەرچاوە / بۆ چی", total="کۆ",
  reset_desc="هەموو هەژمارەکان و تۆمارەکان و وێنەکانت دەسڕێنەوە و هەژمارێکی نوێی بەتاڵ دروست دەبێت.",
  reset_btn="سڕینەوەی هەموو شتێک", cancel="هەڵوەشاندنەوە", yes_delete="بەڵێ، بیسڕەوە",
  confirm_check="تێدەگەم، ئەم کارە ناگەڕێتەوە",
  ttl_clear_in="سڕینەوەی هەموو داهاتەکان؟", ttl_clear_ex="سڕینەوەی هەموو خەرجییەکان؟",
  ttl_clear_all="سڕینەوەی هەموو تۆمارەکان؟", ttl_del_acc="سڕینەوەی هەژمار؟", ttl_reset="سڕینەوەی هەموو شتێک؟",
  msg_clear_in="{n} تۆماری داهات لە هەژماری «{name}» دەسڕدرێنەوە (خەرجییەکان وەک خۆیان دەمێننەوە).",
  msg_clear_ex="{n} تۆماری خەرجی لە هەژماری «{name}» دەسڕدرێنەوە (داهاتەکان وەک خۆیان دەمێننەوە).",
  msg_clear_all="هەموو {n} تۆمارەکانی هەژماری «{name}» (داهات و خەرجی و وێنەکان) دەسڕدرێنەوە. خودی هەژمارەکە دەمێنێتەوە.",
  msg_del_acc="هەژماری «{name}» لەگەڵ هەموو {n} تۆمارەکانی بۆ هەمیشە دەسڕدرێتەوە.",
  msg_reset="هەموو هەژمارەکان و {n} تۆمار و وێنەکانت دەسڕدرێنەوە. ئەمە ناگەڕێتەوە."))
T["ar"].update(dict(
  tab_home="الرئيسية", tab_entries="السجلات", tab_charts="الرسوم", tab_settings="الإعدادات", filter="تصفية",
  done="تم ✓", saved="تم الحفظ ✓", set_user="حسابي", set_lang="اللغة", set_accounts="الحسابات",
  set_clear="حذف بيانات هذا الحساب", set_print="طباعة", set_danger="منطقة الخطر",
  clear_btn="حذف السجلات", entries_n="سجل", print_statement="كشف الحساب (الدخل والمصروف)",
  print_income="الدخل فقط", print_expense="المصروف فقط", print_grand="المجموع الكلي لكل الحسابات",
  print_hint="تُستخدم الفترة المحددة في التصفية:", print_btn="طباعة", back="رجوع", generated="تاريخ الإنشاء",
  col_label="المصدر / البند", total="المجموع",
  reset_desc="سيتم حذف كل الحسابات والسجلات والصور وإنشاء حساب جديد فارغ.",
  reset_btn="حذف كل شيء", cancel="إلغاء", yes_delete="نعم، احذف",
  confirm_check="أفهم أنه لا يمكن التراجع عن هذا",
  ttl_clear_in="حذف كل الدخل؟", ttl_clear_ex="حذف كل المصروفات؟", ttl_clear_all="حذف كل السجلات؟",
  ttl_del_acc="حذف الحساب؟", ttl_reset="حذف كل شيء؟",
  msg_clear_in="سيتم حذف {n} سجل دخل من الحساب «{name}» (تبقى المصروفات).",
  msg_clear_ex="سيتم حذف {n} سجل مصروف من الحساب «{name}» (يبقى الدخل).",
  msg_clear_all="سيتم حذف كل سجلات الحساب «{name}» وعددها {n} (الدخل والمصروف والصور). يبقى الحساب نفسه.",
  msg_del_acc="سيتم حذف الحساب «{name}» نهائياً مع كل سجلاته وعددها {n}.",
  msg_reset="سيتم حذف كل الحسابات و{n} سجل والصور. لا يمكن التراجع."))
T["en"].update(dict(
  tab_home="Home", tab_entries="Entries", tab_charts="Charts", tab_settings="Settings", filter="Filter",
  done="Done ✓", saved="Saved ✓", set_user="My account", set_lang="Language", set_accounts="Accounts",
  set_clear="Clear data of this account", set_print="Print", set_danger="Danger zone",
  clear_btn="Clear entries", entries_n="entries", print_statement="Account statement (income and expense)",
  print_income="Income only", print_expense="Expenses only", print_grand="Grand total of all accounts",
  print_hint="Uses the period chosen in Filter:", print_btn="Print", back="Back", generated="Generated",
  col_label="Source / Purpose", total="Total",
  reset_desc="Deletes all accounts, entries and photos, then creates a fresh empty account.",
  reset_btn="Delete everything", cancel="Cancel", yes_delete="Yes, delete",
  confirm_check="I understand this cannot be undone",
  ttl_clear_in="Delete all income?", ttl_clear_ex="Delete all expenses?", ttl_clear_all="Delete all entries?",
  ttl_del_acc="Delete account?", ttl_reset="Delete everything?",
  msg_clear_in="{n} income entries of account \u201c{name}\u201d will be deleted (expenses stay).",
  msg_clear_ex="{n} expense entries of account \u201c{name}\u201d will be deleted (income stays).",
  msg_clear_all="All {n} entries of account \u201c{name}\u201d (income, expenses, photos) will be deleted. The account itself stays.",
  msg_del_acc="Account \u201c{name}\u201d and all its {n} entries will be permanently deleted.",
  msg_reset="All accounts, {n} entries and photos will be deleted. This cannot be undone."))

T["ku"].update(dict(
  tab_income="داهات", tab_expense="خەرجی", tab_legal="دۆسیەکان", cases_t="مامەڵە یاسایییەکان",
  new_case="دۆسیەی نوێ", case_name="ناوی دۆسیە / مامەڵە", client="ناوی کڕیار (موەکیل)", case_no="ژمارەی دۆسیە",
  court="دادگا", fee="کرێی ڕێککەوتوو", status_open="کراوە", status_closed="داخراوە",
  case_in="وەرگیراو لە کڕیار", case_ex="خەرجییەکانی دۆسیە", case_net="ماوە لە پارەی وەرگیراو", fee_left="کرێی ماوە (نەدراو)",
  add_case_in="پارەی وەرگیراو", add_case_ex="خەرجی دۆسیە",
  src_case_in="جۆری پارە (پێشەکی، کرێ...)", src_case_ex="خەرجی بۆ چی بوو (دادگا، مۆر، گواستنەوە...)",
  edit_case="دەستکاری", close_case="داخستنی دۆسیە", reopen_case="کردنەوەی دۆسیە", del_case="سڕینەوەی دۆسیە",
  no_cases="هیچ دۆسیەیەک نییە. یەکەمیان دروست بکە.", ttl_del_case="سڕینەوەی دۆسیە؟",
  msg_del_case="دۆسیەی «{name}» لەگەڵ هەموو {n} تۆمارەکانی و وێنەکانی بۆ هەمیشە دەسڕدرێتەوە.",
  set_office="نووسینگە و هەژماری من", office="ناوی نووسینگە / پارێزەر", office_hint="لە سەرەوەی هەموو پرینتەکان دەنووسرێت.",
  print_case="کەشفی دۆسیە (وەرگیراو و خەرجی)", print_case_ex="تەنها خەرجییەکان", print_case_in="تەنها وەرگیراو",
  signature="واژوو و مۆر",
  reset_desc="هەموو هەژمارەکان و دۆسیەکان و تۆمارەکان و وێنەکانت دەسڕێنەوە و هەژمارێکی نوێی بەتاڵ دروست دەبێت.",
  msg_reset="هەموو هەژمارەکان و دۆسیەکان و {n} تۆمار و وێنەکانت دەسڕدرێنەوە. ئەمە ناگەڕێتەوە."))
T["ar"].update(dict(
  tab_income="الدخل", tab_expense="المصروف", tab_legal="القضايا", cases_t="المعاملات القانونية",
  new_case="قضية جديدة", case_name="اسم القضية / المعاملة", client="اسم الموكّل", case_no="رقم القضية",
  court="المحكمة", fee="الأتعاب المتفق عليها", status_open="مفتوحة", status_closed="مغلقة",
  case_in="المستلم من الموكّل", case_ex="مصروفات القضية", case_net="المتبقي من المبلغ المستلم", fee_left="الأتعاب المتبقية",
  add_case_in="مبلغ مستلم", add_case_ex="مصروف القضية",
  src_case_in="نوع المبلغ (دفعة مقدمة، أتعاب...)", src_case_ex="على ماذا صُرف (رسوم محكمة، طوابع، تنقل...)",
  edit_case="تعديل", close_case="إغلاق القضية", reopen_case="إعادة فتح القضية", del_case="حذف القضية",
  no_cases="لا توجد قضايا. أنشئ أول قضية.", ttl_del_case="حذف القضية؟",
  msg_del_case="سيتم حذف القضية «{name}» مع كل سجلاتها وعددها {n} وصورها نهائياً.",
  set_office="المكتب وحسابي", office="اسم المكتب / المحامي", office_hint="يُكتب في أعلى كل مطبوعات.",
  print_case="كشف القضية (المستلم والمصروف)", print_case_ex="المصروفات فقط", print_case_in="المستلم فقط",
  signature="التوقيع والختم",
  reset_desc="سيتم حذف كل الحسابات والقضايا والسجلات والصور وإنشاء حساب جديد فارغ.",
  msg_reset="سيتم حذف كل الحسابات والقضايا و{n} سجل والصور. لا يمكن التراجع."))
T["en"].update(dict(
  tab_income="Income", tab_expense="Expenses", tab_legal="Cases", cases_t="Legal cases",
  new_case="New case", case_name="Case / matter name", client="Client name", case_no="Case number",
  court="Court", fee="Agreed fee", status_open="Open", status_closed="Closed",
  case_in="Received from client", case_ex="Case expenses", case_net="Left from received", fee_left="Fee remaining",
  add_case_in="Money received", add_case_ex="Case expense",
  src_case_in="Type (advance, fee...)", src_case_ex="Spent on (court fee, stamps, travel...)",
  edit_case="Edit", close_case="Close case", reopen_case="Reopen case", del_case="Delete case",
  no_cases="No cases yet. Create your first one.", ttl_del_case="Delete case?",
  msg_del_case="Case \u201c{name}\u201d with all its {n} entries and photos will be permanently deleted.",
  set_office="Office and my account", office="Office / lawyer name", office_hint="Printed at the top of every printout.",
  print_case="Case statement (received and expenses)", print_case_ex="Expenses only", print_case_in="Received only",
  signature="Signature and stamp",
  reset_desc="Deletes all accounts, cases, entries and photos, then creates a fresh empty account.",
  msg_reset="All accounts, cases, {n} entries and photos will be deleted. This cannot be undone."))

T["ku"].update(add_new="زیادکردنی تۆمار", grand_total="کۆی گشتی")
T["ar"].update(add_new="إضافة سجل", grand_total="المجموع الكلي")
T["en"].update(add_new="Add entry", grand_total="Grand total")

T["ku"].update(dict(
  edit_t="دەستکاریکردنی تۆمار", search_ph="گەڕان لە تۆمارەکان...", set_data="داتا و هەناردە",
  exp_acc="هەناردەی ئەم هەژمارە (ماوەی هەڵبژێردراو)", exp_all="هەناردەی هەموو داتاکان (باکئەپ)",
  exp_hint="فایلی CSV دروست دەبێت و لە Excel یان Numbers دەکرێتەوە.",
  budget="بودجەی مانگانە", budget_set="دانان", budget_spent="خەرجکراو", budget_left="ماوە",
  budget_over="لە بودجە تێپەڕیوە بە", budget_daily="ڕۆژانە", budget_none="بودجەی مانگانە دانەناوە. دایبنێ بۆ بەدواداچوونی خەرجییەکانت.",
  budget_hint="بڕی بودجەی مانگانەی ئەم هەژمارە (٠ = لابردن).",
  set_rec="تۆمارە دووبارەبووەکان", rec_hint="هەر مانگ بە خۆکاری زیاد دەکرێت (مووچە، کرێی ماڵ، بەشداری...).",
  rec_day="ڕۆژی مانگ (١ تا ٢٨)", rec_empty="هیچ تۆمارێکی دووبارەبوو نییە.", rec_added="تۆمارە دووبارەبووەکان زیادکران ✓",
  rec_for="بۆ هەژماری:", pw_change="گۆڕینی وشەی نهێنی", pw_old="وشەی نهێنی ئێستا", pw_new="وشەی نهێنی نوێ",
  pw_bad="وشەی نهێنی ئێستا هەڵەیە", hearing="دادگایی داهاتوو", hearing_soon="دادگاییەکانی ٧ ڕۆژی داهاتوو"))
T["ar"].update(dict(
  edit_t="تعديل السجل", search_ph="بحث في السجلات...", set_data="البيانات والتصدير",
  exp_acc="تصدير هذا الحساب (الفترة المحددة)", exp_all="تصدير كل البيانات (نسخة احتياطية)",
  exp_hint="يُنشأ ملف CSV يُفتح في Excel أو Numbers.",
  budget="الميزانية الشهرية", budget_set="تحديد", budget_spent="المصروف", budget_left="المتبقي",
  budget_over="تجاوزت الميزانية بمقدار", budget_daily="يومياً", budget_none="لم تحدد ميزانية شهرية. حددها لمتابعة مصروفاتك.",
  budget_hint="مبلغ الميزانية الشهرية لهذا الحساب (0 = إزالة).",
  set_rec="السجلات المتكررة", rec_hint="تُضاف تلقائياً كل شهر (راتب، إيجار، اشتراك...).",
  rec_day="يوم الشهر (1 إلى 28)", rec_empty="لا توجد سجلات متكررة.", rec_added="تمت إضافة السجلات المتكررة ✓",
  rec_for="للحساب:", pw_change="تغيير كلمة المرور", pw_old="كلمة المرور الحالية", pw_new="كلمة المرور الجديدة",
  pw_bad="كلمة المرور الحالية غير صحيحة", hearing="الجلسة القادمة", hearing_soon="جلسات الأيام السبعة القادمة"))
T["en"].update(dict(
  edit_t="Edit entry", search_ph="Search entries...", set_data="Data and export",
  exp_acc="Export this account (selected period)", exp_all="Export all data (backup)",
  exp_hint="Creates a CSV file that opens in Excel or Numbers.",
  budget="Monthly budget", budget_set="Set", budget_spent="Spent", budget_left="Left",
  budget_over="Over budget by", budget_daily="per day", budget_none="No monthly budget set. Set one to track your spending.",
  budget_hint="Monthly budget for this account (0 = remove).",
  set_rec="Recurring entries", rec_hint="Added automatically every month (salary, rent, subscriptions...).",
  rec_day="Day of month (1 to 28)", rec_empty="No recurring entries.", rec_added="Recurring entries added ✓",
  rec_for="For account:", pw_change="Change password", pw_old="Current password", pw_new="New password",
  pw_bad="Current password is wrong", hearing="Next hearing", hearing_soon="Hearings in the next 7 days"))

T["ku"].update(dict(
  share_btn="هاوبەشکردن", share_t="هاوبەشکردنی هەژمار", share_hint="کەسێک بە ناوی بەکارهێنەرەکەی زیاد بکە. دەبێت بانگهێشتەکە قبوڵ بکات.",
  share_user="ناوی بەکارهێنەری ئەو کەسە", role_editor="دەتوانێت تۆمار زیاد بکات", role_viewer="تەنها دەبینێت",
  share_add="ناردنی بانگهێشت", pending="چاوەڕێی قبوڵکردن", leave="جێهێشتن", invite_t="بانگهێشتی هەژمار",
  invite_msg="{name} هەژماری «{acc}»ی لەگەڵ تۆ هاوبەش دەکات", accept="قبوڵکردن", decline="ڕەتکردنەوە",
  view_only="ئەم هەژمارە تەنها بۆ بینینە.", share_err_user="ئەم بەکارهێنەرە نەدۆزرایەوە", share_ok="بانگهێشت نێردرا ✓",
  share_self="ناتوانیت لەگەڵ خۆت هاوبەشی بکەیت", no_members="هێشتا لەگەڵ کەس هاوبەش نەکراوە.",
  transfer_t="گواستنەوە لە نێوان هەژمارەکان", tr_from="گواستنراوە لە", tr_to="گواستنراوە بۆ", tr_src="لە هەژماری",
  tr_dst="بۆ هەژماری", tr_amount_in="بڕی وەرگیراو (بە دراوی هەژماری مەبەست)",
  tr_hint="ئەگەر دراوی دوو هەژمارەکە جیاوازە (دینار/دۆلار)، بڕی وەرگیراو بنووسە. نرخەکە خۆی دەردەکەوێت.",
  tr_list="دوایین گواستنەوەکان", tr_net="گواستنەوە (ماوە)",
  set_theme="ڕووکار", theme_light="ڕووناک", theme_dark="تاریک", theme_auto="خۆکار"))
T["ar"].update(dict(
  share_btn="مشاركة", share_t="مشاركة الحساب", share_hint="أضف شخصاً باسم المستخدم. يجب أن يقبل الدعوة.",
  share_user="اسم المستخدم للشخص", role_editor="يمكنه إضافة سجلات", role_viewer="للعرض فقط",
  share_add="إرسال دعوة", pending="بانتظار القبول", leave="مغادرة", invite_t="دعوة إلى حساب",
  invite_msg="{name} يشارك معك الحساب «{acc}»", accept="قبول", decline="رفض",
  view_only="هذا الحساب للعرض فقط.", share_err_user="لم يتم العثور على هذا المستخدم", share_ok="تم إرسال الدعوة ✓",
  share_self="لا يمكنك المشاركة مع نفسك", no_members="لم تتم المشاركة مع أحد بعد.",
  transfer_t="تحويل بين الحسابات", tr_from="محوَّل من", tr_to="محوَّل إلى", tr_src="من حساب", tr_dst="إلى حساب",
  tr_amount_in="المبلغ المستلم (بعملة الحساب الآخر)",
  tr_hint="إذا اختلفت عملة الحسابين (دينار/دولار) اكتب المبلغ المستلم وسيظهر السعر تلقائياً.",
  tr_list="آخر التحويلات", tr_net="التحويلات (صافي)",
  set_theme="المظهر", theme_light="فاتح", theme_dark="داكن", theme_auto="تلقائي"))
T["en"].update(dict(
  share_btn="Share", share_t="Share account", share_hint="Add a person by username. They must accept the invitation.",
  share_user="Their username", role_editor="Can add entries", role_viewer="View only",
  share_add="Send invitation", pending="Waiting to accept", leave="Leave", invite_t="Account invitation",
  invite_msg="{name} shares the account \u201c{acc}\u201d with you", accept="Accept", decline="Decline",
  view_only="This account is view only.", share_err_user="User not found", share_ok="Invitation sent ✓",
  share_self="You cannot share with yourself", no_members="Not shared with anyone yet.",
  transfer_t="Transfer between accounts", tr_from="Transferred from", tr_to="Transferred to", tr_src="From account",
  tr_dst="To account", tr_amount_in="Amount received (in the other account's currency)",
  tr_hint="If the two accounts use different currencies (IQD/USD), enter the amount received. The rate is shown automatically.",
  tr_list="Latest transfers", tr_net="Transfers (net)",
  set_theme="Appearance", theme_light="Light", theme_dark="Dark", theme_auto="Auto"))

T["ku"].update(dict(
  invite_case_msg="{name} دۆسیەی «{acc}»ی لەگەڵ تۆ هاوبەش دەکات", share_case_t="هاوبەشکردنی دۆسیە",
  shared_by="هاوبەشکراوە لەلایەن", shared_with_me="دۆسیە هاوبەشکراوەکان لەگەڵ من",
  receipt_t="وەسڵی وەرگرتنی پارە", receipt_no="ژمارەی وەسڵ", receipt_from="وەرگیرا لە", receipt_for="بۆ (ڕوونکردنەوە)"))
T["ar"].update(dict(
  invite_case_msg="{name} يشارك معك القضية «{acc}»", share_case_t="مشاركة القضية",
  shared_by="مشاركة من", shared_with_me="قضايا مشتركة معي",
  receipt_t="سند استلام مبلغ", receipt_no="رقم السند", receipt_from="استُلم من", receipt_for="عن"))
T["en"].update(dict(
  invite_case_msg="{name} shares the case \u201c{acc}\u201d with you", share_case_t="Share case",
  shared_by="Shared by", shared_with_me="Shared with me",
  receipt_t="Payment receipt", receipt_no="Receipt no.", receipt_from="Received from", receipt_for="For"))

T["ku"].update(dict(
  set_profile="پرۆفایل", set_letter="پرینت: لۆگۆ و ژمارە", prof_name="ناوی پیشاندان", prof_photo="وێنەی پرۆفایل",
  change_photo="گۆڕینی وێنە", remove_photo="لابردن", prof_user="ناوی بەکارهێنەر", logo="لۆگۆ", phone="ژمارەی تەلەفۆن",
  letter_hint="لە سەرەوەی هەموو پرینتەکان دەردەکەوێت: لۆگۆ، ناوی نووسینگە و ژمارەی تەلەفۆن.",
  started="بەرواری دەستپێکردن", lk_hint="ناوی بەکارهێنەر بنووسە تا وێنە و ناوی کەسەکە ببینیت.",
  lk_nf="ئەم ناوی بەکارهێنەرە نەدۆزرایەوە", lk_self="ئەمە هەژماری خۆتە"))
T["ar"].update(dict(
  set_profile="الملف الشخصي", set_letter="الطباعة: الشعار والهاتف", prof_name="الاسم المعروض", prof_photo="صورة الملف الشخصي",
  change_photo="تغيير الصورة", remove_photo="إزالة", prof_user="اسم المستخدم", logo="الشعار", phone="رقم الهاتف",
  letter_hint="يظهر أعلى كل مطبوعات: الشعار واسم المكتب ورقم الهاتف.",
  started="تاريخ البدء", lk_hint="اكتب اسم المستخدم لتظهر صورة الشخص واسمه.",
  lk_nf="لم يتم العثور على اسم المستخدم", lk_self="هذا حسابك أنت"))
T["en"].update(dict(
  set_profile="Profile", set_letter="Print: logo and phone", prof_name="Display name", prof_photo="Profile photo",
  change_photo="Change photo", remove_photo="Remove", prof_user="Username", logo="Logo", phone="Phone number",
  letter_hint="Shown at the top of every printout: logo, office name and phone.",
  started="Start date", lk_hint="Type a username to see the person's photo and name.",
  lk_nf="Username not found", lk_self="This is your own account"))

def lang():
    return session.get("lang") if session.get("lang") in T else "ku"

def fmt(v, cur, L="en"):
    v = v or 0
    r = round(v, 0 if cur == "IQD" else 2)
    s = f"{abs(r):,.0f}" if cur == "IQD" else f"{abs(r):,.2f}"
    sign = "-" if r < 0 else ""
    if cur == "USD":
        return f"{sign}${s}"
    return f"{sign}{s} " + ("IQD" if L == "en" else "د.ع")

@app.context_processor
def ctx():
    L = lang()
    return dict(t=lambda k: T[L][k], L=L, dir=T[L]["dir"], fm=lambda v, c: fmt(v, c, L),
                link=lambda **kw: url_for("index", **{**request.args.to_dict(), **kw}))

DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫،", "01234567890123456789.,")
def num(s):
    s = (s or "").translate(DIG).replace(",", "").replace(" ", "")
    try: v = float(s)
    except ValueError: return 0
    return v if v == v and abs(v) < 1e13 else 0

def today():
    return (datetime.now(TZ) if TZ else datetime.now()).date()

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

def find_user(u):
    r = sb.table("users").select("*").eq("username", u).limit(1).execute().data
    return r[0] if r else None

def pop_msg(L):
    m = session.pop("msg", None)
    if not m: return ""
    if m is True or m == 1: return T[L]["done"]
    if isinstance(m, str) and m.startswith("!"): return "!" + T[L].get(m[1:], m[1:])
    return T[L].get(m, T[L]["done"])

def my_account(i):
    r = sb.table("accounts").select("*").eq("id", i).eq("user_id", session["uid"]).limit(1).execute().data
    return r[0] if r else None

def drop_imgs(imgs):
    for i in range(0, len(imgs), 100):
        c = imgs[i:i + 100]
        POOL.submit(lambda c=c: sb.storage.from_(BUCKET).remove(c))

@app.route("/app.css")
def app_css():
    r = Response(STYLE, mimetype="text/css")
    r.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return r

@app.after_request
def squeeze(r):
    if (r.status_code == 200 and not r.direct_passthrough and "Content-Encoding" not in r.headers
            and "gzip" in request.headers.get("Accept-Encoding", "")
            and r.mimetype in ("text/html", "text/css", "application/json", "application/manifest+json")):
        data = r.get_data()
        if len(data) > 1024:
            r.set_data(gzip.compress(data, 5))
            r.headers["Content-Encoding"] = "gzip"
            r.headers["Vary"] = "Accept-Encoding"
    return r

# ---------------------------------------------------------------- friendly error page
@app.errorhandler(Exception)
def on_error(ex):
    from werkzeug.exceptions import HTTPException
    if isinstance(ex, HTTPException):
        return ex
    app.logger.exception("unhandled error: %s", ex)
    detail = f"{type(ex).__name__}: {ex}" if "uid" in session else ""
    return render_template_string(ERR, css=CSS_INLINE, detail=detail), 500

# ---------------------------------------------------------------- app install (PWA)
@app.route("/manifest.webmanifest")
def manifest():
    ic = lambda f, n, p: {"src": f"/static/icons/{f}", "sizes": f"{n}x{n}", "type": "image/png", "purpose": p}
    m = dict(id="/", name="جزدانەکەم", short_name="جزدانەکەم", description="My Wallet - جزدانەکەم - محفظتي",
             start_url="/", scope="/", display="standalone", orientation="portrait",
             background_color="#FAF9F5", theme_color="#FAF9F5", lang="ku", dir="rtl",
             icons=[ic("icon-192.png", 192, "any"), ic("icon-512.png", 512, "any"),
                    ic("icon-maskable-512.png", 512, "maskable")])
    return Response(json.dumps(m, ensure_ascii=False), mimetype="application/manifest+json")

@app.route("/sw.js")
def sw():
    r = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    r.headers["Cache-Control"] = "no-cache"
    r.headers["Service-Worker-Allowed"] = "/"
    return r

@app.route("/offline")
def offline():
    return render_template_string(OFFLINE, css=CSS_INLINE)

# ---------------------------------------------------------------- auth
@app.route("/health")
def health():
    return "ok"

@app.route("/lang/<l>")
def setlang(l):
    if l in T: session["lang"] = l
    return redirect(request.referrer or url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    return auth("login")

@app.route("/register", methods=["GET", "POST"])
def register():
    return auth("register")

def auth(mode):
    err = None
    if request.method == "POST":
        u = request.form.get("username", "").strip().lower()
        p = request.form.get("password", "")
        lg = session.get("lang")
        if mode == "register":
            if len(u) < 3 or len(p) < 4:
                err = "short"
            elif find_user(u):
                err = "taken"
            else:
                row = sb.table("users").insert({"username": u, "pw": generate_password_hash(p)}).execute().data[0]
                sb.table("accounts").insert({"user_id": row["id"], "name": T[lg if lg in T else "ku"]["acc_default"],
                                             "currency": "IQD"}, returning=MIN).execute()
                session.clear(); session.permanent = True
                session.update(uid=row["id"], user=u)
                if lg: session["lang"] = lg
                return redirect(url_for("index"))
        else:
            r = find_user(u)
            if r and check_password_hash(r["pw"], p):
                session.clear(); session.permanent = True
                session.update(uid=r["id"], user=r["username"], office=r.get("office") or "",
                               dname=r.get("display_name") or "", phone=r.get("phone") or "")
                if lg: session["lang"] = lg
                return redirect(url_for("index"))
            err = "bad"
    return render_template_string(AUTH, mode=mode, err=err, css=CSS)

@app.route("/logout")
def logout():
    lg = session.get("lang")
    session.clear()
    if lg: session["lang"] = lg
    return redirect(url_for("login"))

# ---------------------------------------------------------------- accounts
@app.route("/a/<int:i>")
@login_required
def pick_acc(i):
    session["acc"] = i          # the database only returns accounts you can access
    return redirect(url_for("index"))

@app.route("/acc/new", methods=["POST"])
@login_required
def acc_new():
    name = request.form.get("name", "").strip()[:40]
    cur = request.form.get("currency")
    if name and cur in ("IQD", "USD"):
        r = sb.table("accounts").insert({"user_id": session["uid"], "name": name, "currency": cur,
                                         "opening": num(request.form.get("opening"))}).execute().data[0]
        session["acc"] = r["id"]
    return redirect(url_for("index"))

@app.route("/acc/<int:i>/delete", methods=["POST"])
@login_required
def acc_delete(i):
    uid = session["uid"]
    n = len(sb.table("accounts").select("id").eq("user_id", uid).eq("kind", "personal").execute().data)
    a = my_account(i)
    if n > 1 and a and a.get("kind") == "personal":
        rows = sb.table("tx").delete().eq("account_id", i).execute().data
        drop_imgs([r["img"] for r in rows if r.get("img")])
        sb.table("accounts").delete().eq("id", i).eq("user_id", uid).execute()
        session.pop("acc", None)
        session["msg"] = 1
    return redirect(url_for("index"))

@app.route("/edit/<int:i>", methods=["POST"])
@login_required
def edit_tx(i):
    ajax = request.headers.get("X-Requested-With") == "fetch"
    amt = num(request.form.get("amount"))
    d = request.form.get("date") or today().isoformat()
    try: datetime.strptime(d, "%Y-%m-%d")
    except ValueError: d = today().isoformat()
    ok = False
    if amt > 0:
        ok = sb.rpc("edit_tx", {"p_user": session["uid"], "p_id": i, "p_amount": amt,
                                "p_label": request.form.get("label", "").strip()[:120],
                                "p_note": request.form.get("note", "")[:500], "p_date": d}).execute().data
    if ajax:
        return jsonify(ok=bool(ok)), (200 if ok else 403)
    return redirect(request.referrer or url_for("index"))

@app.route("/export")
@login_required
def export():
    import csv, io
    uid, scope = session["uid"], request.args.get("scope", "acc")
    rep = sb.rpc("report", {"p_user": uid, "p_from": "2000-01-01", "p_to": "2100-12-31"}).execute().data
    accs = {a["id"]: a for a in rep}
    if scope == "acc":
        try: ids = [int(request.args.get("acc") or session.get("acc") or 0)]
        except ValueError: ids = [0]
        if ids[0] not in accs: abort(404)
        s, e, _ = get_period()
    else:
        ids = list(accs)
    def page(i):
        q = sb.table("tx").select("account_id,type,amount,label,note,date,kind,user_id").in_("account_id", ids)
        if scope == "acc":
            q = q.gte("date", s.isoformat()).lte("date", e.isoformat())
        return q.order("date").order("id").range(i, i + 999).execute().data
    rows, i = [], 0
    while ids and i < 100000:
        part = page(i); rows += part
        if len(part) < 1000: break
        i += 1000
    names = {}
    uids = list({r["user_id"] for r in rows})
    if uids:
        names = {u["id"]: u["username"] for u in sb.table("users").select("id,username").in_("id", uids).execute().data}
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["account", "kind", "currency", "entry", "type", "amount", "label", "note", "date", "by"])
    for r in rows:
        a = accs.get(r["account_id"], {})
        w.writerow([a.get("name", ""), a.get("kind", ""), a.get("currency", ""), r["kind"], r["type"], r["amount"],
                    r["label"] or "", r["note"] or "", r["date"], names.get(r["user_id"], "")])
    name = "wallet-" + today().isoformat() + ".csv"
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})

@app.route("/budget", methods=["POST"])
@login_required
def budget_set():
    try: aid = int(request.form.get("acc", 0))
    except ValueError: aid = 0
    sb.table("accounts").update({"budget": max(0, num(request.form.get("budget")))}, returning=MIN
                                ).eq("id", aid).eq("user_id", session["uid"]).eq("kind", "personal").execute()
    session["msg"] = 1
    return redirect(url_for("index"))

@app.route("/rec/new", methods=["POST"])
@login_required
def rec_new():
    f, td = request.form, today()
    amt, typ = num(f.get("amount")), f.get("type")
    try: day = min(28, max(1, int(num(f.get("day")) or 1)))
    except ValueError: day = 1
    try: aid = int(f.get("acc", 0))
    except ValueError: aid = 0
    acc = my_account(aid)
    if typ in ("income", "expense") and amt > 0 and acc and acc.get("kind") == "personal":
        first = td.replace(day=day) if day >= td.day else (td.replace(day=1) + timedelta(days=32)).replace(day=day)
        sb.table("recurring").insert({"user_id": session["uid"], "account_id": aid, "type": typ, "amount": amt,
                                      "label": f.get("label", "").strip()[:120], "day": day,
                                      "next_date": first.isoformat()}, returning=MIN).execute()
        session.pop("rec", None); session["msg"] = 1
    return redirect(url_for("index") + "#settings")

@app.route("/rec/<int:i>/delete", methods=["POST"])
@login_required
def rec_delete(i):
    sb.table("recurring").delete().eq("id", i).eq("user_id", session["uid"]).execute()
    session["msg"] = 1
    return redirect(url_for("index") + "#settings")

@app.route("/password", methods=["POST"])
@login_required
def password():
    old, new = request.form.get("old", ""), request.form.get("new", "")
    u = sb.table("users").select("pw").eq("id", session["uid"]).limit(1).execute().data
    if not u or not check_password_hash(u[0]["pw"], old): session["msg"] = "!pw_bad"
    elif len(new) < 4: session["msg"] = "!short"
    else:
        sb.table("users").update({"pw": generate_password_hash(new)}, returning=MIN).eq("id", session["uid"]).execute()
        session["msg"] = 1
    return redirect(url_for("index") + "#settings")

@app.route("/clear", methods=["POST"])
@login_required
def clear():
    uid, what = session["uid"], request.form.get("what")
    try: aid = int(request.form.get("acc", 0))
    except ValueError: aid = 0
    if what in ("income", "expense", "all") and my_account(aid):
        q = sb.table("tx").delete().eq("account_id", aid)
        if what != "all": q = q.eq("type", what).eq("kind", "normal")
        drop_imgs([r["img"] for r in q.execute().data if r.get("img")])
        session["msg"] = 1
    return redirect(url_for("index"))

@app.route("/print")
@login_required
def print_view():
    uid, L = session["uid"], lang()
    kind = request.args.get("kind", "statement")
    if kind not in ("statement", "income", "expense", "grand"): kind = "statement"
    s, e, key = get_period()
    rep = sb.rpc("report", {"p_user": uid, "p_from": s.isoformat(), "p_to": e.isoformat()}).execute().data
    plabel = T[L]["all_time"] if key == "all" else (s.isoformat() if s == e else f"{s.isoformat()} \u2192 {e.isoformat()}")
    now = (datetime.now(TZ) if TZ else datetime.now()).strftime("%Y-%m-%d %H:%M")
    u = sb.table("users").select("office,phone,logo").eq("id", uid).limit(1).execute().data
    base = dict(kind=kind, rep=rep, plabel=plabel, now=now, user=session["user"], office=(u[0].get("office") if u else "") or "", phone=(u[0].get("phone") if u else "") or "", has_logo=bool(u and u[0].get("logo")),
                auto=request.args.get("auto") == "1", inc=[], exp=[], trs=[], tots={}, acc=None, cur="IQD")
    if kind == "grand":
        base["rep"] = rep = [a for a in rep if a.get("kind") == "personal"]
        for a in rep:
            c = base["tots"].setdefault(a["currency"], dict(inc=0, exp=0, bal=0))
            c["inc"] += a["inc"]; c["exp"] += a["exp"]; c["bal"] += a["bal"]
        return render_template_string(PRINT, **base)
    try: aid = int(request.args.get("acc") or session.get("acc") or 0)
    except ValueError: aid = 0
    acc = next((a for a in rep if a["id"] == aid), None)
    if not acc: abort(404)
    q = (sb.table("tx").select("id,type,amount,label,note,date,kind").eq("account_id", acc["id"])
         .gte("date", s.isoformat()).lte("date", e.isoformat()))
    rows = q.order("date").order("id").limit(5000).execute().data
    base.update(acc=acc, cur=acc["currency"],
                inc=[r for r in rows if r["kind"] == "normal" and r["type"] == "income"],
                exp=[r for r in rows if r["kind"] == "normal" and r["type"] == "expense"],
                trs=[r for r in rows if r["kind"] == "transfer"] if kind == "statement" else [])
    return render_template_string(PRINT, **base)

# ---------------------------------------------------------------- legal cases
def case_row(i):
    r = sb.table("accounts").select("id").eq("id", i).eq("user_id", session["uid"]).eq("kind", "case").limit(1).execute().data
    return r[0] if r else None

def case_fields():
    f = request.form
    def day(k):
        try: return datetime.strptime(f.get(k, ""), "%Y-%m-%d").date().isoformat()
        except ValueError: return None
    return {"name": f.get("name", "").strip()[:80], "client": f.get("client", "").strip()[:80],
            "case_no": f.get("case_no", "").strip()[:40], "court": f.get("court", "").strip()[:80],
            "fee": num(f.get("fee")), "hearing": day("hearing"), "started": day("started")}

@app.route("/case/new", methods=["POST"])
@login_required
def case_new():
    cur, row = request.form.get("currency"), case_fields()
    if not row["name"] or cur not in ("IQD", "USD"):
        return redirect(url_for("index") + "#cases")
    row.update(user_id=session["uid"], kind="case", currency=cur, opening=0)
    if not row.get("started"): row["started"] = today().isoformat()
    r = sb.table("accounts").insert(row).execute().data[0]
    return redirect(url_for("case_page", i=r["id"]))

@app.route("/case/<int:i>")
@login_required
def case_page(i):
    d = sb.rpc("case_view", {"p_user": session["uid"], "p_case": i}).execute().data
    if not d: abort(404)
    c, L = d["case"], lang()
    def group(items):
        g = {}
        for x in items:
            x["amount"] = float(x["amount"])
            gp = g.setdefault(x["date"], dict(n=0, items=[]))
            gp["n"] += x["amount"]; gp["items"].append(x)
        return list(g.items())
    c["fee"] = float(c["fee"])
    fee_v = int(c["fee"]) if c["fee"] == int(c["fee"]) else c["fee"]
    return render_template_string(
        CASE, c=c, cur=c["currency"], inc=float(d["inc"]), exp=float(d["exp"]), n=len(d["items"]), fee_v=fee_v,
        gi=group([x for x in d["items"] if x["type"] == "income"]),
        ge=group([x for x in d["items"] if x["type"] == "expense"]),
        role=d.get("role", "owner"), owner=d.get("owner", ""), members=d.get("members", []), uid=session["uid"],
        show_by=bool(d.get("members")) or d.get("role", "owner") != "owner",
        css=CSS, td=today().isoformat(), tr=dict(T[L]), msg=pop_msg(L),
        items={x["id"]: dict(type=x["type"], amount=x["amount"], label=x["label"], note=x["note"], date=x["date"]) for x in d["items"]})

@app.route("/case/<int:i>/edit", methods=["POST"])
@login_required
def case_edit(i):
    row = case_fields()
    if row["name"] and case_row(i):
        sb.table("accounts").update(row, returning=MIN).eq("id", i).eq("user_id", session["uid"]).execute()
        session["msg"] = 1
    return redirect(url_for("case_page", i=i))

@app.route("/case/<int:i>/status", methods=["POST"])
@login_required
def case_status(i):
    st = request.form.get("status")
    if st in ("open", "closed") and case_row(i):
        sb.table("accounts").update({"status": st}, returning=MIN).eq("id", i).eq("user_id", session["uid"]).execute()
        session["msg"] = 1
    return redirect(url_for("case_page", i=i))

@app.route("/case/<int:i>/delete", methods=["POST"])
@login_required
def case_delete(i):
    uid = session["uid"]
    if case_row(i):
        rows = sb.table("tx").delete().eq("account_id", i).execute().data
        drop_imgs([r["img"] for r in rows if r.get("img")])
        sb.table("accounts").delete().eq("id", i).eq("user_id", uid).execute()
        session["msg"] = 1
    return redirect(url_for("index") + "#cases")

@app.route("/receipt/<int:i>")
@login_required
def receipt(i):
    uid, L = session["uid"], lang()
    t = sb.table("tx").select("id,account_id,type,amount,label,note,date,kind").eq("id", i).limit(1).execute().data
    if not t or t[0]["type"] != "income" or t[0]["kind"] != "normal": abort(404)
    if not sb.rpc("acc_role", {"p_user": uid, "p_acc": t[0]["account_id"]}).execute().data: abort(404)
    a = sb.table("accounts").select("name,client,case_no,currency,kind").eq("id", t[0]["account_id"]).limit(1).execute().data[0]
    u = sb.table("users").select("office,phone,logo").eq("id", uid).limit(1).execute().data
    now = (datetime.now(TZ) if TZ else datetime.now()).strftime("%Y-%m-%d %H:%M")
    r = dict(t[0], amount=float(t[0]["amount"]))
    return render_template_string(RECEIPT, r=r, acc=a, office=(u[0].get("office") if u else "") or "", phone=(u[0].get("phone") if u else "") or "", has_logo=bool(u and u[0].get("logo")), now=now,
                                  auto=request.args.get("auto") == "1")

_SIGNED = {}
def signed(path):
    import time
    hit = _SIGNED.get(path)
    if hit and hit[1] > time.time(): return hit[0]
    r = sb.storage.from_(BUCKET).create_signed_url(path, 3600)
    url = r.get("signedURL") or r.get("signedUrl")
    if url:
        if len(_SIGNED) > 500: _SIGNED.clear()
        _SIGNED[path] = (url, time.time() + 3000)
    return url

def profile_image(col, i):
    u = sb.table("users").select(col).eq("id", i).limit(1).execute().data
    path = u[0].get(col) if u else None
    url = signed(path) if path else None
    if not url: abort(404)
    r = redirect(url); r.headers["Cache-Control"] = "private, max-age=300"
    return r

@app.route("/avatar/<int:i>")
@login_required
def avatar(i):
    return profile_image("avatar", i)

@app.route("/logo")
@login_required
def logo():
    return profile_image("logo", session["uid"])

@app.route("/user/lookup")
@login_required
def user_lookup():
    name = request.args.get("u", "").strip().lower()
    u = find_user(name) if name else None
    if not u: return jsonify(found=False)
    return jsonify(found=True, id=u["id"], username=u["username"], name=u.get("display_name") or "",
                   avatar=bool(u.get("avatar")), me=u["id"] == session["uid"])

@app.route("/profile/save", methods=["POST"])
@login_required
def profile_save():
    name = request.form.get("name", "").strip()[:50]
    sb.table("users").update({"display_name": name}, returning=MIN).eq("id", session["uid"]).execute()
    session["dname"] = name; session["msg"] = 1
    return redirect(url_for("index") + "#settings")

@app.route("/profile/photo", methods=["POST"])
@login_required
def profile_photo():
    kind, uid = request.form.get("kind"), session["uid"]
    if kind not in ("avatar", "logo"): return jsonify(ok=False), 400
    old = (sb.table("users").select(kind).eq("id", uid).limit(1).execute().data or [{}])[0].get(kind)
    if request.form.get("remove"):
        sb.table("users").update({kind: None}, returning=MIN).eq("id", uid).execute()
    else:
        fl = request.files.get("file")
        ext = os.path.splitext(fl.filename or "")[1].lower() if fl else ""
        data = fl.read() if fl else b""
        if ext not in (".jpg", ".jpeg", ".png", ".webp") or not data or len(data) > 3 * 1024 * 1024:
            return jsonify(ok=False), 400
        path = f"{uid}/{kind}-{uuid.uuid4().hex[:10]}{ext}"
        sb.storage.from_(BUCKET).upload(path, data, {"content-type": fl.mimetype or "image/jpeg"})
        sb.table("users").update({kind: path}, returning=MIN).eq("id", uid).execute()
    if old: drop_imgs([old])
    session["pv"] = uuid.uuid4().hex[:6]
    return jsonify(ok=True)

@app.route("/office", methods=["POST"])
@login_required
def office():
    name, phone = request.form.get("office", "").strip()[:80], request.form.get("phone", "").strip()[:30]
    sb.table("users").update({"office": name, "phone": phone}, returning=MIN).eq("id", session["uid"]).execute()
    session["office"] = name; session["phone"] = phone; session["msg"] = 1
    return redirect(url_for("index") + "#settings")

# ---------------------------------------------------------------- dashboard# ---------------------------------------------------------------- dashboard
def get_period():
    td, a = today(), request.args
    def pd(x):
        try: return datetime.strptime(x, "%Y-%m-%d").date()
        except Exception: return None
    s, e = pd(a.get("from", "")), pd(a.get("to", ""))
    if s and e:
        return (e, s, "range") if s > e else (s, e, "range")
    try:
        y, m = map(int, a.get("m", "").split("-"))
        return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1]), "pick"
    except Exception:
        pass
    p = a.get("p", "month")
    if p == "today": return td, td, "today"
    if p == "week": return td - timedelta(days=(td.weekday() - 5) % 7), td, "week"
    if p == "all": return date(2000, 1, 1), date(2100, 12, 31), "all"
    return td.replace(day=1), date(td.year, td.month, calendar.monthrange(td.year, td.month)[1]), "month"

@app.route("/")
@login_required
def index():
    uid, td, L = session["uid"], today(), lang()
    s, e, key = get_period()
    wk = td - timedelta(days=(td.weekday() - 5) % 7)
    args = {"p_user": uid, "p_acc": session.get("acc"), "p_today": td.isoformat(), "p_week": wk.isoformat(),
            "p_month": td.replace(day=1).isoformat(), "p_from": s.isoformat(), "p_to": e.isoformat()}
    if session.get("rec") != td.isoformat():          # monthly recurring entries that are due
        try:
            n = sb.rpc("run_recurring", {"p_user": uid, "p_today": td.isoformat()}).execute().data
            session["rec"] = td.isoformat()
            if n: session["msg"] = "rec_added"
        except Exception as ex:
            app.logger.warning("run_recurring skipped: %s", ex)
    d = sb.rpc("dashboard", args).execute().data
    if not d["acc"]:   # no personal account yet
        sb.table("accounts").insert({"user_id": uid, "name": T[L]["acc_default"], "currency": "IQD"}, returning=MIN).execute()
        d = sb.rpc("dashboard", args).execute().data
    accs = d["accounts"]
    acc = next(a for a in accs if a["id"] == d["acc"])
    session["acc"] = acc["id"]
    invites, transfers, members = d.get("invites", []), d.get("transfers", []), d.get("members", [])
    owned = len([a for a in accs if a.get("role") == "owner"])
    P = d["periods"]
    budget = float(acc.get("budget") or 0)
    bud = None
    if budget > 0:
        spent = P["month"]["e"]; left = budget - spent
        days_left = calendar.monthrange(td.year, td.month)[1] - td.day + 1
        bud = dict(spent=spent, left=left, pct=round(spent / budget * 100), daily=max(left, 0) / days_left,
                   cls="over" if spent > budget else ("warn" if spent >= 0.8 * budget else "ok"))
    budget_v = int(budget) if budget == int(budget) and budget else (budget or "")
    limit = (td + timedelta(days=7)).isoformat()
    soon = sorted([c for c in d["cases"] if c.get("hearing") and c["status"] == "open" and td.isoformat() <= c["hearing"] <= limit],
                  key=lambda c: c["hearing"])
    items_map = {x["id"]: dict(type=x["type"], amount=x["amount"], label=x["label"], note=x["note"], date=x["date"])
                 for x in d["items_in"] + d["items_ex"]}
    accname = {a["id"]: a["name"] for a in accs}; curmap = {a["id"]: a["currency"] for a in accs}
    pack = lambda k: dict(i=P[k]["i"], e=P[k]["e"], n=P[k]["i"] - P[k]["e"])
    stats = [(k, pack(k)) for k in ("today", "week", "month")]
    rng = pack("range")
    bal = {b["id"]: b["b"] for b in d["bal"]}
    tot = {}
    for a in accs:
        tot[a["currency"]] = tot.get(a["currency"], 0) + bal.get(a["id"], 0)
    # daily chart
    dm = {x["d"]: x for x in d["daily"]}
    if key != "all" and (e - s).days <= 62:
        last = min(e, td) if s <= td else e
        days = [s + timedelta(n) for n in range((last - s).days + 1)]
        keys = [x.isoformat() for x in days]; labels = [str(x.day) for x in days]
    else:
        keys = sorted(dm); labels = [k[5:] for k in keys]
    def top(t):
        rows = [[c["l"], c["v"]] for c in d["cats"] if c["t"] == t]
        if len(rows) > 6:
            rows = rows[:6] + [[T[L]["others"], sum(v for _, v in rows[6:])]]
        return rows
    chart = dict(labels=labels, inc=[dm.get(k, {}).get("i", 0) for k in keys],
                 exp=[dm.get(k, {}).get("e", 0) for k in keys],
                 cats=dict(expense=top("expense"), income=top("income")),
                 cur=acc["currency"], dec=0 if acc["currency"] == "IQD" else 2,
                 sym="IQD" if L == "en" else "د.ع", accs=accs, acc=acc["id"], items=items_map, members=members, role=acc.get("role", "owner"))
    def group(items):
        g = {}
        for x in items:
            x["amount"] = float(x["amount"])
            gp = g.setdefault(x["date"], dict(n=0, items=[]))
            gp["n"] += x["amount"]; gp["items"].append(x)
        return list(g.items())
    pf = dict(m=s.strftime("%Y-%m"), a="" if key == "all" else s.isoformat(), b="" if key == "all" else e.isoformat())
    plabel = T[L]["all_time"] if key == "all" else (s.isoformat() if s == e else s.isoformat() + " \u2192 " + e.isoformat())
    for c in d["cases"]:
        c["fee"] = float(c["fee"]); c.setdefault("role", "owner"); c.setdefault("shared", False)
    return render_template_string(
        HOME, accs=accs, acc=acc, bal=bal, tot=tot, stats=stats, rng=rng, chart=chart, tr=dict(T[L]),
        gi=group(d["items_in"]), ge=group(d["items_ex"]), ni=len(d["items_in"]), nex=len(d["items_ex"]),
        cases=d["cases"], invites=invites, transfers=transfers, owned=owned, uid=uid, bud=bud, soon=soon, recs=d.get("recurring", []), accname=accname, curmap=curmap,
        budget_v=budget_v, td=td.isoformat(), css=CSS, user=session["user"], key=key, plabel=plabel, pf=pf,
        msg=pop_msg(L), office=session.get("office", ""), dname=session.get("dname", ""),
        phone=session.get("phone", ""), pv=session.get("pv", "0"),
        labels=sorted({x["label"] for x in d["items_in"] + d["items_ex"] if x["label"]}))

# ---------------------------------------------------------------- entries# ---------------------------------------------------------------- entries
@app.route("/add", methods=["POST"])
@login_required
def add():
    uid, typ, aid = session["uid"], request.form.get("type"), session.get("acc")
    if request.form.get("acc"):
        try: aid = int(request.form["acc"])
        except ValueError: aid = None
    amt = num(request.form.get("amount"))
    ajax = request.headers.get("X-Requested-With") == "fetch"
    def done(ok=True, code=200):
        return (jsonify(ok=ok), code) if ajax else redirect(request.referrer or url_for("index"))
    if typ not in ("income", "expense") or amt <= 0 or not aid:
        return done(False, 400)
    d = request.form.get("date") or today().isoformat()
    try: datetime.strptime(d, "%Y-%m-%d")
    except ValueError: d = today().isoformat()
    path = data = mime = None
    fl = request.files.get("photo")
    if fl and fl.filename and os.path.splitext(fl.filename)[1].lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        path = f"{uid}/{uuid.uuid4().hex}{os.path.splitext(fl.filename)[1].lower()}"
        data, mime = fl.read(), fl.mimetype or "image/jpeg"
    try:
        up = POOL.submit(lambda: sb.storage.from_(BUCKET).upload(path, data, {"content-type": mime})) if path else None
        sb.rpc("add_tx", {"p_user": uid, "p_acc": aid, "p_type": typ, "p_amount": amt,
                          "p_label": request.form.get("label", "").strip()[:120],
                          "p_note": request.form.get("note", "")[:500], "p_date": d, "p_img": path}).execute()
        if up:
            try: up.result()
            except Exception as ex:
                app.logger.error("upload failed: %s", ex)
                sb.table("tx").update({"img": None}, returning=MIN).eq("img", path).execute()
    except Exception as ex:
        app.logger.error("add failed: %s", ex)
        if path: POOL.submit(lambda: sb.storage.from_(BUCKET).remove([path]))
        return done(False, 403 if "forbidden" in str(ex) else 500)
    return done()

@app.route("/delete/<int:i>", methods=["POST"])
@login_required
def delete(i):
    r = sb.rpc("del_tx", {"p_user": session["uid"], "p_id": i}).execute().data     # checks your role in SQL
    if r and r.get("imgs"):
        drop_imgs(r["imgs"])
    if request.headers.get("X-Requested-With") == "fetch":
        return "", 204
    return redirect(request.referrer or url_for("index"))

@app.route("/transfer", methods=["POST"])
@login_required
def transfer():
    f = request.form
    ajax = request.headers.get("X-Requested-With") == "fetch"
    try: a, b = int(f.get("from", 0)), int(f.get("to", 0))
    except ValueError: a = b = 0
    d = f.get("date") or today().isoformat()
    try: datetime.strptime(d, "%Y-%m-%d")
    except ValueError: d = today().isoformat()
    amt, amt_in = num(f.get("amount")), num(f.get("amount_in")) or None
    ok = False
    if a and b and a != b and amt > 0:
        ok = sb.rpc("transfer", {"p_user": session["uid"], "p_from": a, "p_to": b, "p_amount": amt,
                                 "p_amount_in": amt_in, "p_note": f.get("note", "").strip()[:200], "p_date": d}).execute().data
    if ajax:
        return jsonify(ok=bool(ok)), (200 if ok else 400)
    session["msg"] = 1 if ok else "!err"
    return redirect(url_for("index"))

@app.route("/share/add", methods=["POST"])
@login_required
def share_add():
    uid, f = session["uid"], request.form
    try: aid = int(f.get("acc", 0))
    except ValueError: aid = 0
    acc, role = my_account(aid), f.get("role")
    u = find_user(f.get("username", "").strip().lower())
    if acc and acc.get("kind") in ("personal", "case") and role in ("editor", "viewer"):
        if not u: session["msg"] = "!share_err_user"
        elif u["id"] == uid: session["msg"] = "!share_self"
        else:
            ex = sb.table("account_members").select("account_id").eq("account_id", aid).eq("user_id", u["id"]).limit(1).execute().data
            if ex:
                sb.table("account_members").update({"role": role}, returning=MIN).eq("account_id", aid).eq("user_id", u["id"]).execute()
            else:
                sb.table("account_members").insert({"account_id": aid, "user_id": u["id"], "role": role, "accepted": False}, returning=MIN).execute()
            session["msg"] = "share_ok"
    if acc and acc.get("kind") == "case":
        return redirect(url_for("case_page", i=aid))
    return redirect(url_for("index") + "#settings")

@app.route("/share/remove", methods=["POST"])
@login_required
def share_remove():
    uid, f = session["uid"], request.form
    try: aid, target = int(f.get("acc", 0)), int(f.get("uid", 0))
    except ValueError: aid = target = 0
    if aid and target and (target == uid or my_account(aid)):      # you can leave, the owner can remove anyone
        sb.table("account_members").delete().eq("account_id", aid).eq("user_id", target).execute()
        if target == uid and session.get("acc") == aid: session.pop("acc", None)
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    session["msg"] = 1
    nx = f.get("next", "")
    if re.fullmatch(r"/case/\d+|/#cases", nx):
        return redirect(nx)
    return redirect(url_for("index") + "#settings")

@app.route("/share/respond", methods=["POST"])
@login_required
def share_respond():
    uid, f = session["uid"], request.form
    try: aid = int(f.get("acc", 0))
    except ValueError: aid = 0
    if aid and f.get("action") == "accept":
        sb.table("account_members").update({"accepted": True}, returning=MIN).eq("account_id", aid).eq("user_id", uid).execute()
        k = sb.table("accounts").select("kind").eq("id", aid).limit(1).execute().data
        if k and k[0]["kind"] == "case":
            session["msg"] = 1
            return redirect(url_for("case_page", i=aid))
        session["acc"] = aid
    elif aid:
        sb.table("account_members").delete().eq("account_id", aid).eq("user_id", uid).execute()
    session["msg"] = 1
    return redirect(url_for("index"))

@app.route("/img/<int:owner>/<name>")
@login_required
def img(owner, name):
    if owner != session["uid"]:            # photos added by a member of a shared account
        t = sb.table("tx").select("account_id").eq("img", f"{owner}/{name}").limit(1).execute().data
        if not t or not sb.rpc("acc_role", {"p_user": session["uid"], "p_acc": t[0]["account_id"]}).execute().data:
            abort(404)
    r = sb.storage.from_(BUCKET).create_signed_url(f"{owner}/{name}", 600)
    url = r.get("signedURL") or r.get("signedUrl")
    if not url: abort(404)
    return redirect(url)

# ---------------------------------------------------------------- design
STYLE = """
:root{--bg:#FAF9F5;--card:#fff;--soft:#F0EEE6;--edge:#E4E1D6;--tx:#1F1E1D;--mut:#6F6D66;--acc:#D97757;--in:#2F7D5B;--ex:#C2412F;
--inb:#E8F3ED;--exb:#F8E9E6;--sh:0 1px 2px rgba(31,30,29,.05),0 10px 28px rgba(31,30,29,.07);
--field:#fff;--navbg:rgba(255,255,255,.95);--hero1:#fff;--hero2:#FBEDE5;--hero2u:#E7EEF8;--tint:#FFF7F2;--tintu:#F1F5FB;--glow:#F7E8DF;--hov:#cfcabb}
html.dark{--bg:#1B1A18;--card:#262522;--soft:#33312D;--edge:#3A3834;--tx:#F2F0EA;--mut:#A39F95;--acc:#E39274;--in:#5CC596;--ex:#F28C79;
--inb:rgba(92,197,150,.14);--exb:rgba(242,140,121,.14);--sh:0 1px 2px rgba(0,0,0,.4),0 10px 28px rgba(0,0,0,.35);
--field:#2E2C29;--navbg:rgba(38,37,34,.96);--hero1:#2A2825;--hero2:#3A2B24;--hero2u:#23303F;--tint:#34271F;--tintu:#1F2A38;--glow:#2C211B;--hov:#5a564f}
body.c-USD{--acc:#4A6FA5}
html.dark body.c-USD{--acc:#86A9DB}
html.dark input,html.dark textarea,html.dark select{color-scheme:dark}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{-webkit-text-size-adjust:100%}
html,body{margin:0;min-height:100%}
body{font-family:'Vazirmatn',-apple-system,'Segoe UI',sans-serif;color:var(--tx);background:var(--bg);
padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom);overflow-x:hidden;overscroll-behavior-y:none;-webkit-touch-callout:none}
.blob{display:none}
a,button,.acc,.pill{touch-action:manipulation;-webkit-user-select:none;user-select:none}
input,textarea{-webkit-user-select:text;user-select:text}
.wrap{max-width:1000px;margin:auto;padding:16px 16px 150px}
.glass{background:var(--card);border:1px solid var(--edge);border-radius:22px;box-shadow:var(--sh)}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;gap:8px}
.top b{font-weight:800}.top small{color:var(--mut);display:block;font-weight:300}
.hic{display:flex;gap:8px}
.hic button{width:42px;height:42px;border-radius:14px;border:1px solid var(--edge);background:var(--card);color:var(--tx);display:grid;place-items:center;cursor:pointer;box-shadow:var(--sh)}
.hic svg{width:21px;height:21px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.pills{display:flex;gap:6px;align-items:center}
.pill{padding:7px 13px;border-radius:99px;font-size:13px;color:var(--tx);text-decoration:none;background:var(--card);border:1px solid var(--edge);white-space:nowrap;font-family:inherit;cursor:pointer}
.pill.on{background:var(--tx);color:var(--bg);border-color:var(--tx);font-weight:700}
.ptitle{margin:4px 2px 14px;font-size:20px;font-weight:800}
.accs{display:flex;gap:10px;overflow-x:auto;padding:2px 2px 12px;scrollbar-width:none}
.accs::-webkit-scrollbar{display:none}
.acc{flex:none;min-width:128px;padding:11px 15px;border-radius:18px;text-decoration:none;color:var(--tx);background:var(--card);border:1px solid var(--edge);font-family:inherit;text-align:start;cursor:pointer}
.acc b{display:block;font-weight:700;font-size:14px}.acc small{color:var(--mut);direction:ltr;display:block;font-size:12px;text-align:start}
.acc.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc);background:var(--tint)}
body.c-USD .acc.on{background:var(--tintu)}
.acc.add{display:grid;place-items:center;color:var(--mut)}
body[data-tab=cases] .accs,body[data-tab=settings] .accs{display:none}
.grand{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;margin-bottom:12px;gap:10px;flex-wrap:wrap}
.grand span{color:var(--mut);font-size:13px}.grand div{display:flex;gap:16px;direction:ltr;flex-wrap:wrap}
.grand b{font-weight:800;font-size:17px}
.hero{padding:22px;margin-bottom:12px;background:linear-gradient(135deg,var(--hero1) 30%,var(--hero2))}
body.c-USD .hero{background:linear-gradient(135deg,var(--hero1) 30%,var(--hero2u))}
.hl{display:flex;justify-content:space-between;align-items:center;color:var(--mut);font-size:14px;gap:8px}
.hl em{font-style:normal;color:var(--acc);border:1px solid var(--acc);border-radius:99px;padding:1px 9px;font-size:12px;margin-inline-start:6px}
.hb{font-size:clamp(34px,9vw,52px);font-weight:800;letter-spacing:-1px;direction:ltr;margin:8px 0 2px;text-align:start}
.hero small{color:var(--mut)}
.sumc{padding:18px;margin-bottom:12px}
.sumc .lab{color:var(--mut);font-size:13px;display:block}
.sumc .one{font-size:clamp(26px,8vw,40px);font-weight:800;direction:ltr;display:block;margin:4px 0}
.trio{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}
.trio span{display:block;color:var(--mut);font-size:12px}
.trio b{font-size:clamp(13px,3.8vw,19px);font-weight:800;direction:ltr;display:block;margin-top:3px;word-break:break-word}
.in{color:var(--in)}.ex{color:var(--ex)}
.ratio{height:9px;border-radius:9px;background:var(--inb);margin-top:14px;overflow:hidden;direction:ltr}
.ratio i{display:block;height:100%;background:var(--ex);border-radius:9px}
.ratiol{display:flex;justify-content:space-between;font-size:12px;color:var(--mut);margin-top:6px}
.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
.st{padding:12px 10px;font-size:12px}
.st h4{margin:0 0 8px;font-weight:700;font-size:13px}
.st div{display:flex;justify-content:space-between;gap:4px;direction:ltr;margin:2px 0;flex-wrap:wrap}
.st .n{border-top:1px solid var(--edge);padding-top:5px;margin-top:5px;font-weight:700}
.qa{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.qa button{padding:15px;border-radius:18px;border:1px solid var(--edge);font:inherit;font-weight:700;cursor:pointer}
.qa .i{background:var(--inb);color:var(--in)}.qa .e{background:var(--exb);color:var(--ex)}
.pbar{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;margin-bottom:12px}
.pbar span{font-size:13px;color:var(--mut);direction:ltr}
.charts{display:grid;gap:12px;margin-bottom:6px}
@media(min-width:820px){.charts{grid-template-columns:1.5fr 1fr}.row3,.trio{gap:14px}}
.card{padding:16px}.card h3{margin:0 0 12px;font-size:15px;font-weight:700}
.cv{position:relative;height:230px}.c2w{position:relative;height:190px;margin-bottom:10px}
.seg{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:5px;border-radius:15px;background:var(--soft);margin-bottom:14px}
.seg button{border:0;border-radius:11px;padding:10px;font:inherit;color:var(--tx);background:none;cursor:pointer}
.seg button.on{background:var(--card);box-shadow:0 1px 3px rgba(0,0,0,.14);font-weight:700}
.seg button.on.income{background:var(--inb);color:var(--in)}.seg button.on.expense{background:var(--exb);color:var(--ex)}
.lg{display:grid;grid-template-columns:12px 1fr auto auto;gap:8px;align-items:center;font-size:13px;margin:7px 0}
.lg i{width:10px;height:10px;border-radius:50%}.lg b{font-weight:700}.lg small{color:var(--mut);direction:ltr;min-width:70px;text-align:end}
.day{display:flex;justify-content:space-between;color:var(--mut);font-size:13px;margin:16px 6px 8px;direction:ltr}
.item{display:flex;gap:12px;align-items:center;padding:12px 14px;margin-bottom:8px;border-radius:18px}
.dot{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;font-size:18px;flex:none}
.dot.income{background:var(--inb);color:var(--in)}.dot.expense{background:var(--exb);color:var(--ex)}
.meta{flex:1;min-width:0}.meta b{display:block;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.meta small{color:var(--mut);font-weight:300}
.amt{font-weight:800;direction:ltr;white-space:nowrap}.amt.income{color:var(--in)}.amt.expense{color:var(--ex)}
.thumb{width:40px;height:40px;border-radius:10px;object-fit:cover;border:1px solid var(--edge)}
.x{background:none;border:0;color:var(--mut);font-size:17px;padding:4px;cursor:pointer}
.empty{text-align:center;color:var(--mut);padding:30px 10px;font-size:14px}
.pend{opacity:.7}
.spin{width:15px;height:15px;border:2px solid var(--edge);border-top-color:var(--acc);border-radius:50%;animation:sp .7s linear infinite;flex:none}
@keyframes sp{to{transform:rotate(360deg)}}
.chips{display:flex;gap:8px;margin:0 0 12px;flex-wrap:wrap}
/* nav */
.nav{position:fixed;z-index:8;bottom:calc(12px + env(safe-area-inset-bottom));inset-inline:14px;max-width:460px;margin:auto;display:grid;grid-template-columns:1fr 1fr 78px 1fr 1fr;align-items:end;padding:8px 6px 7px;border-radius:32px;background:var(--navbg);border:1px solid var(--edge);box-shadow:0 10px 30px rgba(31,30,29,.16)}
.nb{background:none;border:0;color:var(--mut);font:inherit;font-size:11px;display:flex;flex-direction:column;align-items:center;gap:3px;padding:6px 0 8px;cursor:pointer;position:relative;transition:color .25s}
.nb svg,.nav .add svg{width:24px;height:24px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;transition:transform .35s cubic-bezier(.3,1.6,.5,1),stroke .25s}
.nb.on{color:var(--tx);font-weight:700}.nb.on svg{transform:translateY(-3px) scale(1.14);stroke:var(--acc)}
.nb:after{content:"";position:absolute;bottom:0;width:5px;height:5px;border-radius:50%;background:var(--acc);transform:scale(0);transition:transform .3s}
.nb.on:after{transform:scale(1)}
.nav .add{width:64px;height:64px;border-radius:50%;margin:-34px auto 0;border:4px solid var(--bg);color:#fff;background:var(--acc);box-shadow:0 10px 24px rgba(217,119,87,.45);display:grid;place-items:center;cursor:pointer;transition:transform .2s}
body.c-USD .nav .add{box-shadow:0 10px 24px rgba(74,111,165,.45)}
.nav .add:active{transform:scale(.92)}.nav .add svg{width:28px;height:28px;stroke:#fff;stroke-width:2.4}
.tab{display:none}.tab.on{display:block}
.sv{display:none}.sv.on{display:block}
@media(prefers-reduced-motion:no-preference){.tab.on{animation:fade .3s ease-out}@keyframes fade{from{opacity:0;transform:translateY(10px)}}
.sheet.open form{animation:up .28s ease-out}@keyframes up{from{transform:translateY(60px);opacity:0}}
.pwa .arrow{animation:bob 1.1s ease-in-out infinite}@keyframes bob{50%{transform:translateY(6px)}}}
/* sheets and forms */
.sheet{position:fixed;inset:0;display:none;align-items:flex-end;background:rgba(31,30,29,.4);z-index:20}
.sheet.open{display:flex}
.sheet form{width:100%;max-width:560px;margin:auto;padding:20px 18px calc(24px + env(safe-area-inset-bottom));border-radius:26px 26px 0 0;background:var(--card);max-height:92vh;overflow:auto;box-shadow:0 -10px 40px rgba(0,0,0,.18)}
.sheet h3{margin:0 0 14px}
label{display:block;font-size:13px;color:var(--mut);margin:12px 4px 5px}
input,textarea{width:100%;padding:13px 14px;border-radius:14px;border:1px solid var(--edge);background:var(--field);color:var(--tx);font:inherit;font-size:16px;outline:none;color-scheme:light}
input:focus,textarea:focus{border-color:var(--acc);box-shadow:0 0 0 3px rgba(217,119,87,.15)}
input[type=file]{padding:10px}
.big{font-size:28px!important;font-weight:800;direction:ltr;text-align:center}
.frow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.btn{display:block;width:100%;margin-top:14px;padding:15px;border:0;border-radius:16px;font:inherit;font-weight:700;font-size:16px;color:#fff;background:var(--acc);cursor:pointer;text-align:center;text-decoration:none}
.btn.ghost{background:var(--soft);color:var(--tx);border:1px solid var(--edge)}
.btn.red{background:var(--ex)}.btn.red:disabled{opacity:.35}
.btn.sm{padding:12px;font-size:15px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.chk{display:flex;gap:10px;align-items:center;font-size:14px;color:var(--tx);margin:14px 0 0}
.chk input{width:22px;height:22px;flex:none;padding:0}
.toast{position:fixed;top:calc(14px + env(safe-area-inset-top));inset-inline:16px;max-width:420px;margin:auto;padding:13px 16px;z-index:50;text-align:center;font-size:14px;color:var(--ex);border-color:rgba(194,65,47,.4)}
.toast.ok{color:var(--in);border-color:rgba(47,125,91,.4)}
/* settings */
.menu{display:flex;align-items:center;justify-content:space-between;width:100%;padding:17px 18px;margin-bottom:10px;font:inherit;font-size:15px;color:var(--tx);text-align:start;cursor:pointer;border-radius:18px}
.menu i{color:var(--mut);font-style:normal;font-size:20px}
.menu.red{color:var(--ex)}
.back{display:inline-block;margin:0 0 12px;padding:8px 14px;border-radius:99px;border:1px solid var(--edge);background:var(--card);font:inherit;font-size:13px;color:var(--tx);cursor:pointer;text-decoration:none}
.sec{padding:16px;margin-bottom:12px}.sec h3{margin:0 0 10px;font-size:15px}.sec p{color:var(--mut);font-size:13px;margin:4px 0 10px}
.setrow{display:flex;align-items:center;gap:8px;padding:11px 0;border-top:1px solid var(--edge);flex-wrap:wrap}
.setrow:first-of-type{border-top:0}
.setrow .nm{flex:1;min-width:130px}.setrow .nm b{display:block;font-weight:700}.setrow .nm small{color:var(--mut);font-size:12px}
.mini{padding:8px 13px;border-radius:12px;border:1px solid var(--edge);background:var(--soft);color:var(--tx);font:inherit;font-size:13px;cursor:pointer;text-decoration:none}
.mini.red{border-color:rgba(194,65,47,.45);color:var(--ex);background:var(--exb)}
.danger{border-color:rgba(194,65,47,.45)}
/* legal cases */
.cc{display:block;padding:15px 16px;margin-bottom:10px;text-decoration:none;color:var(--tx)}
.cch{display:flex;justify-content:space-between;align-items:center;gap:8px}.cch b{font-size:16px}
.cc small{color:var(--mut);display:block;margin:2px 0 10px}
.ccn{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center;border-top:1px solid var(--edge);padding-top:10px}
.ccn span{display:block;font-size:11px;color:var(--mut)}.ccn b{font-size:13px;direction:ltr;display:block;margin-top:2px}
.badge{font-size:12px;padding:3px 10px;border-radius:99px;font-weight:700}
.badge.open{background:var(--inb);color:var(--in)}.badge.closed{background:var(--soft);color:var(--mut)}
.cn{margin:8px 0 6px;font-size:24px;font-weight:800;line-height:1.4}
.cm{display:grid;gap:6px;margin-top:6px}.cm span{color:var(--mut);font-size:12px;display:block}.cm b{font-weight:500}
.stat4{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.stat4>div{padding:13px 14px}.stat4 span{display:block;font-size:12px;color:var(--mut)}.stat4 b{display:block;font-size:17px;direction:ltr;text-align:start;margin-top:3px}
.stat4 .wide{grid-column:1/-1}
.prn{flex-wrap:wrap;margin-bottom:14px}
/* app install banner */
.pwa{position:fixed;inset-inline:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:30;padding:16px;display:none;max-width:520px;margin:auto}
.hasnav .pwa{bottom:calc(104px + env(safe-area-inset-bottom))}
.pwa.show{display:block}
.pwa h4{margin:0 0 10px;font-size:15px;padding-inline-end:30px}
.pwa p{margin:7px 0;font-size:13.5px;color:var(--tx);display:flex;gap:10px;align-items:center}
.pwa p b{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--acc);color:#fff;font-size:12px;flex:none}
.pwa svg{width:18px;height:18px;vertical-align:-4px;color:var(--acc)}
.pwa .cl{position:absolute;top:10px;inset-inline-end:12px;background:none;border:0;color:var(--mut);font-size:18px;padding:4px}
.pwa .go{margin-top:8px;padding:12px}
.pwa .arrow{text-align:center;font-size:24px;color:var(--acc);line-height:1}
.auth{min-height:100vh;display:grid;place-items:center;padding:20px}
.auth form{width:100%;max-width:380px;padding:30px 24px}
.auth h2{margin:0 0 4px;font-size:26px;font-weight:800}.auth p{text-align:center;color:var(--mut);font-size:14px}
.auth a{color:var(--acc)}.err{background:var(--exb);border:1px solid rgba(194,65,47,.4);padding:10px;border-radius:13px;font-size:14px;margin-top:10px;color:var(--ex)}
.off{min-height:100vh;display:grid;place-items:center;padding:20px;text-align:center}
.off .glass{padding:34px 26px;max-width:380px}.off h2{margin:8px 0}.off p{color:var(--mut);font-size:14px;margin:4px 0}

/* ---- case sharing ---- */
.badge.sh{background:#EAF0F8;color:#3F5F8F;display:inline-block;margin:0 0 10px}
.sub{margin:22px 2px 10px;font-size:15px;color:var(--mut)}
#caselist2{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.note-banner{padding:12px 16px;margin-bottom:12px;font-size:14px;background:#F1F5FB;border-color:#cfdcf0}
.x.rc{text-decoration:none;font-size:16px}
/* ---- features ---- */
.av{position:relative;display:inline-grid;place-items:center;width:40px;height:40px;border-radius:50%;background:var(--soft);color:var(--acc);font-weight:800;overflow:hidden;flex:none}
.av img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.av.sm{width:34px;height:34px;font-size:14px}.av.big{width:54px;height:54px;font-size:22px}.av.xl{width:96px;height:96px;font-size:38px}
.who{display:flex;align-items:center;gap:10px;background:none;border:0;padding:0;font:inherit;color:var(--tx);text-align:start;cursor:pointer}
.who small{display:block;color:var(--mut);font-weight:300}.who b{font-weight:800}
.pcard{display:flex;align-items:center;gap:14px;width:100%;padding:16px;margin-bottom:14px;font:inherit;color:var(--tx);text-align:start;cursor:pointer;border-radius:20px}
.pcard div{flex:1}.pcard b{display:block;font-size:17px}.pcard small{color:var(--mut)}.pcard i{color:var(--mut);font-style:normal;font-size:20px}
.menu{gap:12px}.menu span{flex:1}
.menu .mi{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:var(--soft);color:var(--acc);flex:none}
.mi svg{width:21px;height:21px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.ptop{display:flex;flex-direction:column;align-items:center;gap:12px}.pact{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin:6px 0 10px}
.lhprev{display:flex;align-items:center;gap:14px;padding:12px;border:1px dashed var(--edge);border-radius:14px;margin:6px 0 10px}
.lgbox{width:64px;height:64px;border-radius:12px;background:var(--soft);display:grid;place-items:center;overflow:hidden;flex:none}.lgbox img{max-width:100%;max-height:100%;object-fit:contain}
.lhprev small{display:block;color:var(--mut)}
#sh-prev{min-height:56px;margin-top:8px}
.pv{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--acc);border-radius:14px;background:var(--soft)}
.pv div{flex:1}.pv b{display:block}.pv small{color:var(--mut)}.pv i{color:var(--in);font-style:normal;font-weight:800;font-size:20px}
.pv.bad{border-color:var(--ex);color:var(--ex);background:transparent}
.hint{color:var(--mut)}
select{width:100%;padding:13px 14px;border-radius:14px;border:1px solid var(--edge);background:var(--field);color:var(--tx);font:inherit;font-size:16px;outline:none}
.srch{margin:0 0 10px}
.x.ed{font-size:16px}
.alert{padding:14px 16px;margin-bottom:12px;border-color:rgba(217,119,87,.5);background:var(--tint)}
.alert b{display:block;margin-bottom:6px}
.alert a{display:flex;justify-content:space-between;gap:10px;padding:7px 0;color:var(--tx);text-decoration:none;border-top:1px solid var(--edge);font-size:14px}
.alert a i{font-style:normal;color:var(--acc);direction:ltr;font-weight:700}
.bgt{padding:16px 18px;margin-bottom:12px}
.bgt .track{height:11px;border-radius:11px;background:var(--soft);overflow:hidden;margin:12px 0 8px;direction:ltr}
.bgt .track i{display:block;height:100%;border-radius:11px;transition:width .6s}
.bgt .track i.ok{background:var(--in)}.bgt .track i.warn{background:#D9A227}.bgt .track i.over{background:var(--ex)}
.bgt .bl{display:flex;justify-content:space-between;font-size:13px;direction:ltr}
.bgt small{display:block;color:var(--mut);margin-top:6px;line-height:1.7}
/* ---- polish + desktop ---- */
body{background:radial-gradient(900px 420px at 100% -8%,var(--glow) 0%,transparent 62%),var(--bg);font-variant-numeric:tabular-nums}
.hero{position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;inset-inline-end:-70px;top:-90px;width:260px;height:260px;border-radius:50%;background:radial-gradient(circle,rgba(217,119,87,.20),transparent 70%)}
body.c-USD .hero:before{background:radial-gradient(circle,rgba(74,111,165,.20),transparent 70%)}
.hero>*{position:relative}
.item,.cc,.acc,.btn,.mini,.pill{transition:box-shadow .2s,transform .2s,background .2s,border-color .2s}
@media(hover:hover){.item:hover,.cc:hover,.acc:hover{box-shadow:0 10px 28px rgba(31,30,29,.10);transform:translateY(-1px)}.btn:hover{filter:brightness(1.05)}.mini:hover,.pill:hover{border-color:var(--hov)}}
.btn{box-shadow:0 6px 16px rgba(217,119,87,.28)}.btn.ghost,.btn.red{box-shadow:none}
.brand,.dsk,.addt{display:none}
#caselist{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}.cc{margin:0}
@media(min-width:900px){
 .hic{display:none}
 .brand{display:flex;align-items:center;gap:10px;padding:4px 10px 20px;font-size:17px;order:-2}
 .brand img{width:34px;height:34px;border-radius:10px}
 .dsk{display:flex}
 .nav{top:0;bottom:0;inset-inline-start:0;inset-inline-end:auto;width:250px;max-width:none;margin:0;border-radius:0;border:0;border-inline-end:1px solid var(--edge);box-shadow:none;background:var(--card);display:flex;flex-direction:column;align-items:stretch;gap:4px;padding:22px 16px}
 .nb{flex-direction:row;gap:12px;font-size:14.5px;padding:12px 14px;border-radius:14px;justify-content:flex-start;text-align:start}
 .nb:hover{background:var(--soft)}
 .nb.on{background:var(--soft)}.nb.on svg{transform:none}.nb:after{display:none}
 .nav .add{order:-1;width:100%;height:auto;margin:0 0 14px;border-radius:14px;border:0;padding:13px;gap:10px;display:flex;align-items:center;justify-content:center;font:inherit;font-weight:700;font-size:15px;box-shadow:0 6px 16px rgba(217,119,87,.3)}
 .nav .add svg{width:20px;height:20px}.addt{display:inline}
 .hasnav .wrap{margin-inline-start:250px;max-width:none;padding:30px 44px 60px}
 .tab{max-width:1080px}
 .top{margin-bottom:20px}
 .accs{flex-wrap:wrap;overflow:visible}
 .hgrid{display:grid;grid-template-columns:1.35fr 1fr;gap:16px;margin-bottom:16px}
 .hside{display:flex;flex-direction:column;gap:12px}.hside .qa,.hside .grand{margin:0}.hside .grand{flex:1;align-content:center}
 .hero{padding:30px;margin:0}.hb{font-size:58px}
 .row3{gap:16px}.st{padding:18px 20px;font-size:13px}.st h4{font-size:14px}
 .split{display:grid;grid-template-columns:330px 1fr;gap:24px;align-items:start}
 .split .side{position:sticky;top:20px}
 #t-settings{max-width:680px}
 .sheet{align-items:center}.sheet form{border-radius:24px;margin:auto}
 .stat4{grid-template-columns:repeat(4,1fr)}
 .charts{grid-template-columns:1.6fr 1fr}
}

/* ---- sharing + transfers ---- */
.qa .t{grid-column:1/-1;background:var(--soft);color:var(--tx)}
.acc b{white-space:nowrap}
.meta small+small{display:block}

/* ---- phone: standard, compact sizes + swipe animation ---- */
@media(max-width:899px){
 body{font-size:14px}
 .wrap{padding:12px 12px 110px}
 .glass{border-radius:18px}
 .top{margin-bottom:10px}
 .who .av{width:36px;height:36px;font-size:15px}
 .hic button{width:38px;height:38px;border-radius:12px}.hic svg{width:19px;height:19px}
 .pill{padding:6px 11px;font-size:12px}
 .accs{padding-bottom:9px;gap:8px}
 .acc{min-width:108px;padding:8px 12px;border-radius:15px}.acc b{font-size:13px}.acc small{font-size:11px}
 .hero{padding:16px;margin-bottom:10px}.hb{font-size:clamp(28px,8vw,38px);margin:5px 0 1px}
 .hl{font-size:13px}.hl em{font-size:11px}
 .qa{gap:8px;margin-bottom:10px}.qa button{padding:11px;font-size:14px;border-radius:15px}
 .row3{gap:8px;margin-bottom:10px}.st{padding:10px 8px;font-size:11px}.st h4{font-size:12px;margin-bottom:6px}
 .grand{padding:10px 14px;margin-bottom:10px}.grand b{font-size:15px}.grand span{font-size:12px}
 .bgt{padding:12px 14px;margin-bottom:10px}
 .sumc{padding:13px 14px;margin-bottom:10px}.sumc .one{font-size:clamp(22px,7vw,30px)}.trio b{font-size:clamp(12px,3.4vw,16px)}
 .pbar{padding:8px 12px;margin-bottom:10px}
 .alert{padding:11px 14px;margin-bottom:10px}
 .item{padding:9px 12px;gap:10px;border-radius:15px;margin-bottom:6px}
 .dot{width:32px;height:32px;border-radius:10px;font-size:15px}
 .meta b{font-size:14px}.meta small{font-size:12px}.amt{font-size:14px}
 .thumb{width:34px;height:34px;border-radius:9px}
 .day{font-size:12px;margin:12px 4px 6px}
 .btn{padding:12px;font-size:15px;border-radius:14px;margin-top:12px}.btn.sm{padding:10px;font-size:14px}
 .mini{padding:6px 11px;font-size:12px}
 .ptitle{font-size:18px;margin:2px 2px 10px}
 .menu{padding:12px 14px;font-size:14px;margin-bottom:8px}
 .menu .mi{width:34px;height:34px;border-radius:11px}.mi svg{width:19px;height:19px}
 .pcard{padding:13px;margin-bottom:10px}.pcard b{font-size:15px}.av.big{width:46px;height:46px;font-size:19px}.av.xl{width:80px;height:80px;font-size:32px}
 .sec{padding:13px;margin-bottom:10px}.sec h3{font-size:14px}.setrow{padding:9px 0}
 .cc{padding:12px 14px;margin-bottom:8px}.cch b{font-size:15px}.ccn b{font-size:12px}
 .cn{font-size:20px}.stat4{gap:8px}.stat4>div{padding:10px 12px}.stat4 b{font-size:15px}.stat4 span{font-size:11px}
 .card{padding:13px}.cv{height:190px}
 .nav{bottom:calc(8px + env(safe-area-inset-bottom));inset-inline:12px;padding:5px 4px 4px;border-radius:26px;grid-template-columns:1fr 1fr 66px 1fr 1fr}
 .nb{font-size:10px;padding:4px 0 6px;gap:2px}.nb svg{width:21px;height:21px}
 .nav .add{width:52px;height:52px;margin-top:-26px;border-width:3px}.nav .add svg{width:24px;height:24px}
 .hasnav .pwa{bottom:calc(88px + env(safe-area-inset-bottom))}
 .sheet form{padding:16px 14px calc(18px + env(safe-area-inset-bottom));border-radius:22px 22px 0 0}
 .sheet h3{font-size:16px;margin-bottom:10px}
 label{font-size:12px;margin:9px 4px 4px}
 input,textarea,select{padding:10px 12px;border-radius:12px}
 .big{font-size:24px!important}
 .seg button{padding:8px;font-size:13px}
 .toast{font-size:13px;padding:10px 14px}
}
@media(prefers-reduced-motion:no-preference){.tab.on.swp{animation:swipe .26s ease-out}@keyframes swipe{from{opacity:0;transform:translateX(var(--sx,30px))}}}
"""
VER = hashlib.md5(STYLE.encode()).hexdigest()[:8]
HEAD = """<script>(function(){try{var m=localStorage.getItem('theme')||'auto';if(m==='dark'||(m==='auto'&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}})()</script>

<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#FAF9F5">
<meta name="apple-mobile-web-app-title" content="جزدانەکەم">
<meta name="application-name" content="جزدانەکەم">
<meta name="mobile-web-app-capable" content="yes">
<meta name="format-detection" content="telephone=no">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;500;700;800&display=swap">
"""
CSS = HEAD + '<link rel="stylesheet" href="/app.css?v=' + VER + '">'
CSS_INLINE = HEAD + "<style>" + STYLE + "</style>"

LANGS = """<div class="pills">{% for c,n in [('ku','کوردی'),('ar','عربي'),('en','EN')] %}<a class="pill {{'on' if L==c}}" href="/lang/{{c}}">{{n}}</a>{% endfor %}</div>"""

PWA = """
<div class="glass pwa" id="pwa"><button class="cl" onclick="pwaHide()" aria-label="{{t('pwa_close')}}">✕</button>
<h4>📲 {{t('pwa_t')}}</h4>
<div id="pwa-ios"><p><b>1</b><span>{{t('pwa_1')}}
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V3M8 7l4-4 4 4"/><path d="M6 11H5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1"/></svg></span></p>
<p><b>2</b><span>{{t('pwa_2')}}</span></p><div class="arrow">⌄</div></div>
<p id="pwa-sf" style="display:none">{{t('pwa_safari')}}</p>
<button class="btn go" id="pwa-go" style="display:none" onclick="pwaInstall()">{{t('pwa_btn')}}</button></div>
<script>
(function(){
 if('serviceWorker' in navigator)addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})});
 var ua=navigator.userAgent,ios=/iphone|ipad|ipod/i.test(ua)||(/Macintosh/.test(ua)&&navigator.maxTouchPoints>1);
 var standalone=navigator.standalone||matchMedia('(display-mode: standalone)').matches||/WalletApp/.test(ua);
 var last=0;try{last=+localStorage.getItem('pwa_x')||0}catch(e){}
 if(standalone||Date.now()-last<3*864e5)return;
 var box=document.getElementById('pwa'),ev=null,$=function(i){return document.getElementById(i)};
 window.pwaHide=function(){box.classList.remove('show');try{localStorage.setItem('pwa_x',Date.now())}catch(e){}};
 window.pwaInstall=function(){if(!ev)return;ev.prompt();ev.userChoice.then(function(){ev=null;box.classList.remove('show')})};
 addEventListener('appinstalled',function(){box.classList.remove('show')});
 if(ios){
  var safari=/safari/i.test(ua)&&!/crios|fxios|edgios|opios|gsa|instagram|fban|fbav|line[/]/i.test(ua);
  if(!safari){$('pwa-ios').style.display='none';$('pwa-sf').style.display='flex'}
  setTimeout(function(){box.classList.add('show')},1200);
 }else{
  $('pwa-ios').style.display='none';
  addEventListener('beforeinstallprompt',function(e){e.preventDefault();ev=e;$('pwa-go').style.display='block';box.classList.add('show')});
 }
})();
</script>"""

OFFLINE = """<!doctype html><html lang="ku" dir="rtl"><head><meta charset="utf-8"><title>جزدانەکەم</title>{{css|safe}}</head>
<body><div class="blob"></div><div class="off"><div class="glass"><div style="font-size:46px">📡</div>
<h2>ئینتەرنێت نییە</h2><p>پەیوەندی ئینتەرنێتت بپشکنە و دووبارە هەوڵ بدەرەوە.</p>
<h2>لا يوجد اتصال بالإنترنت</h2><p>تحقق من اتصالك وحاول مرة أخرى.</p>
<h2 dir="ltr">No internet connection</h2><p dir="ltr">Check your connection and try again.</p>
<button class="btn" onclick="location.reload()">⟳</button></div></div></body></html>"""

ERR = """<!doctype html><html lang="ku" dir="rtl"><head><meta charset="utf-8"><title>Error</title>{{css|safe}}</head>
<body><div class="off"><div class="glass"><div style="font-size:42px">&#9888;</div>
<h2>هەڵە لە سێرڤەر</h2><p>ئەگەر تازە ئەپدەیتت کردووە، فایلی <b>schema.sql</b> لە Supabase (SQL Editor) Run بکە.</p>
<h2>خطأ في الخادم</h2><p>إذا قمت بالتحديث للتو، شغّل ملف <b>schema.sql</b> في Supabase.</p>
<h2 dir="ltr">Server error</h2><p dir="ltr">If you just updated, run <b>schema.sql</b> in the Supabase SQL Editor.</p>
{% if detail %}<pre dir="ltr" style="text-align:left;white-space:pre-wrap;font-size:12px;background:var(--soft);padding:10px;border-radius:12px;margin-top:14px">{{detail}}</pre>{% endif %}
<a class="btn" href="/">&#8635;</a></div></div></body></html>"""

AUTH = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{t('app')}}</title>{{css|safe}}</head>
<body><div class="blob"></div><div class="auth"><form method="post" class="glass">
<div class="top"><h2>{{t('app')}}</h2>""" + LANGS + """</div>
{% if err %}<div class="err">{{t(err)}}</div>{% endif %}
<label>{{t('username')}}</label><input name="username" autocapitalize="none" autocomplete="username" required>
<label>{{t('password')}}</label><input name="password" type="password" autocomplete="{{'new-password' if mode=='register' else 'current-password'}}" required>
<button class="btn">{{t(mode)}}</button>
<p>{% if mode=='login' %}{{t('no_acc')}} <a href="/register">{{t('register')}}</a>{% else %}{{t('has_acc')}} <a href="/login">{{t('login')}}</a>{% endif %}</p>
</form></div>""" + PWA + """</body></html>"""

COMMON_JS = r"""
const $=i=>document.getElementById(i);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function localToday(){const d=new Date(),p=n=>String(n).padStart(2,'0');return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())}
function openSheet(id){if(id==='sharesheet'){const u=$('sh-user');if(u){u.value='';lookupUser(u)}}$(id).classList.add('open')}
function closeS(id){$(id).classList.remove('open')}
function toast(m,ok){const t=document.createElement('div');t.className='toast glass'+(ok?' ok':'');t.textContent=m;document.body.appendChild(t);setTimeout(()=>t.remove(),3000)}
function shrink(file){return new Promise(res=>{const im=new Image(),u=URL.createObjectURL(file);
 im.onload=()=>{const k=Math.min(1,1280/Math.max(im.width,im.height)),c=document.createElement('canvas');
  c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);c.getContext('2d').drawImage(im,0,0,c.width,c.height);
  URL.revokeObjectURL(u);c.toBlob(b=>res(b),'image/jpeg',0.72)};
 im.onerror=()=>{URL.revokeObjectURL(u);res(null)};im.src=u})}
let _lt;
function lookupUser(inp){clearTimeout(_lt);const v=inp.value.trim().toLowerCase(),box=$('sh-prev'),go=$('sh-go');
 if(go)go.disabled=true;
 if(!v){box.innerHTML='<small class="hint">'+esc(TX.lk_hint)+'</small>';return}
 box.innerHTML='<span class="spin"></span>';
 _lt=setTimeout(async()=>{try{const r=await(await fetch('/user/lookup?u='+encodeURIComponent(v))).json();
  if(inp.value.trim().toLowerCase()!==v)return;
  if(!r.found){box.innerHTML='<div class="pv bad">'+esc(TX.lk_nf)+'</div>';return}
  if(r.me){box.innerHTML='<div class="pv bad">'+esc(TX.lk_self)+'</div>';return}
  const nm=r.name||r.username;
  box.innerHTML='<div class="pv"><span class="av">'+esc(nm[0].toUpperCase())+(r.avatar?'<img src="/avatar/'+r.id+'" alt="" onerror="this.remove()">':'')+'</span><div><b>'+esc(nm)+'</b><small dir="ltr">@'+esc(r.username)+'</small></div><i>&#10003;</i></div>';
  if(go)go.disabled=false}catch(e){box.innerHTML=''}},350)}
function openEdit(id){const it=getItems()[id];if(!it)return;
 $('e-form').action='/edit/'+id;$('e-amount').value=(it.amount%1?it.amount:Math.round(it.amount));
 $('e-label').value=it.label||'';$('e-note').value=it.note||'';$('e-date').value=it.date;openSheet('esheet')}
async function submitEdit(f){closeS('esheet');
 try{const r=await fetch(f.action,{method:'POST',body:new FormData(f),headers:{'X-Requested-With':'fetch'}});if(!r.ok)throw 0;toast(TX.saved,1)}catch(e){toast(TX.err)}
 afterEdit()}
function filterList(kind,q){q=q.trim().toLowerCase();let day=null,vis=0;
 [...$('list-'+kind).children].forEach(el=>{
  if(el.classList.contains('day')){if(day)day.style.display=vis?'':'none';day=el;vis=0}
  else if(el.classList.contains('item')){const ok=!q||el.textContent.toLowerCase().indexOf(q)>-1;el.style.display=ok?'':'none';if(ok)vis++}});
 if(day)day.style.display=vis?'':'none'}
"""

ESHEET = """
<div class="sheet" id="esheet" onclick="if(event.target===this)closeS('esheet')">
<form method="post" id="e-form" onsubmit="submitEdit(this);return false"><h3>{{t('edit_t')}}</h3>
<input class="big" name="amount" id="e-amount" inputmode="decimal" required autocomplete="off">
<label>{{t('col_label')}}</label><input name="label" id="e-label" autocomplete="off">
<label>{{t('note')}}</label><textarea name="note" id="e-note" rows="2"></textarea>
<label>{{t('date')}}</label><input type="date" name="date" id="e-date">
<button class="btn">{{t('save')}}</button></form></div>
"""

CASESHARE = """
<div class="sheet" id="sharesheet" onclick="if(event.target===this)closeS('sharesheet')">
<form method="post" action="/share/add"><h3>&#128101; {{t('share_case_t')}}</h3><p style="color:var(--mut);font-size:13px;line-height:1.7">{{t('share_hint')}}</p>
<input type="hidden" name="acc" value="{{c.id}}"><input type="hidden" name="next" value="/case/{{c.id}}">
{% for m in members %}<div class="setrow"><span class="av sm">{{m.username[:1]|upper}}<img src="/avatar/{{m.uid}}" alt="" onerror="this.remove()"></span><div class="nm"><b>{{m.username}}</b><small>{{t('role_viewer') if m.role=='viewer' else t('role_editor')}}{% if not m.accepted %} &middot; {{t('pending')}}{% endif %}</small></div>
<button class="mini red" formaction="/share/remove" formmethod="post" name="uid" value="{{m.uid}}" formnovalidate>&#10005;</button></div>
{% else %}<p style="color:var(--mut);font-size:13px">{{t('no_members')}}</p>{% endfor %}
<label>{{t('share_user')}}</label><input id="sh-user" name="username" required autocapitalize="none" autocomplete="off" oninput="lookupUser(this)">
<div id="sh-prev"><small class="hint">{{t('lk_hint')}}</small></div>
<select name="role" style="margin-top:10px"><option value="editor">{{t('role_editor')}}</option><option value="viewer">{{t('role_viewer')}}</option></select>
<button class="btn" id="sh-go" disabled>{{t('share_add')}}</button></form></div>
"""

RECEIPT = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{t('receipt_t')}} {{r.id}}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap">
<style>
*{box-sizing:border-box}
body{font-family:'Vazirmatn',-apple-system,sans-serif;color:#111;background:#fff;margin:0 auto;padding:calc(16px + env(safe-area-inset-top)) 16px 40px;max-width:640px;font-size:15px}
.lh{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px double #111;padding-bottom:8px;margin-bottom:18px;gap:10px}
.office{font-size:19px;font-weight:700}.lhl{display:flex;align-items:center;gap:12px}.logo{max-height:64px;max-width:130px;object-fit:contain}.meta{color:#555;font-size:12px}
h1{text-align:center;font-size:22px;margin:10px 0 18px}
table{width:100%;border-collapse:collapse}
th,td{padding:11px 10px;border:1px solid #bbb;text-align:start;vertical-align:top}
th{background:#f1f1f1;width:34%;font-size:13px}
td.n{direction:ltr;text-align:start;font-weight:700;font-size:19px}
.sign{display:flex;justify-content:space-between;margin-top:60px;gap:20px}.sign div{width:46%;border-top:1px solid #111;padding-top:6px;text-align:center;font-size:12px;color:#555}
.bar{display:flex;gap:8px;justify-content:space-between;margin-bottom:14px}
.bar a,.bar button{padding:11px 18px;border-radius:12px;border:1px solid #111;background:#fff;color:#111;font:inherit;text-decoration:none;cursor:pointer}
.bar button{background:#D97757;border-color:#D97757;color:#fff;font-weight:700}
@media print{.noprint{display:none}body{padding:0}@page{margin:14mm}}
</style></head><body>
<div class="bar noprint"><a href="javascript:history.back()">&larr; {{t('back')}}</a><button onclick="print()">&#128424; {{t('print_btn')}}</button></div>
<div class="lh"><div class="lhl">{% if has_logo %}<img class="logo" src="/logo" alt="">{% endif %}<div><div class="office">{{office or t('app')}}</div>{% if phone %}<div class="meta" dir="ltr">&#9742; {{phone}}</div>{% endif %}</div></div><div class="meta">{{t('generated')}}: {{now}}</div></div>
<h1>{{t('receipt_t')}}</h1>
<table>
<tr><th>{{t('receipt_no')}}</th><td>{{r.id}}</td></tr>
<tr><th>{{t('date')}}</th><td>{{r.date}}</td></tr>
{% if acc.client %}<tr><th>{{t('receipt_from')}}</th><td>{{acc.client}}</td></tr>{% endif %}
<tr><th>{{t('case_name') if acc.kind=='case' else t('acc_name')}}</th><td>{{acc.name}}{% if acc.case_no %} ({{acc.case_no}}){% endif %}</td></tr>
{% if r.label or r.note %}<tr><th>{{t('receipt_for')}}</th><td>{{r.label}}{% if r.label and r.note %} &mdash; {% endif %}{{r.note}}</td></tr>{% endif %}
<tr><th>{{t('amount')}}</th><td class="n">{{fm(r.amount, acc.currency)}}</td></tr>
</table>
<div class="sign"><div>{{t('receipt_from')}}</div><div>{{t('signature')}}</div></div>
<script>{% if auto %}addEventListener('load',function(){setTimeout(function(){print()},700)});{% endif %}</script>
</body></html>"""

XSHEETS = """
<div class="sheet" id="sharesheet" onclick="if(event.target===this)closeS('sharesheet')">
<form method="post" action="/share/add"><h3>{{t('share_t')}}</h3><p style="color:var(--mut);font-size:13px">{{t('share_hint')}}</p>
<input type="hidden" name="acc" id="sh-acc"><div id="sh-list"></div>
<label>{{t('share_user')}}</label><input id="sh-user" name="username" required autocapitalize="none" autocomplete="off" oninput="lookupUser(this)">
<div id="sh-prev"><small class="hint">{{t('lk_hint')}}</small></div>
<select name="role" style="margin-top:10px"><option value="editor">{{t('role_editor')}}</option><option value="viewer">{{t('role_viewer')}}</option></select>
<button class="btn" id="sh-go" disabled>{{t('share_add')}}</button></form></div>

<div class="sheet" id="trsheet" onclick="if(event.target===this)closeS('trsheet')">
<form method="post" action="/transfer" onsubmit="submitTransfer(this);return false"><h3>{{t('transfer_t')}}</h3>
<label>{{t('tr_src')}}</label><select name="from" id="tr-from" onchange="trChange()"></select>
<label>{{t('tr_dst')}}</label><select name="to" id="tr-to" onchange="trChange()"></select>
<input class="big" name="amount" id="tr-amt" inputmode="decimal" required placeholder="0" autocomplete="off" style="margin-top:14px" oninput="trChange()">
<div id="tr-in-box" style="display:none"><label>{{t('tr_amount_in')}}</label>
<input class="big" name="amount_in" id="tr-in" inputmode="decimal" placeholder="0" autocomplete="off" oninput="trChange()">
<small id="tr-rate" style="color:var(--mut);display:block;text-align:center;margin-top:6px;direction:ltr"></small></div>
<label>{{t('note')}}</label><input name="note" autocomplete="off">
<label>{{t('date')}}</label><input type="date" name="date" id="tr-date">
<p style="color:var(--mut);font-size:12px">{{t('tr_hint')}}</p>
<button class="btn">{{t('save')}}</button></form></div>
"""

BSHEET = """
<div class="sheet" id="bsheet" onclick="if(event.target===this)closeS('bsheet')">
<form method="post" action="/budget"><h3>{{t('budget')}}</h3><p style="color:var(--mut);font-size:13px">{{t('budget_hint')}}</p>
<input type="hidden" name="acc" value="{{acc.id}}">
<input class="big" name="budget" inputmode="decimal" value="{{budget_v}}" placeholder="0" autocomplete="off">
<button class="btn">{{t('save')}}</button></form></div>
"""

HOME = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{t('app')}}</title>{{css|safe}}
</head>
<body class="c-{{acc.currency}} hasnav" data-tab="home"><div class="wrap">

<div class="top"><button class="who" onclick="setTab('settings');setSub('profile')"><span class="av">{{(dname or user)[:1]|upper}}<img src="/avatar/{{uid}}?v={{pv}}" alt="" onerror="this.remove()"></span><span><small>{{t('hi')}}</small><b>{{dname or user}}</b></span></button>
<div class="hic"><button onclick="setTab('charts')" aria-label="{{t('tab_charts')}}"><svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg></button>
<button onclick="setTab('settings')" aria-label="{{t('tab_settings')}}"><svg viewBox="0 0 24 24"><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></svg></button></div></div>

<div class="accs">
{% for a in accs %}<a class="acc {{'on' if a.id==acc.id}}" href="/a/{{a.id}}"><b>{{a.name}}{% if a.shared %} &#128101;{% endif %}</b><small>{{fm(bal.get(a.id,0),a.currency)}}</small></a>{% endfor %}
<button class="acc add" onclick="openSheet('accsheet')">+ {{t('new_acc')}}</button></div>

<section class="tab on" id="t-home">
{% for i in invites %}<div class="glass alert"><b>&#128101; {{t('invite_t')}}</b><span style="font-size:14px">{{(t('invite_case_msg') if i.kind=='case' else t('invite_msg')).replace('{name}', i.owner).replace('{acc}', i.name)}}</span>
<div class="two"><form method="post" action="/share/respond"><input type="hidden" name="acc" value="{{i.acc}}"><input type="hidden" name="action" value="decline"><button class="btn ghost sm">{{t('decline')}}</button></form>
<form method="post" action="/share/respond"><input type="hidden" name="acc" value="{{i.acc}}"><input type="hidden" name="action" value="accept"><button class="btn sm">{{t('accept')}}</button></form></div></div>{% endfor %}
{% if acc.role=='viewer' %}<div class="glass alert"><small>&#128065; {{t('view_only')}}</small></div>{% endif %}
{% if soon %}<div class="glass alert"><b>&#9878; {{t('hearing_soon')}}</b>{% for c in soon %}<a href="/case/{{c.id}}"><span>{{c.name}}{% if c.client %} &middot; {{c.client}}{% endif %}</span><i>{{c.hearing}}</i></a>{% endfor %}</div>{% endif %}
<div class="hgrid">
<div class="glass hero"><div class="hl"><span>{{acc.name}}<em>{{t('cur_'+acc.currency)}}</em></span><button class="mini" onclick="printReport('statement')">&#128424; {{t('print_btn')}}</button></div>
<div class="hb">{{fm(bal.get(acc.id,0),acc.currency)}}</div><small>{{t('balance')}}</small></div>
<div class="hside">{% if acc.role!='viewer' %}<div class="qa"><button class="i" onclick="openAdd('income')">&#8595; {{t('add_in')}}</button><button class="e" onclick="openAdd('expense')">&#8593; {{t('add_ex')}}</button>
{% if accs|length>1 %}<button class="t" onclick="openTransfer()">&#8644; {{t('transfer_t')}}</button>{% endif %}</div>{% endif %}
<div class="glass grand"><span>{{t('total_all')}}</span><div>{% for c,v in tot.items() %}<b>{{fm(v,c)}}</b>{% endfor %}</div>
<button class="mini" onclick="printReport('grand')">&#128424; {{t('print_btn')}}</button></div></div></div>
<div class="glass bgt"><div class="hl"><span>{{t('budget')}}</span>{% if acc.role=='owner' %}<button class="mini" onclick="openBudget()">{{t('budget_set')}}</button>{% endif %}</div>
{% if bud %}<div class="track"><i class="{{bud.cls}}" style="width:{{[bud.pct,100]|min}}%"></i></div>
<div class="bl"><span>{{t('budget_spent')}}: {{fm(bud.spent,acc.currency)}} ({{bud.pct}}%)</span><span>{{fm(acc.budget,acc.currency)}}</span></div>
<small>{% if bud.left>=0 %}{{t('budget_left')}}: {{fm(bud.left,acc.currency)}} &middot; {{fm(bud.daily,acc.currency)}} {{t('budget_daily')}}{% else %}{{t('budget_over')}} {{fm(-bud.left,acc.currency)}}{% endif %}</small>
{% else %}<small>{{t('budget_none')}}</small>{% endif %}</div>
<div class="row3">{% for k,x in stats %}<div class="glass st"><h4>{{t(k)}}</h4>
<div class="in"><span>+</span><span>{{fm(x.i,acc.currency)}}</span></div><div class="ex"><span>&minus;</span><span>{{fm(x.e,acc.currency)}}</span></div>
<div class="n"><span>=</span><span>{{fm(x.n,acc.currency)}}</span></div></div>{% endfor %}</div>
{% if transfers %}<div class="glass sec"><h3>&#8644; {{t('tr_list')}}</h3>
{% for x in transfers %}<div class="setrow"><div class="nm"><b>{{t('tr_to') if x.type=='expense' else t('tr_from')}}: {{x.label}}</b><small>{{x.date}}{% if acc.shared and x.by_user %} &middot; {{x.by_user}}{% endif %}{% if x.note %} &middot; {{x.note}}{% endif %}</small></div>
<b class="amt {{x.type}}">{{fm(x.amount,acc.currency)}}</b>
{% if acc.role=='owner' or (acc.role=='editor' and x.uid==uid) %}<form method="post" action="/delete/{{x.id}}" onsubmit="if(!confirm('{{t('confirm')}}'))return false;softDel(this);return false"><button class="x">&#10005;</button></form>{% endif %}</div>{% endfor %}</div>{% endif %}
</section>

{% macro page(kind, groups, total, n, cls, addkey) %}
<section class="tab" id="t-{{kind}}"><div class="split"><div class="side">
<div class="glass pbar"><span>{{plabel}}</span><div class="pills"><button class="pill" onclick="openSheet('fsheet')">{{t('filter')}}</button><button class="pill" onclick="printReport('{{kind}}')">&#128424; {{t('print_btn')}}</button></div></div>
<div class="glass sumc"><span class="lab">{{t(kind)}} &middot; {{acc.name}}</span><b class="one {{cls}}">{{fm(total,acc.currency)}}</b><span class="lab">{{n}} {{t('entries_n')}}</span></div>
<button class="btn sm" style="margin:0 0 4px" onclick="openAdd('{{kind}}')">+ {{t(addkey)}}</button></div>
<div class="main"><input class="srch" type="search" placeholder="{{t('search_ph')}}" oninput="filterList('{{kind}}',this.value)">
<div id="list-{{kind}}">{% for d,gp in groups %}<div class="day"><span>{{d}}</span><span>{{fm(gp.n,acc.currency)}}</span></div>
{% for x in gp['items'] %}<div class="glass item">
<div class="dot {{x.type}}">{{'&#8595;'|safe if x.type=='income' else '&#8593;'|safe}}</div>
<div class="meta"><b>{{x.label or t(x.type)}}</b>{% if x.note %}<small>{{x.note}}</small>{% endif %}{% if acc.shared and x.by_user %}<small>&#128100; {{x.by_user}}</small>{% endif %}</div>
{% if x.img %}<a href="/img/{{x.img}}" target="_blank"><img class="thumb" src="/img/{{x.img}}" alt=""></a>{% endif %}
<div class="amt {{x.type}}">{{fm(x.amount,acc.currency)}}</div>
{% if acc.role=='owner' or (acc.role=='editor' and x.uid==uid) %}<button class="x ed" onclick="openEdit({{x.id}})" title="{{t('edit_t')}}">&#9998;</button><form method="post" action="/delete/{{x.id}}" onsubmit="if(!confirm('{{t('confirm')}}'))return false;softDel(this);return false"><button class="x" title="{{t('delete')}}">&#10005;</button></form>{% endif %}
</div>{% endfor %}{% else %}<div class="empty">{{t('empty')}}</div>{% endfor %}</div></div></div>
</section>
{% endmacro %}
{{ page('income', gi, rng.i, ni, 'in', 'add_in') }}
{{ page('expense', ge, rng.e, nex, 'ex', 'add_ex') }}

<section class="tab" id="t-cases">
<h2 class="ptitle">{{t('cases_t')}}</h2>
<div class="chips" id="cfilter"><button class="pill on" data-f="all" onclick="filterCases('all')">{{t('all')}}</button>
<button class="pill" data-f="open" onclick="filterCases('open')">{{t('status_open')}}</button>
<button class="pill" data-f="closed" onclick="filterCases('closed')">{{t('status_closed')}}</button></div>
<button class="btn sm" style="margin:0 0 12px" onclick="openSheet('casesheet')">+ {{t('new_case')}}</button>
{% macro casecard(c) %}<a class="glass cc" data-st="{{c.status}}" href="/case/{{c.id}}">
<div class="cch"><b>{{c.name}}</b><span class="badge {{c.status}}">{{t('status_'+c.status)}}</span></div>
<small>{{c.client}}{% if c.case_no %} &middot; {{c.case_no}}{% endif %}{% if c.started %} &middot; {{c.started}}{% endif %}{% if c.hearing %} &middot; &#9878; {{c.hearing}}{% endif %}</small>
{% if c.role!='owner' %}<span class="badge sh">&#128101; {{c.owner}} &middot; {{t('role_'+c.role)}}</span>{% elif c.shared %}<span class="badge sh">&#128101; {{t('share_btn')}}</span>{% endif %}
<div class="ccn"><div><span>{{t('case_ex')}}</span><b class="ex">{{fm(c.exp,c.currency)}}</b></div>
<div><span>{{t('case_in')}}</span><b class="in">{{fm(c.inc,c.currency)}}</b></div>
<div><span>{{t('case_net')}}</span><b>{{fm(c.inc-c.exp,c.currency)}}</b></div></div></a>{% endmacro %}
<div id="caselist">{% for c in cases if c.role=='owner' %}{{ casecard(c) }}{% else %}<div class="empty">{{t('no_cases')}}</div>{% endfor %}</div>
{% if cases|selectattr('role','ne','owner')|list %}<h3 class="sub">{{t('shared_with_me')}}</h3>
<div id="caselist2">{% for c in cases if c.role!='owner' %}{{ casecard(c) }}{% endfor %}</div>{% endif %}
</section>

<section class="tab" id="t-charts">
<h2 class="ptitle">{{t('tab_charts')}}</h2>
<div class="glass pbar"><span>{{plabel}}</span><div class="pills"><button class="pill" onclick="openSheet('fsheet')">{{t('filter')}}</button></div></div>
<div class="charts">
<div class="glass card"><h3>{{t('chart_daily')}}</h3><div class="cv"><canvas id="c1"></canvas></div></div>
<div class="glass card"><h3>{{t('chart_cat')}}</h3>
<div class="seg"><button type="button" id="tb-expense" class="expense on" onclick="showCats('expense')">{{t('expense')}}</button>
<button type="button" id="tb-income" class="income" onclick="showCats('income')">{{t('income')}}</button></div>
<div class="c2w" id="c2w"><canvas id="c2"></canvas></div><div id="legend"></div></div>
</div>
</section>

<section class="tab" id="t-settings">
<div class="sv on" id="s-menu"><h2 class="ptitle">{{t('tab_settings')}}</h2>
<button class="glass pcard" onclick="setSub('profile')"><span class="av big">{{(dname or user)[:1]|upper}}<img src="/avatar/{{uid}}?v={{pv}}" alt="" onerror="this.remove()"></span>
<div><b>{{dname or user}}</b><small dir="ltr">@{{user}}</small></div><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('lang')"><b class="mi"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/></svg></b><span>{{t('set_lang')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('accounts')"><b class="mi"><svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M3 7a2 2 0 0 1 2-2h13v2"/><circle cx="16.5" cy="13.5" r="1.2"/></svg></b><span>{{t('set_accounts')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('clear')"><b class="mi"><svg viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg></b><span>{{t('set_clear')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('print')"><b class="mi"><svg viewBox="0 0 24 24"><path d="M6 9V3h12v6M6 18H4v-7h16v7h-2M8 14h8v7H8z"/></svg></b><span>{{t('set_letter')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('rec')"><b class="mi"><svg viewBox="0 0 24 24"><path d="M17 2l3 3-3 3M20 5H8a4 4 0 0 0-4 4v1M7 22l-3-3 3-3M4 19h12a4 4 0 0 0 4-4v-1"/></svg></b><span>{{t('set_rec')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('data')"><b class="mi"><svg viewBox="0 0 24 24"><path d="M12 3v12M7 10l5 5 5-5M4 21h16"/></svg></b><span>{{t('set_data')}}</span><i>&rsaquo;</i></button>
<button class="glass menu" onclick="setSub('theme')"><b class="mi"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/></svg></b><span>{{t('set_theme')}}</span><i>&rsaquo;</i></button>
</div>

<div class="sv" id="s-lang"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_lang')}}</h3>""" + LANGS + """</div></div>

<div class="sv" id="s-accounts"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_accounts')}}</h3>
{% for a in accs %}<div class="setrow"><div class="nm"><b>{{a.name}}{% if a.shared %} &#128101;{% endif %}</b><small>{{t('cur_'+a.currency)}} &middot; {{a.ni+a.ne}} {{t('entries_n')}} &middot; {{fm(bal.get(a.id,0),a.currency)}}{% if a.role!='owner' %} &middot; {{a.owner}}{% endif %}</small></div>
{% if a.role=='owner' %}<button class="mini" onclick="openShare({{a.id}})">&#128101; {{t('share_btn')}}</button>
<button class="mini red" onclick="ask('clear_all',{{a.id}})">{{t('clear_btn')}}</button>
{% if owned>1 %}<button class="mini red" onclick="ask('del_acc',{{a.id}})">{{t('delete')}}</button>{% endif %}
{% else %}<form method="post" action="/share/remove"><input type="hidden" name="acc" value="{{a.id}}"><input type="hidden" name="uid" value="{{uid}}"><button class="mini red">{{t('leave')}}</button></form>{% endif %}</div>{% endfor %}
<button class="btn sm ghost" onclick="openSheet('accsheet')">+ {{t('new_acc')}}</button></div></div>

<div class="sv" id="s-clear"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
{% if acc.role!='owner' %}<div class="glass sec"><p>{{t('view_only')}}</p></div>{% else %}<div class="glass sec"><h3>{{t('set_clear')}}: {{acc.name}}</h3>
<div class="setrow"><div class="nm"><b>{{t('income')}}</b><small>{{acc.ni}} {{t('entries_n')}}</small></div><button class="mini red" onclick="ask('clear_in')">{{t('clear_btn')}}</button></div>
<div class="setrow"><div class="nm"><b>{{t('expense')}}</b><small>{{acc.ne}} {{t('entries_n')}}</small></div><button class="mini red" onclick="ask('clear_ex')">{{t('clear_btn')}}</button></div></div>{% endif %}</div>

<div class="sv" id="s-profile"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec ptop"><span class="av xl">{{(dname or user)[:1]|upper}}<img src="/avatar/{{uid}}?v={{pv}}" alt="" onerror="this.remove()"></span>
<b style="font-size:18px">{{dname or user}}</b>
<div class="pact"><button class="mini" onclick="$('av-file').click()">{{t('change_photo')}}</button><button class="mini red" onclick="removePhoto('avatar')">{{t('remove_photo')}}</button></div>
<input type="file" id="av-file" accept="image/*" hidden onchange="uploadPhoto('avatar',this)"></div>
<form method="post" action="/profile/save" class="glass sec"><h3>{{t('set_profile')}}</h3>
<label>{{t('prof_name')}}</label><input name="name" value="{{dname}}" maxlength="50" autocomplete="off">
<label>{{t('prof_user')}}</label><input value="@{{user}}" dir="ltr" disabled>
<button class="btn sm">{{t('save')}}</button></form>
<form method="post" action="/password" class="glass sec"><h3>{{t('pw_change')}}</h3>
<label>{{t('pw_old')}}</label><input type="password" name="old" autocomplete="current-password" required>
<label>{{t('pw_new')}}</label><input type="password" name="new" autocomplete="new-password" required minlength="4">
<button class="btn sm">{{t('save')}}</button></form>
<a class="btn sm red" href="/logout">{{t('logout')}}</a></div>

<div class="sv" id="s-print"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_letter')}}</h3><p>{{t('letter_hint')}}</p>
<div class="lhprev"><span class="lgbox"><img src="/logo?v={{pv}}" alt="" onerror="this.remove()"></span>
<div><b>{{office or t('app')}}</b><small dir="ltr">{{phone}}</small></div></div>
<div class="pact"><button class="mini" onclick="$('lg-file').click()">{{t('logo')}}: {{t('change_photo')}}</button><button class="mini red" onclick="removePhoto('logo')">{{t('remove_photo')}}</button></div>
<input type="file" id="lg-file" accept="image/*" hidden onchange="uploadPhoto('logo',this)">
<form method="post" action="/office"><label>{{t('office')}}</label><input name="office" value="{{office}}" maxlength="80" autocomplete="off">
<label>{{t('phone')}}</label><input name="phone" value="{{phone}}" maxlength="30" inputmode="tel" dir="ltr" autocomplete="off">
<button class="btn sm">{{t('save')}}</button></form></div></div>

<div class="sv" id="s-rec"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_rec')}}</h3><p>{{t('rec_hint')}}</p>
{% for r in recs %}<div class="setrow"><div class="nm"><b>{{r.label or t(r.type)}} &middot; {{fm(r.amount,curmap.get(r.account_id,'IQD'))}}</b><small>{{accname.get(r.account_id,'')}} &middot; {{t(r.type)}} &middot; {{t('rec_day')[:10]}} {{r.day}} &middot; {{r.next}}</small></div>
<form method="post" action="/rec/{{r.id}}/delete" onsubmit="return confirm('{{t('confirm')}}')"><button class="mini red">{{t('delete')}}</button></form></div>
{% else %}<p>{{t('rec_empty')}}</p>{% endfor %}</div>
<form method="post" action="/rec/new" class="glass sec"><h3>+ {{t('set_rec')}}</h3><p>{{t('rec_for')}} <b>{{acc.name}}</b></p>
<input type="hidden" name="acc" value="{{acc.id}}">
<select name="type"><option value="expense">{{t('expense')}}</option><option value="income">{{t('income')}}</option></select>
<input class="big" name="amount" inputmode="decimal" placeholder="0" required autocomplete="off" style="margin-top:10px">
<label>{{t('col_label')}}</label><input name="label" autocomplete="off">
<label>{{t('rec_day')}}</label><input name="day" type="number" min="1" max="28" value="1" required>
<button class="btn sm">{{t('save')}}</button></form></div>

<div class="sv" id="s-data"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_data')}}</h3><p>{{t('exp_hint')}}</p>
<button class="btn sm ghost" onclick="exportCsv('acc')">&#128196; {{t('exp_acc')}}</button>
<button class="btn sm ghost" onclick="exportCsv('all')">&#128190; {{t('exp_all')}}</button></div></div>

<div class="sv" id="s-theme"><button class="back" onclick="setSub('menu')">&lsaquo; {{t('back')}}</button>
<div class="glass sec"><h3>{{t('set_theme')}}</h3>
<div class="seg" style="grid-template-columns:repeat(3,1fr);margin:8px 0 0"><button type="button" id="th-light" onclick="setTheme('light')">&#9728; {{t('theme_light')}}</button>
<button type="button" id="th-dark" onclick="setTheme('dark')">&#9790; {{t('theme_dark')}}</button>
<button type="button" id="th-auto" onclick="setTheme('auto')">&#9680; {{t('theme_auto')}}</button></div></div></div>

</section>
</div>

<nav class="nav">
<div class="brand dsk"><img src="/static/icons/favicon-32.png" alt=""><b>{{t('app')}}</b></div>
<button class="nb on" id="n-home" onclick="setTab('home')"><svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg><span>{{t('tab_home')}}</span></button>
<button class="nb" id="n-income" onclick="setTab('income')"><svg viewBox="0 0 24 24"><path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 20h16"/></svg><span>{{t('tab_income')}}</span></button>
<button class="add" onclick="openAdd('expense')" aria-label="+"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg><span class="addt">{{t('add_new')}}</span></button>
<button class="nb" id="n-expense" onclick="setTab('expense')"><svg viewBox="0 0 24 24"><path d="M12 21V9M7 14l5-5 5 5"/><path d="M4 4h16"/></svg><span>{{t('tab_expense')}}</span></button>
<button class="nb" id="n-cases" onclick="setTab('cases')"><svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/></svg><span>{{t('tab_legal')}}</span></button>
<button class="nb dsk" id="n-charts" onclick="setTab('charts')"><svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg><span>{{t('tab_charts')}}</span></button>
<button class="nb dsk" id="n-settings" onclick="setTab('settings')"><svg viewBox="0 0 24 24"><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></svg><span>{{t('tab_settings')}}</span></button>
</nav>

<div class="sheet" id="sheet" onclick="if(event.target===this)closeS('sheet')">
<form method="post" action="/add" enctype="multipart/form-data" onsubmit="submitAdd(this);return false">
<input type="hidden" name="type" id="type" value="expense">
<div class="seg"><button type="button" id="b-income" class="income" onclick="setType('income')">{{t('add_in')}}</button>
<button type="button" id="b-expense" class="expense" onclick="setType('expense')">{{t('add_ex')}}</button></div>
<input class="big" name="amount" inputmode="decimal" placeholder="0 {{ 'USD' if acc.currency=='USD' else 'IQD' }}" required autocomplete="off">
<label id="lbl">{{t('src_in')}}</label><input name="label" list="dl" autocomplete="off">
<datalist id="dl">{% for l in labels %}<option value="{{l}}">{% endfor %}</datalist>
<label>{{t('note')}}</label><textarea name="note" rows="2"></textarea>
<label>{{t('date')}}</label><input type="date" name="date" id="date" value="{{td}}">
<label>{{t('photo')}}</label><input type="file" name="photo" accept="image/*">
<button class="btn">{{t('save')}}</button></form></div>

<div class="sheet" id="accsheet" onclick="if(event.target===this)closeS('accsheet')">
<form method="post" action="/acc/new"><h3>{{t('new_acc')}}</h3>
<label>{{t('acc_name')}}</label><input name="name" required maxlength="40" autocomplete="off">
<label>{{t('currency')}}</label><input type="hidden" name="currency" id="cur" value="IQD">
<div class="seg"><button type="button" id="cb-IQD" class="on" onclick="setCur('IQD')">{{t('cur_IQD')}} (د.ع)</button>
<button type="button" id="cb-USD" onclick="setCur('USD')">{{t('cur_USD')}} ($)</button></div>
<label>{{t('opening')}}</label><input name="opening" inputmode="decimal" placeholder="0" autocomplete="off">
<button class="btn">{{t('create')}}</button></form></div>

<div class="sheet" id="casesheet" onclick="if(event.target===this)closeS('casesheet')">
<form method="post" action="/case/new"><h3>{{t('new_case')}}</h3>
<label>{{t('case_name')}}</label><input name="name" required maxlength="80" autocomplete="off">
<label>{{t('client')}}</label><input name="client" maxlength="80" autocomplete="off">
<div class="frow"><div><label>{{t('case_no')}}</label><input name="case_no" maxlength="40" autocomplete="off"></div>
<div><label>{{t('court')}}</label><input name="court" maxlength="80" autocomplete="off"></div></div>
<label>{{t('currency')}}</label><input type="hidden" name="currency" id="ccur" value="IQD">
<div class="seg"><button type="button" id="cc-IQD" class="on" onclick="setCaseCur('IQD')">{{t('cur_IQD')}} (د.ع)</button>
<button type="button" id="cc-USD" onclick="setCaseCur('USD')">{{t('cur_USD')}} ($)</button></div>
<label>{{t('fee')}}</label><input name="fee" inputmode="decimal" placeholder="0" autocomplete="off">
<div class="frow"><div><label>{{t('started')}}</label><input type="date" name="started" value="{{td}}"></div>
<div><label>{{t('hearing')}}</label><input type="date" name="hearing"></div></div>
<button class="btn">{{t('create')}}</button></form></div>

<div class="sheet" id="fsheet" onclick="if(event.target===this)closeS('fsheet')">
<form method="get" action="/"><h3>{{t('filter')}}</h3>
<div class="pills" style="flex-wrap:wrap">{% for p,n in [('today','today'),('week','week'),('month','month'),('all','all_time')] %}
<a class="pill {{'on' if key==p}}" href="/?p={{p}}">{{t(n)}}</a>{% endfor %}</div>
<label>{{t('month_pick')}}</label>
<input type="month" name="m" value="{{pf.m}}" onchange="this.form.from.value='';this.form.to.value='';this.form.submit()">
<div class="frow"><div><label>{{t('from_')}}</label><input type="date" name="from" value="{{pf.a}}"></div>
<div><label>{{t('to_')}}</label><input type="date" name="to" value="{{pf.b}}"></div></div>
<button class="btn">{{t('apply')}}</button></form></div>

<div class="sheet" id="csheet" onclick="if(event.target===this)closeS('csheet')">
<form method="post" id="cform"><h3 id="ctitle"></h3><p id="ctext" style="line-height:1.8"></p><div id="cfields"></div>
<label class="chk"><input type="checkbox" id="cchk" onchange="$('cgo').disabled=!this.checked"><span>{{t('confirm_check')}}</span></label>
<div class="two"><button type="button" class="btn ghost" onclick="closeS('csheet')">{{t('cancel')}}</button>
<button class="btn red" id="cgo" disabled>{{t('yes_delete')}}</button></div></form></div>

""" + ESHEET + BSHEET + XSHEETS + """<script id="data" type="application/json">{{ chart|tojson }}</script>
<script>""" + COMMON_JS + """
let D=JSON.parse($('data').textContent),bar=null,pie=null,cat='expense',sub=(function(){try{return sessionStorage.getItem('sub')}catch(e){return null}})()||'menu';
const TX={{ tr|tojson }},MSG={{ msg|tojson }},TABS=['home','income','expense','cases','charts','settings'];
const S={income:TX.src_in,expense:TX.src_ex};
const MAIN=['home','income','expense','cases'];let lastMain='home';
function swipeDir(dx,rtl){return dx<0?(rtl?-1:1):(rtl?1:-1)}
function swipePlan(tab,sub,dir,last){
 if(tab==='settings'&&sub!=='menu')return dir<0?{sub:'menu'}:null;
 const i=MAIN.indexOf(tab);if(i<0)return dir<0?{tab:last||'home'}:null;
 const j=i+dir;return(j<0||j>=MAIN.length)?null:{tab:MAIN[j],slide:dir}}
function swipeGo(dir){const p=swipePlan(tab,sub,dir,lastMain);if(!p)return;
 if(p.sub){setSub(p.sub);return}
 setTab(p.tab);
 const el=$('t-'+tab),rtl=document.documentElement.dir==='rtl';
 el.style.setProperty('--sx',((p.slide||-1)*30*(rtl?-1:1))+'px');el.classList.add('swp');setTimeout(()=>el.classList.remove('swp'),320)}
(function(){let sx=0,sy=0,st=0,ok=false;
 const blocked=e=>e.target.closest&&e.target.closest('.accs,canvas,input,textarea,select,.sheet,.toast');
 addEventListener('touchstart',e=>{if(e.touches.length!==1||blocked(e)){ok=false;return}const t=e.touches[0];sx=t.clientX;sy=t.clientY;st=Date.now();ok=true},{passive:true});
 addEventListener('touchend',e=>{if(!ok)return;ok=false;const t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy;
  if(Date.now()-st>700||Math.abs(dx)<70||Math.abs(dx)<Math.abs(dy)*1.7)return;
  if(document.querySelector('.sheet.open'))return;
  try{if(String(getSelection()))return}catch(x){}
  swipeGo(swipeDir(dx,document.documentElement.dir==='rtl'))},{passive:true});
})();
function prep(file,kind){return new Promise(res=>{const im=new Image(),u=URL.createObjectURL(file);
 im.onload=()=>{const c=document.createElement('canvas');
  if(kind==='avatar'){const sq=Math.min(im.width,im.height);c.width=c.height=256;c.getContext('2d').drawImage(im,(im.width-sq)/2,(im.height-sq)/2,sq,sq,0,0,256,256)}
  else{const k=Math.min(1,600/Math.max(im.width,im.height));c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);c.getContext('2d').drawImage(im,0,0,c.width,c.height)}
  URL.revokeObjectURL(u);c.toBlob(b=>res(b),kind==='logo'?'image/png':'image/jpeg',0.86)};
 im.onerror=()=>{URL.revokeObjectURL(u);res(null)};im.src=u})}
async function uploadPhoto(kind,inp){const f=inp.files[0];if(!f)return;const b=await prep(f,kind);inp.value='';
 if(!b){toast(TX.err);return}
 const fd=new FormData();fd.set('kind',kind);fd.set('file',b,kind==='logo'?'p.png':'p.jpg');
 try{const r=await fetch('/profile/photo',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}});if(!r.ok)throw 0;location.reload()}catch(e){toast(TX.err)}}
async function removePhoto(kind){if(!confirm(TX.confirm))return;const fd=new FormData();fd.set('kind',kind);fd.set('remove','1');
 try{await fetch('/profile/photo',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}})}catch(e){}location.reload()}
function getItems(){return D.items}function afterEdit(){refresh()}function openBudget(){openSheet('bsheet')}
function applyTheme(){let m='auto';try{m=localStorage.getItem('theme')||'auto'}catch(e){}
 const d=m==='dark'||(m==='auto'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);
 ['light','dark','auto'].forEach(k=>{const b=$('th-'+k);if(b)b.classList.toggle('on',k===m)})}
function setTheme(m){try{localStorage.setItem('theme',m)}catch(e){}applyTheme();boot()}
try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',applyTheme)}catch(e){}
function openShare(id){$('sh-acc').value=id;const ms=(D.members||[]).filter(m=>m.acc===id);
 $('sh-list').innerHTML=ms.length?ms.map(m=>'<div class="setrow"><span class="av sm">'+esc((m.username||'?')[0].toUpperCase())+'<img src="/avatar/'+m.uid+'" alt="" onerror="this.remove()"></span><div class="nm"><b>'+esc(m.username)+'</b><small>'+esc(m.role==='viewer'?TX.role_viewer:TX.role_editor)+(m.accepted?'':' &middot; '+esc(TX.pending))+'</small></div><button type="button" class="mini red" onclick="removeMember('+id+','+m.uid+')">&#10005;</button></div>').join(''):'<p style="color:var(--mut);font-size:13px">'+esc(TX.no_members)+'</p>';
 openSheet('sharesheet')}
async function removeMember(acc,uid){const fd=new FormData();fd.set('acc',acc);fd.set('uid',uid);
 try{await fetch('/share/remove',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}})}catch(e){}
 closeS('sharesheet');await refresh()}
function openTransfer(){if(D.role==='viewer')return;const L=D.accs.filter(a=>a.role==='owner'||a.role==='editor');
 const o=L.map(a=>'<option value="'+a.id+'">'+esc(a.name)+' ('+a.currency+')</option>').join('');
 $('tr-from').innerHTML=o;$('tr-to').innerHTML=o;$('tr-from').value=D.acc;
 const other=L.find(a=>a.id!==D.acc);if(other)$('tr-to').value=other.id;
 $('tr-amt').value='';$('tr-in').value='';$('tr-date').value=localToday();trChange();openSheet('trsheet')}
function trChange(){const f=D.accs.find(a=>a.id==$('tr-from').value),t=D.accs.find(a=>a.id==$('tr-to').value);if(!f||!t)return;
 const diff=f.currency!==t.currency;$('tr-in-box').style.display=diff?'':'none';
 if(diff){const n=v=>parseFloat((v||'').replace(/[^0-9.]/g,'')),a=n($('tr-amt').value),b=n($('tr-in').value);
  $('tr-rate').textContent=(a>0&&b>0)?(f.currency==='USD'?'1 USD = '+Math.round(b/a*100)/100+' '+t.currency:'1 USD = '+Math.round(a/b*100)/100+' '+f.currency):''}}
async function submitTransfer(f){closeS('trsheet');
 try{const r=await fetch('/transfer',{method:'POST',body:new FormData(f),headers:{'X-Requested-With':'fetch'}});if(!r.ok)throw 0;toast(TX.saved,1)}catch(e){toast(TX.err)}
 refresh()}
function exportCsv(sc){location.href='/export?scope='+sc+'&acc='+D.acc+(location.search?'&'+location.search.slice(1):'')}
const PAL=['#D97757','#4A6FA5','#2F7D5B','#C9A227','#8E6BBE','#D1788D','#9A978C'];
let tab=(function(){const h=location.hash.slice(1);if(TABS.indexOf(h)>-1)return h;try{return sessionStorage.getItem('tab')}catch(e){return null}})()||'home';
if(location.hash)history.replaceState(null,'',location.pathname+location.search);
function openAdd(t){if(D.role==='viewer'){toast(TX.view_only);return}$('date').value=localToday();setType(t||'expense');openSheet('sheet')}
function setType(t){$('type').value=t;$('lbl').textContent=S[t];['income','expense'].forEach(k=>$('b-'+k).classList.toggle('on',k===t))}
function setCur(c){$('cur').value=c;['IQD','USD'].forEach(k=>$('cb-'+k).classList.toggle('on',k===c))}
function setCaseCur(c){$('ccur').value=c;['IQD','USD'].forEach(k=>$('cc-'+k).classList.toggle('on',k===c))}
function setTab(t,keep){tab=t;if(MAIN.indexOf(t)>-1)lastMain=t;try{sessionStorage.setItem('tab',t)}catch(e){}
 TABS.forEach(k=>{const a=$('t-'+k),b=$('n-'+k);if(a)a.classList.toggle('on',k===t);if(b)b.classList.toggle('on',k===t)});
 document.body.dataset.tab=t;if(!keep)scrollTo(0,0);if(t==='settings'&&!keep)setSub('menu',true);boot()}
function setSub(n,keep){if(!$('s-'+n))n='menu';sub=n;try{sessionStorage.setItem('sub',n)}catch(e){}document.querySelectorAll('.sv').forEach(e=>e.classList.toggle('on',e.id==='s-'+n));if(!keep)scrollTo(0,0)}
function filterCases(st){document.querySelectorAll('.cc').forEach(e=>e.style.display=(st==='all'||e.dataset.st===st)?'':'none');
 document.querySelectorAll('#cfilter .pill').forEach(p=>p.classList.toggle('on',p.dataset.f===st))}

/* ---- dangerous actions always ask first ---- */
function ask(kind,id){
 const a=D.accs.find(x=>x.id===(id||D.acc))||{ni:0,ne:0,name:''},all=D.accs.reduce((s,x)=>s+x.ni+x.ne,0);
 const m={clear_in:['/clear',{acc:a.id,what:'income'},a.ni],clear_ex:['/clear',{acc:a.id,what:'expense'},a.ne],
  clear_all:['/clear',{acc:a.id,what:'all'},a.ni+a.ne],del_acc:['/acc/'+a.id+'/delete',{},a.ni+a.ne]}[kind];
 $('cform').action=m[0];
 $('cfields').innerHTML=Object.keys(m[1]).map(k=>'<input type="hidden" name="'+k+'" value="'+esc(m[1][k])+'">').join('');
 $('ctitle').textContent=TX['ttl_'+kind];
 $('ctext').textContent=TX['msg_'+kind].replace('{n}',()=>m[2]).replace('{name}',()=>a.name);
 $('cchk').checked=false;$('cgo').disabled=true;openSheet('csheet')}
function printReport(k){location.href='/print?kind='+k+'&acc='+D.acc+'&auto=1'+(location.search?'&'+location.search.slice(1):'')}

/* ---- speed: instant UI, photo shrink, background save, soft refresh ---- */
function pend(fd){const t=fd.get('type'),l=$('list-'+t);
 const el=document.createElement('div');el.className='glass item pend';
 el.innerHTML='<div class="dot '+t+'">'+(t==='income'?'&#8595;':'&#8593;')+'</div><div class="meta"><b>'+esc(fd.get('label')||TX[t])+'</b></div><div class="amt '+t+'">'+esc(fd.get('amount'))+'</div><span class="spin"></span>';
 const em=l.querySelector('.empty');if(em)em.remove();l.prepend(el)}
async function refresh(){
 try{const r=await fetch(location.pathname+location.search,{headers:{'X-Requested-With':'fetch'},credentials:'same-origin'});
  if(r.url.indexOf('/login')>-1){location.href='/login';return}
  const doc=new DOMParser().parseFromString(await r.text(),'text/html'),w=doc.querySelector('.wrap'),dj=doc.getElementById('data');
  if(!w||!dj){location.reload();return}
  document.querySelector('.wrap').innerHTML=w.innerHTML;D=JSON.parse(dj.textContent);setTab(tab,true);setSub(sub,true);applyTheme();
 }catch(e){location.reload()}}
async function submitAdd(f){
 const fd=new FormData(f),file=f.photo.files[0];
 closeS('sheet');pend(fd);f.reset();
 try{
  if(file&&file.type.indexOf('image/')===0){const b=await shrink(file);if(b)fd.set('photo',b,'p.jpg')}
  const r=await fetch('/add',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}});
  if(!r.ok)throw 0;toast(TX.saved,1)
 }catch(e){toast(TX.err)}
 refresh()}
function softDel(f){const it=f.closest('.item,.setrow');it.style.opacity='.3';it.style.pointerEvents='none';
 fetch(f.action,{method:'POST',headers:{'X-Requested-With':'fetch'}}).then(refresh).catch(()=>location.reload())}

/* ---- charts (drawn only while the Charts page is open) ---- */
function money(v){const n=new Intl.NumberFormat('en',{minimumFractionDigits:D.dec,maximumFractionDigits:D.dec}).format(v);return D.cur==='USD'?'$'+n:n+' '+D.sym}
function showCats(t){cat=t;
 ['expense','income'].forEach(k=>$('tb-'+k).classList.toggle('on',k===t));
 const lg=$('legend'),box=$('c2w'),rows=D.cats[t];
 if(pie){pie.destroy();pie=null}
 if(!rows.length){box.style.display='none';lg.innerHTML='<div class="empty">'+esc(TX.no_data)+'</div>';return}
 box.style.display='';
 const tot=rows.reduce((a,r)=>a+r[1],0);
 if(window.Chart)pie=new Chart($('c2'),{type:'doughnut',
  data:{labels:rows.map(r=>r[0]),datasets:[{data:rows.map(r=>r[1]),backgroundColor:PAL,borderWidth:2,borderColor:getComputedStyle(document.documentElement).getPropertyValue('--card').trim(),hoverOffset:6}]},
  options:{maintainAspectRatio:false,cutout:'68%',plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>' '+money(c.parsed)}}}}});
 lg.innerHTML=rows.map((r,i)=>'<div class="lg"><i style="background:'+PAL[i%PAL.length]+'"></i><span>'+esc(r[0])+'</span><b>'+Math.round(r[1]/tot*100)+'%</b><small>'+money(r[1])+'</small></div>').join('')}
let chartReady=null;
function loadChart(cb){if(window.Chart)return cb();
 if(!chartReady)chartReady=new Promise(res=>{const sc=document.createElement('script');sc.src='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';sc.onload=res;sc.onerror=res;document.head.appendChild(sc)});
 chartReady.then(cb)}
function draw(){
 if(tab!=='charts')return;
 if(window.Chart){
  const cs=getComputedStyle(document.documentElement),edge=cs.getPropertyValue('--edge').trim();Chart.defaults.color=cs.getPropertyValue('--mut').trim();Chart.defaults.font.family="Vazirmatn,sans-serif";
  const compact=new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1});
  if(bar){bar.destroy();bar=null}
  if(D.labels.length)bar=new Chart($('c1'),{type:'bar',
   data:{labels:D.labels,datasets:[
    {label:TX.income,data:D.inc,backgroundColor:'rgba(47,125,91,.85)',borderRadius:6,borderSkipped:false},
    {label:TX.expense,data:D.exp,backgroundColor:'rgba(194,65,47,.8)',borderRadius:6,borderSkipped:false}]},
   options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{usePointStyle:true,boxWidth:8}},tooltip:{callbacks:{label:c=>' '+c.dataset.label+': '+money(c.parsed.y)}}},
    scales:{x:{grid:{display:false}},y:{beginAtZero:true,grid:{color:edge},ticks:{callback:v=>compact.format(v)}}}}});
 }
 showCats(cat)}
function boot(){
 if(bar){bar.destroy();bar=null}
 if(pie){pie.destroy();pie=null}
 if(tab!=='charts')return;
 loadChart(draw)}
applyTheme();setType('expense');setTab(tab,true);setSub(sub,true);if(MSG)toast(MSG.replace(/^!/,''),MSG[0]!=='!');
setTimeout(()=>loadChart(()=>{}),2500);
</script>""" + PWA + """</body></html>"""

CASE = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{c.name}}</title>{{css|safe}}</head>
<body class="c-{{c.currency}}"><div class="wrap" style="padding-bottom:60px">

<div class="top"><a class="back" style="margin:0" href="/#cases">&lsaquo; {{t('cases_t')}}</a><span class="badge {{c.status}}">{{t('status_'+c.status)}}</span></div>

{% if role!='owner' %}<div class="glass note-banner">&#128101; {{t('shared_by')}} <b>{{owner}}</b> &middot; {{t('role_'+role)}}</div>{% endif %}
<div class="glass hero"><div class="hl"><span>{{t('cur_'+c.currency)}}</span><div class="pills">{% if role=='owner' %}<button class="mini" onclick="openSheet('sharesheet')">&#128101; {{t('share_btn')}}{% if members %} ({{members|length}}){% endif %}</button><button class="mini" onclick="openSheet('editsheet')">{{t('edit_case')}}</button>{% endif %}</div></div>
<h1 class="cn">{{c.name}}</h1>
<div class="cm">{% if c.client %}<div><span>{{t('client')}}</span><b>{{c.client}}</b></div>{% endif %}
{% if c.case_no %}<div><span>{{t('case_no')}}</span><b>{{c.case_no}}</b></div>{% endif %}
{% if c.court %}<div><span>{{t('court')}}</span><b>{{c.court}}</b></div>{% endif %}
{% if c.started %}<div><span>{{t('started')}}</span><b>{{c.started}}</b></div>{% endif %}
{% if c.hearing %}<div><span>&#9878; {{t('hearing')}}</span><b>{{c.hearing}}</b></div>{% endif %}</div></div>

<div class="stat4">
<div class="glass"><span>{{t('fee')}}</span><b>{{fm(c.fee,cur)}}</b></div>
<div class="glass"><span>{{t('case_in')}}</span><b class="in">{{fm(inc,cur)}}</b></div>
<div class="glass"><span>{{t('case_ex')}}</span><b class="ex">{{fm(exp,cur)}}</b></div>
<div class="glass"><span>{{t('case_net')}}</span><b>{{fm(inc-exp,cur)}}</b></div>
{% if c.fee %}<div class="glass wide"><span>{{t('fee_left')}}</span><b>{{fm(c.fee-inc,cur)}}</b></div>{% endif %}</div>

{% if role!='viewer' %}<div class="qa"><button class="e" onclick="openAdd('expense')">&#8593; {{t('add_case_ex')}}</button><button class="i" onclick="openAdd('income')">&#8595; {{t('add_case_in')}}</button></div>{% endif %}

<div class="pills prn"><a class="pill" href="/print?kind=statement&acc={{c.id}}&p=all&auto=1">&#128424; {{t('print_case')}}</a>
<a class="pill" href="/print?kind=expense&acc={{c.id}}&p=all&auto=1">&#128424; {{t('print_case_ex')}}</a>
<a class="pill" href="/print?kind=income&acc={{c.id}}&p=all&auto=1">&#128424; {{t('print_case_in')}}</a></div>

<div class="seg"><button type="button" id="lt-expense" class="expense on" onclick="showL('expense')">{{t('case_ex')}}</button>
<button type="button" id="lt-income" class="income" onclick="showL('income')">{{t('case_in')}}</button></div>

{% macro lst(kind, groups) %}<div id="ls-{{kind}}">{% for d,gp in groups %}<div class="day"><span>{{d}}</span><span>{{fm(gp.n,cur)}}</span></div>
{% for x in gp['items'] %}<div class="glass item">
<div class="dot {{x.type}}">{{'&#8595;'|safe if x.type=='income' else '&#8593;'|safe}}</div>
<div class="meta"><b>{{x.label or t('case_'+('in' if x.type=='income' else 'ex'))}}</b>{% if x.note %}<small>{{x.note}}</small>{% endif %}{% if show_by and x.by_user %}<small>&#128100; {{x.by_user}}</small>{% endif %}</div>
{% if x.img %}<a href="/img/{{x.img}}" target="_blank"><img class="thumb" src="/img/{{x.img}}" alt=""></a>{% endif %}
<div class="amt {{x.type}}">{{fm(x.amount,cur)}}</div>
{% if x.type=='income' %}<a class="x rc" href="/receipt/{{x.id}}?auto=1" title="{{t('receipt_t')}}">&#129534;</a>{% endif %}{% if role=='owner' or (role=='editor' and x.uid==uid) %}<button class="x ed" onclick="openEdit({{x.id}})" title="{{t('edit_t')}}">&#9998;</button><form method="post" action="/delete/{{x.id}}" onsubmit="if(!confirm('{{t('confirm')}}'))return false;softDel(this);return false"><button class="x" title="{{t('delete')}}">&#10005;</button></form>{% endif %}
</div>{% endfor %}{% else %}<div class="empty">{{t('empty')}}</div>{% endfor %}</div>{% endmacro %}
{{ lst('expense', ge) }}{{ lst('income', gi) }}

{% if role=='owner' %}<div class="two" style="margin-top:24px">
<form method="post" action="/case/{{c.id}}/status"><input type="hidden" name="status" value="{{'closed' if c.status=='open' else 'open'}}">
<button class="btn ghost sm" style="margin-top:0">{{t('close_case') if c.status=='open' else t('reopen_case')}}</button></form>
<button class="btn red sm" style="margin-top:0" onclick="$('cchk').checked=false;$('cgo').disabled=true;openSheet('csheet')">{{t('del_case')}}</button></div>{% else %}<form method="post" action="/share/remove" onsubmit="return confirm('{{t('confirm')}}')"><input type="hidden" name="acc" value="{{c.id}}"><input type="hidden" name="uid" value="{{uid}}"><input type="hidden" name="next" value="/#cases"><button class="btn red sm" style="margin-top:24px">{{t('leave')}}</button></form>{% endif %}
</div>

<div class="sheet" id="sheet" onclick="if(event.target===this)closeS('sheet')">
<form method="post" action="/add" enctype="multipart/form-data" onsubmit="submitAdd(this);return false">
<input type="hidden" name="acc" value="{{c.id}}"><input type="hidden" name="type" id="type" value="expense">
<div class="seg"><button type="button" id="b-income" class="income" onclick="setType('income')">{{t('add_case_in')}}</button>
<button type="button" id="b-expense" class="expense" onclick="setType('expense')">{{t('add_case_ex')}}</button></div>
<input class="big" name="amount" inputmode="decimal" placeholder="0 {{ 'USD' if c.currency=='USD' else 'IQD' }}" required autocomplete="off">
<label id="lbl"></label><input name="label" autocomplete="off">
<label>{{t('note')}}</label><textarea name="note" rows="2"></textarea>
<label>{{t('date')}}</label><input type="date" name="date" id="date" value="{{td}}">
<label>{{t('photo')}}</label><input type="file" name="photo" accept="image/*">
<button class="btn">{{t('save')}}</button></form></div>

<div class="sheet" id="editsheet" onclick="if(event.target===this)closeS('editsheet')">
<form method="post" action="/case/{{c.id}}/edit"><h3>{{t('edit_case')}}</h3>
<label>{{t('case_name')}}</label><input name="name" required maxlength="80" value="{{c.name}}" autocomplete="off">
<label>{{t('client')}}</label><input name="client" maxlength="80" value="{{c.client}}" autocomplete="off">
<div class="frow"><div><label>{{t('case_no')}}</label><input name="case_no" maxlength="40" value="{{c.case_no}}" autocomplete="off"></div>
<div><label>{{t('court')}}</label><input name="court" maxlength="80" value="{{c.court}}" autocomplete="off"></div></div>
<label>{{t('fee')}}</label><input name="fee" inputmode="decimal" value="{{fee_v}}" autocomplete="off">
<div class="frow"><div><label>{{t('started')}}</label><input type="date" name="started" value="{{c.started or ''}}"></div>
<div><label>{{t('hearing')}}</label><input type="date" name="hearing" value="{{c.hearing or ''}}"></div></div>
<button class="btn">{{t('save')}}</button></form></div>

<div class="sheet" id="csheet" onclick="if(event.target===this)closeS('csheet')">
<form method="post" action="/case/{{c.id}}/delete"><h3>{{t('ttl_del_case')}}</h3>
<p style="line-height:1.8">{{t('msg_del_case').replace('{name}', c.name).replace('{n}', n|string)}}</p>
<label class="chk"><input type="checkbox" id="cchk" onchange="$('cgo').disabled=!this.checked"><span>{{t('confirm_check')}}</span></label>
<div class="two"><button type="button" class="btn ghost" onclick="closeS('csheet')">{{t('cancel')}}</button>
<button class="btn red" id="cgo" disabled>{{t('yes_delete')}}</button></div></form></div>

""" + ESHEET + CASESHARE + """<script>""" + COMMON_JS + """
const TX={{ tr|tojson }};
const ITEMS={{ items|tojson }};function getItems(){return ITEMS}function afterEdit(){location.reload()}
function setType(t){$('type').value=t;$('lbl').textContent=t==='income'?TX.src_case_in:TX.src_case_ex;['income','expense'].forEach(k=>$('b-'+k).classList.toggle('on',k===t))}
function openAdd(t){$('date').value=localToday();setType(t);openSheet('sheet')}
function showL(k){try{sessionStorage.setItem('lt',k)}catch(e){}
 ['expense','income'].forEach(x=>{$('ls-'+x).style.display=x===k?'':'none';$('lt-'+x).classList.toggle('on',x===k)})}
async function submitAdd(f){const fd=new FormData(f),file=f.photo.files[0];closeS('sheet');document.body.style.opacity='.6';
 try{if(file&&file.type.indexOf('image/')===0){const b=await shrink(file);if(b)fd.set('photo',b,'p.jpg')}
  const r=await fetch('/add',{method:'POST',body:fd,headers:{'X-Requested-With':'fetch'}});if(!r.ok)throw 0;
 }catch(e){document.body.style.opacity='';toast(TX.err);return}
 location.reload()}
function softDel(f){f.closest('.item').style.opacity='.3';
 fetch(f.action,{method:'POST',headers:{'X-Requested-With':'fetch'}}).then(()=>location.reload()).catch(()=>location.reload())}
(function(){let sx=0,sy=0,st=0,ok=false;
 const blocked=e=>e.target.closest&&e.target.closest('canvas,input,textarea,select,.sheet,.toast');
 addEventListener('touchstart',e=>{if(e.touches.length!==1||blocked(e)){ok=false;return}const t=e.touches[0];sx=t.clientX;sy=t.clientY;st=Date.now();ok=true},{passive:true});
 addEventListener('touchend',e=>{if(!ok)return;ok=false;const t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy;
  if(Date.now()-st>700||Math.abs(dx)<70||Math.abs(dx)<Math.abs(dy)*1.7||document.querySelector('.sheet.open'))return;
  const rtl=document.documentElement.dir==='rtl';
  if((dx<0?(rtl?-1:1):(rtl?1:-1))<0)location.href='/#cases'},{passive:true});
})();
setType('expense');showL((function(){try{return sessionStorage.getItem('lt')}catch(e){return null}})()||'expense');
{% if msg %}toast({{ msg|tojson }}.replace(/^!/,''),{{ msg|tojson }}[0]!=='!');{% endif %}
</script></body></html>"""

PRINT = """<!doctype html><html lang="{{L}}" dir="{{dir}}"><head><meta charset="utf-8"><title>{{acc.name if acc else t('print_grand')}}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#FFFFFF"><link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap">
<style>
*{box-sizing:border-box}
body{font-family:'Vazirmatn',-apple-system,sans-serif;color:#111;background:#fff;margin:0 auto;padding:calc(16px + env(safe-area-inset-top)) 16px 40px;max-width:820px;font-size:14px;-webkit-text-size-adjust:100%}
.lh{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px double #111;padding-bottom:8px;margin-bottom:14px;gap:10px}
.office{font-size:18px;font-weight:700}.lhl{display:flex;align-items:center;gap:12px}.logo{max-height:64px;max-width:130px;object-fit:contain}
h1{margin:6px 0 4px;font-size:24px;line-height:1.4}
h2{font-size:16px;margin:22px 0 8px;border-bottom:2px solid #111;padding-bottom:4px}
.meta{color:#555;font-size:12px}
.cinfo{display:grid;gap:4px;margin:6px 0 10px}.cinfo span{color:#555;font-size:12px;margin-inline-end:6px}
table{width:100%;border-collapse:collapse;margin-top:6px}
th,td{padding:7px 8px;border-bottom:1px solid #ddd;text-align:start;vertical-align:top}
th{background:#f1f1f1;font-size:12px}
td.n,th.n{text-align:end;direction:ltr;white-space:nowrap}
tfoot td{font-weight:700;border-top:2px solid #111;border-bottom:0}
tr{page-break-inside:avoid}
.totals{margin:22px 0 0;margin-inline-start:auto;max-width:380px;border:2px solid #111;border-radius:6px;page-break-inside:avoid}
.totals h3{margin:0;padding:7px 10px;background:#111;color:#fff;font-size:13px}
.totals div{display:flex;justify-content:space-between;gap:12px;padding:8px 10px;border-top:1px solid #ddd}
.totals b{direction:ltr}
.totals .gr{background:#f1f1f1;font-size:16px;font-weight:700}
.sign{display:flex;justify-content:flex-end;margin-top:46px}.sign div{width:220px;border-top:1px solid #111;padding-top:6px;text-align:center;font-size:12px;color:#555}
.bar{display:flex;gap:8px;justify-content:space-between;margin-bottom:14px}
.bar a,.bar button{padding:11px 18px;border-radius:12px;border:1px solid #111;background:#fff;color:#111;font:inherit;text-decoration:none;cursor:pointer}
.bar button{background:#D97757;border-color:#D97757;color:#fff;font-weight:700}
@media print{.noprint{display:none}body{padding:0}@page{margin:14mm}}
</style></head><body>
{% macro tbl(rows, total) %}{% if rows %}<table><thead><tr><th>{{t('date')}}</th><th>{{t('col_label')}}</th><th>{{t('note')}}</th><th class="n">{{t('amount')}}</th></tr></thead><tbody>
{% for r in rows %}<tr><td>{{r.date}}</td><td>{{r.label}}</td><td>{{r.note}}</td><td class="n">{{fm(r.amount,cur)}}</td></tr>{% endfor %}</tbody>
<tfoot><tr><td colspan="3">{{t('total')}} ({{rows|length}})</td><td class="n">{{fm(total,cur)}}</td></tr></tfoot></table>{% else %}<p class="meta">{{t('empty')}}</p>{% endif %}{% endmacro %}
<div class="bar noprint"><a href="{{'/case/%s'|format(acc.id) if acc and acc.kind=='case' else '/'}}">&larr; {{t('back')}}</a><button onclick="print()">&#128424; {{t('print_btn')}}</button></div>
<div class="lh"><div class="lhl">{% if has_logo %}<img class="logo" src="/logo" alt="">{% endif %}<div><div class="office">{{office or t('app')}}</div>{% if phone %}<div class="meta" dir="ltr">&#9742; {{phone}}</div>{% endif %}</div></div><div class="meta">{{t('generated')}}: {{now}}</div></div>
{% if kind=='grand' %}
<h1>{{t('print_grand')}}</h1><div class="meta">{{t('period')}}: {{plabel}}</div>
<table><thead><tr><th>{{t('acc_name')}}</th><th class="n">{{t('income')}}</th><th class="n">{{t('expense')}}</th><th class="n">{{t('net')}}</th><th class="n">{{t('balance')}}</th></tr></thead><tbody>
{% for a in rep %}<tr><td>{{a.name}} <span class="meta">({{t('cur_'+a.currency)}})</span></td><td class="n">{{fm(a.inc,a.currency)}}</td><td class="n">{{fm(a.exp,a.currency)}}</td><td class="n">{{fm(a.inc-a.exp,a.currency)}}</td><td class="n">{{fm(a.bal,a.currency)}}</td></tr>{% endfor %}</tbody></table>
<div class="totals"><h3>{{t('grand_total')}}</h3>
{% for c,v in tots.items() %}<div class="gr"><span>{{t('cur_'+c)}}</span><b>{{fm(v.bal,c)}}</b></div>{% endfor %}</div>
{% else %}
{% set case = acc.kind=='case' %}
<h1>{{acc.name}}</h1>
{% if case %}<div class="cinfo">{% if acc.client %}<div><span>{{t('client')}}</span><b>{{acc.client}}</b></div>{% endif %}
{% if acc.case_no %}<div><span>{{t('case_no')}}</span><b>{{acc.case_no}}</b></div>{% endif %}
{% if acc.court %}<div><span>{{t('court')}}</span><b>{{acc.court}}</b></div>{% endif %}{% if acc.started %}<div><span>{{t('started')}}</span><b>{{acc.started}}</b></div>{% endif %}</div>{% endif %}
<div class="meta">{{t('cur_'+cur)}} &middot; {{t('period')}}: {{plabel}}</div>
{% if kind in ('statement','expense') %}<h2>{{t('case_ex') if case else t('expense')}}</h2>{{ tbl(exp, acc.exp) }}{% endif %}
{% if kind in ('statement','income') %}<h2>{{t('case_in') if case else t('income')}}</h2>{{ tbl(inc, acc.inc) }}{% endif %}
{% if kind=='statement' and trs %}<h2>{{t('transfer_t')}}</h2><table><thead><tr><th>{{t('date')}}</th><th>{{t('col_label')}}</th><th>{{t('note')}}</th><th class="n">{{t('amount')}}</th></tr></thead><tbody>
{% for r in trs %}<tr><td>{{r.date}}</td><td>{{t('tr_to') if r.type=='expense' else t('tr_from')}}: {{r.label}}</td><td>{{r.note}}</td><td class="n">{{'-' if r.type=='expense' else '+'}}{{fm(r.amount,cur)}}</td></tr>{% endfor %}</tbody></table>{% endif %}
{% if kind=='statement' %}<div class="totals"><h3>{{t('grand_total')}}</h3>
{% if case %}<div><span>{{t('case_net')}}</span><b>{{fm(acc.inc-acc.exp,cur)}}</b></div>
{% if acc.fee %}<div><span>{{t('fee')}}</span><b>{{fm(acc.fee,cur)}}</b></div><div class="gr"><span>{{t('fee_left')}}</span><b>{{fm(acc.fee-acc.inc,cur)}}</b></div>{% endif %}
{% else %}<div><span>{{t('net')}}</span><b>{{fm(acc.inc-acc.exp,cur)}}</b></div>{% if trs %}<div><span>{{t('tr_net')}}</span><b>{{fm(acc.tin-acc.tout,cur)}}</b></div>{% endif %}<div><span>{{t('opening')}}</span><b>{{fm(acc.opening,cur)}}</b></div>
<div class="gr"><span>{{t('balance')}}</span><b>{{fm(acc.bal,cur)}}</b></div>{% endif %}</div>{% endif %}
{% if case %}<div class="sign"><div>{{t('signature')}}</div></div>{% endif %}
{% endif %}
<script>{% if auto %}addEventListener('load',function(){setTimeout(function(){print()},700)});{% endif %}</script>
</body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("PRODUCTION") != "1")
