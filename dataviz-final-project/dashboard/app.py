"""
Clinical Trials Dashboard — Final Project
Run with: streamlit run app.py
Data: ClinicalTrials.gov trial records for 10 major pharma sponsors (1984-2020),
sourced via Kaggle ("A Quick Overview of Clinical Trials").
"""
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Clinical Trials Explorer", page_icon="\U0001F9EA",
                    layout="wide", initial_sidebar_state="expanded")

# Light polish — matches the styling techniques from the course
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 0; }
[data-testid='metric-container'] {
    background: #F8F9FA; border: 1px solid #E9ECEF;
    padding: 1rem; border-radius: 8px;
}
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

MAIN_PHASES = ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4']
BLUE, ORANGE, GREY = '#2E75B6', '#E07B39', '#AAAAAA'


@st.cache_data
def load_data():
    df = pd.read_csv('data/clinical_trials.csv')
    df['bad_outcome'] = df['Status'].isin(['Terminated', 'Withdrawn'])
    df['completed'] = df['Status'] == 'Completed'
    df['decade'] = (df['Start_Year'] // 10 * 10).astype(str) + 's'

    def categorize(cond):
        if not isinstance(cond, str):
            return 'Other'
        c = cond.lower()
        if any(k in c for k in ['neoplasm', 'cancer', 'carcinoma', 'lymphoma', 'leukemia',
                                 'melanoma', 'tumor', 'sarcoma', 'myeloma']):
            return 'Oncology'
        if any(k in c for k in ['diabetes', 'obesity', 'hypercholesterolemia', 'metabolic']):
            return 'Metabolic'
        if any(k in c for k in ['hepatitis', 'hiv', 'influenza', 'infection', 'tuberculosis', 'pneumonia']):
            return 'Infectious Disease'
        if any(k in c for k in ['asthma', 'pulmonary', 'copd', 'respiratory']):
            return 'Respiratory'
        if any(k in c for k in ['hypertension', 'cardiac', 'heart', 'coronary', 'atrial', 'cardiovascular']):
            return 'Cardiovascular'
        if any(k in c for k in ['alzheimer', 'parkinson', 'schizophrenia', 'depression', 'epilepsy',
                                 'sclerosis', 'neuro']):
            return 'Neurological/Psychiatric'
        if any(k in c for k in ['arthritis', 'psoriasis', 'lupus', 'autoimmune']):
            return 'Autoimmune/Inflammatory'
        return 'Other'

    df['category'] = df['Condition'].apply(categorize)
    return df


def init_filters(df):
    defaults = {
        'flt_sponsors': sorted(df['Sponsor'].unique()),
        'flt_phases': MAIN_PHASES,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
        else:
            st.session_state[key] = st.session_state[key]  # keep alive across reruns
    if 'flt_years' in st.session_state:
        st.session_state['flt_years'] = st.session_state['flt_years']


def sidebar_filters(df):
    init_filters(df)
    with st.sidebar:
        st.header('\U0001F50D Filters')
        st.multiselect('Sponsor', sorted(df['Sponsor'].unique()), key='flt_sponsors')
        st.multiselect('Phase', MAIN_PHASES, key='flt_phases')
        min_y, max_y = int(df['Start_Year'].min()), int(df['Start_Year'].max())
        st.slider('Start year', min_y, max_y, value=(1990, 2018), key='flt_years')
        st.divider()
        st.caption('Trials with missing Phase are excluded from phase filtering. '
                   'No spatial/location data is available in this dataset.')

    out = df[
        df['Sponsor'].isin(st.session_state.flt_sponsors) &
        (df['Phase'].isin(st.session_state.flt_phases) | df['Phase'].isna()) &
        df['Start_Year'].between(*st.session_state.flt_years)
    ]
    if out.empty:
        st.warning('No trials match the current filters.')
        st.stop()
    return out


df_all = load_data()
df = sidebar_filters(df_all)

st.title('The Shifting Landscape of Global Clinical Trials')
st.caption(f'Source: ClinicalTrials.gov (via Kaggle) | {len(df):,} trials shown of {len(df_all):,} total | '
           f'Last updated: {datetime.date.today()}')

k1, k2, k3, k4 = st.columns(4)
k1.metric('Trials Shown', f'{len(df):,}')
k2.metric('Completion Rate', f"{df['completed'].mean()*100:.1f}%")
k3.metric('Terminated/Withdrawn', f"{df['bad_outcome'].mean()*100:.1f}%")
enr = df[df['Enrollment'] > 0]['Enrollment']
k4.metric('Median Enrollment', f"{enr.median():.0f}" if len(enr) else "n/a")

st.divider()

tab1, tab2, tab3 = st.tabs(['\U0001F4C8 Trends Over Time', '\U0001F3E2 Sponsor Comparison', '\U0001F52C Trial Characteristics'])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Trial launches over time')
        yearly = df['Start_Year'].value_counts().sort_index().reset_index()
        yearly.columns = ['year', 'count']
        # BBD: single metric trend — one hue, no categorical split needed
        fig = px.line(yearly, x='year', y='count', color_discrete_sequence=[BLUE],
                      labels={'count': 'Trials Started', 'year': ''})
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Arial', size=11),
                          yaxis=dict(gridcolor='#EEEEEE', rangemode='tozero'), xaxis=dict(showgrid=False),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader('Phase mix by decade')
        q3 = df[df['Phase'].isin(MAIN_PHASES)]
        if len(q3):
            q3_ct = (pd.crosstab(q3['decade'], q3['Phase'], normalize='index') * 100).round(1)
            q3_ct = q3_ct.reindex(columns=MAIN_PHASES).dropna(how='all')
            q3_long = q3_ct.reset_index().melt(id_vars='decade', var_name='Phase', value_name='Share')
            # BBD CATEGORICAL colour: CVD-safe qualitative palette across 4 ordered phases
            fig = px.bar(q3_long, x='decade', y='Share', color='Phase', barmode='stack',
                        category_orders={'Phase': MAIN_PHASES},
                        color_discrete_sequence=px.colors.qualitative.Safe,
                        labels={'Share': 'Share of Trials (%)', 'decade': ''})
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Arial', size=11),
                              yaxis=dict(gridcolor='#EEEEEE', range=[0, 100]), xaxis=dict(showgrid=False),
                              legend=dict(orientation='h', y=1.15), margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info('No phase data available for the current filter selection.')

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Completion rate by sponsor')
        comp = df.groupby('Sponsor')['completed'].mean().mul(100).round(1).reset_index()
        comp = comp.sort_values('completed')
        # BBD HIGHLIGHT colour: blue for best, orange for worst, grey for the rest — no red/green
        comp['highlight'] = comp['Sponsor'].apply(
            lambda s: 'Best' if s == comp.loc[comp['completed'].idxmax(), 'Sponsor'] else
                     ('Worst' if s == comp.loc[comp['completed'].idxmin(), 'Sponsor'] else 'Other'))
        fig = px.bar(comp, x='completed', y='Sponsor', orientation='h', color='highlight',
                    color_discrete_map={'Best': BLUE, 'Worst': ORANGE, 'Other': GREY},
                    labels={'completed': 'Completion Rate (%)', 'Sponsor': ''})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Arial', size=11),
                          showlegend=False, xaxis=dict(gridcolor='#EEEEEE', range=[0, 100]),
                          margin=dict(l=10, r=10, t=10, b=10))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader('Terminated/withdrawn rate by sponsor')
        term = df.groupby('Sponsor')['bad_outcome'].mean().mul(100).round(1).reset_index()
        term = term.sort_values('bad_outcome')
        term['highlight'] = term['Sponsor'].apply(
            lambda s: 'Highest' if s == term.loc[term['bad_outcome'].idxmax(), 'Sponsor'] else 'Other')
        fig = px.bar(term, x='bad_outcome', y='Sponsor', orientation='h', color='highlight',
                    color_discrete_map={'Highest': ORANGE, 'Other': BLUE},
                    labels={'bad_outcome': 'Terminated/Withdrawn (%)', 'Sponsor': ''})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Arial', size=11),
                          showlegend=False, xaxis=dict(gridcolor='#EEEEEE'),
                          margin=dict(l=10, r=10, t=10, b=10))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, width='stretch')

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Enrollment size by phase')
        q1 = df[(df['Enrollment'] > 0) & (df['Phase'].isin(MAIN_PHASES))]
        if len(q1):
            fig = px.box(q1, x='Phase', y='Enrollment', category_orders={'Phase': MAIN_PHASES},
                        color_discrete_sequence=[BLUE], log_y=True,
                        labels={'Enrollment': 'Enrollment (log scale)', 'Phase': ''})
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Arial', size=11),
                              xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#EEEEEE'),
                              margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info('No enrollment data available for the current filter selection.')

    with col2:
        st.subheader('Therapeutic focus by sponsor')
        categorized = df[df['category'] != 'Other']
        if len(categorized) and categorized['Sponsor'].nunique() > 0:
            ct = (pd.crosstab(categorized['Sponsor'], categorized['category'], normalize='index') * 100).round(1)
            fig = px.imshow(ct, text_auto=True, color_continuous_scale='Blues',  # sequential — a % share
                            labels=dict(x='Therapeutic Area', y='', color='Share (%)'))
            fig.update_layout(font=dict(family='Arial', size=10), margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info('No categorized condition data available for the current filter selection.')

with st.expander('\U0001F4CA Show raw data sample'):
    st.dataframe(df.head(100), width='stretch')

st.divider()
st.caption('ClinicalTrials.gov data via Kaggle | No spatial/location data available in this dataset | '
          f'Filters: {len(st.session_state.flt_sponsors)} sponsor(s), '
          f'{len(st.session_state.flt_phases)} phase(s), {st.session_state.flt_years[0]}-{st.session_state.flt_years[1]}')
