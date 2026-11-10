# MECC: MoE Expert Cache Coordination

MECC runs MoE expert inference with GPU memory and CPU memory caching an HDD-backed
expert store. Routing profiles guide the initial placement. At runtime, CPU-to-GPU
promotion reuses the freed CPU cache slot to retain the displaced GPU expert.
Serving requests update expert recency within the allocated capacities.

## Code map

- `mecc_package/compiler.py`: placement scoring and capacity planning.
- `mecc_package/compile.py`: standalone planning command.
- `mecc_package/e2e/compile_config.py`: per-layer placement and initialization plans.
- `mecc_package/e2e/tiered_engine.py`: backing store, expert tensors, tier transitions.
- `mecc_package/e2e/policy_plugin.py`: caching and execution policies.
- `mecc_package/e2e/mixtral_tiered.py`: model loading and expert dispatch.
- `mecc_package/e2e/run_e2e.py`: inference, latency, and quality measurement.
- `mecc_package/e2e/completion_protocol.py`: per-request and per-phase accounting.
- `mecc_package/e2e/correctness_probe.py`: routing, token, gate, and logits diagnostics.
- `mecc_package/scripts/`: profiling, resource-aware launch, and experiment utilities.
- `mecc_package/mecc_framework/`: modular caching and model interfaces.

`compiler.py` stays directly above `e2e/`; the end-to-end modules use flat imports.
The compiler filename is a historical implementation name.

## Installation

Use Python 3.10+ on Linux for GPU inference. Install PyTorch for the local CUDA
environment, followed by the inference dependencies:

```bash
python -m pip install -r mecc_package/e2e/requirements_e2e.txt
```

For the standard-library/NumPy regression suite:

```bash
python -m pip install -r mecc_package/requirements.txt
python mecc_package/scripts/test_completion_protocol.py
```

## Logic check

With inference dependencies installed, the CPU smoke path uses a tiny model:

```bash
cd mecc_package/e2e
python run_e2e.py --smoke --out smoke_report.json
```

This checks loading, dispatch, and caching; its timing is a logic diagnostic.

## Model inference

Obtain a compatible Mixtral model snapshot from its publisher. Select a directory
on the HDD volume for the expert store. Run from the repository root:

```bash
python mecc_package/e2e/run_e2e.py \
  --state_path /path/to/model/snapshot \
  --store_root /path/to/hdd/expert_store \
  --hbm_budget 50 --cpu_budget 16 \
  --policies ours --n_prompts 4 --prompt_len 64 --max_new_tokens 16 \
  --out inference_result.json
```

The first load materializes experts in the store. The harness records its effective
configuration in the output. GPU/CPU budgets configure primary expert residency;
host mirrors and buffers also consume physical memory. The experiment launcher
supports Linux cgroup limits and resource sampling for physical-memory accounting.

## Experiment utilities

Frozen inputs and a routing profile accompany the measured-request protocol.
The queue configuration is in `mecc_package/e2e/configs/completion_20261109.json`.
Inspect the launcher and queue commands before selecting a local model path,
storage path, run name, and resource allocation:

```bash
python mecc_package/scripts/experiment_launcher.py --help
python mecc_package/scripts/completion_queue.py --help
```

The harness compares policies with a shared model loader, expert store, and input
protocol. Configuration files specify workloads and ablations; they are not run
results. Model weights and generated experiment outputs are obtained separately.

See `third_party_notices/` for attribution.
