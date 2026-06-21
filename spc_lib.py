"""
홍익반도체 박막증착 공정 SPC & 공정능력분석 웹앱
스마트제조 기말 프로젝트

강의록(08 공정능력분석, 09 통계적공정관리) 기반으로
- 공정능력분석 (정규성검정, Box-Cox, Cp/Cpk/Pp/Ppk)
- SPC 관리도 (Xbar-R, Xbar-S, I-MR, P, NP, Nelson's Rule, Phase I 개선)
을 데이터 업로드 시 자동 재계산하는 대시보드
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import shapiro, boxcox
from scipy.special import gamma
import io

st.set_page_config(
    page_title="SPC & 공정능력분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 0. 공통 함수 (강의록 08/09 기반)
# =========================================================

UNBIASED_TABLE = {
    'A2': {2:1.880,3:1.023,4:0.729,5:0.577,6:0.483,7:0.419,8:0.373,9:0.337,10:0.308,
           11:0.285,12:0.266,13:0.249,14:0.235,15:0.223,16:0.212,17:0.203,18:0.194,
           19:0.187,20:0.180,21:0.173,22:0.167,23:0.162,24:0.157,25:0.153},
    'A3': {2:2.659,3:1.954,4:1.628,5:1.427,6:1.287,7:1.182,8:1.099,9:1.032,10:0.975,
           11:0.927,12:0.886,13:0.850,14:0.817,15:0.789,16:0.763,17:0.739,18:0.718,
           19:0.698,20:0.680,21:0.663,22:0.647,23:0.633,24:0.619,25:0.606},
    'd2': {2:1.128,3:1.693,4:2.059,5:2.326,6:2.534,7:2.704,8:2.847,9:2.970,10:3.078,
           11:3.173,12:3.258,13:3.336,14:3.407,15:3.472,16:3.532,17:3.588,18:3.640,
           19:3.689,20:3.735,21:3.778,22:3.819,23:3.858,24:3.895,25:3.931},
    'D3': {2:0,3:0,4:0,5:0,6:0,7:0.076,8:0.136,9:0.184,10:0.223,11:0.256,12:0.283,
           13:0.307,14:0.328,15:0.347,16:0.363,17:0.378,18:0.391,19:0.403,20:0.415,
           21:0.425,22:0.434,23:0.443,24:0.451,25:0.459},
    'D4': {2:3.267,3:2.574,4:2.282,5:2.114,6:2.004,7:1.924,8:1.864,9:1.816,10:1.777,
           11:1.744,12:1.717,13:1.693,14:1.672,15:1.653,16:1.637,17:1.622,18:1.608,
           19:1.597,20:1.585,21:1.575,22:1.566,23:1.557,24:1.548,25:1.541},
    'B3': {2:0,3:0,4:0,5:0,6:0.030,7:0.118,8:0.185,9:0.239,10:0.284,
           11:0.321,12:0.354,13:0.382,14:0.406,15:0.428,16:0.448,17:0.466,18:0.482,
           19:0.497,20:0.510,21:0.523,22:0.534,23:0.545,24:0.555,25:0.565},
    'B4': {2:3.267,3:2.568,4:2.266,5:2.089,6:1.970,7:1.882,8:1.815,9:1.761,10:1.716,
           11:1.679,12:1.646,13:1.618,14:1.594,15:1.572,16:1.552,17:1.534,18:1.518,
           19:1.503,20:1.490,21:1.477,22:1.466,23:1.455,24:1.445,25:1.435},
}


def unbiased_coefficient(coef_name, m):
    """강의록 불편화 상수표(m=2~25) 적용. 범위 초과시 근사식/마지막값 사용."""
    m = int(round(m))
    if m < 2:
        m = 2

    if coef_name in UNBIASED_TABLE:
        d = UNBIASED_TABLE[coef_name]
        if 2 <= m <= 25:
            return d[m]
        else:
            return d[25]

    elif coef_name == 'c4':
        return (np.sqrt(2)/np.sqrt(m-1)) * (gamma(m/2) / gamma((m-1)/2))

    elif coef_name == 'E2':
        return 3 / unbiased_coefficient('d2', m)

    return None


def generate_xbar_chart(df_wide, base='R'):
    """Xbar-R / Xbar-S 관리도 (강의록 09 공식)"""
    n = df_wide.shape[1]
    Xbar = df_wide.mean(axis=1)

    if base == 'R':
        R = df_wide.max(axis=1) - df_wide.min(axis=1)
        Xbar_bar, R_bar = Xbar.mean(), R.mean()
        A2, D3, D4 = (unbiased_coefficient(c, n) for c in ['A2','D3','D4'])

        Xbar_chart = pd.DataFrame({'point': Xbar, 'CL': Xbar_bar,
                                    'LCL': Xbar_bar - A2*R_bar, 'UCL': Xbar_bar + A2*R_bar})
        R_chart = pd.DataFrame({'point': R, 'CL': R_bar,
                                 'LCL': D3*R_bar, 'UCL': D4*R_bar})
        return Xbar_chart, R_chart

    elif base == 'S':
        s = df_wide.std(axis=1, ddof=1)
        Xbar_bar, s_bar = Xbar.mean(), s.mean()
        A3, B3, B4 = (unbiased_coefficient(c, n) for c in ['A3','B3','B4'])

        Xbar_chart = pd.DataFrame({'point': Xbar, 'CL': Xbar_bar,
                                    'LCL': Xbar_bar - A3*s_bar, 'UCL': Xbar_bar + A3*s_bar})
        s_chart = pd.DataFrame({'point': s, 'CL': s_bar,
                                 'LCL': B3*s_bar, 'UCL': B4*s_bar})
        return Xbar_chart, s_chart


def generate_imr_chart(series, window=2):
    """I-MR 관리도 (강의록 09 공식)"""
    w = window
    Xbar = series.mean()
    MR_i = series.rolling(window=w).apply(lambda x: x.max() - x.min())
    MR_bar = MR_i[w-1:].mean()
    D3, D4, d2 = (unbiased_coefficient(c, w) for c in ['D3','D4','d2'])

    I_chart = pd.DataFrame({'point': series, 'CL': Xbar,
                             'LCL': Xbar - 3*MR_bar/d2, 'UCL': Xbar + 3*MR_bar/d2})
    MR_chart = pd.DataFrame({'point': MR_i, 'CL': MR_bar,
                              'LCL': D3*MR_bar, 'UCL': D4*MR_bar})
    return I_chart, MR_chart


def generate_np_chart(df_raw):
    """NP 관리도 (n_i 동일해야 적용 가능, 강의록 09 공식)"""
    np_bar = df_raw['Defectives'].sum() / len(df_raw)
    p_bar = df_raw['Defectives'].sum() / df_raw['n'].sum()
    return pd.DataFrame({
        'point': df_raw['Defectives'], 'CL': np_bar,
        'LCL': np_bar - 3*np.sqrt(np_bar*(1-p_bar)),
        'UCL': np_bar + 3*np.sqrt(np_bar*(1-p_bar))
    }, index=df_raw.index)


def generate_p_chart(df_raw):
    """P 관리도 (강의록 09 공식)"""
    p_bar = df_raw['Defectives'].sum() / df_raw['n'].sum()
    return pd.DataFrame({
        'point': df_raw['Defectives']/df_raw['n'], 'CL': p_bar,
        'LCL': p_bar - 3*np.sqrt(p_bar*(1-p_bar)/df_raw['n']),
        'UCL': p_bar + 3*np.sqrt(p_bar*(1-p_bar)/df_raw['n'])
    }, index=df_raw.index)


def nelson_rules(chart):
    """Nelson's Rule 1/2/3/5/6 자동판정 (강의록 09 그림 기준)"""
    chart = chart.copy()
    n = len(chart)
    point = chart['point'].values
    CL, UCL, LCL = chart['CL'].iloc[0], chart['UCL'].iloc[0], chart['LCL'].iloc[0]
    sigma = (UCL - CL) / 3

    rule1 = (point > UCL) | (point < LCL)
    rule2 = np.zeros(n, dtype=bool)
    rule3 = np.zeros(n, dtype=bool)
    rule5 = np.zeros(n, dtype=bool)
    rule6 = np.zeros(n, dtype=bool)

    for i in range(n):
        if i >= 8:
            w = point[i-8:i+1]
            if np.all(w > CL) or np.all(w < CL):
                rule2[i-8:i+1] = True
        if i >= 5:
            w = point[i-5:i+1]
            diffs = np.diff(w)
            if np.all(diffs > 0) or np.all(diffs < 0):
                rule3[i-5:i+1] = True
        if i >= 2:
            w = point[i-2:i+1]
            if (w > CL+2*sigma).sum() >= 2 or (w < CL-2*sigma).sum() >= 2:
                rule5[i-2:i+1] = True
        if i >= 4:
            w = point[i-4:i+1]
            if (w > CL+1*sigma).sum() >= 4 or (w < CL-1*sigma).sum() >= 4:
                rule6[i-4:i+1] = True

    chart['Rule1'], chart['Rule2'], chart['Rule3'] = rule1, rule2, rule3
    chart['Rule5'], chart['Rule6'] = rule5, rule6
    return chart


def phase1_revise(df_wide, base='R', max_iter=10):
    """Phase I 개선: Rule1 위반 부분군 반복 제거"""
    df_cur = df_wide.copy()
    removed_all, log = [], []
    for it in range(max_iter):
        Xbar_chart, sub_chart = generate_xbar_chart(df_cur, base=base)
        Xbar_chart = nelson_rules(Xbar_chart)
        ooc = Xbar_chart[Xbar_chart['Rule1']].index.tolist()
        log.append((it+1, ooc))
        if len(ooc) == 0:
            break
        df_cur = df_cur.drop(index=ooc)
        removed_all.extend(ooc)

    Xbar_final, sub_final = generate_xbar_chart(df_cur, base=base)
    Xbar_final = nelson_rules(Xbar_final)
    sub_final = nelson_rules(sub_final)
    return Xbar_final, sub_final, removed_all, df_cur, log


def process_capability_subgroup(df_wide, USL, LSL):
    """Cp/Cpk(군내), Pp/Ppk(전체) 계산 (강의록 08 공식)"""
    n = df_wide.shape[1]
    all_values = df_wide.values.flatten()
    x_bar = all_values.mean()

    N = len(all_values)
    sigma_hat = all_values.std(ddof=1)
    sigma_overall = sigma_hat / unbiased_coefficient('c4', N)

    s_i = df_wide.std(axis=1, ddof=1)
    sigma_p = np.sqrt((s_i**2).mean())
    sigma_within = sigma_p / unbiased_coefficient('c4', n)

    Cp = (USL - LSL) / (6*sigma_within)
    Cpk = min((USL - x_bar)/(3*sigma_within), (x_bar - LSL)/(3*sigma_within))
    Pp = (USL - LSL) / (6*sigma_overall)
    Ppk = min((USL - x_bar)/(3*sigma_overall), (x_bar - LSL)/(3*sigma_overall))

    return dict(x_bar=x_bar, sigma_within=sigma_within, sigma_overall=sigma_overall,
                Cp=Cp, Cpk=Cpk, Pp=Pp, Ppk=Ppk)


def judge_capability(value):
    """공정능력 등급 판정 (강의록 08 등급표)"""
    if value >= 1.67:
        return "매우 충분", 0, "#1a9850"
    elif value >= 1.33:
        return "충분", 1, "#66bd63"
    elif value >= 1.00:
        return "충분하지 않으나 괜찮음", 2, "#fee08b"
    elif value >= 0.67:
        return "모자람", 3, "#fc8d59"
    else:
        return "매우 부족", 4, "#d73027"


def normality_test(data):
    """Shapiro-Wilk 정규성 검정"""
    stat, p = shapiro(data)
    return p >= 0.05, p


# =========================================================
# 시각화 함수
# =========================================================

def plot_control_chart_with_rules(chart, name, title, x_title='부분군'):
    fig = go.Figure()
    rule_cols = ['Rule1','Rule2','Rule3','Rule5','Rule6']

    fig.add_trace(go.Scatter(x=chart.index, y=chart['point'], mode='lines+markers',
                              marker=dict(size=9, color='#4C78A8'),
                              line=dict(color='lightgray'), name=name))

    colors = {'Rule1':'#E45756', 'Rule2':'#F58518', 'Rule3':'#B279A2', 'Rule5':'#54A24B', 'Rule6':'#9D755D'}
    symbols = {'Rule1':'x', 'Rule2':'diamond', 'Rule3':'triangle-up', 'Rule5':'square', 'Rule6':'star'}

    for r in rule_cols:
        if r in chart.columns:
            sub = chart[chart[r]]
            if len(sub) > 0:
                fig.add_trace(go.Scatter(x=sub.index, y=sub['point'], mode='markers',
                                          marker=dict(size=13, color=colors[r], symbol=symbols[r],
                                                       line=dict(width=2)), name=r))

    CL, LCL, UCL = chart.iloc[0][['CL','LCL','UCL']]
    fig.add_hline(y=CL, line_dash='dashdot', line_color='green', annotation_text=f'CL={CL:.3f}')
    fig.add_hline(y=UCL, line_dash='dot', line_color='magenta', annotation_text=f'UCL={UCL:.3f}')
    fig.add_hline(y=LCL, line_dash='dot', line_color='red', annotation_text=f'LCL={LCL:.3f}')

    fig.update_layout(template='plotly_white', height=380, title=title,
                       xaxis_title=x_title, yaxis_title=name, margin=dict(t=60,b=40,l=50,r=30))
    return fig


def plot_dual_chart(chart1, chart2, names, title, x_title='부분군'):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         subplot_titles=[f'{names[0]} Chart', f'{names[1]} Chart'])
    for i, chart in enumerate([chart1, chart2]):
        fig.add_trace(go.Scatter(x=chart.index, y=chart['point'], mode='lines+markers',
                                  marker=dict(size=7), name=names[i], line=dict(color='#4C78A8')),
                       row=i+1, col=1)
        fig.add_trace(go.Scatter(x=chart.index, y=chart['CL'], mode='lines',
                                  line=dict(color='green', dash='dashdot'), showlegend=False), row=i+1, col=1)
        fig.add_trace(go.Scatter(x=chart.index, y=chart['LCL'], mode='lines',
                                  line=dict(color='red', dash='dot'), showlegend=False), row=i+1, col=1)
        fig.add_trace(go.Scatter(x=chart.index, y=chart['UCL'], mode='lines',
                                  line=dict(color='magenta', dash='dot'), showlegend=False), row=i+1, col=1)
        fig.update_yaxes(title=names[i], row=i+1, col=1)
    fig.update_xaxes(title=x_title, row=2, col=1)
    fig.update_layout(template='plotly_white', height=520, title=title, showlegend=False,
                       margin=dict(t=70,b=40,l=50,r=30))
    return fig


def plot_capability_histogram(values, USL, LSL, target, cap, title):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=values, nbinsx=20, marker_color='#4C78A8', opacity=0.75, name='측정값'))
    fig.add_vline(x=USL, line_dash='dash', line_color='red', annotation_text='USL')
    fig.add_vline(x=LSL, line_dash='dash', line_color='red', annotation_text='LSL')
    fig.add_vline(x=target, line_dash='dot', line_color='green', annotation_text='Target')
    fig.add_annotation(
        xref='paper', yref='paper', x=1.02, y=1.0,
        text=f"Cp={cap['Cp']:.3f}<br>Cpk={cap['Cpk']:.3f}<br>Pp={cap['Pp']:.3f}<br>Ppk={cap['Ppk']:.3f}",
        showarrow=False, align='left', bordercolor='gray', borderwidth=1, bgcolor='white',
        xanchor='left', yanchor='top'
    )
    fig.update_layout(template='plotly_white', height=420, title=title,
                       margin=dict(t=60,b=40,l=50,r=140))
    return fig


def plot_qq(values, title='Q-Q Plot'):
    from scipy import stats as sstats
    z = sstats.zscore(values)
    (x, y), _ = sstats.probplot(z, dist='norm')
    fig = px.scatter(x=x, y=y, title=title, labels={'x':'Theoretical Quantiles','y':'Sample Quantiles'})
    fig.add_shape(type='line', x0=-3, y0=-3, x1=3, y1=3, line=dict(color='red', width=2))
    fig.update_layout(template='plotly_white', height=380, width=380, margin=dict(t=50,b=40,l=40,r=20))
    return fig
