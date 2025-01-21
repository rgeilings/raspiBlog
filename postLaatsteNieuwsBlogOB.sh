#!/bin/bash

# Initialiseer de variabele met een willekeurige tijdsduur tussen 0 en 1800 seconden
INTERVAL=$((RANDOM % 1801))

# Gebruik de variabele met het sleep-commando
sleep "$INTERVAL"

echo "Slept for $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getOmroepBrabantNieuws.py  > LaatsteNieuwsBlog.log
docker exec  raspiblog_python_1 python /scripts/maakBlogPost.py >> LaatsteNieuwsBlog.log
docker exec  raspiblog_python_1 python /scripts/TrendingBlogPost.py Brabants >> LaatsteNieuwsBlog.log
/usr/bin/mv /home/rene/LaatsteNieuwsBlog.log /DockerApps/raspiBlog/log/LaatsteNieuwsBlogOB_$(date +'%Y%m%d_%H%M%S').log
