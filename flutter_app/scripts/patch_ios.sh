#!/bin/sh
# Run after `flutter create --platforms=ios`. Adds the iOS settings the app needs.
set -e
PLIST=ios/Runner/Info.plist
add() { /usr/libexec/PlistBuddy -c "Add :$1 $2 $3" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :$1 $3" "$PLIST"; }
add CFBundleDisplayName string "جزدانەکەم"
add ITSAppUsesNonExemptEncryption bool false

# Google sign-in needs the reversed iOS client ID as a URL scheme
if [ -n "$GOOGLE_IOS_CLIENT_ID" ]; then
  REV="com.googleusercontent.apps.${GOOGLE_IOS_CLIENT_ID%.apps.googleusercontent.com}"
  add GIDClientID string "$GOOGLE_IOS_CLIENT_ID"
  /usr/libexec/PlistBuddy -c "Delete :CFBundleURLTypes" "$PLIST" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes array" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0 dict" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string $REV" "$PLIST"
fi
