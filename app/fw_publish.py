"""Admin tool: publish a firmware image to a node. --sign signs with /certs/fw_priv.pem (Ed25519)."""
import argparse, base64, json
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from common import make_client, connect

ap = argparse.ArgumentParser()
ap.add_argument("--node", required=True)
ap.add_argument("--version", type=int, required=True)
ap.add_argument("--image", default="firmware-body")
ap.add_argument("--sign", action="store_true")
ap.add_argument("--as", dest="ident", default="admin", help="certificate name to present (admin|stolen|none)")
a = ap.parse_args()
img = a.image.encode()
msg = {"version": a.version, "image": base64.b64encode(img).decode(), "sig": ""}
if a.sign:
    key = load_pem_private_key(open("/certs/fw_priv.pem", "rb").read(), None)
    msg["sig"] = base64.b64encode(key.sign(str(a.version).encode() + b"\n" + img)).decode()
c = make_client("fwtool", cert=None if a.ident == "none" else a.ident)
ok, why = connect(c, tries=1, wait=5)
if not ok:
    print(f"RESULT connect_failed: {why}"); raise SystemExit(0)
info = c.publish(f"firmware/{a.node}", json.dumps(msg), qos=1)
info.wait_for_publish(5)
print(f"RESULT published version={a.version} signed={a.sign} to {a.node} (broker accepted the connection)")
c.disconnect()
