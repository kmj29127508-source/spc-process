"""
홍익반도체 박막증착 공정 SPC & 공정능력분석 웹앱
스마트제조 기말 프로젝트 - app.py (메인 엔트리포인트)

실행: streamlit run app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from spc_lib import (
    unbiased_coefficient, generate_xbar_chart, generate_imr_chart,
    generate_np_chart, generate_p_chart, nelson_rules, phase1_revise,
    process_capability_subgroup, judge_capability, normality_test,
    plot_control_chart_with_rules, plot_dual_chart,
    plot_capability_histogram, plot_qq
)

st.set_page_config(page_title="SPC & 공정능력분석 대시보드", page_icon="📊", layout="wide")

# =========================================================
# 사이드바: 데이터 입력 & 규격 설정
# =========================================================

st.sidebar.title("⚙️ 설정")
st.sidebar.markdown("##### 1) 데이터 업로드")

st.sidebar.markdown(
    "**계량형 데이터** (부분군별 다중 측정값)  \n"
    "형식: 1열=부분군ID, 나머지 열=측정값(x1,x2,...)"
)
meas_file = st.sidebar.file_uploader("measurements.csv 업로드", type=['csv'], key='meas')

st.sidebar.markdown(
    "**계수형 데이터** (로트별 불량수)  \n"
    "형식: 로트, 검사수(n), 불량수"
)
def_file = st.sidebar.file_uploader("defects.csv 업로드", type=['csv'], key='def')

use_sample = st.sidebar.checkbox("샘플 데이터 사용 (홍익반도체 박막증착 공정)", value=(meas_file is None))

if use_sample or meas_file is None:
    df_meas_raw = pd.read_csv('measurements.csv')
else:
    df_meas_raw = pd.read_csv(meas_file)

if use_sample or def_file is None:
    df_def_raw = pd.read_csv('defects.csv')
else:
    df_def_raw = pd.read_csv(def_file)

# 계량형 데이터 정리: 첫 컬럼 = 부분군 인덱스, 나머지 = 측정값
df_meas_raw.index = range(1, len(df_meas_raw)+1)
df_meas_raw.index.name = '부분군'
value_cols = df_meas_raw.columns.tolist()

# 계수형 데이터 컬럼 정리 (로트, n, 불량수 형태로 강제 통일)
if df_def_raw.shape[1] >= 3:
    df_def = df_def_raw.copy()
    df_def.columns = ['Lot', 'n', 'Defectives'] + list(df_def.columns[3:])
    df_def = df_def.set_index('Lot')[['n', 'Defectives']]
else:
    df_def = None

st.sidebar.markdown("---")
st.sidebar.markdown("##### 2) 규격(Spec) 설정")
target = st.sidebar.number_input("목표값 (Target)", value=100.0, step=1.0)
tolerance = st.sidebar.number_input("허용오차 (±Tolerance)", value=20.0, step=1.0, min_value=0.1)
USL = target + tolerance
LSL = target - tolerance
st.sidebar.info(f"USL = {USL:.1f}  ,  LSL = {LSL:.1f}")

st.sidebar.markdown("---")
st.sidebar.markdown("##### 3) 분석 옵션")
imr_window = st.sidebar.slider("I-MR 이동범위 윈도우(window)", min_value=2, max_value=5, value=2)
imr_col = st.sidebar.selectbox("I-MR에 사용할 측정 컬럼", value_cols, index=0)
contamination_note = st.sidebar.caption("※ Phase I 개선은 Rule1(관리한계 이탈)만 반복 제거합니다.")

st.sidebar.markdown("---")
st.sidebar.caption("강의록 08(공정능력분석) · 09(통계적공정관리) 기반 구현")

# =========================================================
# 메인 헤더
# =========================================================

st.title("📊 반도체 박막증착 공정 SPC & 공정능력분석 대시보드")
st.caption("Smart Manufacturing Final Project — Process Capability Analysis + Statistical Process Control")

with st.expander("ℹ️ 현재 분석 대상 데이터 개요", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**계량형 데이터 (두께 측정)**")
        st.dataframe(df_meas_raw, use_container_width=True, height=250)
    with c2:
        st.markdown("**계수형 데이터 (불량수)**")
        if df_def is not None:
            st.dataframe(df_def, use_container_width=True, height=250)
        else:
            st.warning("계수형 데이터 형식이 올바르지 않습니다 (로트, 검사수, 불량수 3개 컬럼 필요)")

tabs = st.tabs(["🏠 종합 대시보드", "📐 공정능력분석 (Cp/Cpk/Pp/Ppk)",
                 "📈 계량형 관리도 (Xbar-R/S, I-MR)", "🔢 계수형 관리도 (P/NP)"])

# =========================================================
# TAB 0: 종합 대시보드
# =========================================================
with tabs[0]:
    st.subheader("종합 공정 상태 요약")

    # 빠른 계산 (요약 카드용)
    Xbar_R_chart, R_chart = generate_xbar_chart(df_meas_raw, base='R')
    Xbar_R_chart = nelson_rules(Xbar_R_chart)
    cap = process_capability_subgroup(df_meas_raw, USL, LSL)
    grade_label, grade_num, grade_color = judge_capability(cap['Cpk'])

    is_normal, p_val = normality_test(df_meas_raw.values.flatten())

    n_rule1 = int(Xbar_R_chart['Rule1'].sum())
    n_violations = int(Xbar_R_chart[['Rule1','Rule2','Rule3','Rule5','Rule6']].any(axis=1).sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cpk (단기 공정능력)", f"{cap['Cpk']:.3f}", grade_label)
    col2.metric("Ppk (장기 공정능력)", f"{cap['Ppk']:.3f}", judge_capability(cap['Ppk'])[0])
    col3.metric("Rule1 위반 부분군 수", f"{n_rule1} 개",
                "관리이탈 발생" if n_rule1 > 0 else "정상", delta_color="inverse")
    col4.metric("정규성 검정 (Shapiro-Wilk)", "만족" if is_normal else "불만족", f"p={p_val:.4f}")

    st.markdown("---")

    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown("##### Xbar-R 관리도 (이상점 자동 표시)")
        fig = plot_control_chart_with_rules(Xbar_R_chart, 'Xbar', 'Xbar Chart — Nelson Rule 위반점 표시')
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### 공정능력 등급")
        st.markdown(
            f"""
            <div style="background-color:{grade_color}22; border-left: 6px solid {grade_color};
                        padding: 16px; border-radius: 6px;">
            <h3 style="margin:0; color:{grade_color};">Cpk = {cap['Cpk']:.3f}</h3>
            <p style="margin:4px 0 0 0; font-size:16px;">등급: <b>{grade_label}</b></p>
            </div>
            """, unsafe_allow_html=True
        )
        st.markdown("")
        st.markdown(f"""
        - **Cp** = {cap['Cp']:.3f} (군내변동 기준 산포)
        - **Cpk** = {cap['Cpk']:.3f} (군내변동 기준, 중심치우침 반영)
        - **Pp** = {cap['Pp']:.3f} (전체변동 기준 산포)
        - **Ppk** = {cap['Ppk']:.3f} (전체변동 기준, 중심치우침 반영)
        - σ_within = {cap['sigma_within']:.4f}
        - σ_overall = {cap['sigma_overall']:.4f}
        """)

        if n_violations > 0:
            ooc_list = Xbar_R_chart[Xbar_R_chart[['Rule1','Rule2','Rule3','Rule5','Rule6']].any(axis=1)].index.tolist()
            st.warning(f"⚠️ Nelson Rule 위반 부분군: {ooc_list}")
        else:
            st.success("✅ 모든 부분군이 관리상태입니다.")

    st.markdown("---")
    st.markdown("##### 불량률 추이 (계수형 데이터)")
    if df_def is not None:
        fig_def = px.bar(df_def, x=df_def.index, y='Defectives',
                          title='로트별 불량수', color='Defectives', color_continuous_scale='Reds')
        p_bar = df_def['Defectives'].sum()/df_def['n'].sum()
        fig_def.add_hline(y=p_bar*df_def['n'].mean(), line_dash='dot', line_color='black',
                           annotation_text=f'평균 불량률 p̄={p_bar:.4f}')
        fig_def.update_layout(template='plotly_white', height=320)
        st.plotly_chart(fig_def, use_container_width=True)

# =========================================================
# TAB 1: 공정능력분석
# =========================================================
with tabs[1]:
    st.subheader("공정능력분석 (Process Capability Analysis)")
    st.caption("강의록 08 — Cp/Cpk: 군내변동(σ_within) 기준 / Pp/Ppk: 전체변동(σ_overall) 기준")

    all_values = df_meas_raw.values.flatten()
    is_normal, p_val = normality_test(all_values)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### 1) 정규성 검정 (Shapiro-Wilk)")
        if is_normal:
            st.success(f"p-value = {p_val:.4f} ≥ 0.05 → **정규성 만족**")
        else:
            st.error(f"p-value = {p_val:.4f} < 0.05 → **정규성 불만족**")
            st.markdown("강의록 08 — 정규성 불만족 시 Box-Cox 변환을 통해 정규분포로 변환 후 분석합니다.")
            if st.checkbox("Box-Cox 변환 적용"):
                from scipy.stats import boxcox
                if (all_values <= 0).any():
                    st.warning("Box-Cox는 양수 데이터에만 적용 가능합니다 (음수/0 포함 데이터는 Yeo-Johnson 필요).")
                else:
                    transformed, lam = boxcox(all_values)
                    is_normal_t, p_val_t = normality_test(transformed)
                    st.write(f"Box-Cox λ = {lam:.4f}")
                    st.write(f"변환 후 p-value = {p_val_t:.4f} → "
                             f"{'정규성 만족' if is_normal_t else '정규성 여전히 불만족'}")
                    st.caption("※ 변환된 척도에서의 Cp/Cpk는 무차원 비율이므로 원 데이터 해석에 그대로 사용 가능합니다 "
                               "(단, USL/LSL도 동일하게 변환해야 정확합니다).")
    with c2:
        st.markdown("##### Q-Q Plot")
        st.plotly_chart(plot_qq(all_values), use_container_width=True)

    st.markdown("---")
    st.markdown("##### 2) Phase I 개선 적용 여부")
    apply_phase1 = st.checkbox("이상 부분군(Rule1) 제거 후 공정능력 계산", value=False)

    if apply_phase1:
        _, _, removed_lots, df_clean, log = phase1_revise(df_meas_raw, base='R')
        st.info(f"제거된 부분군: {removed_lots if removed_lots else '없음'} "
                f"(원본 {len(df_meas_raw)}개 → {len(df_clean)}개)")
        data_for_cap = df_clean
    else:
        data_for_cap = df_meas_raw

    cap = process_capability_subgroup(data_for_cap, USL, LSL)

    st.markdown("##### 3) 공정능력지수 결과")
    cc1, cc2, cc3, cc4 = st.columns(4)
    for col, name, key in zip([cc1,cc2,cc3,cc4], ['Cp','Cpk','Pp','Ppk'], ['Cp','Cpk','Pp','Ppk']):
        label, _, color = judge_capability(cap[key])
        col.metric(name, f"{cap[key]:.4f}", label)

    st.plotly_chart(
        plot_capability_histogram(data_for_cap.values.flatten(), USL, LSL, target, cap,
                                    f"공정능력 분석 (n={data_for_cap.values.size})"),
        use_container_width=True
    )

    with st.expander("📋 공정능력 등급 기준표 (강의록 08)"):
        grade_df = pd.DataFrame({
            'Cp/Cpk 범위': ['≥ 1.67', '1.33 ~ 1.67', '1.00 ~ 1.33', '0.67 ~ 1.00', '< 0.67'],
            '등급': [0, 1, 2, 3, 4],
            '판정': ['매우 충분', '충분', '충분하지 않으나 괜찮음', '모자람', '매우 부족']
        })
        st.table(grade_df)

# =========================================================
# TAB 2: 계량형 관리도
# =========================================================
with tabs[2]:
    st.subheader("계량형 관리도 (Variable Control Chart)")
    chart_type = st.radio("관리도 종류 선택", ["Xbar-R", "Xbar-S", "I-MR"], horizontal=True)

    show_rules = st.checkbox("Nelson's Rule 자동 판정 표시 (Rule 1/2/3/5/6)", value=True)
    do_phase1 = st.checkbox("Phase I 개선 (Rule1 위반 부분군 반복 제거)", value=False, key='phase1_tab2')

    if chart_type in ["Xbar-R", "Xbar-S"]:
        base = 'R' if chart_type == 'Xbar-R' else 'S'

        if do_phase1:
            Xbar_chart, sub_chart, removed, df_clean, log = phase1_revise(df_meas_raw, base=base)
            st.info(f"제거된 부분군: {removed if removed else '없음'} "
                    f"({len(log)}회 반복, {len(df_meas_raw)}개 → {len(df_meas_raw)-len(removed)}개)")
        else:
            Xbar_chart, sub_chart = generate_xbar_chart(df_meas_raw, base=base)
            Xbar_chart = nelson_rules(Xbar_chart)
            sub_chart = nelson_rules(sub_chart)

        sub_name = 'R' if base == 'R' else 's'

        if show_rules:
            st.plotly_chart(plot_control_chart_with_rules(Xbar_chart, 'Xbar', f'{chart_type} — Xbar Chart'),
                             use_container_width=True)
            st.plotly_chart(plot_control_chart_with_rules(sub_chart, sub_name, f'{chart_type} — {sub_name} Chart'),
                             use_container_width=True)
        else:
            st.plotly_chart(plot_dual_chart(Xbar_chart, sub_chart, ['Xbar', sub_name], f'{chart_type} Control Chart'),
                             use_container_width=True)

        c1, c2 = st.columns(2)
        c1.write(f"**Xbar**: CL={Xbar_chart['CL'].iloc[0]:.4f}, "
                 f"LCL={Xbar_chart['LCL'].iloc[0]:.4f}, UCL={Xbar_chart['UCL'].iloc[0]:.4f}")
        c2.write(f"**{sub_name}**: CL={sub_chart['CL'].iloc[0]:.4f}, "
                 f"LCL={sub_chart['LCL'].iloc[0]:.4f}, UCL={sub_chart['UCL'].iloc[0]:.4f}")

        if show_rules:
            with st.expander("🔍 Nelson Rule 위반 상세"):
                for r in ['Rule1','Rule2','Rule3','Rule5','Rule6']:
                    viol = Xbar_chart[Xbar_chart[r]].index.tolist()
                    st.write(f"- **{r}**: {viol if viol else '위반 없음'}")

    else:  # I-MR
        series = df_meas_raw[imr_col]
        I_chart, MR_chart = generate_imr_chart(series, window=imr_window)
        I_chart = nelson_rules(I_chart)
        MR_chart = nelson_rules(MR_chart)

        if show_rules:
            st.plotly_chart(plot_control_chart_with_rules(I_chart, f'I ({imr_col})',
                             f'I-MR Chart (window={imr_window})'), use_container_width=True)
            st.plotly_chart(plot_control_chart_with_rules(MR_chart, 'MR', 'Moving Range Chart'),
                             use_container_width=True)
        else:
            st.plotly_chart(plot_dual_chart(I_chart, MR_chart, [f'I ({imr_col})', 'MR'],
                             f'I-MR Control Chart (window={imr_window})'), use_container_width=True)

        c1, c2 = st.columns(2)
        c1.write(f"**I**: CL={I_chart['CL'].iloc[0]:.4f}, "
                 f"LCL={I_chart['LCL'].iloc[0]:.4f}, UCL={I_chart['UCL'].iloc[0]:.4f}")
        c2.write(f"**MR**: CL={MR_chart['CL'].iloc[0]:.4f}, "
                 f"LCL={MR_chart['LCL'].iloc[0]:.4f}, UCL={MR_chart['UCL'].iloc[0]:.4f}")

# =========================================================
# TAB 3: 계수형 관리도
# =========================================================
with tabs[3]:
    st.subheader("계수형 관리도 (Attribute Control Chart)")

    if df_def is None:
        st.error("계수형 데이터 형식이 올바르지 않습니다. (컬럼: 로트, 검사수, 불량수)")
    else:
        same_n = df_def['n'].nunique() == 1
        count_type = st.radio("관리도 종류 선택", ["NP (불량개수)", "P (불량률)"], horizontal=True)
        show_rules2 = st.checkbox("Nelson's Rule 자동 판정 표시", value=True, key='rules2')

        if count_type.startswith("NP") and not same_n:
            st.warning("⚠️ NP 관리도는 표본 크기(n)가 동일해야 적용 가능합니다. "
                       "현재 데이터는 로트별 검사수가 다르므로 P 관리도 사용을 권장합니다.")

        if count_type.startswith("NP"):
            chart = generate_np_chart(df_def)
            name = 'Defectives (NP)'
        else:
            chart = generate_p_chart(df_def)
            name = 'Defect Rate (P)'

        chart = nelson_rules(chart)

        if show_rules2:
            st.plotly_chart(plot_control_chart_with_rules(chart, name, f'{count_type} Control Chart', x_title='로트'),
                             use_container_width=True)
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=chart.index, y=chart['point'], mode='lines+markers', name=name))
            fig.add_hline(y=chart['CL'].iloc[0], line_dash='dashdot', line_color='green')
            fig.add_hline(y=chart['UCL'].iloc[0], line_dash='dot', line_color='magenta')
            fig.add_hline(y=chart['LCL'].iloc[0], line_dash='dot', line_color='red')
            fig.update_layout(template='plotly_white', height=400, title=f'{count_type} Control Chart')
            st.plotly_chart(fig, use_container_width=True)

        st.write(f"CL={chart['CL'].iloc[0]:.4f}, LCL={chart['LCL'].iloc[0]:.4f}, UCL={chart['UCL'].iloc[0]:.4f}")

        if show_rules2:
            ooc = chart[chart['Rule1']].index.tolist()
            if ooc:
                st.warning(f"⚠️ Rule1 위반 로트: {ooc}")
            else:
                st.success("✅ 모든 로트가 관리상태입니다.")

st.markdown("---")
st.caption("스마트제조 기말 프로젝트 · 강의록 08(공정능력분석)/09(통계적공정관리) 기반 구현 · "
           "Built with Streamlit & Plotly")
