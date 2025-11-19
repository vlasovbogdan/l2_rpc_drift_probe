#!/usr/bin/env python3
import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from web3 import Web3
from web3.exceptions import BlockNotFound


@dataclass
class EndpointSnapshot:
    label: str
    rpc_url: str
    connected: bool
    chain_id: Optional[int]
    latest_block: Optional[int]
    latest_timestamp: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]


@dataclass
class DriftReport:
    primary: EndpointSnapshot
    secondary: EndpointSnapshot
    block_diff: Optional[int]
    time_diff_sec: Optional[float]
    consistent_chain: bool


def now_ms() -> float:
    return time.time() * 1000.0


def connect_and_snapshot(label: str, rpc_url: str, timeout: int) -> EndpointSnapshot:
    t0 = now_ms()
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": timeout}))
    except Exception as exc:
        return EndpointSnapshot(
            label=label,
            rpc_url=rpc_url,
            connected=False,
            chain_id=None,
            latest_block=None,
            latest_timestamp=None,
            latency_ms=None,
            error=f"provider error: {exc}",
        )

    if not w3.is_connected():
        return EndpointSnapshot(
            label=label,
            rpc_url=rpc_url,
            connected=False,
            chain_id=None,
            latest_block=None,
            latest_timestamp=None,
            latency_ms=None,
            error="not connected",
        )

    try:
        chain_id = w3.eth.chain_id
        latest_block = w3.eth.block_number
        block = w3.eth.get_block(latest_block)
        ts = int(block.timestamp) if hasattr(block, "timestamp") else None
    except BlockNotFound:
        chain_id = None
        latest_block = None
        ts = None
        err = "latest block not found"
    except Exception as exc:
        chain_id = None
        latest_block = None
        ts = None
        err = f"RPC error: {exc}"
    else:
        err = None

    latency = now_ms() - t0

    return EndpointSnapshot(
        label=label,
        rpc_url=rpc_url,
        connected=err is None,
        chain_id=chain_id,
        latest_block=latest_block,
        latest_timestamp=ts,
        latency_ms=latency,
        error=err,
    )


def compute_drift(primary: EndpointSnapshot, secondary: EndpointSnapshot) -> DriftReport:
    consistent_chain = (
        primary.connected
        and secondary.connected
        and primary.chain_id is not None
        and primary.chain_id == secondary.chain_id
    )

    if (
        not primary.connected
        or not secondary.connected
        or primary.latest_block is None
        or secondary.latest_block is None
    ):
        block_diff = None
    else:
        block_diff = secondary.latest_block - primary.latest_block

    if (
        not primary.connected
        or not secondary.connected
        or primary.latest_timestamp is None
        or secondary.latest_timestamp is None
    ):
        time_diff = None
    else:
        time_diff = float(secondary.latest_timestamp - primary.latest_timestamp)

    return DriftReport(
        primary=primary,
        secondary=secondary,
        block_diff=block_diff,
        time_diff_sec=time_diff,
        consistent_chain=consistent_chain,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="l2_rpc_drift_probe",
        description=(
            "Compare two Web3 RPC endpoints (e.g. L1 and L2 rollups like Aztec-inspired, Zama-style FHE, "
            "or soundness-focused infra) for block height and time drift."
        ),
    )
    parser.add_argument(
        "--rpc-primary",
        required=True,
        help="Primary RPC endpoint URL.",
    )
    parser.add_argument(
        "--rpc-secondary",
        required=True,
        help="Secondary RPC endpoint URL to compare against.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Per-endpoint timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text.",
    )
    return parser.parse_args()


def print_human(report: DriftReport) -> None:
    p = report.primary
    s = report.secondary

    print("🔍 l2_rpc_drift_probe")
    print("")
    print(f"[Primary]   {p.label}")
    print(f"  RPC URL       : {p.rpc_url}")
    print(f"  Connected     : {'yes' if p.connected else 'no'}")
    print(f"  Chain ID      : {p.chain_id}")
    print(f"  Latest block  : {p.latest_block}")
    print(f"  Block time    : {p.latest_timestamp}")
    print(f"  Latency (ms)  : {f'{p.latency_ms:.2f}' if p.latency_ms is not None else 'n/a'}")
    if p.error:
        print(f"  Error         : {p.error}")
    print("")
    print(f"[Secondary] {s.label}")
    print(f"  RPC URL       : {s.rpc_url}")
    print(f"  Connected     : {'yes' if s.connected else 'no'}")
    print(f"  Chain ID      : {s.chain_id}")
    print(f"  Latest block  : {s.latest_block}")
    print(f"  Block time    : {s.latest_timestamp}")
    print(f"  Latency (ms)  : {f'{s.latency_ms:.2f}' if s.latency_ms is not None else 'n/a'}")
    if s.error:
        print(f"  Error         : {s.error}")
    print("")
    print("Drift analysis:")
    if not report.consistent_chain:
        print("  ⚠️ Chain IDs differ or endpoints are offline; drift metrics may be invalid.")
    if report.block_diff is None:
        print("  Block drift   : unknown")
    else:
        direction = "ahead" if report.block_diff > 0 else "behind" if report.block_diff < 0 else "aligned"
        print(f"  Block drift   : {report.block_diff} blocks ({direction} vs primary)")
    if report.time_diff_sec is None:
        print("  Time drift    : unknown")
    else:
        print(f"  Time drift    : {report.time_diff_sec:.2f} seconds (secondary minus primary)")


def main() -> int:
    args = parse_args()

    primary = connect_and_snapshot("primary", args.rpc_primary, args.timeout)
    secondary = connect_and_snapshot("secondary", args.rpc_secondary, args.timeout)

    report = compute_drift(primary, secondary)

    if args.json:
        payload: Dict[str, Any] = {
            "primary": asdict(primary),
            "secondary": asdict(secondary),
            "blockDiff": report.block_diff,
            "timeDiffSec": report.time_diff_sec,
            "consistentChain": report.consistent_chain,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(report)

    if not report.consistent_chain:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
