"""Run from flutter_app/ after `flutter create --platforms=android`.
Adds the INTERNET permission (missing from release builds by default) and the app name."""
import re

P = "android/app/src/main/AndroidManifest.xml"
s = open(P, encoding="utf-8").read()
if "android.permission.INTERNET" not in s:
    s = s.replace("<application", '<uses-permission android:name="android.permission.INTERNET"/>\n    <application', 1)
s = re.sub(r'android:label="[^"]*"', 'android:label="\u062c\u0632\u062f\u0627\u0646\u06d5\u06a9\u06d5\u0645"', s, count=1)
open(P, "w", encoding="utf-8").write(s)
print("AndroidManifest patched")
