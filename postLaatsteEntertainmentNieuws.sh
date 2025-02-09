#!/bin/bash

# Initialiseer de variabele met een willekeurige tijdsduur tussen 0 en 1800 seconden
INTERVAL=$((RANDOM % 300))

# Gebruik de variabele met het sleep-commando
sleep "$INTERVAL"

echo "Slept for $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/maakBlogPost.py Entertainment >> LaatsteNieuwsBlog.log
/usr/bin/mv /home/rene/LaatsteNieuwsBlog.log /DockerApps/raspiBlog/log/EntertainmentNieuwsBlog_$(date +'%Y%m%d_%H%M%S').log
