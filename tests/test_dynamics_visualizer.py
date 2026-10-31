from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from PIL import Image
from sim.global_config import GlobalSimulationConfig
from sim.global_data import load_world
from sim.global_engine import run_paired_global
from sim.dynamics_visualizer import render_dynamics_frame, create_simulation_gif, generate_gif_from_results

def test_dynamics_visualizer_and_gif():
    world, _ = load_world(Path(__file__).resolve().parents[1] / "data", 10)
    cfg = GlobalSimulationConfig(years=2, representative_agents=50)
    
    cb_calls = []
    def on_step(yr, total_yrs, bau_res, em_ann, em_mon, em_spp):
        cb_calls.append(yr)
        
    res = run_paired_global(cfg, world, 50, step_callback=on_step)
    
    # Assert callback was invoked for both years
    assert len(cb_calls) == 2, f"Expected 2 callback calls for 2 years, got {len(cb_calls)}"
    assert cb_calls == [1, 2]
    
    # Test frame rendering
    frame = render_dynamics_frame(
        year=1,
        total_years=2,
        bau_annual=res["BAU"].annual,
        em_annual=res["EM"].annual,
        bau_species=res["BAU"].species_annual,
        em_species=res["EM"].species_annual,
        cfg=cfg
    )
    assert isinstance(frame, Image.Image)
    assert frame.size[0] > 0 and frame.size[1] > 0
    
    # Test GIF creation in temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_gif = Path(tmp_dir) / "test_sim.gif"
        out = generate_gif_from_results(res["BAU"], res["EM"], cfg, tmp_gif)
        assert out.exists()
        assert out.stat().st_size > 50000  # Should be a multi-frame GIF of substantial size
