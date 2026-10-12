from typing import Dict, Any
from .dfa import DFA

def dfa_to_dot(dfa: DFA, title="DFA") -> str:
    states = dfa.states()

    lines = []
    lines.append("digraph DFA {")
    lines.append('rankdir=LR;')
    lines.append(f'label="{title}"; labelloc=top; fontsize=20;')
    lines.append('node [shape=circle];')

    # Accept states
    for s in dfa.accept:
        lines.append(f'"{s}" [shape=doublecircle];')

    # Start arrow
    lines.append('start [shape=point];')
    lines.append(f'start -> "{dfa.start}";')

    # Transitions
    for (src, sym), dst in dfa.transitions.items():
        lines.append(f'"{src}" -> "{dst}" [label="{sym}"];')

    lines.append("}")
    return "\n".join(lines)
