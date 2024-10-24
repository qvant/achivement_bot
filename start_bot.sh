#!/bin/bash
export APP_HOME="/usr/app/achievement_bot"
cd $APP_HOME  || { echo "Failure"; exit 1; }
python3 $APP_HOME/main.py --mode=bot & disown
