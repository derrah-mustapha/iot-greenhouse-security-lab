#!/bin/bash
# analyze_pcap.sh <label>  -- what can an eavesdropper on the broker's network see?
cd "$(dirname "$0")/.."
T() { docker run --rm -v "$PWD/captures:/cap" nicolaka/netshoot tshark -r "/cap/$1.pcap" "${@:2}" 2>/dev/null; }
L=$1
pub=$(T $L -Y 'mqtt.msgtype == 3' | wc -l || true)
tele=$(T $L -Y 'mqtt.msgtype == 3 && mqtt.topic contains "telemetry"' | wc -l || true)
fw=$(T $L -Y 'mqtt.msgtype == 3 && mqtt.topic contains "firmware"' | wc -l || true)
conn=$(T $L -Y 'mqtt.msgtype == 1' | wc -l || true)
tls=$(T $L -Y 'tls.record.content_type == 23' | wc -l || true)
hello=$(T $L -Y 'tls.handshake.type == 1' | wc -l || true)
echo "- readable MQTT PUBLISH packets          : $pub"
echo "- readable sensor readings (telemetry)   : $tele"
echo "- readable firmware-update messages      : $fw"
echo "- readable MQTT CONNECT packets          : $conn"
echo "- TLS handshakes seen / encrypted records: $hello / $tls"
ex=$(T $L -Y 'mqtt.msgtype == 3 && mqtt.topic contains "telemetry"' -T fields -e mqtt.topic -e mqtt.msg | head -1)
if [ -n "$ex" ]; then
  topic=${ex%%$'\t'*}; hex=${ex#*$'\t'}
  echo "- example: $topic  $(printf '%s' "$hex" | tr -d ':' | xxd -r -p)"
fi
