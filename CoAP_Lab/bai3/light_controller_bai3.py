#!/usr/bin/env python3
"""Light Controller Client - Bai 3.

Dieu khien den thong minh bang CoAP PUT va doc trang thai bang GET.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import aiocoap
from aiocoap import error
from aiocoap.numbers import ContentFormat


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def resolve_host(host: str) -> str:
    if host.lower() == "localhost":
        return "127.0.0.1"
    return host


def build_uri(host: str, port: int, device_id: str) -> str:
    return f"coap://{resolve_host(host)}:{port}/iot/lab/{device_id}/status"


async def send(
    context: aiocoap.Context,
    request: aiocoap.Message,
    timeout: float,
) -> aiocoap.Message | None:
    try:
        return await asyncio.wait_for(context.request(request).response, timeout)
    except asyncio.TimeoutError:
        print(f"ERROR: Server khong phan hoi sau {timeout:g} giay.")
    except error.NetworkError as exc:
        print(f"ERROR: Loi mang: {exc}")
    except (error.Error, OSError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
    return None


async def put_command(
    context: aiocoap.Context,
    uri: str,
    device_id: str,
    command: str,
    timeout: float,
) -> bool:
    payload = json.dumps(
        {"device_id": device_id, "command": command},
        separators=(",", ":"),
    ).encode("utf-8")

    print("\nSending PUT request...")
    request = aiocoap.Message(code=aiocoap.PUT, uri=uri, payload=payload)
    request.opt.content_format = ContentFormat.JSON

    response = await send(context, request, timeout)
    if response is None:
        return False

    print(f"Response Code: {response.code}")
    message = response.payload.decode("utf-8", errors="replace")
    if message:
        print(message)
    return response.code.is_successful()


async def get_status(
    context: aiocoap.Context,
    uri: str,
    timeout: float,
) -> bool:
    print("\nSending GET request...")
    request = aiocoap.Message(code=aiocoap.GET, uri=uri)

    response = await send(context, request, timeout)
    if response is None:
        return False

    print("Response:")
    print(response.payload.decode("utf-8", errors="replace"))
    return response.code.is_successful()


async def handle_command(
    context: aiocoap.Context,
    uri: str,
    device_id: str,
    command: str,
    timeout: float,
) -> str:
    """Xu ly mot lenh, tra ve 'ok', 'error' hoac 'exit'."""
    if command == "EXIT":
        print("Ket thuc chuong trinh.")
        return "exit"

    if command in ("ON", "OFF"):
        ok = await put_command(context, uri, device_id, command, timeout)
        return "ok" if ok else "error"

    if command == "STATUS":
        ok = await get_status(context, uri, timeout)
        return "ok" if ok else "error"

    print("Lenh khong hop le. Chi nhap ON, OFF, STATUS hoac EXIT.")
    return "invalid"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Light Controller Client cho Bai 3")
    parser.add_argument("--host", default="localhost", help="Host cua Server")
    parser.add_argument("--port", type=int, default=5683, help="Cong CoAP")
    parser.add_argument("--device", default="light01", help="Ma thiet bi can dieu khien")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout moi request")
    parser.add_argument(
        "--commands",
        default=None,
        help="Chay khong tuong tac, vi du: --commands ON,STATUS,OFF,EXIT",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    uri = build_uri(args.host, args.port, args.device)

    print("=" * 58)
    print("Light Controller Client - Bai 3")
    print("Device:", args.device)
    print("URI:", f"coap://{args.host}:{args.port}/iot/lab/{args.device}/status")
    print("Lenh: ON / OFF / STATUS / EXIT")
    print("=" * 58)

    context = await aiocoap.Context.create_client_context()
    had_error = False

    try:
        if args.commands is not None:
            commands = [item.strip().upper() for item in args.commands.split(",") if item.strip()]
            for command in commands:
                result = await handle_command(
                    context, uri, args.device, command, args.timeout
                )
                had_error = had_error or result in ("error", "invalid")
                if result == "exit":
                    break
        else:
            while True:
                try:
                    raw = input("\nNhap lenh (ON/OFF/STATUS/EXIT): ")
                except EOFError:
                    print("\nKet thuc chuong trinh.")
                    break

                command = raw.strip().upper()
                if not command:
                    continue

                result = await handle_command(
                    context, uri, args.device, command, args.timeout
                )
                had_error = had_error or result == "error"
                if result == "exit":
                    break
    finally:
        await context.shutdown()

    return 1 if had_error else 0


if __name__ == "__main__":
    configure_console()
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nDa huy boi nguoi dung.")
        sys.exit(130)
