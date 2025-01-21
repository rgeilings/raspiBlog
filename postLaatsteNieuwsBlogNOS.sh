#!/bin/bash

# Initialiseer de variabele met een willekeurige tijdsduur tussen 0 en 1800 seconden
INTERVAL=$((RANDOM % 1801))

# Gebruik de variabele met het sleep-commando
sleep "$INTERVAL"

echo "Slept for $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getNOSNieuws.py  > LaatsteNieuwsBlogNOS.log
docker exec  raspiblog_python_1 python /scripts/maakBlogPost.py >> LaatsteNieuwsBlogNOS.log
docker exec  raspiblog_python_1 python /scripts/TrendingBlogPost.py Laatste >> LaatsteNieuwsBlogNOS.log
/usr/bin/mv /home/rene/LaatsteNieuwsBlogNOS.log /DockerApps/raspiBlog/log/LaatsteNieuwsBlogNOS_$(date +'%Y%m%d_%H%M%S').log
