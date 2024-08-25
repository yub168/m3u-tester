#!/bin/sh -e
cd /home/yub168/m3u-tester
git fetch origin
git reset --hard origin/master
python3 m3u-tester.py
git add .
git commit -m 'update'
git push origin master
