Optional branding files, detected automatically at startup -- nothing to
configure in the app itself, these are developer-side assets:

  icon.ico  -> the .exe's own file icon (via build_exe.bat --icon) AND
               the window/taskbar icon while running. Any .ico in this
               folder works, doesn't have to be named exactly "icon.ico".
  icon.png  -> fallback for the window icon alone, if you don't have a
               .ico (won't set the .exe file icon itself -- Windows
               requires .ico for that one).
  logo.png  -> shown next to the "PALVERSATION" title in the header. A
               wider banner-style image works better here than a square
               icon. Just drop it in; nothing else to do.

All three are optional. Without them, the app just uses Tk's default
icon and no header logo.
