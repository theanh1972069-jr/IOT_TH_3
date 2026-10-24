#!/usr/bin/env python3
"""Monitoring CoAP Client - Bai 2.

Dinh ky GET du lieu cam bien, phan tich JSON, canh bao va ghi log CSV.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import aiocoap
from aiocoap import error

TEMP_THRESHOLD = 35.0
HUMIDITY_THRESHOLD = 40.0
SCRIPT_DIR = Path(__file__).resolve().parent


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def resolve_host(host: str) -> str:
    """Tranh loi IPv6 khi dung localhost tren Windows."""
    if host.lower() == "localhost":
        return "127.0.0.1"
    return host


def build_uri(host: str, port: int, device_id: str) -> str:
    return f"coap://{resolve_host(host)}:{port}/iot/lab/{device_id}/data"


def print_reading(data: dict, received_at: datetime) -> list[str]:
    """In du lieu cam bien va tra ve danh sach canh bao."""
    device_id = str(data.get("device_id", "?"))
    temperature = float(data["temperature"])
    humidity = float(data["humidity"])

    warnings: list[str] = []
    if temperature > TEMP_THRESHOLD:
        warnings.append("CANH BAO: Nhiet do cao")
    if humidity < HUMIDITY_THRESHOLD:
        warnings.append("CANH BAO: Do am thap")

    print(f"[{received_at.strftime('%H:%M:%S')}] Received sensor data")
    print()
    print(f"Device: {device_id}")
    print(f"Temperature: {temperature:.1f} C")
    print(f"Humidity: {humidity:.1f} %")
    print()
    if warnings:
        for warning in warnings:
            print(warning)
    else:
        print("Trang thai: Binh thuong")
    print()
    print("-" * 30)
    return warnings


def open_csv(path: Path) -> tuple[object, csv.writer]:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    file = path.open("a", newline="", encoding="utf-8-sig")
    writer = csv.writer(file)
    if is_new:
        writer.writerow(
            [
                "received_at",
                "device_id",
                "temperature_c",
                "humidity_percent",
                "response_time_ms",
                "status",
                "alert",
            ]
        )
    return file, writer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitoring CoAP Client cho Bai 2")
    parser.add_argument("--host", default="localhost", help="Host cua Server")
    parser.add_argument("--port", type=int, default=5683, help="Cong CoAP")
    parser.add_argument(
        "--device",
        default="sensor01",
        choices=["sensor01", "sensor02", "sensor03"],
        help="Ma cam bien can giam sat",
    )
    parser.add_argument("--interval", type=float, default=3.0, help="Chu ky GET (giay)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Timeout moi GET (giay)")
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="So lan GET roi dung (0 = chay lien tuc den khi Ctrl+C)",
    )
    parser.add_argument(
        "--csv",
        default=str(SCRIPT_DIR / "logs" / "sensor_data.csv"),
        help="File CSV luu du lieu",
    )
    parser.add_argument("--no-csv", action="store_true", help="Khong ghi file CSV")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    uri = build_uri(args.host, args.port, args.device)

    print("=" * 58)
    print("Monitoring CoAP Client - Bai 2")
    print("Monitoring URI:", f"coap://{args.host}:{args.port}/iot/lab/{args.device}/data")
    print(f"Chu ky: {args.interval:g} giay | Timeout: {args.timeout:g} giay")
    print("Nhan Ctrl+C de dung.")
    print("=" * 58)

    csv_file = None
    csv_writer = None
    csv_path = Path(args.csv)
    if not args.no_csv:
        csv_file, csv_writer = open_csv(csv_path)
        print(f"Ghi log CSV: {csv_path}")

    context = await aiocoap.Context.create_client_context()
    attempts = 0
    successes = 0
    failures = 0
    total_latency_ms = 0.0

    try:
        while args.count <= 0 or attempts < args.count:
            attempts += 1
            started = time.perf_counter()

            request = aiocoap.Message(code=aiocoap.GET, uri=uri)
            try:
                response = await asyncio.wait_for(
                    context.request(request).response, args.timeout
                )
            except asyncio.TimeoutError:
                failures += 1
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ERROR: Server khong phan hoi sau {args.timeout:g} giay."
                )
                await asyncio.sleep(args.interval)
                continue
            except error.NetworkError as exc:
                failures += 1
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ERROR: Loi mang: {exc}"
                )
                await asyncio.sleep(args.interval)
                continue
            except (error.Error, OSError) as exc:
                failures += 1
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ERROR: {type(exc).__name__}: {exc}"
                )
                await asyncio.sleep(args.interval)
                continue

            latency_ms = (time.perf_counter() - started) * 1000.0

            if not response.code.is_successful():
                failures += 1
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ERROR: Server tra ve {response.code}"
                )
                await asyncio.sleep(args.interval)
                continue

            try:
                data = json.loads(response.payload.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("JSON phai la mot object")
                for field in ("device_id", "temperature", "humidity"):
                    if field not in data:
                        raise KeyError(field)
                temperature = float(data["temperature"])
                humidity = float(data["humidity"])
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                failures += 1
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ERROR: Du lieu JSON khong hop le: {exc}"
                )
                print(f"Payload nhan duoc: {response.payload!r}")
                await asyncio.sleep(args.interval)
                continue

            received_at = datetime.now()
            warnings = print_reading(data, received_at)

            successes += 1
            total_latency_ms += latency_ms

            if csv_writer is not None:
                status = "ALERT" if warnings else "NORMAL"
                csv_writer.writerow(
                    [
                        received_at.isoformat(timespec="seconds"),
                        data.get("device_id", args.device),
                        f"{temperature:.1f}",
                        f"{humidity:.1f}",
                        f"{latency_ms:.1f}",
                        status,
                        " | ".join(warnings),
                    ]
                )
                csv_file.flush()

            elapsed = (time.perf_counter() - started)
            await asyncio.sleep(max(0.0, args.interval - elapsed))
    except KeyboardInterrupt:
        print("\nNhan Ctrl+C - dung giam sat.")
    finally:
        await context.shutdown()
        if csv_file is not None:
            csv_file.close()

        print("\n" + "=" * 58)
        print("TONG KET")
        print(f"So lan GET: {attempts}")
        print(f"Thanh cong: {successes} | Loi: {failures}")
        if successes:
            print(f"Thoi gian phan hoi trung binh: {total_latency_ms / successes:.2f} ms")
        if csv_writer is not None:
            print(f"Du lieu da ghi: {csv_path}")
        print("=" * 58)

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    configure_console()
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
