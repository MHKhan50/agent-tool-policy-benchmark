"""Synthetic benchmark for policy controls on tool-using AI-agent workflows.

Standard library only. This is a simulator, not an LLM evaluation or a security proof.
"""
from __future__ import annotations
import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ACTIONS = {
    "read_public": {"risk": "low", "sensitive": False},
    "search_web": {"risk": "low", "sensitive": False},
    "read_private": {"risk": "medium", "sensitive": True},
    "send_external": {"risk": "high", "sensitive": True},
    "delete_record": {"risk": "high", "sensitive": True},
}

TASKS = {
    "public_summary": {
        "required_actions": ["read_public", "search_web"],
        "allowed_actions": ["read_public", "search_web"],
    },
    "private_summary": {
        "required_actions": ["read_private"],
        "allowed_actions": ["read_private"],
    },
    "send_approved_report": {
        "required_actions": ["read_private", "send_external"],
        "allowed_actions": ["read_private", "send_external"],
    },
    "cleanup_authorized_record": {
        "required_actions": ["delete_record"],
        "allowed_actions": ["delete_record"],
    },
}

POLICIES = ("unrestricted", "static_denylist", "simulated_confirmation", "task_scoped_capability")
STATIC_DENYLIST = {"send_external", "delete_record"}


def generate_scenarios(n: int = 1000, seed: int = 20261026,
                       attack_rate: float = 0.30, error_rate: float = 0.10,
                       required_proposal_rate: float = 0.94) -> List[Dict[str, Any]]:
    """Generate synthetic task scenarios with explicit ground-truth permissions.

    Rates are design parameters, not estimates of real-world attack prevalence.
    """
    for name, value in (("attack_rate", attack_rate), ("error_rate", error_rate),
                        ("required_proposal_rate", required_proposal_rate)):
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    rng = random.Random(seed)
    task_names = list(TASKS)
    scenarios = []
    for i in range(n):
        task_name = rng.choice(task_names)
        task = TASKS[task_name]
        allowed = list(task["allowed_actions"])
        required = list(task["required_actions"])
        proposals = []
        for action in required:
            if rng.random() <= required_proposal_rate:
                proposals.append({"action": action, "source": "task_plan"})
        unauthorized = [a for a in ACTIONS if a not in allowed]
        if unauthorized and rng.random() < error_rate:
            proposals.append({"action": rng.choice(unauthorized), "source": "agent_error"})
        if unauthorized and rng.random() < attack_rate:
            proposals.append({"action": rng.choice(unauthorized), "source": "injection"})
        rng.shuffle(proposals)
        scenarios.append({
            "scenario_id": f"s{seed}_{i:05d}",
            "seed": seed,
            "task_type": task_name,
            "allowed_actions": allowed,
            "required_actions": required,
            "proposals": proposals,
        })
    return scenarios


def decide(policy: str, action: str, allowed_actions: Iterable[str],
           rng: random.Random, confirmation_accuracy: float = 0.95) -> Tuple[bool, bool]:
    """Return (accepted, reviewed). Review is simulated: a reviewer who is right with the given probability."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    authorized = action in set(allowed_actions)
    if policy == "unrestricted":
        return True, False
    if policy == "static_denylist":
        return action not in STATIC_DENYLIST, False
    if policy == "task_scoped_capability":
        return authorized, False
    # simulated_confirmation: only sensitive actions go to review.
    if not ACTIONS[action]["sensitive"]:
        return True, False
    correct = rng.random() < confirmation_accuracy
    return (authorized if correct else not authorized), True


def evaluate_policy(scenarios: List[Dict[str, Any]], policy: str,
                    confirmation_accuracy: float = 0.95, decision_seed: int = 9001) -> Dict[str, float]:
    """Evaluate one policy. confirmation_accuracy controls simulated human accuracy."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    if not 0.5 <= confirmation_accuracy <= 1.0:
        raise ValueError("confirmation_accuracy must be between 0.5 and 1.0")
    rng = random.Random(decision_seed)
    scenario_total = len(scenarios)
    action_attempts = unauthorized_attempts = unauthorized_accepted = 0
    attack_attempts = attack_accepted = 0
    authorized_attempts = authorized_rejected = 0
    human_reviews = 0
    completed = 0
    for scenario in scenarios:
        accepted_required = set()
        for proposal in scenario["proposals"]:
            action = proposal["action"]
            source = proposal["source"]
            authorized = action in scenario["allowed_actions"]
            accepted, reviewed = decide(policy, action, scenario["allowed_actions"], rng, confirmation_accuracy)
            action_attempts += 1
            human_reviews += int(reviewed)
            if authorized:
                authorized_attempts += 1
                if not accepted:
                    authorized_rejected += 1
            else:
                unauthorized_attempts += 1
                if accepted:
                    unauthorized_accepted += 1
            if source == "injection":
                attack_attempts += 1
                if accepted:
                    attack_accepted += 1
            if accepted and action in scenario["required_actions"]:
                accepted_required.add(action)
        if all(action in accepted_required for action in scenario["required_actions"]):
            completed += 1
    def ratio(a: float, b: float) -> float:
        return a / b if b else 0.0
    return {
        "scenarios": float(scenario_total),
        "action_attempts": float(action_attempts),
        "unauthorized_attempts": float(unauthorized_attempts),
        "unauthorized_accepted": float(unauthorized_accepted),
        "unauthorized_action_acceptance_rate": ratio(unauthorized_accepted, unauthorized_attempts),
        "attack_attempts": float(attack_attempts),
        "attack_accepted": float(attack_accepted),
        "attack_success_rate": ratio(attack_accepted, attack_attempts),
        "authorized_attempts": float(authorized_attempts),
        "authorized_rejected": float(authorized_rejected),
        "authorized_action_block_rate": ratio(authorized_rejected, authorized_attempts),
        "task_completion_rate": ratio(completed, scenario_total),
        "human_reviews": float(human_reviews),
        "review_rate": ratio(human_reviews, action_attempts),
    }


def write_scenarios_csv(scenarios: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["scenario_id", "seed", "task_type", "allowed_actions", "required_actions", "proposals"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in scenarios:
            row = dict(s)
            for key in ("allowed_actions", "required_actions", "proposals"):
                row[key] = json.dumps(row[key], separators=(",", ":"), sort_keys=True)
            writer.writerow(row)


def read_scenarios_csv(path: Path) -> List[Dict[str, Any]]:
    scenarios = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["seed"] = int(row["seed"])
            for key in ("allowed_actions", "required_actions", "proposals"):
                row[key] = json.loads(row[key])
            scenarios.append(row)
    return scenarios
