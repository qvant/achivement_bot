chcp 65001
C:\Python\Python38-64\python.exe C:\Python\Python38-64\Tools\i18n\pygettext.py -d .. -o ..\locale\base.pot ..\lib\telegram.py
xcopy ..\locale\base.pot ..\locale\en\LC_MESSAGES\base.po /y
xcopy ..\locale\base.pot ..\locale\ru\LC_MESSAGES\base.po /y
