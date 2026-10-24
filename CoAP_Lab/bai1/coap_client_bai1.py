#!/usr/bin/env python3
"""CoAP Client - Bai 1.

Gui GET va POST toi:
    coap://localhost:5683/iot/lab/message
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import aiocoap
from aiocoap import error

DEFAULT_NAME = "Nguyen Van A"
DEFAULT_MSSV = "B23DCCN001"


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def resolve_host(host: str) -> str:
    """Doi localhost thanh 127.0.0.1 de tranh loi IPv6 tren mot so may Windows.

    Server trong bai thuc hanh lang nghe tren IPv4, trong khi localhost co the
    duoc phan giai thanh ::1 (IPv6) nen ket noi se that bai.
    """
    if host.lower() == "localhost":
        return "127.0.0.1"
    return host


def build_uri(host: str, port: int) -> str:
    return f"coap://{resolve_host(host)}:{port}/iot/lab/message"


async def send_request(
    context: aiocoap.Context,
    message: aiocoap.Message,
    timeout: float,
) -> aiocoap.Message | None:
    """Gui request va cho response, tra ve None neu timeout/loi mang."""
    try:
        return await asyncio.wait_for(context.request(message).response, timeout)
    except asyncio.TimeoutError:
        print(f"ERROR: Het thoi gian cho phan hoi sau {timeout:g} giay.")
        print("Kiem tra Server da chay chua va dia chi IP/cong co dung khong.")
    except error.NetworkError as exc:
        print(f"ERROR: Loi mang: {exc}")
        print("Khong the ket noi toi Server. Hay khoi dong Server truoc.")
    except (error.Error, OSError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
    return None


def decode_payload(message: aiocoap.Message) -> str:
    return message.payload.decode("utf-8", errors="replace")


async def main() -> int:
    parser = argparse.ArgumentParser(description="CoAP Client cho Bai 1")
    parser.add_argument("--host", default="localhost", help="Host cua Server")
    parser.add_argument("--port", type=int, default=5683, help="Cong CoAP")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Ho ten sinh vien")
    parser.add_argument("--mssv", default=DEFAULT_MSSV, help="Ma sinh vien")
    parser.add_argument(
        "--message",
        default=None,
        help="Noi dung POST tuy chinh (mac dinh: Xin chao tu CoAP Client - <MSSV> - <Ho ten>)",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout moi request (giay)")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="So lan gui POST lien tiep (ho tro kiem tra Server luu thong diep moi nhat)",
    )
    args = parser.parse_args()

    uri = build_uri(args.host, args.port)
    display_uri = f"coap://{args.host}:{args.port}/iot/lab/message"
    post_payload = args.message or (
        f"Xin chao tu CoAP Client - {args.mssv} - {args.name}"
    )

    print("=" * 58)
    print("CoAP Client - Bai 1")
    print("Server URI:", display_uri)
    print("=" * 58)

    context = await aiocoap.Context.create_client_context()
    had_error = False

    try:
        # ---------------- GET ----------------
        print("\nSending GET request...")
        print(f"URI: {display_uri}\n")

        request = aiocoap.Message(code=aiocoap.GET, uri=uri)
        response = await send_request(context, request, args.timeout)
        if response is None:
            had_error = True
        else:
            print("Response:")
            print(f"Code: {response.code}")
            print(f"Payload: {decode_payload(response)}")

        # ---------------- POST ----------------
        for attempt in range(1, max(1, args.repeat) + 1):
            print(f"\nSending POST request... ({attempt}/{max(1, args.repeat)})")
            print(f"Payload: {post_payload}\n")

            request = aiocoap.Message(
                code=aiocoap.POST,
                uri=uri,
                payload=post_payload.encode("utf-8"),
            )
            request.opt.content_format = aiocoap.numbers.ContentFormat.TEXT

            response = await send_request(context, request, args.timeout)
            if response is None:
                had_error = True
                continue

            print("Response:")
            print(f"Code: {response.code}")
            print(f"Payload: {decode_payload(response)}")

            if not response.code.is_successful():
                had_error = True

        # Doc lai GET de minh hoa Server da luu thong diep POST gan nhat.
        if args.repeat > 0:
            print("\nSending GET request (kiem tra thong diep da luu)...")
            request = aiocoap.Message(code=aiocoap.GET, uri=uri)
            response = await send_request(context, request, args.timeout)
            if response is not None:
                print(f"Code: {response.code}")
                print(f"Payload: {decode_payload(response)}")
    finally:
        await context.shutdown()

    print("\nHoan tat.")
    return 1 if had_error else 0


if __name__ == "__main__":
    configure_console()
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nDa huy boi nguoi dung.")
        sys.exit(130)
