"""Shared MQTT helper. TLS and port come from the profile (lab.env)."""
import os, ssl, threading, time
import paho.mqtt.client as mqtt

HOST = os.environ.get("MQTT_HOST", "broker")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
TLS = os.environ.get("MQTT_TLS", "0") == "1"


def make_client(cid, cert=None):
    """cert = name of /certs/<cert>.crt|key to present (None: TLS without a client certificate)."""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    if TLS:
        kw = {"ca_certs": "/certs/ca.crt"}
        if cert:
            kw.update(certfile=f"/certs/{cert}.crt", keyfile=f"/certs/{cert}.key")
        c.tls_set(**kw)
    return c


def connect(c, tries=60, wait=5.0):
    """Connect with retries. Returns (True, '') or (False, reason). Starts the network loop."""
    state = {"ok": None, "why": ""}
    ev = threading.Event()

    def on_connect(cl, ud, flags, rc, props=None):
        state["ok"] = (not rc.is_failure)
        state["why"] = str(rc)
        ev.set()

    def on_disconnect(cl, ud, flags, rc, props=None):
        if state["ok"] is None:
            state["ok"], state["why"] = False, "disconnected during handshake: " + str(rc)
            ev.set()

    c.on_connect, c.on_disconnect = on_connect, on_disconnect
    reason = ""
    for _ in range(tries):
        state["ok"] = None
        ev.clear()
        try:
            c.connect(HOST, PORT, keepalive=30)
        except (ssl.SSLError, OSError) as e:
            reason = f"{type(e).__name__}: {e}"
            time.sleep(2)
            continue
        c.loop_start()
        ev.wait(wait)
        if state["ok"]:
            return True, ""
        reason = state["why"] or "timeout"
        c.loop_stop()
        try:
            c.disconnect()
        except Exception:
            pass
        if tries <= 2:
            break
        time.sleep(2)
    return False, reason
