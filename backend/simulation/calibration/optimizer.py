"""Bayesian optimization for simulation calibration.

Uses scikit-optimize (skopt) to find parameter values that minimize
weighted RMSE between simulation outputs and empirical targets.
"""

from typing import Callable, Optional

import numpy as np

from simulation.calibration.parameters import (
    PARAMETER_SPACE,
    get_bounds,
    get_default_point,
    get_param_names,
    vector_to_dict,
)
from simulation.calibration.targets import (
    CALIBRATION_TARGETS,
    get_target_dict,
    get_weight_dict,
)


def compute_weighted_rmse(
    sim_outputs: dict[str, float],
    targets: Optional[dict[str, float]] = None,
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Compute weighted RMSE between simulation outputs and calibration targets.

    Parameters
    ----------
    sim_outputs : dict
        Simulation-produced metric values keyed by target name.
    targets : dict, optional
        Target values. Defaults to CALIBRATION_TARGETS.
    weights : dict, optional
        Per-target weights. Defaults to calibration weights.

    Returns
    -------
    float
        Weighted root-mean-square error (normalized by target magnitude).
    """
    if targets is None:
        targets = get_target_dict()
    if weights is None:
        weights = get_weight_dict()

    squared_errors: list[float] = []
    total_weight: float = 0.0

    for name, target_val in targets.items():
        if name not in sim_outputs:
            continue
        sim_val: float = sim_outputs[name]
        w: float = weights.get(name, 1.0)

        # Normalized squared error
        if abs(target_val) > 1e-10:
            nse: float = ((sim_val - target_val) / target_val) ** 2
        else:
            nse = (sim_val - target_val) ** 2

        squared_errors.append(w * nse)
        total_weight += w

    if total_weight == 0:
        return float("inf")

    wmse: float = sum(squared_errors) / total_weight
    return float(np.sqrt(wmse))


def run_calibration(
    run_simulation_fn: Callable[[dict[str, float]], dict[str, float]],
    n_calls: int = 50,
    n_initial_points: int = 10,
    random_state: int = 42,
    verbose: bool = True,
) -> dict:
    """Run Bayesian optimization to calibrate simulation parameters.

    Parameters
    ----------
    run_simulation_fn : callable
        Function that takes a param dict and returns a dict of metric values
        matching calibration target names.
    n_calls : int
        Total number of function evaluations.
    n_initial_points : int
        Number of random initial evaluations before fitting surrogate.
    random_state : int
        RNG seed for reproducibility.
    verbose : bool
        Print progress.

    Returns
    -------
    dict
        Keys: "best_params" (dict), "best_rmse" (float), "result" (skopt result).
    """
    try:
        from skopt import gp_minimize
        from skopt.space import Real, Integer
    except ImportError:
        raise ImportError(
            "scikit-optimize is required for calibration. "
            "Install with: pip install scikit-optimize"
        )

    # Build search space
    dimensions = []
    for p in PARAMETER_SPACE:
        if p.name == "construction_lag_steps":
            dimensions.append(Integer(int(p.lower), int(p.upper), name=p.name))
        else:
            dimensions.append(Real(p.lower, p.upper, name=p.name))

    param_names: list[str] = get_param_names()

    def objective(x: list) -> float:
        param_dict: dict[str, float] = {
            name: val for name, val in zip(param_names, x)
        }
        try:
            sim_outputs: dict[str, float] = run_simulation_fn(param_dict)
            rmse: float = compute_weighted_rmse(sim_outputs)
        except Exception as e:
            if verbose:
                print(f"Simulation failed with params {param_dict}: {e}")
            rmse = 10.0  # penalty for failed runs
        if verbose:
            print(f"RMSE: {rmse:.4f}")
        return rmse

    result = gp_minimize(
        objective,
        dimensions,
        n_calls=n_calls,
        n_initial_points=n_initial_points,
        random_state=random_state,
        verbose=verbose,
        x0=get_default_point(),
    )

    best_params: dict[str, float] = vector_to_dict(result.x)

    return {
        "best_params": best_params,
        "best_rmse": float(result.fun),
        "result": result,
    }
