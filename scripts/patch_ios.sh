#!/bin/sh
# Run after `flutter create --platforms=ios`. Adds the iOS settings the app needs.
set -e
PLIST=ios/Runner/Info.plist
add() { /usr/libexec/PlistBuddy -c "Add :$1 $2 $3" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :$1 $3" "$PLIST"; }
add CFBundleDisplayName string "جزدانەکەم"
add ITSAppUsesNonExemptEncryption bool false
