"""Small command-line smoke runner for environments without Streamlit."""
from sim.config import SimulationConfig
from sim.data_adapter import demo_empirical_priors
from sim.engine import run_paired_monte_carlo

if __name__ == "__main__":
    cfg = SimulationConfig(years=5, replications=5, representative_agents=500, adoption_pct=50)
    result = run_paired_monte_carlo(cfg, demo_empirical_priors(cfg.n_regions))
    print("Summary")
    for k, v in result.summary.items():
        print(f"{k}: {v}")
