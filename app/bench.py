"""Round-trip latency through the broker: publish N QoS1 messages to bench/x and time delivery to ourselves."""
import statistics, sys, time
from common import make_client, connect

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
c = make_client("bench", cert="admin")
got = {}
c.on_message = lambda cl, ud, m: got.__setitem__(int(m.payload), time.perf_counter())
ok, why = connect(c, tries=1, wait=5)
if not ok:
    print("RESULT connect_failed", why); sys.exit(0)
c.subscribe("bench/x", qos=1); time.sleep(0.5)
sent = {}
t0 = time.perf_counter()
for i in range(N):
    sent[i] = time.perf_counter()
    c.publish("bench/x", str(i), qos=1).wait_for_publish(5)
time.sleep(1)
rtt = [(got[i] - sent[i]) * 1000 for i in sent if i in got]
dur = time.perf_counter() - t0
print(f"RESULT n={len(rtt)} avg_ms={statistics.mean(rtt):.2f} p95_ms={sorted(rtt)[int(len(rtt)*.95)]:.2f} msgs_per_s={len(rtt)/dur:.0f}")
