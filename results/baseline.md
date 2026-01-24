# Results: baseline profile

_generated 2026-11-12 18:09 UTC by scripts/run_experiments.sh_

### E1. What can an eavesdropper on the network see? (captures/baseline.pcap)
```
- readable MQTT PUBLISH packets          : 1289
- readable sensor readings (telemetry)   : 681
- readable firmware-update messages      : 8
- readable MQTT CONNECT packets          : 9
- TLS handshakes seen / encrypted records: 0 / 0
- example: greenhouse/node3/telemetry  {"node": "node3", "seq": 146, "ts": 1794506973.54, "temp": 26.16, "hum": 59.8, "soil": 37.5, "fw": 1, "src": "node3"}
```

### E2. Can an outsider connect to the broker and read everything?
```
RESULT connected (none); received 48 messages on 3 topics
example: greenhouse/node3/telemetry {"node": "node3", "seq": 165, "ts": 1794506983.05, "temp": 25.13, "hum": 57.77, "soil": 36.93, "fw": 1, "src": "node3"}
```

### E3. Can an attacker inject fake sensor readings?
```
--- crude forgery (temp 95, seq 0), no credentials:
RESULT connected (none); sent 5 forged 'crude' readings to greenhouse/node1/telemetry
--- stealth forgery (copies the latest seq, plausible temp), no credentials:
RESULT connected (none); sent 5 forged 'stealth' readings to greenhouse/node1/telemetry
--- subtle forgery (copies the latest seq, only +0.8 degrees), no credentials:
RESULT connected (none); sent 5 forged 'stealth' readings to greenhouse/node1/telemetry
```
forged readings that reached the database, and how many the detector flagged:
```
node=node1	15	5
legitimate node1/node2 readings wrongly flagged afterwards (side effect of an undetected forgery): 10
```

### E4. Anomaly detection quality (node3 has a real sensor fault every 40th reading)
```
fault spikes in data: 4, detected: 4
false alarms on normal readings: 10 of 588 normal readings
```

### E5. Firmware update integrity
```
--- legitimate signed update v2 -> node1 (admin):
RESULT published version=2 signed=True to node1 (broker accepted the connection)
node1 now reports fw=2
--- attacker, no credentials, malicious unsigned v99 -> node2:
RESULT published version=99 signed=False to node2 (broker accepted the connection)
node2 now reports fw=99
--- admin credentials but UNSIGNED v100 -> node3 (compromised build server / insider):
RESULT published version=100 signed=False to node3 (broker accepted the connection)
node3 now reports fw=100
node3 log: FW APPLIED version=100 size=15 verified=False
--- replay of an old signed image (v1) -> node1 (rollback):
RESULT published version=1 signed=True to node1 (broker accepted the connection)
node1 now reports fw=1
node1 log: FW APPLIED version=1 size=15 verified=False
```

### E6. Cost of the protection (300 QoS1 round trips through the broker)
```
RESULT n=300 avg_ms=0.22 p95_ms=0.12 msgs_per_s=275
```

