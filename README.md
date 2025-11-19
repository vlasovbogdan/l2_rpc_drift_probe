# l2_rpc_drift_probe

A tiny CLI tool that compares two Web3 RPC endpoints and reports how far they drift in terms of block height and block timestamp.

It is useful when you operate privacy rollups or research systems inspired by Aztec, Zama, or soundness-focused labs and you want to sanity check that your L1 and L2 infra, archival and non-archival nodes, or multiple providers are in a consistent state.


Repository layout

This repository contains exactly two files:

- app.py
- README.md


What it does

Given two RPC URLs, l2_rpc_drift_probe:

- Connects to both endpoints with a configurable timeout.
- Fetches:
  - chain ID
  - latest block number
  - latest block timestamp
  - simple latency measurement
- Computes:
  - block_diff: secondary latest block minus primary latest block
  - time_diff_sec: secondary latest block timestamp minus primary latest block timestamp
  - consistent_chain flag (true when both are connected and chain IDs match)
- Prints a human-readable summary or JSON for automation.

It does not send transactions, does not require private keys, and is read-only.


Installation

Requirements:

- Python 3.10 or newer
- web3 Python package

Install dependency:

pip install web3

Then create a GitHub repository, place app.py and README.md in the root, and commit.


Usage

Compare a rollup RPC to an L1 RPC:

python app.py --rpc-primary https://mainnet.infura.io/v3/YOUR_KEY --rpc-secondary https://your-rollup-rpc.example

Compare two providers for the same chain:

python app.py --rpc-primary https://eth.llamarpc.com --rpc-secondary https://rpc.ankr.com/eth

Use a longer timeout and JSON output for monitoring:

python app.py --rpc-primary https://mainnet.infura.io/v3/YOUR_KEY --rpc-secondary https://eth.llamarpc.com --timeout 20 --json


Output interpretation

Human-readable mode shows for each endpoint:

- RPC URL
- Connected or offline
- Chain ID
- Latest block and block timestamp
- Measured latency in milliseconds
- Any connection or RPC error

The drift analysis section shows:

- Block drift: secondary minus primary latest block
- Time drift: secondary minus primary latest block timestamp in seconds
- A warning when chain IDs differ or one endpoint is offline


Exit codes

- 0 when both endpoints are connected and chain IDs match (even if there is some block drift).
- 2 when chain IDs differ or one of the endpoints is offline, indicating that drift metrics may not be meaningful.


Relation to Aztec, Zama, and soundness

While this tool does not directly model zk circuits, FHE, or formal verification, it fits into the same theme of sound infrastructure assumptions:

- For Aztec-style zk rollups, you might compare your rollup RPC to Ethereum L1 to ensure your sequencer and data availability view is reasonable.
- For Zama-style FHE systems, you might compare encrypted compute nodes against public gateways or archival nodes.
- For soundness-driven labs, l2_rpc_drift_probe can be part of your monitoring to detect inconsistent RPC views that could undermine proof systems or research experiments.

Extend it as needed by adding more endpoints, richer metrics, or integrating with your observability stack.
