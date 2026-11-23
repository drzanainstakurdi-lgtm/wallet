# جزدانەکەم - ئەپی ئایفۆنی سەربەخۆ (Flutter + Supabase)

ئەپەکە ڕاستەوخۆ لەگەڵ Supabase قسە دەکات. Flask، Render و ڤێرسڵ هیچیان نایەنە ناوی.
سایتەکەت وەک خۆی دەمێنێتەوە و هەمان داتا بەکاردێنن.

## ١. Supabase (تەنها یەک جار)
1. SQL Editor: ئەگەر پێشتر `schema.sql` ـی سایتەکەت ڕانکردووە، ڕایبکە.
2. SQL Editor: ناوەڕۆکی `supabase/app_setup.sql (لە ڕەگی پڕۆژەکە)` بنووسە و Run بکە.
   ئەمە تەنها فانکشنی نوێ و یەک ستوونی نوێ (`users.auth_id`) زیاد دەکات. هیچ شتێکی کۆن ناگۆڕێت.
3. Authentication > Providers > Email: **Confirm email** بکوژێنەرەوە.
4. Project Settings > API: `Project URL` و `anon public` key کۆپی بکە.
   **service_role key هەرگیز مەخەرە ناو ئەپەکە.**

## ٢. بەکارهێنەرە کۆنەکان (ئەوانەی لە سایتەکەوە هەیانە)
پاسوۆردی سایتەکە بە شێوەیەک هەڵگیراوە کە Supabase Auth ناتوانێت بیخوێنێتەوە، بۆیە تۆ بۆ هەر بەکارهێنەرێک پاسوۆردی ئەپەکە دیاری دەکەیت:

    pip install httpx python-dotenv
    python flutter_app/tools/link_legacy_users.py .env

(ئەمە لە کۆمپیوتەری خۆتدا ڕا بکە؛ داتاکانیان هەمان داتای ڕابردوون.)
بەکارهێنەری نوێ دەتوانێت لە ناو ئەپەکەدا خۆی تۆمار بکات.

## ٣. دروستکردنی ئەپ لە ویندۆزەوە (Codemagic)
1. فۆڵدەرەکە بخە ناو GitHub.
2. https://codemagic.io: ریپۆکە زیاد بکە.
3. Codemagic > Environment variables: `SUPABASE_URL` و `SUPABASE_ANON_KEY` زیاد بکە.
4. `codemagic.yaml`: `CHANGE_ME_KEY_NAME` و `APP_STORE_APPLE_ID` بگۆڕە (Bundle ID: `com.dana.wallet`).
5. Build بکە، ئەپەکە دەچێتە TestFlight.

## چی هەیە / چی نییە (وەشانی ١)
هەیە: چوونەژوورەوە و خۆتۆمارکردن، چەند هەژمار، سەرەکی (ماوە، ئەمڕۆ/هەفتە/مانگ، بودجە، دانیشتنی نزیک)،
داهات و خەرجی (زیادکردن، دەستکاری، سڕینەوە، گەڕان)، کەیسەکان (دروستکردن، پێشەکی، وەرگیراو/خەرجکراو، داخستن)،
هێڵکاری، ڕێکخستنەکان (زمان کوردی/English/عربي، پرۆفایل، بودجە، پاسوۆرد).
هێشتا نییە (دەتوانرێت دواتر زیاد بکرێت): گواستنەوە لەنێوان هەژمار، هاوبەشکردنی هەژمار، دووبارەبووەوەکان،
وێنەی وەسڵ، Print/CSV، لاپەڕەی موڤەکیلەکان، چوونەژوورەوە بە Google.

## ئەندرۆید
- Codemagic: workflow ـی `wallet-flutter-android` بەکاربهێنە. دوای Build، فایلی `.apk` دابەزێنە و بینێرە بۆ مۆبایلەکە (ڕێگە بدە بە «Install unknown apps»). ئەم APK بە کلیلی debug واژۆ دەکرێت، بۆ بەکارهێنانی خۆت باشە؛ بۆ Google Play پێویستت بە keystore ـی خۆت هەیە.
- لە ویندۆزەوە بەبێ Codemagic (پێویستی بە Flutter SDK و Android Studio هەیە):

      cd flutter_app
      flutter create --platforms=android --org com.dana --project-name wallet .
      python scripts/patch_android.py
      flutter pub get
      dart run flutter_launcher_icons
      flutter build apk --release --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_ANON_KEY=...

  فایلەکە لە `build/app/outputs/flutter-apk/app-release.apk` دەبێت.

## GitHub Actions (بەبێ Codemagic)
فایلەکان لە `.github/workflows/` ـن: `android.yml` و `ios.yml`.

1. پڕۆژەکە بخە ناو ریپۆی GitHub (باشترە Private بێت). فایلی `.env` مەخەرە ناوی.
2. GitHub > Settings > Secrets and variables > Actions > New repository secret:
   `SUPABASE_URL` و `SUPABASE_ANON_KEY` (تەنها anon key).
3. **ئەندرۆید:** Actions > Android APK > Run workflow. کە تەواو بوو، بچۆ ناو ئەو run و لە Artifacts ـەوە
   `wallet-android-apk` دابەزێنە. ناو zip ـەکە `app-release.apk` ـە.
4. **ئایفۆن:** پێویستی بە ئەکاونتی Apple Developer هەیە. ئەم هەنگاوانە بکە:
   - Apple Developer > Identifiers: Bundle ID بە ناوی `com.dana.wallet` دروست بکە.
   - App Store Connect > Apps: ئەپێک بە هەمان Bundle ID دروست بکە.
   - App Store Connect > Users and Access > Integrations > Team Keys: کلیلێک دروست بکە (ڕۆڵ: Admin) و فایلی `.p8` دابەزێنە (تەنها یەک جار دەتوانیت).
   - لە GitHub ئەم secret ـانە زیاد بکە: `APPSTORE_KEY_ID`، `APPSTORE_ISSUER_ID`، `APPSTORE_KEY_P8` (ناوەڕۆکی فایلی .p8)، `IOS_TEAM_ID` (Team ID لە Membership).
   - Actions > iOS (TestFlight) > Run workflow. دوای چەند خولەک ئەپەکە لە TestFlight دەردەکەوێت.
   بەبێ secret ـە Apple ـیەکان، workflow ـەکە تەنها پشکنین دەکات کە ئەپەکە کۆمپایل دەبێت.
5. تێبینی: macOS لە GitHub بۆ ریپۆی Private کاتی زیاتر دەخوات لە پلانی خۆڕایی.

## چوونەژوورەوە بە Google (ئەندرۆید و ئایفۆن)
دوگمەی Google تەنها کاتێک دەردەکەوێت کە `GOOGLE_WEB_CLIENT_ID` دانرابێت.

**١. Google Cloud Console** (console.cloud.google.com):
- APIs & Services > OAuth consent screen: ناوی ئەپ و ئیمەیڵ پڕ بکەرەوە، و دوایی **Publish app** بکە.
- Credentials > Create credentials > OAuth client ID، سێ دانە دروست بکە:
  - **Web application**: Authorized redirect URI ـەکەی ئەمە بێت: `https://<project-ref>.supabase.co/auth/v1/callback`. ئەمە Client ID و Client secret ـی web دەدات.
  - **Android**: Package name = `com.dana.wallet`، و SHA-1 ـی کلیلەکەت (بڕوانە خوارەوە).
  - **iOS**: Bundle ID = `com.dana.wallet`. ئەمە iOS Client ID دەدات.

**٢. Supabase** > Authentication > Providers > Google:
- Enable بکە. لە Client IDs هەر سێ ID بنووسە بە کۆما جیا کراوەتەوە (`web,ios,android`). Client Secret ـی web دابنێ.
- **Skip nonce checks** بکەرەوە (بۆ iOS پێویستە).

**٣. کلیلی ئەندرۆید (SHA-1)** - دەبێت ثابت بێت، چونکە GitHub هەر جارێک کلیلێکی نوێ دروست دەکات و Google ڕەتی دەکاتەوە. لە ویندۆز (کە Java هەبێت) یەک جار:

    keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
    keytool -list -v -keystore debug.keystore -storepass android -alias androiddebugkey
    powershell -c "[Convert]::ToBase64String([IO.File]::ReadAllBytes('debug.keystore'))"

- ئەنجامی `SHA1:` ی دووەم فەرمان بدە بە Android OAuth client لە Google Cloud.
- ئەنجامی سێیەم (دەقە درێژەکە) بکە بە GitHub secret بە ناوی `ANDROID_DEBUG_KEYSTORE_B64`.
- فایلی `debug.keystore` لە جێیەکی سەلامەت بپارێزە (ئەگەر ون بوو، SHA-1 دەگۆڕێت).

**٤. GitHub secrets**: `GOOGLE_WEB_CLIENT_ID` و `GOOGLE_IOS_CLIENT_ID` (بۆ Codemagic وەک Environment variables).

**٥. Supabase SQL Editor**: `supabase/app_setup.sql` دووبارە ڕا بکە (بێ مەترسییە). ئەمە لۆجیکی Google زیاد دەکات.

**چی ڕوودەدات:**
- ئەگەر پێشتر بە هەمان هەژماری Google لە سایتەکەدا خۆت تۆمار کردبێت، یەکەم جار لە ئەپەکەدا بە Google بچیتە ژوورەوە، هەمان هەژمار و هەموو داتاکانت وەردەگرێت.
- هەژماری نوێ بە ناوی بەکارهێنەری لە ئیمەیڵەکەوە دروست دەبێت.
- بەکارهێنەرێک بە ناوی بەکارهێنەر و پاسوۆرد لە سایتەکە هەیبێت، ناتوانێت Google بەستەوە؛ ئەو بە پاسوۆردی ئەپەکە دەچێتە ژوورەوە (`link_legacy_users.py`).

## ئەرشیف و داونلۆد
- لە ناو کەیسەکە، مینووی سێ خاڵ > **کۆتایی پێ بهێنە**: کەیسەکە دەچێتە **ئەرشیف** (ئایکۆنی سندووق لە لاپەڕەی کەیسەکان).
- لە ئەرشیف بۆ **٣٠ ڕۆژ** دەمێنێتەوە و ژمارەی ڕۆژی ماوە پیشان دەدرێت؛ دوای ئەوە بە تەواوی دەسڕدرێتەوە (کەیس و هەموو تۆمارەکانی).
- هەر کاتێک لە ئەرشیف **گەڕاندنەوە** بکەیت، دەگەڕێتەوە ناو کەیسە کراوەکان.
- **داونلۆد**: فایلی CSV دروست دەکات (لە Excel دەکرێتەوە) و لیستی هاوبەشکردنی مۆبایل دەکاتەوە: Save to Files، Drive، WhatsApp و هتد.
- ژمارەی ڕۆژەکان لە `supabase/app_setup.sql` ـدایە: `app_archive_days()` (٣٠). بیکە `0` ئەگەر نەتەوێت هەرگیز بسڕدرێتەوە. دوای گۆڕین، فایلەکە دووبارە ڕا بکە.
- ئەو کەیسانەی پێشتر لە سایتەکەدا داخراون، ٣٠ ڕۆژەکەیان لە یەکەم جاری کردنەوەی ئەپەکەوە دەست پێدەکات.
- وێنەی وەسڵی کەیسە سڕاوەکان لە Storage دەمێننەوە (تەنها تۆمارەکانی داتابەیس دەسڕدرێنەوە).

## سڕینەوەی کەیس (وەشانی نوێ)
- مینووی کەیس > **سڕینەوە**: کەیسەکە ناسڕدرێتەوە، دەچێتە ئەرشیف بۆ ٣٠ ڕۆژ (نیشانەی «سڕاوەتەوە»).
- لە ئەرشیف دەتوانیت: **داونلۆد**، **گەڕاندنەوە**، یان **سڕینەوەی هەمیشەیی** (یەکسەر، بێ گەڕانەوە).
- ئەگەر هیچ نەکەیت، دوای ٣٠ ڕۆژ خۆکارانە بۆ هەمیشە دەسڕدرێتەوە.
- هەموو کردارەکان (تەواوبوون، سڕینەوە، گەڕاندنەوە، سڕینەوەی هەمیشەیی، سڕینەوەی خۆکار) لە خشتەی `case_log` دەنووسرێن و لە خوارەوەی ئەرشیف بە «مێژوو» پیشان دەدرێن، تەنانەت دوای ئەوەی کەیسەکە بۆ هەمیشە سڕایەوە.
- `supabase/app_setup.sql` دووبارە ڕا بکە.

## دیزاینی نوێی دۆسیەکان
- ڕەنگەکان بوون بە شینی تاریکی مەرەکەب (ink) و ئاڵتوونی (brass) لەسەر پاشبنەمایەکی خۆڵەمێشی کاڵ. هەموو ئەپەکە ئەم ڕەنگانە بەکاردێنێت؛ لە `lib/ui.dart` (سەرەتای فایلەکە) دەتوانیت بیگۆڕیت.
- هەر دۆسیەیەک وەک **فۆڵدەرێک** پیشان دەدرێت، بە تابێکی ڕەنگاوڕەنگ (دادگا، خانوو، ئۆتۆمبێل، تر) و ژمارەی دۆسیە.
- لاپەڕەی دۆسیەکان: ژمارەی دۆسیە کراوەکان و کۆی پارەی ماوە بۆ وەرگرتن، گەڕان، فلتەر (دانیشتنی نزیک / ماوەی هەیە)، و ژمارەی ڕۆژی ماوە بۆ دانیشتن.
- لاپەڕەی دۆسیە: بەشی سەرەوە، دانیشتنی داهاتوو، ماوە و پێشکەوتنی پارە، و تۆمارەکان بەپێی مانگ. دوگمەی «وەرگیراو» و «خەرجکراو» لە خوارەوە جێگیرن.
- فۆرمی دۆسیەی نوێ بووە بە لاپەڕەیەکی تەواو بە بەشەکان.
