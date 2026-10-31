"""
First-to-Last Mile Supply Chain & Traceability Engine.

Models the complete seafood value chain:
  First Mile: At-Sea Harvest -> Edge EM AI & Sensor Loggers -> Satellite Telemetry -> Dock Landing
  Middle Mile: Port State Measures (PSMA) Clearance -> Cold Chain IoT -> Cannery/Loining Mass Balance
  Last Mile: GDST 1.2 Digital Twin -> US SIMP / EU CATCH Clearance -> Retail Premium -> Consumer QR
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any
import numpy as np
import pandas as pd


@dataclass
class CompetitorProfile:
    name: str
    stage: str  # "First Mile", "Middle Mile", "Last Mile", "Cross-Chain"
    headquarters: str
    flagship_products: List[str]
    technology_stack: str
    target_segments: str
    gdst_compliance: str
    strengths: str
    relationship_to_our_platform: str


COMPETITOR_DATABASE: List[CompetitorProfile] = [
    CompetitorProfile(
        name="Satlink",
        stage="First Mile",
        headquarters="Madrid, Spain",
        flagship_products=["SeaTube EM", "Horus AI Platform", "Smart Satellite FAD Buoys"],
        technology_stack="Rugged high-definition marine CCTV, edge neural networks (face-blurring, species counting), satellite transceiver (Inmarsat/Iridium)",
        target_segments="Industrial tropical tuna purse seiners and longliners; RFMO compliance (ICCAT, IOTC, WCPFC)",
        gdst_compliance="Exportable CSV/API; partial EPCIS alignment via third-party integrations",
        strengths="Dominant market share in Atlantic and Indian Ocean tuna fleets; integrated buoy ecosystem",
        relationship_to_our_platform="Direct competitor in vessel-level EM edge hardware and AI catch accounting; our platform adds coupled bio-economic predictive dynamics and dynamic MPA feedback which Satlink lacks."
    ),
    CompetitorProfile(
        name="Marine Instruments",
        stage="First Mile",
        headquarters="Pontevedra, Spain",
        flagship_products=["MarineView EM", "M3i+ Echo-sounder Buoys", "Tunadrone"],
        technology_stack="Satellite-linked acoustic buoys, onboard CCTV, hydraulic sensors, aerial reconnaissance drones",
        target_segments="Tuna purse seine and longline fleets across Spanish, French, and Pacific operators",
        gdst_compliance="Proprietary data format with REST API connectors to regional logbooks",
        strengths="Unrivaled acoustic echo-sounder biomass estimation under FADs; rugged maritime engineering",
        relationship_to_our_platform="Hardware and telemetry competitor in First Mile; our simulation models the fleet-wide macroeconomic and spatial stock impact of such acoustic & camera technologies."
    ),
    CompetitorProfile(
        name="Archipelago Marine Research",
        stage="First Mile",
        headquarters="Victoria, BC, Canada",
        flagship_products=["FishVue Vantage EM", "FishVue Mobile e-Log", "Center for Marine Observer Services"],
        technology_stack="Rugged marine camera housings, rotation/pressure deck gear sensors, proprietary forensic review software",
        target_segments="North American demersal and pelagic fisheries (NOAA West Coast, Alaska, New England groundfish)",
        gdst_compliance="Aligned with NOAA Catch Accounting standards and emerging GDST pilot feeds",
        strengths="Over 35 years of fisheries monitoring experience; gold standard in regulatory compliance certifications",
        relationship_to_our_platform="Benchmark for regulatory-grade EM audit integrity; our platform extends Archipelago's vessel-centric model into last-mile retail premium and consumer provenance."
    ),
    CompetitorProfile(
        name="Saltwater Inc.",
        stage="First Mile",
        headquarters="Anchorage, AK, USA",
        flagship_products=["Saltwater EM Systems", "On-Deck Review AI", "Observer Deployment"],
        technology_stack="Custom edge compute units, multi-camera arrays, automated review pipelines",
        target_segments="Alaskan groundfish, Gulf of Mexico reef fish, Pacific highly migratory species",
        gdst_compliance="Compliant with NOAA National EM Policy Directive",
        strengths="Strong US federal government contract footprint; human-in-the-loop audit verification",
        relationship_to_our_platform="First-mile service peer; our simulation provides the overarching predictive framework that justifies investments in Saltwater-style monitoring."
    ),
    CompetitorProfile(
        name="ThisFish",
        stage="Middle Mile",
        headquarters="Vancouver, BC, Canada",
        flagship_products=["Tally-ERP", "Tally Process", "Tally Cold Storage"],
        technology_stack="Tablet-based factory floor UI, IoT scales, RFID lot tags, cloud mass-balance reconciliation algorithms",
        target_segments="Seafood processing plants, canneries, loining facilities, primary distributors globally (SE Asia, Latin America)",
        gdst_compliance="Fully GDST 1.2 compliant (Critical Tracking Events for Processing, Transformation, Aggregation)",
        strengths="Leading digitization of factory-floor yield loss, mass-balance fraud prevention, and worker productivity",
        relationship_to_our_platform="Complementary upstream/downstream partner. Our platform hands off vessel catch & compliance hashes to ThisFish Tally-ERP at the port dock for cannery processing."
    ),
    CompetitorProfile(
        name="BlueTrace",
        stage="Middle Mile",
        headquarters="Castine, ME, USA",
        flagship_products=["BlueTrace Tagging App", "Distributor Hub", "Logbook Mobile"],
        technology_stack="iOS/Android mobile apps, rugged thermal Bluetooth label printers, QR/2D barcode scanners",
        target_segments="Shellfish growers, coastal artisanal harvesters, local seafood dealers, primary wholesalers",
        gdst_compliance="GDST aligned for shellfish harvest and dealer receipt KDEs",
        strengths="Frictionless mobile usability for non-technical dockside dealers; fast tagging compliance",
        relationship_to_our_platform="Informs our small-coastal fleet (Class 0/1) landing workflow; models how digital tagging accelerates dockside clearance."
    ),
    CompetitorProfile(
        name="Trace Register",
        stage="Last Mile",
        headquarters="Seattle, WA, USA",
        flagship_products=["TR5 Digital Traceability Platform", "Continuous Data Validation Engine"],
        technology_stack="Enterprise cloud platform, rule-based algorithmic data verification, GS1 EPCIS data repository",
        target_segments="Tier-1 retail supermarket chains (e.g., Walmart, Whole Foods), global seafood importers, brand owners",
        gdst_compliance="Certified GDST 1.2 Pioneer; native EPCIS 1.2/2.0 data exchange",
        strengths="Largest enterprise market footprint; automated validation rules that reject non-compliant supplier lots",
        relationship_to_our_platform="Downstream recipient of our EM verification data. Our simulation models the retail price premium and import clearance speed enabled by TR5 integration."
    ),
    CompetitorProfile(
        name="Wholechain",
        stage="Last Mile",
        headquarters="Washington, DC, USA",
        flagship_products=["Wholechain Traceability Platform", "GS1/GDST Mobile Verifier"],
        technology_stack="Enterprise blockchain ledger, GS1 EPCIS standard, mobile QR scanning, FDA FSMA 204 validation",
        target_segments="Global consumer packaged seafood brands, tuna supply chains, retail brands committed to zero-IUU",
        gdst_compliance="GDST 1.2 Founding Solution Provider; seamless cross-platform interoperability",
        strengths="Native mobile-to-cloud blockchain provenance, verified consumer QR storytelling, multi-tier supply chain mapping",
        relationship_to_our_platform="Our First-to-Last-Mile simulation models the end-to-end economic dividends realized when our EM data streams into Wholechain digital twins."
    ),
    CompetitorProfile(
        name="OceanMind & Global Fishing Watch",
        stage="Cross-Chain",
        headquarters="Oxford, UK / Washington, DC, USA",
        flagship_products=["OceanMind Intelligence", "GFW Map", "PSMA Risk Profiler"],
        technology_stack="Satellite AIS, SAR (Synthetic Aperture Radar), VIIRS optical nighttime lights, machine learning vessel behavior classification",
        target_segments="Port authorities, coastal state fisheries agencies, FAO Port State Measures Agreement (PSMA) inspectors",
        gdst_compliance="Supplies external verification layers for GDST harvest CTEs",
        strengths="Unrivaled independent satellite surveillance and global vessel transparency",
        relationship_to_our_platform="Validates our Port State Measures Agreement (PSMA) risk model, where vessels with verified EM receive green-channel clearance and unmonitored vessels face customs scrutiny."
    ),
]


def compute_supply_chain_metrics(bau_result: Any, em_result: Any, cfg: Any) -> Dict[str, Any]:
    """
    Computes comparative First-to-Last Mile supply chain metrics across 15-year simulation.
    """
    # 15-year cumulative totals
    bau_catch = float(bau_result.annual["catch_tonnes"].sum())
    em_catch = float(em_result.annual["catch_tonnes"].sum())

    bau_landed_val = float(bau_result.annual["landed_value"].sum())
    em_landed_val = float(em_result.annual["landed_value"].sum())

    em_adoption_realized = float(em_result.meta.get("realized_em_share", 0.75))

    # --- FIRST MILE: At-Sea Harvest & Edge Telemetry ---
    # Data fidelity: unmonitored paper logbooks have ~28% missing/erroneous KDEs; EM edge verification provides 98.8%
    bau_data_fidelity = 0.715
    em_data_fidelity = 0.715 * (1.0 - em_adoption_realized) + 0.988 * em_adoption_realized

    # Telemetry volume generated at sea (GB over 15 years)
    # Class 2 & 3 vessels upload ~35 MB/day of compressed event bursts and sensor telemetry via Starlink/Iridium
    bau_telemetry_gb = float(bau_catch * 0.002)  # minimal manual radio/logbook transmissions
    em_telemetry_gb = float(em_catch * 0.045 * em_adoption_realized + bau_catch * 0.002 * (1 - em_adoption_realized))

    # --- MIDDLE MILE: Port Landing, PSMA Inspection & Processing ---
    # FAO PSMA (Port State Measures Agreement) port clearance delay
    # BAU unverified vessels face customs risk audits: ~72-96 hours demurrage/quarantine
    # EM pre-verified digital vessels receive green-channel clearance: ~6-12 hours
    bau_avg_port_delay_hours = 78.0
    em_avg_port_delay_hours = 78.0 * (1.0 - em_adoption_realized) + 8.5 * em_adoption_realized
    port_hours_saved_per_trip = (78.0 - em_avg_port_delay_hours)

    # Demurrage cost savings ($1,200/day = $50/hour per large vessel)
    estimated_trips = em_catch / 45.0  # ~45 tonnes per trip average
    demurrage_savings_billion = float((port_hours_saved_per_trip * 50.0 * estimated_trips) / 1e9)

    # Cold chain spoilage & degradation:
    # Unmonitored catch suffers 4.5% quality downgrade (from sashimi/fresh loin to canned flake/pet food)
    # IoT-monitored unbroken cold chain reduces downgrade to 0.75%
    bau_spoilage_rate = 0.045
    em_spoilage_rate = 0.045 * (1.0 - em_adoption_realized) + 0.0075 * em_adoption_realized
    spoilage_avoided_tonnes = float(em_catch * (bau_spoilage_rate - em_spoilage_rate))
    spoilage_avoided_value_billion = float(spoilage_avoided_tonnes * 4200.0 / 1e9)

    # Processing yield (Raw round tuna to loins, steaks, canned chunks)
    # Average yield: 44% prime loins, 13% canning chunks, 27% fishmeal/oil by-product, 16% moisture/loss
    bau_prime_loins_tonnes = float(bau_catch * 0.44)
    em_prime_loins_tonnes = float(em_catch * 0.44)

    # --- LAST MILE: GDST 1.2 Digital Twin, Market Clearance & Retail Premium ---
    # GDST 1.2 Full-Chain Compliance Score (%)
    bau_gdst_score = 22.5
    em_gdst_score = 22.5 * (1.0 - em_adoption_realized) + 93.5 * em_adoption_realized

    # Trade regulatory clearance pass rate (US SIMP & EU IUU CATCH portal)
    bau_regulatory_pass_rate = 81.5
    em_regulatory_pass_rate = 81.5 * (1.0 - em_adoption_realized) + 99.4 * em_adoption_realized

    # Seafood fraud & mislabelling elimination
    # Global benchmark: ~19.5% unverified tuna is mislabelled or laundered
    # Full GDST + EM traceability reduces fraud to < 1.2%
    bau_fraud_rate = 19.5
    em_fraud_rate = 19.5 * (1.0 - em_adoption_realized) + 1.1 * em_adoption_realized

    # Retail / Food Service Traceability Premium:
    # Verified legal, zero-IUU, dolphin-safe tuna captures +14.5% wholesale/retail premium
    retail_premium_pct = 14.5
    bau_traceable_volume = bau_catch * (bau_gdst_score / 100.0)
    em_traceable_volume = em_catch * (em_gdst_score / 100.0)

    # Additional retail premium captured ($B)
    bau_retail_premium_val = float(bau_traceable_volume * 4500.0 * (retail_premium_pct / 100.0) / 1e9)
    em_retail_premium_val = float(em_traceable_volume * 4500.0 * (retail_premium_pct / 100.0) / 1e9)
    net_retail_premium_dividend_billion = em_retail_premium_val - bau_retail_premium_val

    # --- SCOPE 3 CARBON ACCOUNTING (Sea to Shelf) ---
    # Fuel at sea: 0.95 L/kg catch = 2.45 kg CO2e / kg
    # Reefer ocean shipping: 0.32 kg CO2e / kg
    # Retail distribution: 0.18 kg CO2e / kg
    # Total baseline footprint: 2.95 kg CO2e / kg finished tuna
    # Optimized fleet logistics (reduced illegal steaming + fast port turnaround) reduces footprint by ~11%
    bau_carbon_intensity_kg_co2_per_kg = 2.95
    em_carbon_intensity_kg_co2_per_kg = 2.62
    total_co2_saved_million_tonnes = float((bau_carbon_intensity_kg_co2_per_kg - em_carbon_intensity_kg_co2_per_kg) * em_catch / 1000.0)

    # Summary table
    comparison_df = pd.DataFrame([
        {"Supply Chain Dimension": "1. First Mile: Catch Data Fidelity", "BAU Legacy": f"{bau_data_fidelity*100:.1f}%", "EM Connected": f"{em_data_fidelity*100:.1f}%", "Impact / Benefit": f"+{(em_data_fidelity-bau_data_fidelity)*100:.1f}% verifiable catch events"},
        {"Supply Chain Dimension": "1. First Mile: Satellite Telemetry Volume", "BAU Legacy": f"{bau_telemetry_gb:,.0f} GB", "EM Connected": f"{em_telemetry_gb:,.0f} GB", "Impact / Benefit": "Real-time edge camera bursts & sensor telemetry"},
        {"Supply Chain Dimension": "2. Middle Mile: Port PSMA Customs Delay", "BAU Legacy": f"{bau_avg_port_delay_hours:.1f} hrs (3.3 days)", "EM Connected": f"{em_avg_port_delay_hours:.1f} hrs (0.9 days)", "Impact / Benefit": f"-{port_hours_saved_per_trip:.1f} hrs green-channel clearance"},
        {"Supply Chain Dimension": "2. Middle Mile: Port Demurrage Savings", "BAU Legacy": "$0.00 B (baseline)", "EM Connected": f"${demurrage_savings_billion:.2f} B", "Impact / Benefit": "Drastic reduction in idle dockside hold costs"},
        {"Supply Chain Dimension": "2. Middle Mile: Cold Chain Spoilage Loss", "BAU Legacy": f"{bau_spoilage_rate*100:.1f}% ({bau_catch*bau_spoilage_rate:,.0f} t)", "EM Connected": f"{em_spoilage_rate*100:.1f}% ({em_catch*em_spoilage_rate:,.0f} t)", "Impact / Benefit": f"{spoilage_avoided_tonnes:,.0f} tonnes saved (${spoilage_avoided_value_billion:.2f} B)"},
        {"Supply Chain Dimension": "2. Middle Mile: Prime Loins & Steaks Yield", "BAU Legacy": f"{bau_prime_loins_tonnes:,.0f} t", "EM Connected": f"{em_prime_loins_tonnes:,.0f} t", "Impact / Benefit": f"+{em_prime_loins_tonnes-bau_prime_loins_tonnes:,.0f} t mass-balance reconciled"},
        {"Supply Chain Dimension": "3. Last Mile: GDST 1.2 Digital Twin Score", "BAU Legacy": f"{bau_gdst_score:.1f}%", "EM Connected": f"{em_gdst_score:.1f}%", "Impact / Benefit": f"+{em_gdst_score-bau_gdst_score:.1f}% full chain-of-custody compliance"},
        {"Supply Chain Dimension": "3. Last Mile: US SIMP / EU CATCH Pass Rate", "BAU Legacy": f"{bau_regulatory_pass_rate:.1f}%", "EM Connected": f"{em_regulatory_pass_rate:.1f}%", "Impact / Benefit": "Zero detention risk at EU/US import borders"},
        {"Supply Chain Dimension": "3. Last Mile: Seafood Fraud & Mislabelling", "BAU Legacy": f"{bau_fraud_rate:.1f}% (high risk)", "EM Connected": f"{em_fraud_rate:.1f}% (near zero)", "Impact / Benefit": f"-{bau_fraud_rate-em_fraud_rate:.1f}% elimination of fish laundering"},
        {"Supply Chain Dimension": "3. Last Mile: Retail Price Premium Captured", "BAU Legacy": f"${bau_retail_premium_val:.2f} B", "EM Connected": f"${em_retail_premium_val:.2f} B", "Impact / Benefit": f"+${net_retail_premium_dividend_billion:.2f} B brand & retail margin dividend"},
        {"Supply Chain Dimension": "3. Last Mile: Scope 3 Carbon Intensity", "BAU Legacy": f"{bau_carbon_intensity_kg_co2_per_kg:.2f} kg CO2e/kg", "EM Connected": f"{em_carbon_intensity_kg_co2_per_kg:.2f} kg CO2e/kg", "Impact / Benefit": f"{total_co2_saved_million_tonnes:.2f}M t CO2e avoided from sea to shelf"},
    ])

    return {
        "bau_catch": bau_catch,
        "em_catch": em_catch,
        "em_adoption": em_adoption_realized,
        "comparison_table": comparison_df,
        "metrics": {
            "first_mile_fidelity_gain": (em_data_fidelity - bau_data_fidelity) * 100,
            "port_delay_reduction_hours": port_hours_saved_per_trip,
            "demurrage_savings_billion": demurrage_savings_billion,
            "spoilage_avoided_tonnes": spoilage_avoided_tonnes,
            "spoilage_avoided_value_billion": spoilage_avoided_value_billion,
            "gdst_score_em": em_gdst_score,
            "gdst_score_gain": em_gdst_score - bau_gdst_score,
            "regulatory_pass_rate": em_regulatory_pass_rate,
            "fraud_reduction_pct": bau_fraud_rate - em_fraud_rate,
            "retail_premium_dividend_billion": net_retail_premium_dividend_billion,
            "co2_saved_million_tonnes": total_co2_saved_million_tonnes,
        }
    }


def generate_sample_gdst_record() -> Dict[str, Any]:
    """
    Generates an illustrative GDST 1.2 compliant Critical Tracking Event (CTE) record.
    """
    return {
        "standard": "GDST 1.2 / GS1 EPCIS 2.0",
        "blockchain_hash": "0x7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "critical_tracking_events": {
            "harvest_cte": {
                "event_time": "2026-10-14T06:42:18Z",
                "vessel_name": "F/V Pacific Vanguard",
                "imo_number": "IMO 9248102",
                "flag_state": "Marshall Islands (RMI)",
                "vessel_class": "Class 3: Distant-water freezer longliner",
                "coordinates": {"lat": 4.821, "lon": -86.915, "zone": "Eastern Tropical Pacific (Outside Cocos Sanctuary Buffer)"},
                "gear_type": "LL - Pelagic Longline with circle hooks & tori lines",
                "target_species": "Yellowfin tuna (Thunnus albacares - YFT)",
                "lot_weight_kg": 4250,
                "em_audit_hash": "SHA256:d59b207a4b8f... (Verified 0 shark-finning, 0 turtle bycatch, 100% tori line deployment)",
                "observer_mode": "Automated Edge AI EM Camera 4-channel continuous"
            },
            "transshipment_cte": {
                "event_time": "2026-10-18T14:10:00Z",
                "status": "Direct Landing (Zero At-Sea Transshipment — Low IUU Risk)"
            },
            "landing_cte": {
                "event_time": "2026-10-22T08:15:30Z",
                "port_name": "Port of Caldera, Costa Rica",
                "psma_inspection_status": "Green-Channel Cleared (< 4 hours) — FAO PSMA Protocol Passed",
                "landed_weight_kg": 4218,
                "cold_chain_temp_celsius": -58.4,
                "inspector_id": "CR-INCOPESCA-941"
            },
            "processing_cte": {
                "event_time": "2026-10-24T11:00:00Z",
                "facility": "Pacific Blue Seafood Processing Co.",
                "transformation_type": "Ultra-low temperature sashimi loining & nitrogen flash-freeze",
                "output_yield_loins_kg": 1856,
                "byproduct_meal_oil_kg": 1434,
                "mass_balance_ratio": 0.992,
                "msc_chain_of_custody_cert": "MSC-C-54910"
            },
            "distribution_and_retail_cte": {
                "event_time": "2026-10-28T09:30:00Z",
                "destination_market": "European Union / North America",
                "regulatory_clearance": "EU CATCH Declaration Approved #EU-2026-99214; US SIMP Verified",
                "retail_channel": "Premium Sushi & Fresh Fillet Case",
                "consumer_qr_code": "https://trace.ems-platform.org/verify/0x7f83b1657ff1",
                "retail_price_premium": "+16.5% vs. uncertified commodity",
                "scope_3_carbon_intensity": "2.58 kg CO2e / kg finished loin"
            }
        }
    }
