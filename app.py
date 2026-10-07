import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="Czech Collective Redress Simulator: Viability under ZHŘS",
    layout="wide",
    initial_sidebar_state="expanded"
)

MIN_MEMBERS = 10      # ZHŘS: proceedings stop if fewer than 10 members opt in
STATUTORY_CAP = 0.16  # ZHŘS §65: maximum fee as % of the award

st.title("Czech Collective Redress Simulator: Viability under ZHŘS")
st.markdown("""
Models when a Czech representative action (Act No. 179/2024 Coll., transposing Directive (EU) 2020/1828) is economically viable
for a qualified entity (NGO), given a statutory fee cap, opt-in enrolment and loser-pays costs.
**Tab 1** shows the minimum claim value per member by group size. **Tab 2** stress-tests a specific case.
""")

st.caption("Illustrative model for analysis; not legal or financial advice.")

with st.expander("Assumptions"):
    st.markdown(
        """
- A win means full recovery of C per member; the fee is a percentage of the award (§65 ZHŘS). The fixed-sum alternative is not modeled.
- The fee pool is the only revenue source. It is shared between the NGO and counsel by β, and in funded mode the funder is repaid first.
- Self-financed: the NGO bears all upfront costs and adverse costs. Funded: the funder bears them and is repaid only from the fee.
- Adverse costs are a flat amount, independent of group size. Cost recovery on a win is excluded (conservative).
- v is the cost per *opted-in* member and does not rise when take-up is low. The opt-in group size (N) is an input, not a forecast.
- β, the cost parameters and the case presets are illustrative assumptions, not statutory values or empirical data.
"""
    )

# --- SIDEBAR: FINANCING STRUCTURE & COSTS ---
st.sidebar.header("1. Financing Structure")

funding_mode = st.sidebar.radio(
    "Who funds the case?",
    ["Self-financed by the NGO", "Third-party funded (funder repaid first)"],
    index=0,
    help="Self-financed: the NGO carries upfront costs and adverse-cost risk. Third-party funded: an external funder carries them and is repaid first from the fee."
)

is_tplf = (funding_mode == "Third-party funded (funder repaid first)")

if is_tplf:
    funder_multiple = st.sidebar.slider(
        "Funder Return Hurdle (M, × invested capital)",
        min_value=1.0, max_value=4.0, value=2.5, step=0.25,
        help="Multiple of invested capital the funder must receive from the fee on a win, before the NGO and counsel are paid anything."
    )
else:
    funder_multiple = 1.0

st.sidebar.header("2. Regulatory & Operational Costs")

alpha = st.sidebar.slider(
    "Contingency Fee Rate (α)",
    min_value=0.05, max_value=0.30, value=STATUTORY_CAP, step=0.01,
    help="Fee as % of the award. ZHŘS cap: 16% (§65). Values above 16% are a counterfactual (e.g. US-style fees)."
)
if alpha > STATUTORY_CAP + 1e-9:
    st.sidebar.caption("⚠ Above the Czech statutory cap: de lege ferenda modeling.")

beta = st.sidebar.slider(
    "NGO Fee Retention Share (β)",
    min_value=0.10, max_value=1.00, value=0.50, step=0.05,
    help="Share of the fee kept by the NGO (in funded mode: of the fee remaining after the funder is repaid). The rest pays mandatory counsel (§14 ZHŘS)."
)

v = st.sidebar.number_input(
    "Onboarding Cost per Member (v, CZK)",
    min_value=10, max_value=2000, value=250, step=25,
    help="Fully-loaded cost of enrolling one opted-in member: notice, verification, proof collection, platform friction."
)

F = st.sidebar.number_input(
    "Fixed Operational Costs (F, CZK)",
    min_value=10_000, max_value=1_000_000, value=150_000, step=10_000,
    help="Costs independent of group size: court fees, merits assessment, IT, funding-source disclosure (§57 ZHŘS)."
)

ac_w = st.sidebar.number_input(
    "Adverse Costs if Case Lost (CZK)",
    min_value=0, max_value=2_000_000, value=350_000, step=25_000,
    help="Opponent's costs payable by the losing party (§142 OSŘ). Applied only on a loss."
)

st.sidebar.header("3. Merits Risk Assessment")

p_est = st.sidebar.slider(
    "Merits Win Probability (p)",
    min_value=0.10, max_value=1.00, value=0.60, step=0.05,
    help="Probability of winning, with full recovery of C per member."
)

# Derived asymptotic floor calculations
if is_tplf:
    floor_asymptote = (funder_multiple * v) / alpha
    floor_label = f"Min. Claim at Scale (Funder Hurdle {funder_multiple:.1f}×)"
    floor_help = "Per-member claim below which the funder's hurdle absorbs the entire fee, even with unlimited opt-ins."
else:
    floor_asymptote = v / (p_est * alpha * beta)
    floor_label = "Minimum Viable Claim at Scale"
    floor_help = "Per-member claim below which the NGO's expected value is negative (EV < 0), even with unlimited opt-ins."

st.sidebar.markdown("---")
st.sidebar.metric(label=floor_label, value=f"{floor_asymptote:,.0f} CZK", help=floor_help)

# --- TABS ---
tab1, tab2 = st.tabs([
    "1. Viability Frontier",
    "2. Case Test & Payout Waterfall"
])

# ==============================================================================
# TAB 1: VIABILITY FRONTIER
# ==============================================================================
with tab1:
    st.subheader(f"Minimum Viable Claim by Group Size ({funding_mode})")

    n_axis = np.linspace(10, 5000, 300)
    fig1 = go.Figure()

    if is_tplf:
        st.markdown(
            "With third-party funding, the funder is repaid first: it takes $M \\times K$ from the statutory fee, where "
            "$K = F + v \\cdot N$ is the capital deployed. The NGO and counsel are paid only if the fee exceeds that hurdle, "
            "i.e. when the claim lies above the frontier:"
        )
        st.latex(r'''
        C^*_{\text{TPLF}}(N) = \frac{M \cdot F}{\alpha \cdot N} + \frac{M \cdot v}{\alpha}, \quad \lim_{N \to \infty} C^*_{\text{TPLF}} = \frac{M \cdot v}{\alpha}
        ''')
        st.caption(
            "Hurdle-clearance frontier, not a break-even. By construction it ignores p and adverse costs (these enter through "
            "the funder's pricing of M), so it is not comparable with the self-financed EV = 0 frontier. "
            "Tab 2 reports whether the funder would actually accept the deal."
        )
        c_frontier = (funder_multiple * F) / (alpha * n_axis) + floor_asymptote

        fig1.add_trace(go.Scatter(
            x=n_axis, y=c_frontier, mode="lines",
            name=f"Hurdle-clearance frontier (M={funder_multiple:.1f}×)",
            line=dict(color="#1fb451", width=4),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>Min. Claim:</b> %{y:,.0f} CZK<extra></extra>"
        ))

    else:
        st.markdown(
            "When the NGO funds the litigation from its own balance sheet, the claim must satisfy the zero expected value threshold ($EV \\ge 0$):"
        )
        st.latex(r'''
        C^*_{\text{Self}}(N) = \frac{F + (1 - p) \cdot AC}{p \cdot \alpha \cdot \beta \cdot N} + \frac{v}{p \cdot \alpha \cdot \beta}
        ''')

        c_frontier = (F + (1 - p_est) * ac_w) / (p_est * alpha * beta * n_axis) + floor_asymptote
        c_frontier_base = F / (alpha * beta * n_axis) + (v / (alpha * beta))

        fig1.add_trace(go.Scatter(
            x=n_axis, y=c_frontier, mode="lines",
            name=f"EV = 0 frontier (p={p_est:.0%})",
            line=dict(color="#1fb451", width=4),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>Min. Claim:</b> %{y:,.0f} CZK<extra></extra>"
        ))

        fig1.add_trace(go.Scatter(
            x=n_axis, y=c_frontier_base, mode="lines",
            name="Best case (p = 100%, no adverse costs)",
            line=dict(color="#7f7f7f", width=1.5, dash="dot"),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>Best-case Min. Claim:</b> %{y:,.0f} CZK<extra></extra>"
        ))

    fig1.add_hline(
        y=floor_asymptote, line_dash="dash", line_color="#c82042",
        annotation_text=f"Floor at unlimited scale: {floor_asymptote:,.0f} CZK",
        annotation_position="bottom right"
    )

    fig1.add_vline(
        x=MIN_MEMBERS, line_dash="dot", line_color="#7f7f7f",
        annotation_text="Statutory minimum: 10 opted-in members", annotation_position="top right"
    )

    fig1.update_layout(
        xaxis_title="Opted-in Group Size (N)",
        yaxis_title="Minimum Claim Value per Member (CZK)",
        hovermode="x unified",
        template="plotly_white",
        height=520,
        yaxis=dict(range=[0, max(25000, floor_asymptote * 2.2)])
    )

    st.plotly_chart(fig1)
    if is_tplf:
        st.caption("Claims above the blue curve leave a surplus for the NGO and counsel after the funder is repaid. "
                   "The dashed line is the minimum claim even at unlimited scale.")
    else:
        st.caption("Claims above the blue curve have a non-negative expected value for the NGO. "
                   "The dashed line is the minimum claim even at unlimited scale.")

# ==============================================================================
# TAB 2: CASE TEST & PAYOUT WATERFALL
# ==============================================================================
with tab2:
    st.subheader(f"Case Test & Payout Waterfall ({funding_mode})")

    # Archetype Presets
    preset = st.selectbox(
        "Load Case Archetype Preset",
        [
            "Flight Delay Compensation (€250 / ~6,250 CZK)",
            "E-Commerce Defect / Unfair Commercial Practice (2,500 CZK)",
            "Banking Micro-Fee Overcharge (800 CZK)",
            "High-Value Consumer Claim: Vehicle Defect / Cartel Overcharge (15,000 CZK)",
            "Custom Input"
        ],
        index=0
    )

    if preset.startswith("Flight Delay"):
        c_init, n_eval_init, n_max_init = 6_250, 1_500, 20_000      # 7.5% opt-in
    elif preset.startswith("E-Commerce"):
        c_init, n_eval_init, n_max_init = 2_500, 3_000, 60_000      # 5%
    elif preset.startswith("Banking"):
        c_init, n_eval_init, n_max_init = 800, 10_000, 200_000      # 5%
    elif preset.startswith("High-Value"):
        c_init, n_eval_init, n_max_init = 15_000, 750, 5_000        # 15%
    else:
        c_init, n_eval_init, n_max_init = 5_000, 1_500, 30_000

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        c_val = st.number_input("Recoverable Claim per Member (C, CZK)", min_value=50, max_value=1_000_000, value=c_init, step=250)
    with col_c2:
        n_eval = st.number_input("Opted-in Group Size to Test (N)", min_value=10, max_value=1_000_000, value=n_eval_init, step=100)
    with col_c3:
        n_max_val = st.number_input("Harmed Consumer Pool (N_max)", min_value=10, max_value=1_000_000, value=n_max_init, step=250)

    if n_eval > n_max_val:
        st.error("The opted-in group (N) cannot exceed the harmed pool (N_max).")
        st.stop()

    party = "Funder" if is_tplf else "NGO"

    # --- BREAK-EVEN CALCULATIONS ---
    if is_tplf:
        denom = alpha * c_val - funder_multiple * v
        n_star_raw = (funder_multiple * F) / denom if denom > 0 else np.inf
        n_star_label = "N* to Clear Funder Hurdle"
        n_star_help = ("Smallest opted-in group at which the fee exceeds the funder's hurdle (M × capital deployed), "
                       "so that the NGO and counsel receive something. This is hurdle clearance, not funder break-even.")
    else:
        denom = p_est * alpha * beta * c_val - v
        n_star_raw = (F + (1 - p_est) * ac_w) / denom if denom > 0 else np.inf
        n_star_label = "Break-even Group Size N*"
        n_star_help = "Smallest opted-in group at which the NGO's expected value is ≥ 0."

    n_star = max(n_star_raw, MIN_MEMBERS)
    is_viable = bool(np.isfinite(n_star))               # unit economics positive at scale
    is_feasible = is_viable and n_star <= n_max_val     # reachable within the harmed pool
    conv_rate = n_star / n_max_val if is_viable else np.inf

    # --- REALIZED WATERFALL DISTRIBUTION (AT N_EVAL) ---
    total_damages = n_eval * c_val
    gross_fee_pool = alpha * total_damages
    capital_deployed = F + v * n_eval
    max_loss = capital_deployed + ac_w

    if is_tplf:
        # Senior waterfall: funder takes min(fee pool, M × capital deployed)
        funder_target_claim = funder_multiple * capital_deployed
        funder_payout = min(gross_fee_pool, funder_target_claim)
        residual_pool = max(0.0, gross_fee_pool - funder_payout)

        ngo_payout = beta * residual_pool
        counsel_payout = (1.0 - beta) * residual_pool
        is_cannibalized = (residual_pool <= 0)
        eval_ev = p_est * funder_payout - capital_deployed - (1 - p_est) * ac_w
        m_min = (1 / p_est) * (1 + (1 - p_est) * ac_w / capital_deployed)
    else:
        # Self-financed: counsel takes (1 - β) of the fee; NGO takes β of the fee, net of capital deployed
        counsel_payout = (1.0 - beta) * gross_fee_pool
        ngo_gross_share = beta * gross_fee_pool
        ngo_payout = ngo_gross_share - capital_deployed
        funder_payout = 0.0
        is_cannibalized = (ngo_payout < 0)
        eval_ev = p_est * ngo_gross_share - capital_deployed - (1 - p_est) * ac_w

    expected_roi = eval_ev / capital_deployed  # capital_deployed ≥ F > 0

    # --- VERDICT ---
    if not is_viable:
        st.error("**Not viable at any scale:** each additional member costs more to enrol than the fee income they generate. "
                 "Only a higher claim value, a lower onboarding cost or a higher fee rate can change this.")
    elif is_tplf and eval_ev < 0:
        if funder_multiple < m_min:
            reason = (f"At p = {p_est:.0%} and N = {n_eval:,.0f}, a risk-neutral funder needs a hurdle of at least {m_min:.2f}× "
                      f"(current: {funder_multiple:.2f}×).")
        else:
            reason = "The fee pool is too small to repay the hurdle, so the funder recovers only the fee and does not earn its cost of risk."
        st.error(f"**Unlikely to be funded:** the funder's expected value is {eval_ev:,.0f} CZK. {reason}")
    elif is_tplf and is_cannibalized:
        st.warning("**Fundable, but the NGO and counsel receive nothing:** the funder's hurdle absorbs the entire fee pool.")
    elif eval_ev < 0:
        gap = (f"Break-even needs {n_star:,.0f} opted-in members ({conv_rate:.0%} of the harmed pool)."
               if is_feasible else
               f"Break-even needs {n_star:,.0f} opted-in members, more than the entire harmed pool of {n_max_val:,.0f}.")
        st.error(f"**Negative expected value for the NGO ({eval_ev:,.0f} CZK).** {gap}")
    else:
        who = "the funder earns a positive expected return and the NGO and counsel receive a residual" if is_tplf \
            else "the NGO's expected value is positive"
        st.success(f"**Viable at N = {n_eval:,.0f}:** {who}.")

    # --- SECTION: PAYOUTS ON A WIN ---
    st.markdown("### Payouts if the Case Is Won")
    st.caption(f"Distribution among stakeholders at N = {n_eval:,.0f} opted-in members:")

    # Layout adapts if beta == 1.0 (no external counsel share)
    if beta < 1.0:
        k_cols = st.columns(5 if is_tplf else 4)
    else:
        k_cols = st.columns(4 if is_tplf else 3)

    k_cols[0].metric(
        "Total Award to Group (N × C)",
        f"{total_damages:,.0f} CZK",
        help="Total redress awarded against the defendant. The fee below is calculated as a percentage of this amount."
    )
    k_cols[1].metric(
        f"Contingency Fee Pool ({alpha:.0%} of award)",
        f"{gross_fee_pool:,.0f} CZK",
        help="Fee payable on a win (§65 ZHŘS cap: 16%). Shared between the funder (if any), the NGO and counsel as shown."
    )

    col_idx = 2
    if is_tplf:
        realized_moic = funder_payout / capital_deployed
        k_cols[col_idx].metric(
            f"Funder Payout (hurdle {funder_multiple:.1f}×)",
            f"{funder_payout:,.0f} CZK",
            help="Senior priority payout: the lower of the fee pool and M × capital deployed."
        )
        col_idx += 1

    k_cols[col_idx].metric(
        "NGO Share of Residual" if is_tplf else "NGO Net Result (after costs)",
        f"{ngo_payout:,.0f} CZK",
        help=("β × the fee remaining after the funder is repaid." if is_tplf
              else f"β × fee pool, minus {capital_deployed:,.0f} CZK of upfront costs. Negative means the NGO loses money even on a win.")
    )
    col_idx += 1

    if beta < 1.0:
        k_cols[col_idx].metric(
            "Counsel Share",
            f"{counsel_payout:,.0f} CZK",
            help=("(1 − β) × the fee remaining after the funder is repaid." if is_tplf else "(1 − β) × the fee pool.")
        )

    if is_tplf:
        st.caption(f"The funder takes {funder_payout / gross_fee_pool:.0%} of the fee pool ({realized_moic:.2f}× its invested capital).")

    # Status callouts
    if is_tplf and is_cannibalized:
        st.error(
            f"**Total Fee Cannibalization:** At N = {n_eval:,.0f}, the funder's hurdle ({funder_target_claim:,.0f} CZK) "
            f"absorbs **100%** of the fee pool ({gross_fee_pool:,.0f} CZK). The NGO and counsel receive 0 CZK."
        )
    elif not is_tplf and is_cannibalized:
        st.warning(
            f"**Cost Deficit on Win:** At N = {n_eval:,.0f}, the NGO's {beta:.0%} share of the fee ({ngo_gross_share:,.0f} CZK) "
            f"does not cover the upfront costs ({capital_deployed:,.0f} CZK). The NGO loses {-ngo_payout:,.0f} CZK despite winning."
        )

    st.markdown("---")

    # --- SECTION: VIABILITY & REQUIRED OPT-IN ---
    st.markdown("### Viability & Required Opt-in")

    f1, f2, f3, f4, f5 = st.columns(5)

    if not is_viable:
        f1.metric(n_star_label, "Not viable", help="Each additional member costs more than the fee income they generate, so no group size works.")
        f2.metric("Required Opt-in Rate (κ*)", "N/A", help="No opt-in rate can make the case viable.")
    else:
        f1.metric(n_star_label, f"{n_star:,.0f} members", help=n_star_help)
        f2.metric(
            "Required Opt-in Rate (κ*)",
            f"{conv_rate:.1%}" if conv_rate < 1 else f"{conv_rate:.0%}",
            help="Share of the harmed pool that must opt in to reach N*. Above 100% the case is infeasible even if every harmed consumer joins."
        )

    f3.metric("Upfront Capital Required", f"{capital_deployed:,.0f} CZK", help="F + v × N, spent regardless of the outcome.")

    f4.metric(
        f"Max Loss if Case Lost ({party})",
        f"-{max_loss:,.0f} CZK",
        help=f"Borne by the {party.lower()}: upfront capital plus adverse costs."
    )

    f5.metric(
        f"Expected Value ({party})",
        f"{eval_ev:,.0f} CZK",
        help=f"Probability-weighted payoff at N = {n_eval:,.0f}. Expected return on capital: {expected_roi:.1%}."
    )

    if is_feasible:
        st.caption("Compare κ* with the take-up you consider realistic: opt-in regimes typically enrol only a fraction of the harmed pool.")

    # --- SECTION: PAYOFF PLOT ---
    st.markdown("### Payoff & Exposure Profile Across Group Size")

    max_plot_n = int(max(n_max_val * 1.05, 500))   # N cannot exceed the harmed pool
    n_plot = np.linspace(10, max_plot_n, 400)
    costs_plot = F + v * n_plot
    gross_fees_plot = alpha * n_plot * c_val
    max_loss_plot = -(costs_plot + ac_w)

    fig2 = go.Figure()

    if is_tplf:
        funder_claim_plot = funder_multiple * costs_plot
        funder_payout_plot = np.minimum(gross_fees_plot, funder_claim_plot)
        residual_plot = np.maximum(0.0, gross_fees_plot - funder_claim_plot)
        ngo_gain_plot = beta * residual_plot
        funder_ev_plot = p_est * funder_payout_plot - costs_plot - (1 - p_est) * ac_w

        fig2.add_trace(go.Scatter(
            x=n_plot, y=ngo_gain_plot, mode="lines",
            name="NGO share of residual (if won)",
            line=dict(color="#2ca02c", width=2.5),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>NGO (if won):</b> %{y:,.0f} CZK<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=n_plot, y=residual_plot, mode="lines",
            name="NGO + counsel residual (if won)",
            line=dict(color="#17becf", width=1.5, dash="dot"),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>NGO + Counsel (if won):</b> %{y:,.0f} CZK<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=n_plot, y=funder_ev_plot, mode="lines",
            name="Funder expected value",
            line=dict(color="#1f77b4", width=2.5),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>Funder EV:</b> %{y:,.0f} CZK<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=n_plot, y=max_loss_plot, mode="lines",
            name="Funder maximum loss",
            line=dict(color="#d62728", width=2, dash="dash"),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>Funder Max Loss:</b> %{y:,.0f} CZK<extra></extra>"
        ))

    else:
        win_net_ngo = (alpha * beta * n_plot * c_val) - costs_plot
        ev_ngo = p_est * (alpha * beta * n_plot * c_val) - costs_plot - (1 - p_est) * ac_w

        fig2.add_trace(go.Scatter(
            x=n_plot, y=win_net_ngo, mode="lines",
            name="NGO net result (if won)",
            line=dict(color="#2ca02c", width=2.5),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>NGO (if won):</b> %{y:,.0f} CZK<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=n_plot, y=ev_ngo, mode="lines",
            name="NGO expected value",
            line=dict(color="#1f77b4", width=3),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>NGO EV:</b> %{y:,.0f} CZK<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=n_plot, y=max_loss_plot, mode="lines",
            name="NGO maximum loss",
            line=dict(color="#d62728", width=2, dash="dash"),
            hovertemplate="<b>Group Size (N):</b> %{x:,.0f}<br><b>NGO Max Loss:</b> %{y:,.0f} CZK<extra></extra>"
        ))

    fig2.add_hline(y=0, line_width=1, line_color="#333333")

    # Key threshold vertical markers
    fig2.add_vline(
        x=MIN_MEMBERS, line_dash="dot", line_color="#7f7f7f",
        annotation_text="Statutory min (10)", annotation_position="bottom left"
    )

    fig2.add_vline(
        x=n_eval, line_dash="solid", line_color="#ff7f0e",
        annotation_text=f"Tested N = {n_eval:,.0f}", annotation_position="top left"
    )

    if is_feasible:
        fig2.add_vline(
            x=n_star, line_dash="dash", line_color="#1f77b4",
            annotation_text=f"N* = {n_star:,.0f}", annotation_position="bottom right"
        )

    fig2.add_vline(
        x=n_max_val, line_dash="dot", line_color="#8c564b",
        annotation_text=f"Pool N_max = {n_max_val:,.0f}", annotation_position="top right"
    )

    fig2.update_layout(
        xaxis_title="Opted-in Group Size (N)",
        yaxis_title="Payoff (CZK)",
        hovermode="x unified",
        template="plotly_white",
        height=540,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig2)