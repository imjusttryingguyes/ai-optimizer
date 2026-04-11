#!/usr/bin/env python3
"""
Phase 4 Analytics Dashboard - JSON Edition with Level 3
===============================================

Reads pre-calculated results from JSON files instead of querying database.
Fast, secure, scalable visualization layer.

Now includes Level 3: Campaign-level analysis and insights.
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
    page_title="Phase 4: Аналитика кампаний",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# JSON LOADERS
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
    """Load account KPI data from JSON."""
    filepath = find_json_file('account_kpi.json')
    
    if not filepath:
        st.error("❌ account_kpi.json not found")
        st.stop()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'])
        st.session_state['account_cpa'] = data['account_cpa']
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading account_kpi.json: {str(e)}")
        st.stop()

@st.cache_data(ttl=300)
def load_insights():
    """Load insights (good/bad trends) from JSON."""
    filepath = find_json_file('insights.json')
    
    if not filepath:
        st.error("❌ insights.json not found")
        st.stop()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_trends = []
        for trend in data.get('good_trends', []):
            trend['classification'] = 'good'
            all_trends.append(trend)
        for trend in data.get('bad_trends', []):
            trend['classification'] = 'bad'
            all_trends.append(trend)
        
        df = pd.DataFrame(all_trends)
        return df
    except Exception as e:
        st.error(f"❌ Error loading insights.json: {str(e)}")
        st.stop()

@st.cache_data(ttl=300)
def load_campaigns():
    """Load campaign data from JSON."""
    filepath = find_json_file('campaigns.json')
    
    if not filepath:
        st.error("❌ campaigns.json not found")
        st.stop()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"❌ Error loading campaigns.json: {str(e)}")
        st.stop()

# ============================================================================
# PAGE: OVERVIEW
# ============================================================================

def page_overview():
    """Display account KPI overview."""
    st.header("📊 Overview - Account KPI")
    
    kpi_df = load_account_kpi()
    account_cpa = st.session_state.get('account_cpa', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cost", f"₽{kpi_df['cost'].sum():,.0f}")
    with col2:
        st.metric("Total Conversions", f"{kpi_df['conversions'].sum():,.0f}")
    with col3:
        st.metric("Average CPA", f"₽{account_cpa:,.0f}")
    with col4:
        st.metric("Period", f"{len(kpi_df)} days")
    
    st.divider()
    
    st.subheader("💰 Daily Cost")
    fig_cost = px.line(kpi_df, x='date', y='cost', markers=True,
                       labels={'date': 'Date', 'cost': 'Cost (₽)'})
    fig_cost.update_traces(line=dict(color='#FF6B6B', width=3))
    st.plotly_chart(fig_cost, use_container_width=True)
    
    st.subheader("🎯 Daily Conversions")
    fig_conv = px.bar(kpi_df, x='date', y='conversions',
                      labels={'date': 'Date', 'conversions': 'Conversions'},
                      color_discrete_sequence=['#4ECDC4'])
    st.plotly_chart(fig_conv, use_container_width=True)
    
    st.subheader("📋 Daily Details")
    st.dataframe(kpi_df, use_container_width=True)

# ============================================================================
# PAGE: INSIGHTS
# ============================================================================

def page_insights():
    """Display account trends insights."""
    st.header("📈 Insights - Segment Trends (30 days)")
    
    insights_df = load_insights()
    good_df = insights_df[insights_df['classification'] == 'good']
    bad_df = insights_df[insights_df['classification'] == 'bad']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Good Trends", len(good_df))
    with col2:
        st.metric("❌ Bad Trends", len(bad_df))
    with col3:
        st.metric("Total Segments", len(insights_df))
    
    st.divider()
    
    st.subheader("✅ Good Trends (CPA ≤ 67% of avg)")
    if not good_df.empty:
        display_good = good_df[['segment_type', 'segment_value', 'cost', 'conversions', 'cpa', 'ratio']].copy()
        display_good = display_good.sort_values('cost', ascending=False)
        st.dataframe(display_good, use_container_width=True)
    else:
        st.info("No good trends found")
    
    st.divider()
    
    st.subheader("❌ Bad Trends (CPA ≥ 150% of avg)")
    if not bad_df.empty:
        display_bad = bad_df[['segment_type', 'segment_value', 'cost', 'conversions', 'cpa', 'ratio']].copy()
        display_bad = display_bad.sort_values('ratio', ascending=False)
        st.dataframe(display_bad, use_container_width=True)
    else:
        st.info("No bad trends found")

# ============================================================================
# PAGE: CAMPAIGNS
# ============================================================================

def page_campaigns():
    """Display campaign-level analysis."""
    st.header("🎯 Campaigns - Level 3 Analysis")
    
    campaigns_data = load_campaigns()
    account_cpa = st.session_state.get('account_cpa', 7000)
    campaigns = campaigns_data.get('campaigns', [])
    
    if not campaigns:
        st.info("No campaigns data available")
        return
    
    # Campaign selector
    campaign_names = [f"{c['campaign_name']} (ID: {c['campaign_id']})" for c in campaigns]
    selected_idx = st.selectbox("Select Campaign:", range(len(campaigns)), 
                                format_func=lambda i: campaign_names[i])
    campaign = campaigns[selected_idx]
    
    st.divider()
    
    # Campaign header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Campaign:** {campaign['campaign_name']}")
    with col2:
        st.write(f"**Type:** {campaign['campaign_type']}")
    with col3:
        status_color = "🟢" if campaign['status'] == 'active' else "🔴"
        st.write(f"**Status:** {status_color} {campaign['status'].upper()}")
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 30-Day Stats", "📈 7-Day Comparison", "🔄 Dynamics"])
    
    # TAB 1: 30-Day Stats
    with tab1:
        st.subheader("30-Day Performance")
        stats_30d = campaign['stats_30d']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Cost", f"₽{stats_30d['cost']:,.0f}")
        with col2:
            st.metric("Conversions", f"{stats_30d['conversions']}")
        with col3:
            cpa_ratio = stats_30d['cpa'] / account_cpa
            delta_text = f"{cpa_ratio:.2f}x avg"
            st.metric("CPA", f"₽{stats_30d['cpa']:,.0f}", delta=delta_text)
        with col4:
            st.metric("CTR", f"{stats_30d['ctr']:.2f}%")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Impressions", f"{stats_30d['impressions']:,.0f}")
        with col2:
            st.metric("Clicks", f"{stats_30d['clicks']:,.0f}")
    
    # TAB 2: 7-Day Comparison
    with tab2:
        st.subheader("Last 7 Days vs Previous 7 Days")
        
        stats_7d = campaign['stats_7d']
        stats_7d_prev = campaign['stats_7d_prev']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Last 7 Days**")
            st.metric("Cost", f"₽{stats_7d['cost']:,.0f}")
            st.metric("CPA", f"₽{stats_7d['cpa']:,.0f}")
            st.metric("Conversions", f"{stats_7d['conversions']}")
        
        with col2:
            st.write("**Previous 7 Days**")
            st.metric("Cost", f"₽{stats_7d_prev['cost']:,.0f}")
            st.metric("CPA", f"₽{stats_7d_prev['cpa']:,.0f}")
            st.metric("Conversions", f"{stats_7d_prev['conversions']}")
        
        with col3:
            st.write("**Change (%)**")
            cost_change = ((stats_7d['cost'] - stats_7d_prev['cost']) / stats_7d_prev['cost']) * 100
            cpa_change = ((stats_7d['cpa'] - stats_7d_prev['cpa']) / stats_7d_prev['cpa']) * 100
            conv_change = ((stats_7d['conversions'] - stats_7d_prev['conversions']) / stats_7d_prev['conversions']) * 100
            
            st.metric("Cost Change", f"{cost_change:+.1f}%")
            st.metric("CPA Change", f"{cpa_change:+.1f}%")
            st.metric("Conv Change", f"{conv_change:+.1f}%")
    
    # TAB 3: Dynamics & Insights
    with tab3:
        st.subheader("Trend Analysis & Recommendations")
        
        dynamics = campaign.get('dynamics', {})
        trend = dynamics.get('trend', 'stable')
        
        # Trend indicator
        if trend == 'improving':
            trend_emoji = "📈"
            trend_color = "green"
        elif trend == 'declining':
            trend_emoji = "📉"
            trend_color = "red"
        else:
            trend_emoji = "➡️"
            trend_color = "blue"
        
        st.markdown(f"### {trend_emoji} Trend: **{trend.upper()}**")
        
        # Insights
        st.subheader("Insights & Recommendations")
        insights = campaign.get('insights', [])
        
        for insight in insights:
            insight_type = insight.get('type', 'info')
            message = insight.get('message', '')
            
            if insight_type == 'good':
                st.success(f"✅ {message}")
            elif insight_type == 'bad':
                st.error(f"❌ {message}")
            else:
                st.info(f"ℹ️ {message}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main dashboard."""
    
    with st.sidebar:
        page = option_menu(
            "Navigation",
            ["Overview", "Insights", "Campaigns"],
            icons=["graph-up", "bar-chart", "bullseye"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "#FF6B6B", "font-size": "25px"},
                "nav-link": {"font-size": "16px", "margin": "0px", "--hover-color": "#eee"},
            }
        )
        
        st.divider()
        
        st.info("""
        **ℹ️ Data Source**
        
        Results from JSON files (fast & secure).
        
        Updates: Daily via cron
        """)
    
    if page == "Overview":
        page_overview()
    elif page == "Insights":
        page_insights()
    elif page == "Campaigns":
        page_campaigns()

if __name__ == "__main__":
    main()
