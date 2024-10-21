#!/bin/sh -e
cd /home/yub168/m3u-tester
git fetch origin
git reset --hard origin/master
chmod -R 755 /home/yub168/m3u-tester
python3 creatIPTVpool.py
git add .
git commit -m 'update ipPool'
git push origin master