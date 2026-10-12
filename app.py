import streamlit as st
from engine.nfa import regex_to_nfa
from engine.convert import nfa_to_dfa
from engine.minimize import minimize_dfa
from engine.viz import dfa_to_dot
import pandas as pd



def build_state_labels(start_state, accept_states, all_states):
    """
    Map internal numeric states -> friendly labels: S, F, q0, q1...
    """
    accept_states = set(accept_states)

    labels = {}
    labels[start_state] = "S"

    # If multiple accept states, name them F1, F2...
    if len(accept_states) == 1:
        labels[next(iter(accept_states))] = "F"
    else:
        for i, s in enumerate(sorted(accept_states), start=1):
            labels[s] = f"F{i}"

    # Remaining states become q0, q1, q2...
    remaining = [s for s in sorted(all_states) if s not in labels]
    for i, s in enumerate(remaining):
        labels[s] = f"q{i}"

    return labels

def extract_edges(transitions):
    """
    Convert transitions (whatever its structure) into a list of edges:
    (src, symbol, dst)

    Supports common formats:
    1) {(src, sym): {dst1, dst2}}
    2) {src: {sym: {dst1, dst2}}}
    3) list of (src, sym, dst)
    """
    edges = []

    # Case 3: list/tuple edges
    if isinstance(transitions, (list, tuple)):
        for item in transitions:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                edges.append((item[0], item[1], item[2]))
        return edges

    # Case 1 or 2: dict based
    if isinstance(transitions, dict):
        # Case 1: keys like (src, sym)
        for k, v in transitions.items():
            if isinstance(k, tuple) and len(k) == 2:
                src, sym = k
                dsts = v
                if isinstance(dsts, (set, list, tuple)):
                    for d in dsts:
                        edges.append((src, sym, d))
                else:
                    edges.append((src, sym, dsts))
            # Case 2: src -> {sym -> dsts}
            elif isinstance(v, dict):
                src = k
                for sym, dsts in v.items():
                    if isinstance(dsts, (set, list, tuple)):
                        for d in dsts:
                            edges.append((src, sym, d))
                    else:
                        edges.append((src, sym, dsts))

    return edges

st.set_page_config(
    page_title="LexOpt Tool",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ LexOpt Tool")
st.caption("Regex → NFA → DFA → Minimized DFA (Lexical Analysis Optimizer)")

# --- Sidebar inputs ---
st.sidebar.header("Input")

token_type = st.sidebar.selectbox(
    "Token type",
    ["Identifier", "Number", "Keyword", "Custom"]
)

default_examples = {
    "Identifier": r"[a-zA-Z_][a-zA-Z0-9_]*",
    "Number": r"[0-9]+",
    "Keyword": r"(if|else|while|for)",
    "Custom": r"(a|b)*abb",
}

regex_input = st.sidebar.text_input(
    "Regex pattern",
    value=default_examples[token_type]
)

show_examples = st.sidebar.checkbox("Show quick examples", value=True)

run_btn = st.sidebar.button("Run / Generate", type="primary")

# --- Main page layout ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📌 Selected Input")
    st.write(f"**Token type:** {token_type}")
    st.write(f"**Regex:** `{regex_input}`")

    if show_examples:
        st.markdown("### Quick Examples (click to copy)")
        examples = [
            r"(a|b)*abb",
            r"a(b|c)*d",
            r"[0-9]+",
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            r"(ab|ba)+",
            r"a?b*",
        ]
        for ex in examples:
            st.code(ex, language="text")

with col2:
    st.subheader("🧩 Output Panels")

    # Default placeholders
    st.info("Module B will generate NFA here.")
    st.info("Module C will convert NFA → DFA here.")
    st.info("Module D will minimize DFA here.")
    st.info("Module E will compare states/transitions/time here.")

def dfa_step(dfa, state, ch):
    """
    Robust DFA transition getter.
    Supports:
      1) dfa.transitions[(state, ch)] = next_state
      2) dfa.transitions[state][ch] = next_state
    """
    T = getattr(dfa, "transitions", None)
    if T is None:
        return None

    # Case 1: dict with tuple key
    try:
        if (state, ch) in T:
            return T[(state, ch)]
    except Exception:
        pass

    # Case 2: nested dict
    try:
        return T.get(state, {}).get(ch, None)
    except Exception:
        return None


def get_dfa_states(dfa):
    """
    Robust DFA states collector from transitions + start/accept.
    """
    states = set()
    start = getattr(dfa, "start", None)
    accept = set(getattr(dfa, "accept", set()) or set())

    if start is not None:
        states.add(start)
    states |= accept

    T = getattr(dfa, "transitions", None)
    if isinstance(T, dict):
        # tuple-key transitions
        for k, v in T.items():
            # k can be (state, symbol) or state
            if isinstance(k, tuple) and len(k) == 2:
                s, sym = k
                states.add(s)
                states.add(v)
            else:
                # nested dict form
                states.add(k)
                if isinstance(v, dict):
                    for sym, nxt in v.items():
                        states.add(nxt)
    return states


def estimate_memory_units(num_states, num_transitions):
    """
    Not real bytes, but a simple 'units' estimate for comparison.
    Good for class/paper: fewer states/transitions => less memory.
    """
    return num_states + num_transitions

    # ✅ Only generate + show NFA when button is clicked
   # --- Run button action ---
if run_btn:
    if not regex_input.strip():
        st.error("Please enter a regex pattern.")
    else:
        st.success("✅ Input received. Generating NFA...")

        # =========================
        # MODULE B: REGEX → NFA
        # =========================
        nfa = regex_to_nfa(regex_input)

        # Extract edges safely
        edges = extract_edges(nfa.transitions)

        # Collect all NFA states
        all_states = set([nfa.start]) | set(nfa.accept)
        for s, sym, d in edges:
            all_states.add(s)
            all_states.add(d)

        # Build readable labels (S, F, q1, q2...)
        labels = build_state_labels(nfa.start, nfa.accept, all_states)

        # ---- NFA Summary ----
        st.subheader("🔹 Module B: NFA Summary")
        st.write(f"Start state: **{labels[nfa.start]}**")
        st.write(
            "Accept states: " +
            ", ".join(f"**{labels[s]}**" for s in sorted(set(nfa.accept)))
        )
        st.write(f"Number of states: **{len(all_states)}**")
        st.write(f"Number of transitions: **{len(edges)}**")

        # ---- NFA Diagram ----
        st.subheader("🧭 NFA Transition Diagram")

        nfa_dot = []
        nfa_dot.append("digraph NFA {")
        nfa_dot.append("rankdir=LR;")
        nfa_dot.append("node [shape=circle];")

        # Accept states
        for s in set(nfa.accept):
            nfa_dot.append(f'{labels[s]} [shape=doublecircle];')

        # Start arrow
        nfa_dot.append("start [shape=point];")
        nfa_dot.append(f"start -> {labels[nfa.start]};")

        # Transitions
        for src, sym, dst in edges:
            sym_label = "ε" if sym in (None, "", "eps", "EPS", "ε") else str(sym)
            nfa_dot.append(f'{labels[src]} -> {labels[dst]} [label="{sym_label}"];')

        nfa_dot.append("}")
        st.graphviz_chart("\n".join(nfa_dot))

        # =========================
        # MODULE C: NFA → DFA
        # =========================
        st.subheader("🟦 Module C: DFA (Subset Construction)")

        dfa = nfa_to_dfa(nfa)

        st.write(f"DFA states: **{len(dfa.states())}**")
        st.write(f"DFA transitions: **{len(dfa.transitions)}**")

        st.graphviz_chart(
            dfa_to_dot(dfa, title="DFA generated from NFA")
        )

        # =========================
        # MODULE D: DFA MINIMIZATION
        # =========================
        st.subheader("🟩 Module D: Minimized DFA")

        min_dfa = minimize_dfa(dfa)

        st.write(f"Minimized DFA states: **{len(min_dfa.states())}**")
        st.write(f"Minimized DFA transitions: **{len(min_dfa.transitions)}**")

        st.graphviz_chart(
            dfa_to_dot(min_dfa, title="Minimized DFA (Hopcroft Algorithm)")
        )

        # =========================
        # MODULE E: COMPARISON
        # =========================

        
        # -----------------------------
# ✅ Module E: Optimization Comparison (with Memory/Time/Suitability table)
# -----------------------------
st.subheader("🟧 Module E: Optimization Comparison")

# You already have these counts in your UI, but we compute again safely:
nfa_states = len(all_states)
nfa_transitions = len(edges)

dfa_states_set = get_dfa_states(dfa)
dfa_states = len(dfa_states_set)
dfa_transitions = len(getattr(dfa, "transitions", {}))

min_states_set = get_dfa_states(min_dfa)
min_states = len(min_states_set)
min_transitions = len(getattr(min_dfa, "transitions", {}))

# Show simple numbers (your existing cards are fine too)
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("NFA States", nfa_states)
    st.metric("NFA Transitions", nfa_transitions)
with c2:
    st.metric("DFA States", dfa_states)
    st.metric("DFA Transitions", dfa_transitions)
with c3:
    st.metric("Min DFA States", min_states)
    st.metric("Min DFA Transitions", min_transitions)

# ✅ Now the BIG table (memory/time/suitability)
comparison_df = pd.DataFrame([
    {
        "Automaton": "NFA",
        "States": nfa_states,
        "Transitions": nfa_transitions,
        "Epsilon (ε) transitions": "Yes",
        "Deterministic?": "No",
        "Time per char": "Variable (may branch)",
        "Overall time": "≈ O(n × branching)",
        "Memory (units)": estimate_memory_units(nfa_states, nfa_transitions),
        "Compiler suitability": "❌ Not ideal"
    },
    {
        "Automaton": "DFA",
        "States": dfa_states,
        "Transitions": dfa_transitions,
        "Epsilon (ε) transitions": "No",
        "Deterministic?": "Yes",
        "Time per char": "Constant",
        "Overall time": "O(n)",
        "Memory (units)": estimate_memory_units(dfa_states, dfa_transitions),
        "Compiler suitability": "⚠️ OK"
    },
    {
        "Automaton": "Minimized DFA",
        "States": min_states,
        "Transitions": min_transitions,
        "Epsilon (ε) transitions": "No",
        "Deterministic?": "Yes",
        "Time per char": "Constant (best)",
        "Overall time": "O(n)",
        "Memory (units)": estimate_memory_units(min_states, min_transitions),
        "Compiler suitability": "✅ Best"
    },
])

st.markdown("### 📊 Memory / Time / Suitability Comparison")
st.dataframe(comparison_df, use_container_width=True)

st.info("Key idea: Minimized DFA keeps the same language, but uses fewer states → less memory + faster scanning in a lexer.")


# -----------------------------
# ✅ String Tracing (Lexical Analysis Simulation)
# -----------------------------
st.subheader("🔎 String Tracing (Run input through Minimized DFA)")

test_str = st.text_input("Enter a test string to trace", value="")

if test_str != "":
    cur = getattr(min_dfa, "start", None)
    accept_set = set(getattr(min_dfa, "accept", set()) or set())

    steps = []
    ok = True

    steps.append({"Step": 0, "Read": "(start)", "State": str(cur), "Status": "Start"})

    for i, ch in enumerate(test_str, start=1):
        nxt = dfa_step(min_dfa, cur, ch)
        if nxt is None:
            steps.append({"Step": i, "Read": ch, "State": "—", "Status": "❌ No transition"})
            ok = False
            break
        else:
            cur = nxt
            steps.append({"Step": i, "Read": ch, "State": str(cur), "Status": "OK"})

    st.markdown("### Trace Steps")
    st.table(pd.DataFrame(steps))

    if ok and cur in accept_set:
        st.success(f"✅ ACCEPTED: ended in final state {cur}")
    else:
        st.error(f"❌ REJECTED: ended in non-final state {cur}")
