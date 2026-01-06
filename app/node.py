"""Simulated ESP32 greenhouse node: temperature, humidity, soil moisture + firmware updates over MQTT."""
import base64, json, math, os, random, time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from common import make_client, connect

NODE = os.environ["NODE_ID"]
FAULT = os.environ.get("FAULT", "0") == "1"
VERIFY = os.environ.get("FW_VERIFY", "0") == "1"
PERIOD = float(os.environ.get("PERIOD", "0.5"))
state = {"fw": 1}


def on_fw(c, ud, msg):
    try:
        d = json.loads(msg.payload)
        ver, image = int(d["version"]), base64.b64decode(d["image"])
    except Exception as e:
        print(f"FW REJECTED malformed: {e}", flush=True); return
    if VERIFY:
        try:
            pub = load_pem_public_key(open("/certs/fw_pub.pem", "rb").read())
            pub.verify(base64.b64decode(d.get("sig", "")), str(ver).encode() + b"\n" + image)
        except (InvalidSignature, ValueError, KeyError):
            print(f"FW REJECTED version={ver}: invalid or missing signature", flush=True); return
        if ver <= state["fw"]:
            print(f"FW REJECTED version={ver}: downgrade/replay (current {state['fw']})", flush=True); return
    state["fw"] = ver
    print(f"FW APPLIED version={ver} size={len(image)} verified={VERIFY}", flush=True)


c = make_client(NODE, cert=NODE)
c.on_message = on_fw
ok, why = connect(c)
if not ok:
    raise SystemExit(f"cannot connect: {why}")
c.subscribe(f"firmware/{NODE}", qos=1)
print(f"{NODE} online (verify_fw={VERIFY})", flush=True)
seq = 0
while True:
    seq += 1
    temp = 24 + 3 * math.sin(seq / 60) + random.gauss(0, 0.25)
    hum = 60 + 4 * math.cos(seq / 80) + random.gauss(0, 0.8)
    soil = max(5, 38 - seq * 0.004 + random.gauss(0, 0.6))
    if FAULT and seq >= 40 and seq % 40 == 0:      # sensor fault: spike every 40th reading
        temp += 25
    msg = {"node": NODE, "seq": seq, "ts": round(time.time(), 2), "temp": round(temp, 2),
           "hum": round(hum, 2), "soil": round(soil, 2), "fw": state["fw"], "src": NODE}
    c.publish(f"greenhouse/{NODE}/telemetry", json.dumps(msg), qos=1)
    time.sleep(PERIOD)
