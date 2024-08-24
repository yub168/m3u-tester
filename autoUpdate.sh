#!/bin/sh -e
cd /home/yub168/m3u-tester
git pull origin master
python3 m3u-tester.py
git add .
git commit -m 'update'
git push origin master
