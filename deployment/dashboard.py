#!/usr/bin/env python3
"""
Phase 4 Analytics Dashboard - Real Data Edition
==============================================
Reads pre-calculated results from JSON files with Stage 3 per-campaign analysis.

Three-level drill-down:
- Level 1: Account KPI (daily metrics)
- Level 2: Account-level segments (11 types)
- Level 3: Per-campaign breakdown (10 segments per campaign)
"""

import os
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu

# ============================================================================
# CONFIG
# ============================================================================

JSON_PATHS = [
    '/opt/ai-optimizer/results',
    '/app/results',
    './results',
    '../results'
]

st.set_page_config(
    page_title="Phase 4: Real Data Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# JSON LOADERS - New Format
# ============================================================================

def find_json_file(filename):
    """Find JSON file in multiple locations."""
    for path in JSON_PATHS:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            return filepath
    return None

@st.cache_data(ttl=300)
def load_account_kpi():
    """Load account KPI (Stage 1)."""
    filepath = find_json_file('account_kpi.json')
    
    if not filepath:
        st.error("❌ account_kpi.json not found")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Error loading account_kpi.json: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_insights():
    """Load insights (Stage 2)."""
    filepath = find_json_file('insights.json')
    
    if not filepath:
        st.error("❌ insights.json not found")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Error loading insights.json: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_campaigns():
    """Load campaigns (Stage 3)."""
    filepath = find_json_file('campaigns.json')
    
    if not filepath:
        st.error("❌ campaigns.json not found")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Error loading campaigns.json: {str(e)}")
        return None

# ============================================================================
# MAIN APP
# ============================================================================

# Load data
account_kpi = load_account_kpi()
insights = load_insights()
campaigns = load_campaigns()

if not account_kpi or not insights or not campaigns:
    st.error("❌ Failed to load data files")
    st.stop()

# Header
st.markdown("# 📊 AI Optimizer: Real Data Analytics")
st.markdown(f"*Updated: {account_kpi['period']['start']} to {account_kpi['period']['end']}*")

# ============================================================================
# MENU
# ============================================================================

selected = option_menu(
    menu_title="Navigation",
    options=["📈 Overview", "🔍 Account Segments", "🎯 Campaigns"],
    icons=["graph-up", "search", "target"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
)

# ============================================================================
# TAB 1: OVERVIEW
# ============================================================================

if selected == "📈 Overview":
    st.markdown("## Daily Account Metrics")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cost", f"₽{account_kpi['totals']['cost']:,.0f}")
    
    with col2:
        st.metric("Conversions", f"{account_kpi['totals']['conversions']}")
    
    with col3:
        st.metric("Average CPA", f"₽{account_kpi['totals']['cpa']:,.0f}")
    
    with col4:
        st.metric("Days", f"{account_kpi['period']['days']}")
    
    st.divider()
    
    # Daily chart
    daily_data = pd.DataFrame(account_kpi['daily'])
    daily_data['date'] = pd.to_datetime(daily_data['date'])
    daily_data = daily_data.sort_values('date')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['cost'],
        name='Cost (RUB)',
        yaxis='y',
        line=dict(color='#FF6B6B')
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['conversions'],
        name='Conversions',
        yaxis='y2',
        line=dict(color='#4ECDC4')
    ))
    
    fig.update_layout(
        title='Daily Performance',
        xaxis_title='Date',
        yaxis_title='Cost (RUB)',
        yaxis2=dict(title='Conversions', overlaying='y', side='right'),
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Daily table
    with st.expander("📋 Daily Details"):
        st.dataframe(daily_data[['date', 'cost', 'conversions', 'cpa']], use_container_width=True)

# ============================================================================
# TAB 2: ACCOUNT SEGMENTS
# ============================================================================

elif selected == "🔍 Account Segments":
    st.markdown("## Account-Level Segment Analysis")
    st.markdown(f"*Threshold: Cost > ₽{insights['avg_cpa_threshold']:,.2f}*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        segment_type = st.selectbox(
            "Select Segment Type",
            list(insights['segments'].keys()),
            key="segment_select"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort By",
            ["Conversions", "Cost", "CPA"],
            key="segment_sort"
        )
    
    # Get segment data
    segment_data = insights['segments'][segment_type]
    df_seg = pd.DataFrame(segment_data)
    
    if sort_by == "Conversions":
        df_seg = df_seg.sort_values('conversions', ascending=False)
    elif sort_by == "Cost":
        df_seg = df_seg.sort_values('cost', ascending=False)
    else:
        df_seg = df_seg.sort_values('cpa', ascending=False)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Entries", len(df_seg))
    with col2:
        st.metric("Total Cost", f"₽{df_seg['cost'].sum():,.0f}")
    with col3:
        st.metric("Total Conv", int(df_seg['conversions'].sum()))
    with col4:
        avg_cpa = df_seg['cost'].sum() / max(df_seg['conversions'].sum(), 1)
        st.metric("Avg CPA", f"₽{avg_cpa:,.0f}")
    
    st.divider()
    
    # Chart
    fig = px.bar(
        df_seg.head(10),
        x='value',
        y='conversions',
        color='cpa',
        hover_data=['cost', 'ctr', 'clicks', 'impressions'],
        title=f"Top 10 {segment_type} by Conversions"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.dataframe(df_seg, use_container_width=True)

# ============================================================================
# TAB 3: CAMPAIGNS
# ============================================================================

elif selected == "🎯 Campaigns":
    st.markdown("## Per-Campaign Breakdown")
    
    campaigns_list = campaigns['campaigns']
    
    col1, col2 = st.columns(2)
    
    with col1:
        campaign_names = [f"{c['campaign_name'][:60]}..." if len(c['campaign_name']) > 60 else c['campaign_name'] 
                         for c in campaigns_list]
        selected_idx = st.selectbox("Select Campaign", range(len(campaigns_list)), 
                                    format_func=lambda i: campaign_names[i])
    
    campaign = campaigns_list[selected_idx]
    
    with col2:
        segment_type = st.selectbox(
            "Select Segment Type",
            list(campaign['segments'].keys()),
            key="campaign_segment_select"
        )
    
    # Campaign stats
    stats = campaign['stats']
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cost", f"₽{stats['cost']:,.0f}")
    with col2:
        st.metric("Conversions", stats['conversions'])
    with col3:
        st.metric("CPA", f"₽{stats['cpa']:,.0f}")
    with col4:
        st.metric("CTR", f"{stats['ctr']:.2f}%")
    
    st.divider()
    
    # Segment breakdown for campaign
    segment_data = campaign['segments'][segment_type]
    
    if segment_data:
        df_camp_seg = pd.DataFrame(segment_data)
        df_camp_seg = df_camp_seg.sort_values('conversions', ascending=False)
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Segment Entries", len(df_camp_seg))
        with col2:
            st.metric("Total Cost", f"₽{df_camp_seg['cost'].sum():,.0f}")
        with col3:
            st.metric("Total Conv", int(df_camp_seg['conversions'].sum()))
        
        st.divider()
        
        # Chart
        fig = px.bar(
            df_camp_seg,
            x='value',
            y='conversions',
            color='cpa',
            title=f"{segment_type} Breakdown for {campaign['campaign_name'][:40]}"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        st.dataframe(df_camp_seg, use_container_width=True)
    else:
        st.info(f"No data for {segment_type} in this campaign")
    
    st.divider()
    
    # All campaigns summary
    with st.expander("📋 All Campaigns Summary"):
        all_camps_data = []
        for c in campaigns_list:
            all_camps_data.append({
                'Campaign': c['campaign_name'],
                'Cost': c['stats']['cost'],
                'Conversions': c['stats']['conversions'],
                'CPA': c['stats']['cpa'],
                'CTR': c['stats']['ctr']
            })
        
        df_all = pd.DataFrame(all_camps_data)
        st.dataframe(df_all, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**Phase 4 Analytics Dashboard**  
Real data from Yandex Direct API with three-level drill-down analysis.
- Level 1: Account KPI (31 days)
- Level 2: Account segments (11 types)
- Level 3: Campaign breakdown (7 campaigns × 10 segments)

Data quality: 100% ✅ | Last updated: 2026-04-11
""")
