import pandas as pd
import streamlit as st

from frontend.api_client import api_client


def render_sustainability_tab(token: str, user: dict, organization_id: int | None = None):
    st.subheader("🌱 Sustainability & Circular Economy Impact")
    st.caption("Live tracking of positive circular steps, avoided manufacturing emissions, e-waste diversion, and green fleet logistics.")

    # Top Status Badges
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown("🏅 **ISO 14040/44 LCA Certified**")
    with b2:
        st.markdown("🛡️ **NIST 800-88 Zero-Waste Wipes**")
    with b3:
        st.markdown("♻️ **100% Zero-Landfill Policy**")
    with b4:
        st.markdown("⚡ **Green EV Logistics Priority**")

    st.markdown("---")

    # Fetch aggregated sustainability data from backend API
    try:
        summary = api_client.get_sustainability_summary(token, organization_id=organization_id)
    except Exception as e:
        st.error(f"Failed to fetch sustainability summary: {e}")
        return

    # 1. Headline Impact Metrics
    st.markdown("#### 🌍 Headline Environmental Savings")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(
            "Net Avoided Carbon Emissions",
            f"{summary['total_co2_saved_kg']:.1f} kg CO₂e",
            help="Emissions avoided by preventing brand-new replacement device manufacturing."
        )
    with m_col2:
        st.metric(
            "E-Waste Diverted from Landfills",
            f"{summary['total_ewaste_diverted_kg']:.2f} kg",
            help="100% of product mass kept out of toxic municipal e-waste dumps."
        )
    with m_col3:
        st.metric(
            "Critical Minerals Conserved",
            f"{summary['total_minerals_saved_grams']:.1f} grams",
            help="Precious and rare earth minerals (Cobalt, Lithium, Gold, Copper) saved from virgin open-pit mining."
        )

    m_col4, m_col5, m_col6 = st.columns(3)
    with m_col4:
        st.metric(
            "Circular Recovery Rate",
            f"{summary['circular_rate_pct']:.1f}%",
            help="Proportion of customer returns routed into life extension, refurbishment, or recycling."
        )
    with m_col5:
        st.metric(
            "Zero-Emission Fleet Pickups",
            f"{summary['green_fleet_pickups']} shipments",
            help="Doorstep pickups handled by Electric Vans or CNG cargo vehicles."
        )
    with m_col6:
        st.metric(
            "Certified Data Sanitizations",
            f"{summary['data_sanitized_count']} devices",
            help="Devices verified with NIST SP 800-88 cryptographic sanitization to prevent privacy-related discarding."
        )

    st.markdown("---")

    # 2. Tangible Environmental Equivalencies
    st.markdown("#### 🌳 Real-World Environmental Equivalencies")
    st.write("Translating avoided manufacturing carbon emissions into tangible everyday metrics:")

    eq_col1, eq_col2, eq_col3 = st.columns(3)
    with eq_col1:
        st.info(
            f"### 🌲 {summary['trees_equivalent']:.1f} Trees\n\n"
            "**Annual Carbon Absorption Equivalent**\n\n"
            "Equal to the net carbon sequestered by mature trees growing for an entire full year."
        )
    with eq_col2:
        st.success(
            f"### 🚗 {summary['km_avoided']:,.1f} km\n\n"
            "**Passenger Vehicle Driving Avoided**\n\n"
            "Gasoline emissions eliminated compared to driving an average passenger combustion car."
        )
    with eq_col3:
        st.warning(
            f"### 🔋 {summary['phone_charges_thousand']:.1f}k Recharges\n\n"
            "**Smartphone Full Cycle Energy**\n\n"
            "Equivalent energy saved compared to powering thousands of full smartphone battery recharges."
        )

    st.markdown("---")

    # 3. Circular Strategies & Positive Steps Pillars
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("#### 🔄 Circular Recovery Distribution")
        strategy_counts = summary.get("strategy_counts", {})
        strat_df = pd.DataFrame([
            {"Strategy": "🔄 Refurbish & Restore", "Cases": strategy_counts.get("REFURBISH", 0), "Circularity": "High (Life Extension)"},
            {"Strategy": "🛠️ Component Repair", "Cases": strategy_counts.get("REPAIR", 0), "Circularity": "High (Repair)"},
            {"Strategy": "📦 Certified Resale As-Is", "Cases": strategy_counts.get("RESALE_AS_IS", 0), "Circularity": "Direct Reuse"},
            {"Strategy": "♻️ Material Recycling", "Cases": strategy_counts.get("RECYCLE", 0), "Circularity": "Material Recovery"},
            {"Strategy": "↩️ Custody Reverted", "Cases": strategy_counts.get("RETURN_TO_RETAILER", 0), "Circularity": "Reverted"}
        ])
        st.dataframe(strat_df, width="stretch", hide_index=True)

        st.markdown("##### 📦 Category Carbon Savings")
        cat_breakdown = summary.get("category_breakdown", [])
        if cat_breakdown:
            cat_df = pd.DataFrame([
                {
                    "Category": c["category"],
                    "Processed Units": c["count"],
                    "CO₂ Saved": f"{c['co2_saved_kg']:.1f} kg",
                    "E-Waste Diverted": f"{c['ewaste_diverted_kg']:.2f} kg"
                }
                for c in cat_breakdown
            ])
            st.dataframe(cat_df, width="stretch", hide_index=True)

    with c_right:
        st.markdown("#### 🏆 Positive Steps Towards Sustainability")

        with st.expander("🛡️ 1. Mandatory NIST 800-88 Data Sanitization", expanded=True):
            st.write(
                "Many consumer electronics are prematurely shredded or dumped in landfills due to fears of personal data leakage. "
                "Our platform requires certified NIST SP 800-88 Rev 1 cryptographic erasure before any device can be restocked, "
                "completely eliminating privacy risk and unlocking 100% circular device reuse."
            )

        with st.expander("⭐ 2. Best-Condition First Policy", expanded=True):
            st.write(
                "Our automated decision engine prioritizes certified refurbishment over raw material recycling whenever positive Net Recovery Value (NRV) "
                "can be achieved. Refurbishment preserves 95%+ of the original embodied carbon in the product, whereas recycling only recovers raw scrap."
            )

        with st.expander("🚚 3. Zero-Emission Green Logistics Fleet", expanded=True):
            st.write(
                "Field doorstep collections are routed through zero-emission electric cargo vans (EcoLogix Express) and CNG hybrid vehicles (GreenRoute 3PL). "
                "The public tasks marketplace empowers electric vehicle drivers to consolidate nearby reverse pickups with zero tailpipe emissions."
            )

        with st.expander("📦 4. 100% Biodegradable & Recycled Eco-Packaging", expanded=True):
            st.write(
                "All restocked and serviced items are packaged in unbleached post-consumer corrugated cardboard with water-activated paper tape, "
                "completely phasing out single-use plastics and petroleum-derived bubble wrap."
            )

    st.markdown("---")

    # 4. Returns Sustainability Ledger
    st.markdown("#### 📋 Returns Circularity & Environmental Ledger")
    st.caption("Case-by-case audit ledger detailing avoided manufacturing emissions and material diversion.")

    ledger = summary.get("ledger", [])
    if ledger:
        ledger_df = pd.DataFrame([
            {
                "Return ID": row["return_id"],
                "Order Ref": row["order_ref"],
                "Product Model": row["product_name"],
                "Category": row["category"],
                "Workflow Status": row["status"],
                "Circular Strategy": row["circular_strategy"],
                "CO₂ Saved (kg)": f"{row['co2_saved_kg']:.1f}",
                "E-Waste Diverted (kg)": f"{row['ewaste_diverted_kg']:.2f}",
                "Minerals Saved (g)": f"{row['minerals_saved_g']:.1f}",
                "Logistics Fleet": row["fleet_transit"],
                "Data Sanitization": row["data_sanitization"]
            }
            for row in ledger
        ])
        st.dataframe(ledger_df, width="stretch", hide_index=True)
    else:
        st.info("No returns logged yet in the sustainability ledger.")

    st.markdown("---")

    # 5. Scientific LCA Methodology
    with st.expander("🔬 Transparent ISO 14040/44 LCA Methodology & Environmental Assumptions"):
        st.markdown(
            r"""
            ##### ISO 14040/44 Life Cycle Assessment (LCA) Methodology

            Our carbon calculation framework conforms to **ISO 14040:2006** and **ISO 14044:2006** standards for environmental Life Cycle Assessments.

            $$\text{Net Avoided Emissions} = \text{Embodied Manufacturing Footprint} - (\text{Reprocessing Footprint} + \text{Logistics Transport Footprint})$$

            - **Displacement Credit**: Extending product lifespan by 1-3 years displaces the need to manufacture a brand-new replacement device from virgin ore.
            - **Baseline Manufacturing Footprint**:
              - *Smartphones*: **70.0 kg CO₂e** (Source: Apple, Fairphone, and Dell Product Carbon Footprint reports)
              - *Laptops*: **280.0 kg CO₂e**
              - *Smartwatches*: **35.0 kg CO₂e**
              - *Headphones*: **25.0 kg CO₂e**
            - **Reprocessing Overhead**: Average technical refurbishing and diagnostic testing emits less than **2%** of virgin manufacturing footprint (1.5 kg CO₂e for smartphones).
            - **E-Waste Management Rules**: Adheres to e-waste and RoHS regulations, preventing heavy metals (Lead, Cadmium, Mercury) from leaching into municipal groundwater.
            """
        )
