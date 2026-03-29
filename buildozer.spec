[app]
title = Shekel Weight Display
package.name = scaledisplay
package.domain = org.scaledisplay
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
icon.filename = %(source.dir)s/logo.jpg

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
