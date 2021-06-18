#!/bin/bash
export APP_HOME="/usr/app/achievement_bot"
cd $APP_HOME
sleep 45
nohup python3 $APP_HOME/main.py --mode=core &
sleep 5
nohup python3 $APP_HOME/main.py --mode=updater &
sleep 5
nohup python3 $APP_HOME/main.py --mode=worker &
sleep 5
nohup python3 $APP_HOME/main.py --mode=bot &

