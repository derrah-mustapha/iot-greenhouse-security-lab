#!/bin/bash
# run_experiments.sh <baseline|hardened>  -> results/<profile>.md   (the lab must be up with the same profile)
set -uo pipefail
cd "$(dirname "$0")/.."
PROFILE=${1:?baseline|hardened}; export PROFILE
OUT=results/$PROFILE.md
A()  { docker compose exec -T attacker python /app/attack.py "$@" 2>&1 | grep -E 'RESULT|example' || echo "RESULT (no output)"; }
AD() { docker compose exec -T admin python /app/fw_publish.py "$@" 2>&1 | grep RESULT || echo "RESULT (no output)"; }
Q()  { docker compose exec -T ingestor python /app/q.py "$1"; }
FW() { docker compose exec -T ingestor python /app/q.py "select fw from readings where node='$1' order by id desc limit 1"; }
nlog() { docker compose logs --no-log-prefix "$1" 2>&1 | grep -E 'FW ' | tail -1; }

echo "waiting 60 s so every detector has a warm-up window..."; sleep 60
scripts/capture.sh start $PROFILE
{
echo "# Results: $PROFILE profile"; echo; echo "_generated $(date -u '+%F %H:%M UTC') by scripts/run_experiments.sh_"; echo
echo "### E2. Can an outsider connect to the broker and read everything?"
echo '```'
A sniff --as none --secs 8
if [ "$PROFILE" = hardened ]; then
  echo "--- a device with a stolen certificate (node2) subscribing to '#':"
  A sniff --as stolen --secs 8
  echo "--- same outsider, plaintext port 1883:"
  docker compose exec -T attacker python - <<'PY' 2>&1 | tail -1
import socket
s=socket.socket(); s.settimeout(3)
try: s.connect(("10.30.1.10",1883)); print("RESULT port 1883 OPEN")
except Exception as e: print("RESULT port 1883 closed/unreachable:", type(e).__name__)
PY
fi
echo '```'; echo
echo "### E3. Can an attacker inject fake sensor readings?"
echo '```'
Q "delete from readings where src='attacker'" >/dev/null
echo "--- crude forgery (temp 95, seq 0), no credentials:"; A crude --as none --target node1 --count 5
echo "--- stealth forgery (copies the latest seq, plausible temp), no credentials:"; A stealth --as none --target node1 --count 5
echo "--- subtle forgery (copies the latest seq, only +0.8 degrees), no credentials:"; A stealth --as none --target node1 --count 5 --delta 0.8
if [ "$PROFILE" = hardened ]; then
  echo "--- attacker holding node2's STOLEN certificate, forging node1's topic:"; A crude --as stolen --target node1 --count 5
  echo "--- attacker holding node2's STOLEN certificate, forging node2's own topic (stealth):"; A stealth --as stolen --target node2 --count 5
fi
echo '```'
sleep 3
echo "forged readings that reached the database, and how many the detector flagged:"
echo '```'
Q "select node, count(*) as stored, sum(anomaly) as flagged_by_detector from readings where src='attacker' group by node" | sed 's/^/node=/'
[ -z "$(Q "select 1 from readings where src='attacker' limit 1")" ] && echo "none stored (0 forged readings reached the gateway)"
echo "legitimate node1/node2 readings wrongly flagged afterwards (side effect of an undetected forgery): $(Q "select count(*) from readings where src in ('node1','node2') and anomaly=1 and ts > (select min(ts) from readings where src='attacker')")"
echo '```'; echo
echo "### E4. Anomaly detection quality (node3 has a real sensor fault every 40th reading)"
echo '```'
Q "select 'fault spikes in data: '||count(*)||', detected: '||coalesce(sum(anomaly),0) from readings where node='node3' and src='node3' and seq>=40 and seq%40=0"
Q "select 'false alarms on normal readings: '||count(*)||' of '||(select count(*) from readings where src!='attacker' and not (node='node3' and seq>=40 and seq%40=0))||' normal readings' from readings where src!='attacker' and anomaly=1 and not (node='node3' and seq>=40 and seq%40=0)"
echo '```'; echo
echo "### E5. Firmware update integrity"
echo '```'
echo "--- legitimate signed update v2 -> node1 (admin):";           AD --node node1 --version 2 --sign --image good-firmware-v2; sleep 3; echo "node1 now reports fw=$(FW node1)"
echo "--- attacker, no credentials, malicious unsigned v99 -> node2:"; docker compose exec -T attacker python /app/fw_publish.py --node node2 --version 99 --as none --image EVIL 2>&1 | grep RESULT; sleep 3; echo "node2 now reports fw=$(FW node2)"
echo "--- admin credentials but UNSIGNED v100 -> node3 (compromised build server / insider):"; AD --node node3 --version 100 --image EVIL-from-admin; sleep 3; echo "node3 now reports fw=$(FW node3)"; echo "node3 log: $(nlog node3)"
echo "--- replay of an old signed image (v1) -> node1 (rollback):"; AD --node node1 --version 1 --sign --image old-firmware-v1; sleep 3; echo "node1 now reports fw=$(FW node1)"; echo "node1 log: $(nlog node1)"
echo '```'; echo
echo "### E6. Cost of the protection (300 QoS1 round trips through the broker)"
echo '```'
docker compose exec -T admin python /app/bench.py 300 2>&1 | grep RESULT
echo '```'; echo
} > $OUT
scripts/capture.sh stop $PROFILE
{
echo "### E1. What can an eavesdropper on the network see? (captures/$PROFILE.pcap)"
echo '```'; scripts/analyze_pcap.sh $PROFILE; echo '```'
} > results/.e1.tmp
python3 - "$OUT" <<'PY'
import sys
p=sys.argv[1]; t=open(p).read(); e1=open("results/.e1.tmp").read()
head,rest=t.split("### E2.",1)
open(p,"w").write(head+e1+"\n### E2."+rest)
PY
rm -f results/.e1.tmp
echo "done -> $OUT"
