import argparse, json, sys, time
from devicerouter.host.service import HostService
from devicerouter.schema import normalize_schema

def build_parser():
    p = argparse.ArgumentParser(description="Host ↔ GUI VM (vsock) using JSON schema snapshot")
    p.add_argument("--schema-json", required=True, help="Path to schema JSON (devices/current-mount)")
    p.add_argument("--guest-cid", type=int, required=True, help="GUI VM guest CID (e.g., 101)")
    p.add_argument("--guest-port", type=int, default=7000, help="GUI VM vsock listen port (default 7000)")
    p.add_argument("--ack-delay", type=float, default=0.0, help="Simulated seconds before ACK")
    return p

def main():
    args = build_parser().parse_args()
    with open(args.schema_json, "r") as f:
        schema = normalize_schema(json.load(f))
    svc = HostService(schema, args.guest_cid, args.guest_port, ack_delay=args.ack_delay)
    svc.start()
    try:
        print("[HOST] Running. Ctrl+C to exit.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        svc.stop()

if __name__ == "__main__":
    main()

