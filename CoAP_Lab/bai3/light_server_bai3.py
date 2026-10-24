#!/usr/bin/env python3
"""Smart Light CoAP Server - Bai 3.

Tai nguyen:
    coap://<host>:<port>/iot/lab/<device>/status

Ho tro:
    GET     : doc trang thai hien tai.
    PUT     : dieu khien ON/OFF.
    Observe : tu dong thong bao khi trang thai thay doi.

Mac dinh mo phong 3 thiet bi: light01, fan01, pump01.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import aiocoap
import aiocoap.resource as resource
from aiocoap.numbers import ContentFormat

SCRIPT_DIR = Path(__file__).resolve().parent
VALID_COMMANDS = {"ON", "OFF"}


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def json_payload(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class LightResource(resource.ObservableResource):
    """Tai nguyen trang thai cua mot thiet bi, ho tro Observe."""

    def __init__(self, device_id: str, initial_state: str = "OFF") -> None:
        super().__init__()
        self.device_id = device_id
        self.status = initial_state
        self.last_changed = datetime.now().isoformat(timespec="seconds")
        self._observer_count = 0
        self._lock = asyncio.Lock()
        self._log_path: Path | None = None

    # ------------- Observe hooks -------------
    def update_observation_count(self, newcount: int) -> None:
        if newcount > self._observer_count:
            print(f"\nNew Observe registration received ({self.device_id})")
        elif newcount < self._observer_count:
            print(f"\nObserve client disconnected ({self.device_id})")
        self._observer_count = newcount
        print(f"Observers hien tai cua {self.device_id}: {newcount}")

    # ------------- Resources -------------
    def as_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "status": self.status,
            "timestamp": self.last_changed,
        }

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        is_observe = request.opt.observe is not None
        async with self._lock:
            payload = json_payload(self.as_dict())
            status = self.status

        if not is_observe:
            print(
                f"\n[{now_str()}] GET /iot/lab/{self.device_id}/status "
                f"-> {status}"
            )

        response = aiocoap.Message(payload=payload)
        response.opt.content_format = ContentFormat.JSON
        return response

    async def render_put(self, request: aiocoap.Message) -> aiocoap.Message:
        # 1. Parse JSON
        try:
            data = json.loads(request.payload.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Payload phai la JSON object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            print(f"\n[{now_str()}] PUT {self.device_id}: JSON khong hop le ({exc})")
            return self._bad_request("Payload JSON khong hop le")

        device_id = str(data.get("device_id", self.device_id))
        command = str(data.get("command", "")).strip().upper()

        print(f"\nPUT request received:")
        print(f"Device: {device_id}")
        print(f"Command: {command or '(rong)'}")

        # 2. Kiem tra du lieu
        if device_id != self.device_id:
            print(f"-> Tu choi: device_id khong khop ({device_id})")
            return self._bad_request(
                f"device_id khong khop, tai nguyen nay la {self.device_id}"
            )

        if command not in VALID_COMMANDS:
            print(f"-> Tu choi: lenh khong hop le ({command!r})")
            return self._bad_request("Lenh khong hop le, chi chap nhan ON hoac OFF")

        # 3. Cap nhat trang thai
        async with self._lock:
            old_status = self.status
            if old_status != command:
                self.status = command
                self.last_changed = datetime.now().isoformat(timespec="seconds")

        if old_status != command:
            print(f"Light state changed: {old_status} -> {command}")
            print(f"Notify observers: {command}")
            # Trigger CoAP Observe notifications toi tat ca observer.
            self.updated_state()
            self._write_log(old_status, command)
            message = f"Da bat den {self.device_id}" if command == "ON" else f"Da tat den {self.device_id}"
        else:
            print(f"Trang thai khong doi: {command}")
            message = f"Thiet bi {self.device_id} da o trang thai {command}"

        return aiocoap.Message(
            code=aiocoap.CHANGED,
            payload=message.encode("utf-8"),
        )

    @staticmethod
    def _bad_request(message: str) -> aiocoap.Message:
        return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=message.encode("utf-8"))

    def _write_log(self, old_status: str, new_status: str) -> None:
        if self._log_path is None:
            return
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    f"{datetime.now().isoformat(timespec='seconds')},"
                    f"{self.device_id},{old_status},{new_status}\n"
                )
        except OSError as exc:
            print(f"WARNING: Khong ghi duoc log: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Light CoAP Server cho Bai 3")
    parser.add_argument("--host", default="127.0.0.1", help="Dia chi IP lang nghe")
    parser.add_argument("--port", type=int, default=5683, help="Cong UDP CoAP")
    parser.add_argument(
        "--devices",
        default="light01,fan01,pump01",
        help="Danh sach thiet bi, cach nhau boi dau phay",
    )
    parser.add_argument(
        "--log-file",
        default=str(SCRIPT_DIR / "logs" / "light_state.log"),
        help="File luu nhat ky thay doi trang thai",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    device_ids = [item.strip() for item in args.devices.split(",") if item.strip()]
    if not device_ids:
        raise SystemExit("Danh sach thiet bi rong.")

    log_path = Path(args.log_file)
    if not log_path.is_absolute():
        log_path = SCRIPT_DIR / log_path

    root = resource.Site()
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )

    resources: dict[str, LightResource] = {}
    for device_id in device_ids:
        device = LightResource(device_id, "OFF")
        device._log_path = log_path
        resources[device_id] = device
        root.add_resource(["iot", "lab", device_id, "status"], device)

    context = await aiocoap.Context.create_server_context(
        root, bind=(args.host, args.port)
    )

    print("=" * 62)
    print("CoAP Smart Light Server started...")
    for device_id in device_ids:
        print(f"Resource: coap://{args.host}:{args.port}/iot/lab/{device_id}/status")
    print(f"Log trang thai: {log_path}")
    print("Ho tro GET, PUT, Observe. Nhan Ctrl+C de dung Server.")
    print("=" * 62)

    try:
        await asyncio.Event().wait()
    finally:
        await context.shutdown()
        print("\nCoAP Smart Light Server da dung.")


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
