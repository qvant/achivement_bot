rem en
cd ..\locale\en\LC_MESSAGES\
C:\Python\Python38-64\python.exe C:\Python\Python38-64\Tools\i18n\msgfmt.py -o base.mo  base
cd ..\..\..\utils
rem ru
cd ..\locale\ru\LC_MESSAGES\
C:\Python\Python38-64\python.exe C:\Python\Python38-64\Tools\i18n.py -o base.mo  base
cd ..\..\..\utils