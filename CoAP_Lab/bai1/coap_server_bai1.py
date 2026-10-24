#!/usr/bin/env python3
"""CoAP Server - Bai 1.

Tai nguyen:
    coap://<host>:<port>/iot/lab/message

Phuong thuc:
    GET  : tra ve thong diep chao moi (hoac thong diep POST gan nhat).
    POST : nhan thong diep tu Client, luu lai va tra ve xac nhan.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime

import aiocoap
import aiocoap.resource as resource
from aiocoap.numbers import ContentFormat

DEFAULT_MESSAGE = "Xin chao tu CoAP Server"
RESOURCE_PATH = ("iot", "lab", "message")


def now_str() -> str:
    """Tra ve thoi diem hien tai theo dinh dang HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def configure_console() -> None:
    """Dam bao console Windows hien thi UTF-8 on dinh."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class MessageResource(resource.Resource):
    """Tai nguyen /iot/lab/message."""

    def __init__(self) -> None:
        super().__init__()
        self.last_message = DEFAULT_MESSAGE
        self.last_time: str | None = None
        self.post_count = 0

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        print("\nGET request received: /iot/lab/message")
        print(f"Time: {now_str()}")
        print(f"Tra ve thong diep: {self.last_message}")
        if self.last_time is not None:
            print(f"Thong diep POST gan nhat luc: {self.last_time}")

        response = aiocoap.Message(payload=self.last_message.encode("utf-8"))
        response.opt.content_format = ContentFormat.TEXT
        return response

    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        payload = request.payload.decode("utf-8", errors="replace").strip()

        print("\nPOST request received:")
        print(f"Payload: {payload or '(rong)'}")
        print(f"Time: {now_str()}")

        if not payload:
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST,
                payload=b"Payload rong, vui long gui thong diep",
            )

        # Luu thong diep moi nhat de GET tiep theo tra ve (phan mo rong).
        self.last_message = payload
        self.last_time = now_str()
        self.post_count += 1
        print(f"Da luu thong diep thu {self.post_count}.")

        return aiocoap.Message(
            code=aiocoap.CHANGED,
            payload=b"Server da nhan thong diep",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CoAP Server cho Bai 1")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Dia chi IP de lang nghe (mac dinh: 127.0.0.1). "
        "Khi chay trong LAN, truyen IP LAN cua may, vi du 192.168.1.10.",
    )
    parser.add_argument("--port", type=int, default=5683, help="Cong UDP (mac dinh: 5683)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    root = resource.Site()
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )
    root.add_resource(RESOURCE_PATH, MessageResource())

    context = await aiocoap.Context.create_server_context(
        root, bind=(args.host, args.port)
    )

    uri = f"coap://{args.host}:{args.port}/iot/lab/message"
    print("=" * 58)
    print("CoAP Server started on port", args.port)
    print("Resource:", uri)
    print("Phuong thuc ho tro: GET, POST")
    print("Nhan Ctrl+C de dung Server.")
    print("=" * 58)

    try:
        await asyncio.Event().wait()  # Chay mai cho den khi bi dung.
    finally:
        await context.shutdown()
        print("\nCoAP Server da dung.")


if __name__ == "__main__":
    configure_console()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
