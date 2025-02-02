#!/bin/bash

# Initialiseer de variabele met een willekeurige tijdsduur tussen 0 en 180 seconden
INTERVAL=$((RANDOM % 120))

# Gebruik de variabele met het sleep-commando
sleep "$INTERVAL"

echo "Slept first time: $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getRTLnetBinnen.py  > LaatsteNieuwsBlog.log
INTERVAL=$((RANDOM % 120))
sleep "$INTERVAL"
echo "Slept second time: $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getNOSEntertainmentNieuws.py  >> LaatsteNieuwsBlog.log
INTERVAL=$((RANDOM % 120))
sleep "$INTERVAL"
echo "Slept third time: $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getNOSNieuws.py  >> LaatsteNieuwsBlog.log
INTERVAL=$((RANDOM % 120))
sleep "$INTERVAL"
echo "Slept fourh time: $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getOmroepBrabantSportNieuws.py  >> LaatsteNieuwsBlog.log
INTERVAL=$((RANDOM % 120))
sleep "$INTERVAL"
echo "Slept fifth time: $INTERVAL seconds."
docker exec  raspiblog_python_1 python /scripts/getOmroepBrabantNieuws.py  >> LaatsteNieuwsBlog.log
/usr/bin/mv /home/rene/LaatsteNieuwsBlog.log /DockerApps/raspiBlog/log/getNieuwsBlog_$(date +'%Y%m%d_%H%M%S').log
