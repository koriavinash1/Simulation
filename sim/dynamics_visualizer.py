from __future__ import annotations
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

def render_dynamics_frame(
    year: int,
    total_years: int,
    bau_annual: pd.DataFrame,
    em_annual: pd.DataFrame,
    bau_species: Optional[pd.DataFrame] = None,
    em_species: Optional[pd.DataFrame] = None,
    cfg: Optional[Any] = None,
    width_in: float = 12.0,
    height_in: float = 7.5,
    dpi: int = 100,
) -> Image.Image:
    """
    Renders a multi-panel visual frame of the coupled dynamical systems trajectory
    up to `year`, returning a PIL Image.
    """
    plt.style.use("fast")
    fig, axes = plt.subplots(2, 2, figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor("#0F172A")  # Deep slate/navy background
    
    # Custom styling helper
    def style_ax(ax, title, xlabel, ylabel):
        ax.set_facecolor("#1E293B")
        ax.set_title(title, fontsize=11, fontweight="bold", color="#F8FAFC", pad=8)
        ax.set_xlabel(xlabel, fontsize=9, color="#94A3B8")
        ax.set_ylabel(ylabel, fontsize=9, color="#94A3B8")
        ax.tick_params(colors="#94A3B8", labelsize=8)
        ax.grid(True, linestyle="--", alpha=0.18, color="#CBD5E1")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.0)

    max_yr = max(total_years, 1)
    x_lim = (0.8, max_yr + 0.2)
    
    # Slice data up to current year
    b_df = bau_annual[bau_annual["year"] <= year] if not bau_annual.empty else pd.DataFrame()
    e_df = em_annual[em_annual["year"] <= year] if not em_annual.empty else pd.DataFrame()
    yrs_b = b_df["year"].values if "year" in b_df.columns else np.array([])
    yrs_e = e_df["year"].values if "year" in e_df.columns else np.array([])

    # Panel 1: Annual Landed Value ($M)
    ax1 = axes[0, 0]
    style_ax(ax1, "1. Annual Landed Value ($M / yr)", "Simulation Year", "Landed Value ($M)")
    ax1.set_xlim(x_lim)
    if len(yrs_b) > 0 and "landed_value" in b_df.columns:
        b_val = b_df["landed_value"].values / 1e6
        e_val = e_df["landed_value"].values / 1e6 if not e_df.empty else b_val
        ax1.plot(yrs_b, b_val, color="#EF4444", linewidth=2.2, label="BAU Baseline", marker="o", markersize=4)
        ax1.plot(yrs_e, e_val, color="#10B981", linewidth=2.5, label="EM Intervention", marker="o", markersize=4)
        ax1.fill_between(yrs_e, b_val, e_val, color="#10B981", alpha=0.15, label="Reform Premium")
        if len(e_val) > 0:
            diff = e_val[-1] - b_val[-1]
            ax1.annotate(
                f"+${diff:.1f}M/yr",
                (yrs_e[-1], e_val[-1]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                fontweight="bold",
                color="#34D399"
            )
    h1, l1 = ax1.get_legend_handles_labels()
    if l1:
        ax1.legend(loc="upper left", facecolor="#1E293B", edgecolor="#334155", labelcolor="#F8FAFC", fontsize=8)

    # Panel 2: Cumulative Fleet Operating Profit ($M) - The Bioeconomic J-Curve
    ax2 = axes[0, 1]
    style_ax(ax2, "2. Cumulative Fleet Operating Profit ($M)", "Simulation Year", "Cumulative Profit ($M)")
    ax2.set_xlim(x_lim)
    if len(yrs_b) > 0 and "fleet_profit" in b_df.columns:
        b_prof_cum = np.cumsum(b_df["fleet_profit"].values) / 1e6
        e_prof_cum = np.cumsum(e_df["fleet_profit"].values) / 1e6 if not e_df.empty else b_prof_cum
        ax2.plot(yrs_b, b_prof_cum, color="#F87171", linestyle="--", linewidth=2.0, label="BAU Cumulative")
        ax2.plot(yrs_e, e_prof_cum, color="#06B6D4", linewidth=2.5, label="EM Cumulative J-Curve")
        ax2.axhline(0, color="#64748B", linestyle=":", alpha=0.6)
        if len(e_prof_cum) > 0:
            p_diff = e_prof_cum[-1] - b_prof_cum[-1]
            ax2.annotate(
                f"+${p_diff:,.0f}M net",
                (yrs_e[-1], e_prof_cum[-1]),
                textcoords="offset points",
                xytext=(5, -8),
                fontsize=8,
                fontweight="bold",
                color="#38BDF8"
            )
    h2, l2 = ax2.get_legend_handles_labels()
    if l2:
        ax2.legend(loc="upper left", facecolor="#1E293B", edgecolor="#334155", labelcolor="#F8FAFC", fontsize=8)

    # Panel 3: Target Pelagic Stock Biomass ($B / K$)
    ax3 = axes[1, 0]
    style_ax(ax3, "3. Standing Target Biomass Ratio (Mean B / K)", "Simulation Year", "Stock Ratio (Virgin = 1.0)")
    ax3.set_xlim(x_lim)
    ax3.set_ylim(0.35, 1.05)
    ax3.axhline(0.80, color="#10B981", linestyle=":", alpha=0.5, label="Target Healthy Threshold (0.80)")
    ax3.axhline(0.50, color="#F59E0B", linestyle=":", alpha=0.5, label="Precautionary Limit (0.50)")
    if bau_species is not None and em_species is not None and not bau_species.empty and not em_species.empty:
        b_spp_yr = bau_species[bau_species["year"] <= year]
        e_spp_yr = em_species[em_species["year"] <= year]
        # Commercial tunas only
        comm_codes = ["YFT", "BET", "ALB"]
        colors_spp = {"YFT": "#38BDF8", "BET": "#A78BFA", "ALB": "#FBBF24"}
        for c in comm_codes:
            sub_b = b_spp_yr[b_spp_yr["code"] == c]
            sub_e = e_spp_yr[e_spp_yr["code"] == c]
            if not sub_e.empty:
                ax3.plot(sub_b["year"].values, sub_b["population_ratio"].values, linestyle="--", alpha=0.5, color=colors_spp.get(c, "#94A3B8"))
                ax3.plot(sub_e["year"].values, sub_e["population_ratio"].values, linewidth=2.0, color=colors_spp.get(c, "#94A3B8"), label=f"{c} (EM vs BAU)")
    h3, l3 = ax3.get_legend_handles_labels()
    if l3:
        ax3.legend(loc="lower left", facecolor="#1E293B", edgecolor="#334155", labelcolor="#F8FAFC", fontsize=7.5)

    # Panel 4: Poaching Incursions & Incidental Bycatch Events
    ax4 = axes[1, 1]
    style_ax(ax4, "4. Annual Poaching Incursions (Events / yr)", "Simulation Year", "Illegal Incursion Events")
    ax4.set_xlim(x_lim)
    if len(yrs_b) > 0 and "illegal_events" in b_df.columns:
        b_ilg = b_df["illegal_events"].values
        e_ilg = e_df["illegal_events"].values if not e_df.empty else b_ilg
        ax4.plot(yrs_b, b_ilg, color="#F43F5E", linewidth=2.2, label="BAU Poaching (Paper Parks)", marker="x", markersize=5)
        ax4.plot(yrs_e, e_ilg, color="#34D399", linewidth=2.5, label="EM Enforced Compliance", marker="o", markersize=4)
        if len(e_ilg) > 0:
            suppr = max(0.0, 100.0 * (b_ilg[-1] - e_ilg[-1]) / max(b_ilg[-1], 1))
            ax4.annotate(
                f"-{suppr:.1f}% incursions",
                (yrs_e[-1], e_ilg[-1]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                fontweight="bold",
                color="#34D399"
            )
    h4, l4 = ax4.get_legend_handles_labels()
    if l4:
        ax4.legend(loc="upper right", facecolor="#1E293B", edgecolor="#334155", labelcolor="#F8FAFC", fontsize=8)

    # Overall Header & Progress Banner
    pct = int(100.0 * min(year, max_yr) / max_yr)
    fig.suptitle(
        f"Coupled Dynamical Systems Digital Twin Trajectory — Year {min(year, max_yr)} of {max_yr} ({pct}% Horizon Complete)",
        fontsize=13,
        fontweight="bold",
        color="#F8FAFC",
        y=0.98
    )
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    
    # Save to PIL Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).copy()
    buf.close()
    return img

def create_simulation_gif(
    frames: List[Image.Image],
    output_path: Path,
    duration_ms: int = 350,
    loop: int = 0
) -> Path:
    """
    Compiles a sequence of PIL Images into an animated GIF.
    """
    if not frames:
        raise ValueError("No frames provided to create_simulation_gif")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save using Pillow
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True
    )
    return output_path

def generate_gif_from_results(
    bau_res: Any,
    em_res: Any,
    cfg: Any,
    output_path: Path,
    duration_ms: int = 350
) -> Path:
    """
    Post-hoc generation of the full animated GIF from completed simulation results.
    """
    total_years = cfg.years
    frames = []
    for yr in range(1, total_years + 1):
        b_spp = getattr(bau_res, "species_annual", getattr(bau_res, "species", None))
        e_spp = getattr(em_res, "species_annual", getattr(em_res, "species", None))
        frame_img = render_dynamics_frame(
            year=yr,
            total_years=total_years,
            bau_annual=bau_res.annual,
            em_annual=em_res.annual,
            bau_species=b_spp,
            em_species=e_spp,
            cfg=cfg,
            dpi=100
        )
        frames.append(frame_img)
    # Add a hold on the final frame (repeat final frame 3 times for visual clarity)
    if frames:
        frames.extend([frames[-1]] * 3)
    return create_simulation_gif(frames, output_path, duration_ms=duration_ms)
