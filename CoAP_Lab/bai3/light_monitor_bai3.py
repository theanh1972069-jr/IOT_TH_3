#!/usr/bin/env python3
"""Light Monitoring Client - Bai 3.

Dang ky CoAP Observe de nhan thong bao trang thai tu dong.
KHONG dung vong lap GET dinh ky.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import aiocoap
from aiocoap import error

SCRIPT_DIR = Path(__file__).resolve().parent


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def resolve_host(host: str) -> str:
    if host.lower() == "localhost":
        return "127.0.0.1"
    return host


def build_uri(host: str, port: int, device_id: str) -> str:
    return f"coap://{resolve_host(host)}:{port}/iot/lab/{device_id}/status"


def parse_state(payload: bytes, fallback_device: str) -> tuple[str, str]:
    try:
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON khong phai object")
        return (
            str(data.get("device_id", fallback_device)),
            str(data.get("status", "?")).upper(),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return fallback_device, payload.decode("utf-8", errors="replace")


def print_state(message: aiocoap.Message, title: str, fallback_device: str) -> tuple[str, str]:
    device_id, status = parse_state(message.payload, fallback_device)
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {title}")
    print(f"Device: {device_id}")
    print(f"Status: {status}")
    return device_id, status


def append_log(path: Path | None, title: str, device_id: str, status: str) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"{datetime.now().isoformat(timespec='seconds')},"
                f"{title},{device_id},{status}\n"
            )
    except OSError as exc:
        print(f"WARNING: Khong ghi duoc log: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Light Monitoring Client cho Bai 3")
    parser.add_argument("--host", default="localhost", help="Host cua Server")
    parser.add_argument("--port", type=int, default=5683, help="Cong CoAP")
    parser.add_argument("--device", default="light01", help="Ma thiet bi can theo doi")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout dang ky Observe")
    parser.add_argument(
        "--log-file",
        default=str(SCRIPT_DIR / "logs" / "light_observe.log"),
        help="File log cac thong bao nhan duoc",
    )
    parser.add_argument("--no-log", action="store_true", help="Khong ghi log")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    uri = build_uri(args.host, args.port, args.device)
    log_path = Path(args.log_file)
    if not log_path.is_absolute():
        log_path = SCRIPT_DIR / log_path

    print("=" * 58)
    print("Light Monitoring Client - Bai 3 (CoAP Observe)")
    print("Observe URI:", f"coap://{args.host}:{args.port}/iot/lab/{args.device}/status")
    print("Nhan Ctrl+C de dung theo doi.")
    print("=" * 58)
    print("\nRegistering CoAP Observe...")

    context = await aiocoap.Context.create_client_context()
    protocol = None
    exit_code = 0

    try:
        request = aiocoap.Message(code=aiocoap.GET, uri=uri)
        request.opt.observe = 0
        protocol = context.request(request)

        try:
            first = await asyncio.wait_for(protocol.response, args.timeout)
        except asyncio.TimeoutError:
            print(f"ERROR: Khong nhan duoc phan hoi Observe sau {args.timeout:g} giay.")
            return 1

        if first.opt.observe is None:
            print("ERROR: Server khong ho tro Observe cho tai nguyen nay.")
            print("Co the Server chua chay dung chuong trinh light_server_bai3.py.")
            return 1

        print("Observe registration successful")

        device_id, status = print_state(first, "Initial State", args.device)
        append_log(None if args.no_log else log_path, "Initial State", device_id, status)

        async for notification in protocol.observation:
            device_id, status = print_state(
                notification, "State Updated", args.device
            )
            append_log(
                None if args.no_log else log_path,
                "State Updated",
                device_id,
                status,
            )
    except error.ObservationCancelled:
        print("\nServer da ket thuc Observe.")
    except error.Error as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}")
        exit_code = 1
    except OSError as exc:
        print(f"\nERROR: Loi mang: {exc}")
        exit_code = 1
    finally:
        if protocol is not None and protocol.observation is not None:
            try:
                if not protocol.observation.cancelled:
                    protocol.observation.cancel()
            except Exception:
                pass
        await context.shutdown()

    return exit_code


if __name__ == "__main__":
    configure_console()
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nDa dung theo doi.")
        sys.exit(0)
