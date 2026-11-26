"""F2A: instancia, lectura/escritura, 12 reglas, motor constructivo y *rollout*."""

from .engine import Policy, Solution, complete_k, run, run_cocktail, run_rule, step
from .instance import Instance, iter_bits, mask_of
from .io import load_instance, save_instance, validate_instance
from .rollout import DecisionRecord, completions, run_rollout
from .rules import DEFAULT_TIEBREAK, RULE_IDS, RULES, TIEBREAKS, pick, picks
from .state import ConstructionState, initial_state
from .verify import verify_solution

__all__ = [
    "ConstructionState", "DEFAULT_TIEBREAK", "DecisionRecord", "Instance", "Policy", "RULES",
    "RULE_IDS", "Solution", "TIEBREAKS", "complete_k", "completions", "initial_state", "iter_bits",
    "load_instance", "mask_of", "pick", "picks", "run", "run_cocktail", "run_rollout", "run_rule",
    "save_instance", "step", "validate_instance", "verify_solution",
]
