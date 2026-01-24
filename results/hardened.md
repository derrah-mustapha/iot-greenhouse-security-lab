# Results: hardened profile

_generated 2026-11-12 18:11 UTC by scripts/run_experiments.sh_

### E1. What can an eavesdropper on the network see? (captures/hardened.pcap)
```
- readable MQTT PUBLISH packets          : 0
- readable sensor readings (telemetry)   : 0
- readable firmware-update messages      : 0
- readable MQTT CONNECT packets          : 0
- TLS handshakes seen / encrypted records: 12 / 1080
```

### E2. Can an outsider connect to the broker and read everything?
```
RESULT connect_failed (none): disconnected during handshake: Unspecified error
--- a device with a stolen certificate (node2) subscribing to '#':
RESULT connected (stolen); received 0 messages on 0 topics
--- same outsider, plaintext port 1883:
RESULT port 1883 closed/unreachable: ConnectionRefusedError
```

### E3. Can an attacker inject fake sensor readings?
```
--- crude forgery (temp 95, seq 0), no credentials:
RESULT connect_failed (none): disconnected during handshake: Unspecified error
--- stealth forgery (copies the latest seq, plausible temp), no credentials:
RESULT connect_failed (none): disconnected during handshake: Unspecified error
--- subtle forgery (copies the latest seq, only +0.8 degrees), no credentials:
RESULT connect_failed (none): disconnected during handshake: Unspecified error
--- attacker holding node2's STOLEN certificate, forging node1's topic:
RESULT connected (stolen); sent 5 forged 'crude' readings to greenhouse/node1/telemetry
--- attacker holding node2's STOLEN certificate, forging node2's own topic (stealth):
RESULT connected (stolen) but could not read node2 traffic; falling back to blind forgery
RESULT connected (stolen); sent 5 forged 'stealth' readings to greenhouse/node2/telemetry
```
forged readings that reached the database, and how many the detector flagged:
```
node=node2	5	5
legitimate node1/node2 readings wrongly flagged afterwards (side effect of an undetected forgery): 0
```

### E4. Anomaly detection quality (node3 has a real sensor fault every 40th reading)
```
fault spikes in data: 4, detected: 4
false alarms on normal readings: 1 of 586 normal readings
```

### E5. Firmware update integrity
```
--- legitimate signed update v2 -> node1 (admin):
RESULT published version=2 signed=True to node1 (broker accepted the connection)
node1 now reports fw=2
--- attacker, no credentials, malicious unsigned v99 -> node2:
RESULT connect_failed: disconnected during handshake: Unspecified error
node2 now reports fw=1
--- admin credentials but UNSIGNED v100 -> node3 (compromised build server / insider):
RESULT published version=100 signed=False to node3 (broker accepted the connection)
node3 now reports fw=1
node3 log: FW REJECTED version=100: invalid or missing signature
--- replay of an old signed image (v1) -> node1 (rollback):
RESULT published version=1 signed=True to node1 (broker accepted the connection)
node1 now reports fw=2
node1 log: FW REJECTED version=1: downgrade/replay (current 2)
```

### E6. Cost of the protection (300 QoS1 round trips through the broker)
```
RESULT n=300 avg_ms=0.25 p95_ms=0.15 msgs_per_s=271
```

