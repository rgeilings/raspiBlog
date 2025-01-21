#!/bin/bash

# Initialiseer de variabele met een willekeurige tijdsduur tussen 0 en 1800 seconden
INTERVAL=$((RANDOM % 1801))

# Gebruik de variabele met het sleep-commando
sleep "$INTERVAL"

echo "Slept for $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getRTLnetBinnen.py  > LaatsteNieuwsBlog.log
docker exec  raspiblog_python_1 python /scripts/maakSportBlogPost.py >> LaatsteNieuwsBlog.log
docker exec  raspiblog_python_1 python /scripts/TrendingBlogPost.py Sport >> LaatsteNieuwsBlog.log
/usr/bin/mv /home/rene/LaatsteNieuwsBlog.log /DockerApps/raspiBlog/log/SportNieuwsBlog_$(date +'%Y%m%d_%H%M%S').log
