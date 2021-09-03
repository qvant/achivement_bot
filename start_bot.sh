#!/bin/bash
export APP_HOME="/usr/app/achievement_bot"
cd $APP_HOME
python3 $APP_HOME/main.py --mode=bot & disown
