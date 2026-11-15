# The game no classical team can always win

A team game that no team of separated classical players can win every round, and that a team sharing
entangled qubits wins every time. Built for the Quantum Leap track at Hack The Nest 2026
on the Quantum Rings SDK. It runs at up to 200 qubits on a laptop.

## The game

- Every player gets a card showing 0 or 1. The referee always deals an even number of 1-cards.
- Players cannot talk. Each one answers 0 or 1, seeing only their own card.
- The team wins if the answers total an even number when 0, 4, 8... 1-cards were dealt,
  and an odd number when 2, 6, 10... were dealt.

This is the Mermin-GHZ game. The best classical plan wins 75% of rounds with three
players and approaches 50% as the team grows. A team sharing a GHZ state wins 100%.

## How the quantum team plays

1. Link the qubits into a GHZ state: one `h` gate, then a chain of `cx` gates.
2. Each player holding a 1-card applies an `s` gate (a quarter twist).
3. Every player applies `h` and measures. The measured bit is their answer.

## What the app shows

- **Play:** classical team against quantum team over many rounds, at 3 to 200 players.
  A sabotage switch plants one hidden wrong gate in the quantum circuit.
- **One round, step by step:** the cards, the twists and the answers for a single round.
- **You coach the classical team:** pick a rule for each of three players and try to win all four deals.
- **How big can it go?:** times the quantum team from 3 to 200 qubits.

The classical team always uses the best possible plan. Every fixed plan reduces to one of
2(n+1) kinds (how many players copy their card, and whether one player flips), and
`game.py` scores each kind exactly. For 3 to 7 players this was also checked by trying
all 4^n plans directly, and it matches the known limit of 1/2 + 2^-ceil(n/2).

## The accuracy test (the game as a check on the simulator)

Quantum Rings' CPU engine is MPS-based and compresses as it goes; its `threshold`
setting is a compression dial that controls truncation. The accuracy test sends the
three players' linked qubits on a round trip, through a heavy scrambling circuit that
mixes them with helper qubits and then exactly backwards, before they play the game.
A perfect simulation returns them untouched, so the quantum team keeps winning every
round. Too much compression makes the quantum team lose rounds, and at some setting it
falls below 75%, the best any classical team can do. The page sweeps the dial and
reports the cheapest setting that keeps the quantum team perfect.

Command-line sweep: `python benchmark.py --accuracy-test --quick`

## Sign in, publish and compare (SSOJet + MongoDB Atlas)

After running the accuracy test you can download a JSON "receipt" of the result, or
sign in with **SSOJet** and publish it. Published runs are stored in **MongoDB Atlas**,
one document per run holding the whole receipt, and appear on the **Community results**
page, so you can compare how different laptops handled the same test.

Both are optional. Without them, the app works and explains what is missing.
To set them up, copy `secrets.toml.example` to `.streamlit/secrets.toml` and fill in your
SSOJet OIDC client and MongoDB Atlas connection string. That file is in `.gitignore`.

## Run it

Needs Python 3.11 or newer and a Quantum Rings SDK key.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export QR_TOKEN="your-sdk-key"
export QR_ACCOUNT="your-account-email"
streamlit run app.py
```

## Files

- `game.py`: the referee, the quantum circuit and the classical team.
- `app.py`: Part 1, the game.
- `pages/1_The_accuracy_test.py`: the game as an accuracy test for the simulator.
- `pages/2_Can_a_laptop_keep_up.py`: which circuits are easy or hard for a laptop.
- `benchmark.py`: runs circuits with a time limit; the benchmarks and the accuracy test.
- `pages/3_Community_results.py`: published results from every laptop.
- `community.py`: SSOJet sign-in, receipts, and the MongoDB Atlas results collection.
- `secrets.toml.example`: template for the private settings file.

## Honest notes

- Quantum Rings is a simulator. The circuit runs on a classical laptop, not on quantum hardware.
- The 100% win rate is for an ideal, noise-free simulation. Real hardware would win less often.
- This circuit has a simple structure, which is why it simulates easily at 200 qubits.
  The project demonstrates entanglement; it does not claim a quantum speed-up.
- The classical limit applies to separated players who cannot communicate.
- The Mermin-GHZ game is a known result (Mermin, 1990), and earlier demos of it exist.
  What this project adds: the n-player version on the Quantum Rings SDK, an exact
  classical-plan scorer, a coach mode, a sabotage mode, and a scale test.

## Team and tools

Team: (add your names)

AI tools used: Claude (Anthropic) explained the quantum concepts and wrote much of the code with us; we ran, tested and debugged it on a MacBook with the real Quantum Rings SDK. ChatGPT and Gemini reviewed our plan.
