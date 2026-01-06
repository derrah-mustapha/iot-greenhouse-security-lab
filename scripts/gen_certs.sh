#!/bin/bash
# Private CA, broker certificate, one certificate per device/service, and an Ed25519 firmware-signing key pair.
# Lab-only keys; never reuse them anywhere else.
set -euo pipefail
cd "$(dirname "$0")/../config/certs"
[ -f ca.crt ] && { echo "certs already exist (delete config/certs/* to regenerate)"; exit 0; }
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 825 -subj "/CN=iot-lab-ca" 2>/dev/null
mk() { # name [san]
  openssl req -newkey rsa:2048 -nodes -keyout "$1.key" -out "$1.csr" -subj "/CN=$1" 2>/dev/null
  printf "subjectAltName=%s\n" "${2:-DNS:$1}" > "$1.ext"
  openssl x509 -req -in "$1.csr" -CA ca.crt -CAkey ca.key -CAcreateserial -out "$1.crt" -days 825 -extfile "$1.ext" 2>/dev/null
  rm -f "$1.csr" "$1.ext"
}
mk broker "DNS:broker,IP:10.30.1.10"
for n in node1 node2 node3 ingestor admin; do mk "$n"; done
openssl genpkey -algorithm ed25519 -out fw_priv.pem
openssl pkey -in fw_priv.pem -pubout -out fw_pub.pem
chmod 644 *.key *.pem *.crt          # containers run as different users; lab only
echo "generated: $(ls | tr '\n' ' ')"
