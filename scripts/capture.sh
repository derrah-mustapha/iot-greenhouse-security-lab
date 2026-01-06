#!/bin/bash
# capture.sh start <label> | stop <label>  -- tcpdump sidecar inside the broker's network namespace
cd "$(dirname "$0")/.."
BR=$(docker compose ps -q broker)
case "$1" in
  start)
    docker rm -f iot-sniff >/dev/null 2>&1 || true
    docker run -d --name iot-sniff --net container:"$BR" --cap-add NET_RAW --cap-add NET_ADMIN \
      -v "$PWD/captures:/cap" nicolaka/netshoot tcpdump -i eth0 -U -w "/cap/$2.pcap" 'tcp port 1883 or tcp port 8883' >/dev/null
    sleep 2;;
  stop)
    sleep 2; docker stop iot-sniff >/dev/null; docker rm iot-sniff >/dev/null
    docker run --rm -v "$PWD/captures:/cap" nicolaka/netshoot chown "$(id -u):$(id -g)" "/cap/$2.pcap";;
esac
