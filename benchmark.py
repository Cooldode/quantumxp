"""Benchmark: which circuits are easy or hard for the Quantum Rings simulator?

Run it from the quantum-game folder, with QR_TOKEN and QR_ACCOUNT set:
    python benchmark.py            # full run, about 10 to 25 minutes
    python benchmark.py --quick    # short run, a few minutes
    python benchmark.py --accuracy-test --quick   # the game as an accuracy test

Part A times two kinds of circuit as the qubit count grows:
  - game:      our GHZ game circuit (simple pattern, expected to stay cheap)
  - scrambled: layers of random rotations and CX gates (expected to get expensive)

Part B takes one scrambled circuit, runs it forward and then backward
(a "mirror" circuit, which should return exactly to all zeros), and turns
the simulator's accuracy dial (the `threshold` setting). The SDK's
get_fidelity() then says how close to perfect each setting got.
This follows Quantum Rings' own "Mirror Fidelity Calculation" example notebook.

Every run happens in its own process with a time limit, so one slow
circuit cannot freeze the whole test. Results are printed and saved to
benchmark_results.json.
"""
import json
import math
import os
import random
import subprocess
import sys
import time

TIME_LIMIT = 45          # seconds allowed per run before we give up on it
SCRAMBLED_DEPTH = 12     # layers of random gates in a scrambled circuit

FULL = {
    "game_sizes": [10, 50, 100, 200],
    "scrambled_sizes": [8, 12, 16, 20, 24, 28],
    "mirror_sizes": [20, 24],
    "thresholds": [4, 8, 16, 32, 64, 128],
}
QUICK = {
    "game_sizes": [10, 200],
    "scrambled_sizes": [8, 16, 24],
    "mirror_sizes": [20],
    "thresholds": [4, 16, 64],
}


# ---------- Circuits ----------

def game_circuit(qc, n, seed):
    """Our GHZ game: link the qubits, twist where a card is 1, then look."""
    rng = random.Random(seed)
    cards = [rng.randint(0, 1) for _ in range(n - 1)]
    cards.append(sum(cards) % 2)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    for i, card in enumerate(cards):
        if card:
            qc.s(i)
        qc.h(i)


def scrambled_circuit(qc, n, seed, depth=SCRAMBLED_DEPTH):
    """Layers of random rotations on every qubit, then CX gates between
    neighbours, alternating which pairs are joined (a "brickwall")."""
    rng = random.Random(seed)
    for layer in range(depth):
        for q in range(n):
            qc.rx(rng.uniform(0, 2 * math.pi), q)
            qc.ry(rng.uniform(0, 2 * math.pi), q)
            qc.rz(rng.uniform(0, 2 * math.pi), q)
        for q in range(layer % 2, n - 1, 2):
            qc.cx(q, q + 1)


def recipe_circuit(qc, n, seed, spins, links, layers):
    """A circuit built from three plain choices (used by the app's games).

    spins:  "none", "quarter" (quarter turns only) or "random" (random spins)
    links:  "none", "chain" (one chain of links, like the game) or
            "layers" (links between neighbours in every layer)
    layers: how many rounds of spinning (and linking, if links == "layers")
    """
    rng = random.Random(seed)
    for layer in range(layers):
        for q in range(n):
            if spins == "random":
                qc.rx(rng.uniform(0, 2 * math.pi), q)
                qc.ry(rng.uniform(0, 2 * math.pi), q)
                qc.rz(rng.uniform(0, 2 * math.pi), q)
            elif spins == "quarter":
                qc.h(q)
                if rng.random() < 0.5:
                    qc.s(q)
        if links == "chain" and layer == 0:
            for q in range(n - 1):
                qc.cx(q, q + 1)
        elif links == "layers":
            for q in range(layer % 2, n - 1, 2):
                qc.cx(q, q + 1)


def peak_size(result):
    """Peak simulation size as reported by the SDK (units not documented)."""
    try:
        return result.get_peakmemorysize(0)   # as in Quantum Rings' notebooks
    except Exception:
        try:
            return result.get_peakmemorysize()
        except Exception as error:
            return f"unavailable: {error}"


# ---------- The accuracy test (the game as a check on the simulator) ----------
#
# The players' linked qubits go on a round trip: through a heavy scrambling
# circuit that also tangles them with helper qubits, then exactly backwards.
# A perfect simulation brings them back untouched, so the quantum team still
# wins every round. If the simulator compresses too hard, errors creep in and
# the quantum team starts losing rounds.

DIAL = [2, 4, 8, 16, 32, 64, 128, 256, "full"]   # "full" = HIGHESTACCURACY


def legal_deals_for(players, seed, how_many=4):
    """All legal deals for 3 or 4 players; otherwise a fixed random sample."""
    if players <= 4:
        from itertools import product
        return [list(d) for d in product([0, 1], repeat=players) if sum(d) % 2 == 0]
    rng = random.Random(seed)
    deals = []
    for _ in range(how_many):
        cards = [rng.randint(0, 1) for _ in range(players - 1)]
        deals.append(cards + [sum(cards) % 2])
    return deals


def accuracy_test_circuit(QuantumCircuit, cards, total, layers, seed):
    """Players are qubits 0..p-1; helpers are the rest, up to `total`."""
    players = len(cards)
    scramble = QuantumCircuit(total, total)
    scrambled_circuit(scramble, total, seed, layers)
    qc = QuantumCircuit(total, total)
    qc.h(0)                                   # link the players' qubits
    for i in range(players - 1):
        qc.cx(i, i + 1)
    qc.append(scramble)                       # the round trip: forward...
    qc.append(scramble.inverse())             # ...and exactly back
    for i, card in enumerate(cards):          # then play the game as usual
        if card:
            qc.s(i)
        qc.h(i)
    qc.measure_all()
    return qc


def run_accuracy_test(spec, backend, QuantumCircuit, job_monitor):
    players, total = spec["players"], spec["total"]

    # Which end of the result string is qubit 0? Flip only qubit 0 and look.
    probe = QuantumCircuit(2, 2)
    probe.x(0)
    probe.measure_all()
    job = backend.run(probe, shots=1, mode="async", quiet=True)
    job_monitor(job, quiet=True)
    rightmost_is_qubit_0 = _clean(next(iter(job.result().get_counts()))) != "10"

    options = {"shots": spec["shots"], "mode": "async", "quiet": True}
    if spec["threshold"] == "full":
        options["performance"] = "HIGHESTACCURACY"
    else:
        options.update(performance="custom", threshold=spec["threshold"])

    wins = rounds = 0
    seconds = 0.0
    peak = 0
    for cards in legal_deals_for(players, spec["seed"]):
        qc = accuracy_test_circuit(QuantumCircuit, cards, total, spec["layers"], spec["seed"])
        start = time.time()
        job = backend.run(qc, **options)
        job_monitor(job, quiet=True)
        result = job.result()
        seconds += time.time() - start
        need = (sum(cards) // 2) % 2
        for bitstring, count in result.get_counts().items():
            bits = _clean(bitstring)
            if len(bits) != total:
                raise RuntimeError(f"expected {total} bits, got {len(bits)}: {bitstring!r}")
            if rightmost_is_qubit_0:
                answers = [int(bits[-1 - i]) for i in range(players)]
            else:
                answers = [int(bits[i]) for i in range(players)]
            rounds += count
            wins += count if sum(answers) % 2 == need else 0
        size = peak_size(result)
        if isinstance(size, (int, float)):
            peak = max(peak, int(size))
    return {"wins": wins, "rounds": rounds, "seconds": round(seconds, 3),
            "peak_bytes": peak}


def _clean(bitstring):
    return "".join(ch for ch in bitstring if ch in "01")


# ---------- One run (this part executes inside a separate process) ----------

def run_point(spec):
    from QuantumRingsLib import QuantumRingsProvider, QuantumCircuit, job_monitor
    provider = QuantumRingsProvider(token=os.environ["QR_TOKEN"],
                                    name=os.environ["QR_ACCOUNT"])
    backend = provider.get_backend("scarlet_quantum_rings")
    if spec["part"] == "C":
        return run_accuracy_test(spec, backend, QuantumCircuit, job_monitor)
    n, seed = spec["n"], spec["seed"]

    qc = QuantumCircuit(n, n)
    if spec["family"] == "game":
        game_circuit(qc, n, seed)
    elif spec["family"] == "recipe":
        recipe_circuit(qc, n, seed, spec["spins"], spec["links"], spec["layers"])
    else:
        scrambled_circuit(qc, n, seed, spec.get("layers", SCRAMBLED_DEPTH))

    options = {"shots": 1, "mode": "async", "quiet": True}
    if spec["part"] == "B":
        qc.append(qc.inverse())               # forward, then backward
        options.update(performance="custom", threshold=spec["threshold"])
    else:
        qc.measure_all()

    start = time.time()
    job = backend.run(qc, **options)
    job_monitor(job, quiet=True)
    result = job.result()
    seconds = time.time() - start

    out = {"seconds": round(seconds, 3), "peak_size": peak_size(result)}
    if spec["part"] == "B":
        out["fidelity"] = result.get_fidelity()
    return out


# ---------- The controller ----------

def run_with_limit(spec, limit=TIME_LIMIT):
    """Run one point in a fresh process; give up after `limit` seconds."""
    try:
        done = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--point", json.dumps(spec)],
            capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return {"status": f"gave up after {limit} s"}
    for line in reversed(done.stdout.splitlines()):
        if line.startswith("RESULT "):
            return {"status": "ok", **json.loads(line[len("RESULT "):])}
    error = (done.stderr.strip().splitlines() or ["no output"])[-1]
    return {"status": f"error: {error}"}


def show(row):
    parts = [f"{key}={value}" for key, value in row.items()]
    print("  " + "  ".join(parts), flush=True)


def main():
    plan = QUICK if "--quick" in sys.argv else FULL
    for name in ("QR_TOKEN", "QR_ACCOUNT"):
        if name not in os.environ:
            sys.exit(f"Set {name} first (export {name}=...).")

    rows = []
    print("Part A: time per circuit as qubits grow", flush=True)
    for family, sizes in (("game", plan["game_sizes"]),
                          ("scrambled", plan["scrambled_sizes"])):
        for n in sizes:
            spec = {"part": "A", "family": family, "n": n, "seed": n}
            row = {**spec, **run_with_limit(spec)}
            rows.append(row)
            show(row)

    print("\nPart B: the accuracy dial on a scrambled mirror circuit", flush=True)
    for n in plan["mirror_sizes"]:
        for threshold in plan["thresholds"]:
            spec = {"part": "B", "family": "scrambled", "n": n, "seed": n,
                    "threshold": threshold}
            row = {**spec, **run_with_limit(spec)}
            rows.append(row)
            show(row)

    with open("benchmark_results.json", "w") as handle:
        json.dump({"time_limit_s": TIME_LIMIT, "scrambled_depth": SCRAMBLED_DEPTH,
                   "rows": rows}, handle, indent=2)
    print("\nSaved benchmark_results.json")


def accuracy_sweep():
    """python benchmark.py --accuracy-test [--quick]"""
    for name in ("QR_TOKEN", "QR_ACCOUNT"):
        if name not in os.environ:
            sys.exit(f"Set {name} first (export {name}=...).")
    quick = "--quick" in sys.argv
    totals = [16, 20] if quick else [12, 16, 20, 24]
    layer_options = [12] if quick else [8, 12, 16]
    dial = [2, 8, 32, 128, "full"] if quick else DIAL
    rows = []
    print("Accuracy test: 3 players, all 4 deals, 25 rounds each", flush=True)
    for total in totals:
        for layers in layer_options:
            for setting in dial:
                spec = {"part": "C", "players": 3, "total": total, "layers": layers,
                        "threshold": setting, "seed": 7, "shots": 25}
                row = {**spec, **run_with_limit(spec)}
                if row["status"] == "ok":
                    row["win_rate"] = round(100 * row["wins"] / row["rounds"], 1)
                rows.append(row)
                show(row)
                if row["status"] != "ok":
                    break        # higher settings only get slower
    with open("accuracy_test_results.json", "w") as handle:
        json.dump({"time_limit_s": TIME_LIMIT, "rows": rows}, handle, indent=2)
    print("\nSaved accuracy_test_results.json")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--point":
        print("RESULT " + json.dumps(run_point(json.loads(sys.argv[2]))), flush=True)
    elif "--accuracy-test" in sys.argv:
        accuracy_sweep()
    else:
        main()
