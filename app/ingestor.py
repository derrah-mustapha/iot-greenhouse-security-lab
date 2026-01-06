"""Gateway: subscribes to all telemetry, stores it in SQLite and flags anomalies.
Detectors: physical range, sequence regression (replay/forgery), rolling robust z-score (median/MAD)."""
import json, os, sqlite3, statistics, time
from collections import defaultdict, deque
from common import make_client, connect

db = sqlite3.connect("/data/readings.db", check_same_thread=False, isolation_level=None)
db.execute("pragma journal_mode=wal")
db.execute("""create table if not exists readings(id integer primary key, ts real, node text, seq int,
              temp real, hum real, soil real, fw int, src text, anomaly int, reason text)""")
RANGES = {"temp": (-10, 50), "hum": (0, 100), "soil": (0, 100)}
WIN, MIN_N, Z = 30, 10, 6.0
hist = defaultdict(lambda: defaultdict(lambda: deque(maxlen=WIN)))
last_seq = {}


def judge(d):
    reasons = []
    node = d["node"]
    for k, (lo, hi) in RANGES.items():
        if not lo <= d[k] <= hi:
            reasons.append(f"range:{k}")
    if node in last_seq:
        if d["seq"] <= last_seq[node]:
            reasons.append("seq")               # replay / regression
        elif d["seq"] > last_seq[node] + 100:
            reasons.append("seq-jump")          # flagged readings never update state, so this cannot poison it
    for k in RANGES:
        h = hist[node][k]
        if len(h) >= MIN_N:
            med = statistics.median(h)
            mad = statistics.median(abs(x - med) for x in h)
            z = 0.6745 * (d[k] - med) / max(mad, 0.05)
            if abs(z) > Z:
                reasons.append(f"zscore:{k}")
    return reasons


def on_message(c, ud, msg):
    try:
        d = json.loads(msg.payload)
        node = msg.topic.split("/")[1]
        d["node"] = node
        reasons = judge(d)
        if not reasons:
            for k in RANGES:
                hist[node][k].append(d[k])
            last_seq[node] = d["seq"]
        db.execute("insert into readings(ts,node,seq,temp,hum,soil,fw,src,anomaly,reason) values(?,?,?,?,?,?,?,?,?,?)",
                   (time.time(), node, d["seq"], d["temp"], d["hum"], d["soil"], d.get("fw"), d.get("src", "?"),
                    1 if reasons else 0, ",".join(reasons)))
    except Exception as e:
        print("bad message:", e, flush=True)


c = make_client("ingestor", cert="ingestor")
c.on_message = on_message
ok, why = connect(c)
if not ok:
    raise SystemExit(f"cannot connect: {why}")
c.subscribe("greenhouse/+/telemetry", qos=1)
print("ingestor ready", flush=True)
while True:
    time.sleep(3600)
