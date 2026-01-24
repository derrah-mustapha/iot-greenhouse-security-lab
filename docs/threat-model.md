# Threat model (STRIDE) of the greenhouse IoT lab

Assets: sensor integrity (decisions such as watering/ventilation depend on it), device firmware, confidentiality of readings, availability of the gateway.
Attackers: (A1) passive observer on the network, (A2) active outsider on the network with no credentials, (A3) holder of one stolen device key, (A4) insider/compromised build server with admin access.

| Component / flow | STRIDE | Threat | Lab evidence | Mitigation (hardened) | Residual risk |
|---|---|---|---|---|---|
| Device -> broker (telemetry) | **I** | A1 reads all readings | E1: 681 readable readings | TLS | Traffic analysis (sizes, timing) |
| Broker access | **S**, **E** | A2 connects anonymously and subscribes to `#` | E2 | mutual TLS, `allow_anonymous false` | CA key theft |
| Telemetry topic | **T**, **S** | A2 forges readings as a node | E3: 15/15 stored | mutual TLS + ACL (own topic only) | A3 forging that node's own topic; subtle values undetected |
| Stolen device key | **S**, **I** | A3 publishes as node2 or reads other topics | E2/E3 stolen-cert rows | ACL stops cross-device read/write | Needs revocation; secure element |
| Firmware channel | **T**, **E** | Malicious image installed; rollback to a vulnerable version | E5 baseline: v99, v100, v1 all applied | only `admin` may publish; Ed25519 signature; version must increase | Signing-key theft; no secure boot or encrypted images |
| Gateway detector | **T**, **D** | Forged sequence numbers poison state and cause false alarms | E3 side effect (10 false alarms) | flagged readings never update state; large seq jumps flagged | A subtle forgery that passes still shifts the sequence |
| Broker / gateway availability | **D** | Connection or message flood | not tested | none | open item (rate limits, `max_connections`) |
| Repudiation | **R** | A device denies sending a reading | out of scope | per-device certificate identity gives attribution at the broker | no signed readings or audit log |

Out of scope: radio layer, physical attacks on a device, supply chain of the ESP32 SDK, denial of service, cloud dashboard.
