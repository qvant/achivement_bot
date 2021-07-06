#!/bin/bash
export APP_HOME="/usr/app/achievement_bot"
cd $APP_HOME
sleep 45
python3 $APP_HOME/main.py --mode=bot & disown
sleep 5
python3 $APP_HOME/main.py --mode=updater & disown
sleep 5
python3 $APP_HOME/main.py --mode=worker & disown
sleep 5
python3 $APP_HOME/main.py --mode=core & disown

