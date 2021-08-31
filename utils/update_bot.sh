#!/bin/bash
cd /home/achievement_user/distr
rm -rf /home/achievement_user/distr/achivement_bot
git clone https://github.com/qvant/achivement_bot.git
rm -rf /home/achievement_user/distr/achivement_bot/.gitignore
rm -rf /home/achievement_user/distr/achivement_bot/.git
rm -rf /home/achievement_user/distr/achivement_bot/.github
chmod u+x achivement_bot/start_bot.sh
chmod u+x achivement_bot/start_worker.sh
chmod u+x achivement_bot/start_all.sh
cd achivement_bot/locale/en/LC_MESSAGES
msgfmt -o base.mo base.po
cd ../../ru/LC_MESSAGES
msgfmt -o base.mo  base
cd /home/achievement_user/distr
cp -a achivement_bot/. /usr/app/achievement_bot/
