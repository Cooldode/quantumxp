"""Game logic: referee, quantum team, classical team.

The quantum team runs on the Quantum Rings SDK (QuantumRingsLib).
Set two environment variables before running (never put the key in code):
    QR_TOKEN   = your SDK key from the Quantum Rings portal
    QR_ACCOUNT = the email on your Quantum Rings account
"""
import os
import random
from itertools import product
from math import comb

_provider = None
_backend = None
_rightmost_is_player_0 = None

SCALE_SIZES = [3, 10, 25, 50, 100, 150, 200]   # team sizes for the scale test
SCALE_ROUNDS = 5                               # circuits timed per size


def _clean(bitstring):
    """Keep only the 0s and 1s of a result string."""
    return "".join(ch for ch in bitstring if ch in "01")


def _run_once(qc):
    """Run a circuit one time and return its result as a string of bits."""
    from QuantumRingsLib import job_monitor
    job = _backend.run(qc, shots=1)
    job_monitor(job)
    return _clean(next(iter(job.result().get_counts())))


def get_backend():
    """Log in to Quantum Rings once and reuse the connection."""
    global _provider, _backend, _rightmost_is_player_0
    if _backend is None:
        from QuantumRingsLib import QuantumRingsProvider, QuantumCircuit
        # Keep the provider in a global: if Python deletes it, the login is lost.
        _provider = QuantumRingsProvider(token=os.environ["QR_TOKEN"],
                                         name=os.environ["QR_ACCOUNT"])
        _backend = _provider.get_backend("scarlet_quantum_rings")  # CPU mode
        # Find out which end of the result string belongs to player 0:
        # flip only qubit 0 to a 1 and see where the 1 shows up.
        test = QuantumCircuit(2, 2)
        test.x(0)
        test.measure_all()
        _rightmost_is_player_0 = _run_once(test) != "10"
    return _backend


# ---------- Referee ----------

def deal_cards(n):
    """Give each of n players a 0 or 1, with an even number of 1s overall."""
    cards = [random.randint(0, 1) for _ in range(n - 1)]
    cards.append(sum(cards) % 2)          # last card makes the count even
    return cards


def legal_deals(n):
    """Every possible deal for a small team (even number of 1s)."""
    return [list(d) for d in product([0, 1], repeat=n) if sum(d) % 2 == 0]


def needed_parity(cards):
    """0 = answers must total even, 1 = answers must total odd."""
    return (sum(cards) // 2) % 2


def team_wins(cards, answers):
    return sum(answers) % 2 == needed_parity(cards)


# ---------- Quantum team ----------

def quantum_answers(cards, sabotage=False):
    """Run one round on Quantum Rings. Returns one 0/1 answer per player.

    sabotage=True secretly adds one wrong gate, to show how a hidden bug
    breaks the team even though every single answer still looks random.
    """
    get_backend()                         # log in BEFORE building any circuit
    from QuantumRingsLib import QuantumCircuit
    n = len(cards)
    qc = QuantumCircuit(n, n)
    qc.h(0)                               # 1. link the coins (GHZ state)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    if sabotage:
        qc.z(0)                           # the hidden bug: one stray gate
    for i, card in enumerate(cards):
        if card == 1:
            qc.s(i)                       # 2. quarter twist if card is 1
        qc.h(i)                           # 3. look
    qc.measure_all()
    bits = [int(ch) for ch in _run_once(qc)]
    return bits[::-1] if _rightmost_is_player_0 else bits


# ---------- Classical team ----------
# Every fixed plan boils down to two choices:
#   m = how many players answer with their own card (the rest say 0)
#   c = 1 if one player flips their answer, else 0
# So we can check every possible plan exactly, for any team size.

def classical_win_chance(n, m, c):
    """Exact chance that plan (m, c) wins, over all legal deals."""
    wins = 0
    for j in range(m + 1):                # 1-cards held by the m "copy" players
        for l in range(n - m + 1):        # 1-cards held by everyone else
            if (j + l) % 2:
                continue                  # deals always have an even count
            total = (c + j) % 2
            if total == ((j + l) // 2) % 2:
                wins += comb(m, j) * comb(n - m, l)
    return wins / 2 ** (n - 1)


def best_classical_plan(n):
    """Try every plan; return (m, c, win chance) for the best one."""
    return max(((m, c, classical_win_chance(n, m, c))
                for m in range(n + 1) for c in (0, 1)),
               key=lambda plan: plan[2])


def classical_answers(cards, m, c):
    answers = [cards[i] if i < m else 0 for i in range(len(cards))]
    if c:
        answers[-1] ^= 1                  # one player flips their answer
    return answers


# ---------- "You coach the classical team" ----------
# The four things one player can do with the single card they see.

PLAYER_RULES = {
    "Always say 0": lambda card: 0,
    "Always say 1": lambda card: 1,
    "Copy my card": lambda card: card,
    "Flip my card": lambda card: 1 - card,
}


def score_plan(rule_names):
    """Play a plan (one rule per player) on every deal.
    Returns a list of (cards, answers, won)."""
    rows = []
    for cards in legal_deals(len(rule_names)):
        answers = [PLAYER_RULES[rule](card)
                   for rule, card in zip(rule_names, cards)]
        rows.append((cards, answers, team_wins(cards, answers)))
    return rows


def best_score_of_any_plan(n):
    """Brute force: the most deals any plan can win (small teams only)."""
    return max(sum(won for _, _, won in score_plan(plan))
               for plan in product(PLAYER_RULES, repeat=n))
