"""Page 1: play the game (Mermin-GHZ), quantum team vs. the best classical team."""
import time
import pandas as pd
import streamlit as st
import community
import game
import ui

ui.hero("Quantum Leap · Quantum Rings SDK",
        "The game no classical team can always win",
        "A cooperative card game where players can't talk. The best classical plan wins "
        "75% of the time with 3 players. A team sharing entangled qubits wins every round.")

ui.cards([
    ("01 · THE DEAL", "Everyone gets a card",
     "Each player gets a 0 or a 1. The referee always deals an even number of 1-cards."),
    ("02 · NO TALKING", "Answer blind",
     "Each player answers 0 or 1, seeing only their own card."),
    ("03 · THE WIN", "Add up the answers",
     "The team wins or loses together. Whether the total must be even or odd "
     "depends on how many 1-cards were dealt."),
])
st.markdown("""
**Example with 3 players.** There are only four possible deals:

| Cards dealt | 1-cards | To win, the answers must add up to |
|---|---|---|
| 0 · 0 · 0 | none | an **even** number |
| 1 · 1 · 0 | two | an **odd** number |
| 1 · 0 · 1 | two | an **odd** number |
| 0 · 1 · 1 | two | an **odd** number |

Say the cards are 1, 1, 0. If the players answer 1, 0, 0, the total is 1, which is odd, so
the team **wins**. If they answer 1, 1, 0, the total is 2, which is even, so the team **loses**.

**The catch.** A player holding a 0 can't tell whether the deal was 0 · 0 · 0 (even needed)
or one with two 1-cards (odd needed), and nobody can ask.

For bigger teams the rule is the same idea: with 0, 4, 8… 1-cards the total must be even,
and with 2, 6, 10… it must be odd.
""")
st.markdown("""
**Why it is hard.** The right total depends on every card, and each player sees only one.
No plan agreed in advance can win every time: with 3 players, the best plan wins 3 deals out of 4.

**How the quantum team wins.** The players share entangled qubits, one each.
A player holding a 1 gives their qubit a quarter twist, then everyone measures.
Each answer alone is random, but entanglement makes the total come out right every time.
""")
st.caption("Runs on the Quantum Rings SDK, which simulates the quantum circuit on this laptop. "
           "The 100% is for an ideal, noise-free simulation. Real quantum hardware is noisy "
           "and would win somewhat less often.")

tab_play, tab_how, tab_round, tab_coach, tab_scale = st.tabs(
    ["▶ Play", "How it works", "One round, step by step",
     "You coach the classical team", "How big can it go?"])


def digits_of_two_to_the(n):
    return len(str(2 ** n))


# ---------- Tab 1: play many rounds ----------
with tab_play:
    n = st.slider("Team size (one qubit per player)", 3, 200, 3, key="play_n")
    rounds = st.slider("Rounds to play", 5, 100, 20, key="play_rounds")
    sabotage = st.checkbox(
        "Sabotage: secretly add one wrong gate to the quantum circuit", key="play_sabotage")

    m, c, chance = game.best_classical_plan(n)
    st.caption(f"Best possible classical plan for {n} players wins "
               f"{100 * chance:.1f}% of the time. Every fixed plan falls into one of "
               f"{2 * (n + 1)} kinds, and we scored each kind exactly.")

    if st.button("Play the rounds", key="play_button", type="primary"):
        quantum_wins = classical_wins = 0
        progress = st.progress(0.0)
        start = time.time()
        for r in range(rounds):
            cards = game.deal_cards(n)
            quantum_wins += game.team_wins(cards, game.quantum_answers(cards, sabotage))
            classical_wins += game.team_wins(cards, game.classical_answers(cards, m, c))
            progress.progress((r + 1) / rounds)
        st.session_state["play_result"] = {
            "n": n, "rounds": rounds, "sabotage": sabotage,
            "quantum": quantum_wins, "classical": classical_wins,
            "seconds": time.time() - start}

    result = st.session_state.get("play_result")
    if result:
        q_rate = 100 * result["quantum"] / result["rounds"]
        k_rate = 100 * result["classical"] / result["rounds"]
        left, right = st.columns(2)
        left.metric("Classical team", f"{k_rate:.0f}%")
        right.metric("Quantum team", f"{q_rate:.0f}%")
        st.bar_chart({"Win rate (%)": {"Classical": k_rate, "Quantum": q_rate}})
        st.write(f"Ran {result['rounds']} circuits of {result['n']} qubits in "
                 f"{result['seconds']:.1f} seconds on this laptop.")
        st.write(f"Writing a {result['n']}-qubit state out in full would take "
                 f"2^{result['n']} numbers. That count is "
                 f"{digits_of_two_to_the(result['n'])} digits long.")
        if result["sabotage"]:
            st.warning("Sabotage was on. One stray gate flipped the group's hidden "
                       "pattern. Every single answer still looks random, so you "
                       "cannot spot the bug by looking at one player. Only the "
                       "team's score reveals it.")

# ---------- Tab: how it works ----------
with tab_how:
    st.subheader("The game as a story")
    st.markdown("""
Ana, Ben and Cy sit in separate rooms with no phones. A referee hands each of
them a card showing 0 or 1, and always deals an even number of 1-cards.

Each of them says 0 or 1 back. They see only their own card. The referee adds
up the three **answers**, not the cards.

- If no 1-cards were dealt, the answers must total an **even** number.
- If two 1-cards were dealt, the answers must total an **odd** number.

They win or lose together. Nobody is playing against anybody. The opponent is
the rule itself.
""")

    st.subheader("Why a normal team cannot always win")
    st.markdown("""
A normal team can only agree on a plan beforehand. Take this one: "Ana says 0
when she holds a 1. Everyone else says what their card shows."
""")
    st.table(pd.DataFrame({
        "Deal (Ana, Ben, Cy)": ["0, 0, 0", "1, 1, 0", "1, 0, 1", "0, 1, 1"],
        "Answers": ["0, 0, 0", "0, 1, 0", "0, 0, 1", "0, 1, 1"],
        "Total": [0, 1, 1, 2],
        "Needed": ["even", "odd", "odd", "odd"],
        "Result": ["win", "win", "win", "lose"]}).set_index("Deal (Ana, Ben, Cy)"))
    st.markdown("""
It fails when Ben and Cy hold the two 1-cards, because Ana is not one of them.
Ben knows someone else has a 1, but not who. Every plan has a blind spot like
this, so no plan wins more than 3 deals in 4. With bigger teams it gets worse,
down to a coin flip.
""")

    st.subheader("The linked coins")
    st.markdown("""
Before the round, the quantum team shares a set of **linked coins**, one each.

- Holding a 1-card: give your coin a **quarter twist**.
- Holding a 0-card: leave it alone.
- Then everyone **looks** at their coin and says what they see.

Each answer on its own is random. The link controls the total. With no twists
the total comes out even. Two quarter twists make a half twist, and a half
twist flips the total to odd. That is exactly what the rule asks for, so the
team wins every deal, and no player ever learns another player's card.
""")

    st.subheader("What the story stands for")
    st.table(pd.DataFrame({
        "In the story": ["Linked coins", "Quarter twist", "Looking at a coin",
                         "The referee"],
        "In quantum computing": ["Entangled qubits (a GHZ state)", "The S gate",
                                 "The H gate, then a measurement",
                                 "Ordinary Python code"],
        "In our code": ["qc.h(0), then qc.cx(i, i + 1)", "qc.s(i)",
                        "qc.h(i), then qc.measure_all()",
                        "deal_cards() and team_wins()"]}).set_index("In the story"))

    st.markdown("This is the whole quantum program for one round:")
    st.code("""qc = QuantumCircuit(n, n)        # one qubit per player
qc.h(0)                          # 1. link the coins
for i in range(n - 1):
    qc.cx(i, i + 1)
for i, card in enumerate(cards):
    if card == 1:
        qc.s(i)                  # 2. quarter twist if the card is 1
    qc.h(i)                      # 3. look
qc.measure_all()                 # each measured bit is one player's answer""",
            language="python")

    st.subheader("Where the story stops being accurate")
    st.markdown("""
- The coins do not carry answers written in advance. If they did, that would
  be a normal plan, and normal plans cannot win every time.
- No message travels between the coins. The link is made when they are
  created together.
- A twist does not change what that player sees, which stays random. It
  changes how the whole group's answers add up.
""")

    st.subheader("Why this counts as proof")
    st.markdown("""
The game is built so that nothing normal can score 100%. A team that does
score 100% must be using entanglement. Experiments of this kind are how
physicists showed entanglement is real, and that work won the 2022 Nobel Prize
in Physics.

Two honest notes. This app runs on the Quantum Rings simulator, so a normal
laptop is simulating the quantum circuit. And the limit on normal teams is
about separated players who cannot communicate.
""")

    st.subheader("Words used on this page")
    st.markdown("""
- **Bit:** a 0 or a 1, like a light switch.
- **Qubit:** the quantum version of a bit. It can be a blend of 0 and 1 until
  it is measured.
- **Measurement:** looking at a qubit, which makes it show a plain 0 or 1.
- **Gate:** one instruction that changes a qubit.
- **Entanglement:** a link between qubits. Each looks random alone, but the
  group follows a pattern.
- **Circuit:** a list of gates in order, ending in measurements.
""")

# ---------- Tab 2: one round, step by step ----------
with tab_round:
    small_n = st.slider("Team size", 3, 8, 3, key="round_n")
    if st.button("Deal one round", key="round_button"):
        cards = game.deal_cards(small_n)
        rm, rc, _ = game.best_classical_plan(small_n)
        st.session_state["round"] = {
            "cards": cards,
            "quantum": game.quantum_answers(cards),
            "classical": game.classical_answers(cards, rm, rc)}

    one = st.session_state.get("round")
    if one:
        cards, q, k = one["cards"], one["quantum"], one["classical"]
        ones = sum(cards)
        need = "odd" if game.needed_parity(cards) else "even"
        table = pd.DataFrame({
            "Player": [f"Player {i + 1}" for i in range(len(cards))],
            "Card": cards,
            "Twist": ["quarter turn" if card else "none" for card in cards],
            "Quantum answer": q,
            "Classical answer": k}).set_index("Player")
        st.table(table)

        st.write(f"**Step 1, the deal.** {ones} players hold a 1-card, "
                 f"so the answers must total an **{need}** number.")
        turn = (90 * ones) % 360
        meaning = "a half turn, which makes the total odd" if turn == 180 \
            else "no net turn, which keeps the total even"
        st.write(f"**Step 2, the twists.** {ones} quarter turns add up to "
                 f"{90 * ones} degrees. That is {meaning}.")
        st.write("**Step 3, the answers.**")
        for name, answers in (("Quantum team", q), ("Classical team", k)):
            total = sum(answers)
            kind = "odd" if total % 2 else "even"
            line = f"{name}: answers total {total}, which is {kind}."
            if game.team_wins(cards, answers):
                st.success(line + " Win.")
            else:
                st.error(line + " Lose.")

# ---------- Tab 3: you coach the classical team ----------
with tab_coach:
    st.write("Three players, no qubits. Give each player a rule and try to win "
             "all four possible deals.")
    names = ["Ana", "Ben", "Cy"]
    columns = st.columns(3)
    rules = [columns[i].selectbox(names[i], list(game.PLAYER_RULES),
                                  index=1, key=f"coach_rule_{i}")
             for i in range(3)]

    rows = game.score_plan(rules)
    wins = sum(won for _, _, won in rows)
    st.table(pd.DataFrame({
        "Deal (Ana, Ben, Cy)": [", ".join(map(str, cards)) for cards, _, _ in rows],
        "Answers": [", ".join(map(str, answers)) for _, answers, _ in rows],
        "Total": [sum(answers) for _, answers, _ in rows],
        "Needed": ["odd" if game.needed_parity(cards) else "even" for cards, _, _ in rows],
        "Result": ["win" if won else "lose" for _, _, won in rows]}).set_index("Deal (Ana, Ben, Cy)"))
    st.metric("Your plan wins", f"{wins} of 4 deals")
    best = game.best_score_of_any_plan(3)
    if wins == best:
        st.info(f"That is the best any plan can do. We tried all 64 plans and "
                f"none wins more than {best} of 4.")
    else:
        st.info(f"You can do better, but never 4 of 4. We tried all 64 plans "
                f"and the best wins {best}.")

    if st.button("Let the quantum team try the same four deals", key="coach_button"):
        st.session_state["coach_quantum"] = [
            (cards, game.quantum_answers(cards)) for cards in game.legal_deals(3)]
    quantum_rows = st.session_state.get("coach_quantum")
    if quantum_rows:
        q_wins = sum(game.team_wins(cards, answers) for cards, answers in quantum_rows)
        st.table(pd.DataFrame({
            "Deal (Ana, Ben, Cy)": [", ".join(map(str, cards)) for cards, _ in quantum_rows],
            "Quantum answers": [", ".join(map(str, answers)) for _, answers in quantum_rows],
            "Total": [sum(answers) for _, answers in quantum_rows],
            "Needed": ["odd" if game.needed_parity(cards) else "even" for cards, _ in quantum_rows],
            "Result": ["win" if game.team_wins(cards, answers) else "lose"
                       for cards, answers in quantum_rows]}).set_index("Deal (Ana, Ben, Cy)"))
        st.metric("Quantum team wins", f"{q_wins} of 4 deals")

# ---------- Tab 4: scale test ----------
with tab_scale:
    st.write("Times the quantum team at growing team sizes, up to 200 qubits.")
    if st.button("Run the scale test", key="scale_button"):
        progress = st.progress(0.0)
        scale_rows = []
        for i, size in enumerate(game.SCALE_SIZES):
            start = time.time()
            wins = 0
            for _ in range(game.SCALE_ROUNDS):
                cards = game.deal_cards(size)
                wins += game.team_wins(cards, game.quantum_answers(cards))
            scale_rows.append({
                "Qubits": size,
                "Seconds per circuit": round((time.time() - start) / game.SCALE_ROUNDS, 3),
                "Quantum wins": f"{wins} of {game.SCALE_ROUNDS}",
                "Numbers to write the state out": f"2^{size}"})
            progress.progress((i + 1) / len(game.SCALE_SIZES))
        st.session_state["scale"] = scale_rows

    scale_rows = st.session_state.get("scale")
    if scale_rows:
        frame = pd.DataFrame(scale_rows)
        st.line_chart(frame, x="Qubits", y="Seconds per circuit")
        st.table(frame.set_index("Qubits"))
        largest = scale_rows[-1]["Qubits"]
        st.write(f"At {largest} qubits, the full state would need 2^{largest} numbers, "
                 f"a count {digits_of_two_to_the(largest)} digits long. "
                 "The simulator never writes that list out. This circuit has a simple, "
                 "regular structure, which is what lets a laptop simulate it at this size. "
                 "It shows entanglement at scale, not a speed-up over normal computers.")
