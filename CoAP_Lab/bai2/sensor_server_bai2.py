#!/usr/bin/env python3
"""Sensor CoAP Server - Bai 2.

Mo phong 3 cam bien nhiet do / do am:
    coap://<host>:<port>/iot/lab/sensor01/data
    coap://<host>:<port>/iot/lab/sensor02/data
    coap://<host>:<port>/iot/lab/sensor03/data

Du lieu duoc cap nhat moi 3 giay va tra ve dang JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from datetime import datetime

import aiocoap
import aiocoap.resource as resource
from aiocoap.numbers import ContentFormat


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def json_payload(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class SensorResource(resource.Resource):
    """Tai nguyen du lieu cua mot cam bien."""

    def __init__(
        self,
        device_id: str,
        temperature: float,
        humidity: float,
    ) -> None:
        super().__init__()
        self.device_id = device_id
        self.temperature = round(temperature, 1)
        self.humidity = round(humidity, 1)
        self.updated_at = datetime.now().isoformat(timespec="seconds")
        self.read_count = 0

    def update(self) -> None:
        """Sinh gia tri moi theo kieu random walk trong khoang hop ly."""
        self.temperature = round(
            min(40.0, max(20.0, self.temperature + random.uniform(-0.8, 0.8))), 1
        )
        self.humidity = round(
            min(95.0, max(30.0, self.humidity + random.uniform(-2.0, 2.0))), 1
        )
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    def as_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "timestamp": self.updated_at,
        }

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        self.read_count += 1
        data = self.as_dict()

        print(
            f"[{now_str()}] GET /iot/lab/{self.device_id}/data -> "
            f"{data['temperature']} C, {data['humidity']} %"
        )

        response = aiocoap.Message(payload=json_payload(data))
        response.opt.content_format = ContentFormat.JSON
        return response


class SensorsResource(resource.Resource):
    """Tai nguyen tong hop tat ca cam bien (phan mo rong)."""

    def __init__(self, sensors: dict[str, SensorResource]) -> None:
        super().__init__()
        self.sensors = sensors

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        data = [sensor.as_dict() for sensor in self.sensors.values()]
        print(f"[{now_str()}] GET /iot/lab/sensors -> {len(data)} thiet bi")

        response = aiocoap.Message(payload=json_payload(data))
        response.opt.content_format = ContentFormat.JSON
        return response


async def update_loop(
    sensors: dict[str, SensorResource],
    interval: float,
) -> None:
    while True:
        await asyncio.sleep(interval)
        for sensor in sensors.values():
            sensor.update()
            print(
                f"[{now_str()}] {sensor.device_id} updated: "
                f"{sensor.temperature} C, {sensor.humidity} %"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sensor CoAP Server cho Bai 2")
    parser.add_argument("--host", default="127.0.0.1", help="Dia chi IP lang nghe")
    parser.add_argument("--port", type=int, default=5683, help="Cong UDP CoAP")
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Chu ky cap nhat cam bien (giay, mac dinh: 3)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    sensors = {
        "sensor01": SensorResource("sensor01", 28.5, 65.2),
        "sensor02": SensorResource("sensor02", 31.2, 55.0),
        "sensor03": SensorResource("sensor03", 36.1, 38.7),
    }

    root = resource.Site()
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )
    for device_id, sensor in sensors.items():
        root.add_resource(["iot", "lab", device_id, "data"], sensor)
    root.add_resource(["iot", "lab", "sensors"], SensorsResource(sensors))

    context = await aiocoap.Context.create_server_context(
        root, bind=(args.host, args.port)
    )
    updater = asyncio.create_task(update_loop(sensors, args.interval))

    print("=" * 62)
    print("Sensor CoAP Server started on port", args.port)
    print("Cap nhat cam bien moi", args.interval, "giay")
    for device_id in sensors:
        print(f"  - coap://{args.host}:{args.port}/iot/lab/{device_id}/data")
    print(f"  - coap://{args.host}:{args.port}/iot/lab/sensors (tong hop)")
    print("Nhan Ctrl+C de dung Server.")
    print("=" * 62)

    try:
        await asyncio.Event().wait()
    finally:
        updater.cancel()
        try:
            await updater
        except asyncio.CancelledError:
            pass
        await context.shutdown()
        print("\nSensor CoAP Server da dung.")


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
