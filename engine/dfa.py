from dataclasses import dataclass
from typing import Dict, Set, Tuple, FrozenSet, Any

@dataclass
class DFA:
    start: Any
    accept: Set[Any]
    alphabet: Set[str]
    transitions: Dict[Tuple[Any, str], Any]

    def states(self) -> Set[Any]:
        st = {self.start} | set(self.accept)
        for (src, sym), dst in self.transitions.items():
            st.add(src)
            st.add(dst)
        return st
