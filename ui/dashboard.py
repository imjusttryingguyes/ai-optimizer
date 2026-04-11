#!/usr/bin/env python3
"""
Phase 4 Analytics Dashboard
============================
Modern Streamlit dashboard for three-level analytics visualization.

Complete fresh build - no legacy code, clean architecture.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu

# Load environment variables - works both locally and on HF
load_dotenv()  # Will find .env in current directory if exists
# On HuggingFace, variables come from Repository Secrets as env vars

# ============================================================================
# CONFIG
# ============================================================================

DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
YANDEX_LOGIN = os.getenv('YANDEX_LOGIN')

# Check if all required env vars are set
if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    st.error("❌ Missing database configuration. Please add all required Secrets to HF Settings.")
    st.stop()

st.set_page_config(
    page_title="Phase 4: Аналитика кампаний",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# DATABASE
# ============================================================================

@st.cache_resource
def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )


def execute_query_safe(query, retries=2):
    """
    Execute query with automatic retry on connection failure.
    
    Handles:
    - Connection closed by server
    - Stale connections from cache
    - Network timeouts
    """
    import psycopg2
    
    last_error = None
    for attempt in range(retries):
        try:
            conn = get_db_conn()
            df = execute_query_safe(query)
            conn.close()
            return df
        except (psycopg2.InterfaceError, psycopg2.OperationalError, Exception) as e:
            last_error = e
            if attempt < retries - 1:
                # Try again
                continue
            else:
                # Out of retries
                raise
    
    raise last_error


# ============================================================================
# DATA LOADERS
# ============================================================================

@st.cache_data(ttl=300)  # Cache 5 minutes
def load_account_kpi():
    """Load Level 1: Daily KPI."""
    conn = get_db_conn()
    query = """
        SELECT date, cost, conversions, cpa
        FROM account_kpi
        ORDER BY date
    """
    df = execute_query_safe(query)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_insights():
    """Load Level 2: 30-day trends."""
    conn = get_db_conn()
    query = """
        SELECT segment_type, segment_value, classification, 
               cost, conversions, cpa, ratio_to_account
        FROM segment_trends_30d
        ORDER BY classification DESC, ratio_to_account DESC
    """
    df = execute_query_safe(query)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_campaign_insights(segment_type, segment_value):
    """Load Level 3: Campaign drill-down."""
    conn = get_db_conn()
    query = """
        SELECT campaign_id, campaign_type, cost, conversions, 
               cpa, classification, ratio_to_account
        FROM campaign_insights_30d
        WHERE segment_type = %s AND segment_value = %s
        ORDER BY cost DESC
        LIMIT 10
    """
    df = pd.read_sql(query, conn, params=(segment_type, segment_value))
    conn.close()
    return df

# ============================================================================
# PAGE: ОБЗОР (Overview)
# ============================================================================

def page_overview():
    st.title("📊 Аналитика кампаний. Phase 4")
    st.subheader("Три уровня анализа: KPI → Инсайты → Кампании")
    
    # Load data
    kpi_df = load_account_kpi()
    insights_df = load_insights()
    
    if kpi_df.empty:
        st.error("❌ Нет данных в базе. Запустите extraction scripts!")
        return
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_cost = kpi_df['cost'].sum()
    total_conv = kpi_df['conversions'].sum()
    account_cpa = total_cost / total_conv if total_conv > 0 else 0
    days_count = len(kpi_df)
    
    with col1:
        st.metric("💰 Расход 30 дней", f"{total_cost:,.0f}₽")
    
    with col2:
        st.metric("🎯 Конверсии", f"{total_conv:,.0f}")
    
    with col3:
        st.metric("📈 Средний CPA", f"{account_cpa:,.0f}₽")
    
    with col4:
        st.metric("📅 Дней данных", f"{days_count}")
    
    st.divider()
    
    # Daily trend
    st.subheader("📉 Динамика расхода и конверсий")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=kpi_df['date'], y=kpi_df['cost'],
        name='Расход', yaxis='y1',
        line=dict(color='#FF6B6B', width=2),
        hovertemplate='%{x|%d.%m}: %{y:,.0f}₽<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=kpi_df['date'], y=kpi_df['conversions'],
        name='Конверсии', yaxis='y2',
        line=dict(color='#4ECDC4', width=2),
        hovertemplate='%{x|%d.%m}: %{y} conv<extra></extra>'
    ))
    
    fig.update_layout(
        title="Расход vs Конверсии (30 дней)",
        hovermode='x unified',
        height=400,
        yaxis=dict(title='Расход (₽)', titlefont=dict(color='#FF6B6B')),
        yaxis2=dict(title='Конверсии', titlefont=dict(color='#4ECDC4'), 
                    overlaying='y', side='right')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Daily CPA trend
    st.subheader("💹 Тренд CPA по дням")
    
    fig_cpa = go.Figure()
    fig_cpa.add_trace(go.Scatter(
        x=kpi_df['date'], y=kpi_df['cpa'],
        name='CPA',
        fill='tozeroy',
        line=dict(color='#95E1D3', width=2),
        hovertemplate='%{x|%d.%m}: %{y:,.0f}₽<extra></extra>'
    ))
    
    fig_cpa.add_hline(y=account_cpa, line_dash="dash", line_color="red",
                      annotation_text=f"Средний: {account_cpa:,.0f}₽")
    
    fig_cpa.update_layout(
        title="CPA по дням (плюс средний в красном)",
        height=300,
        hovermode='x'
    )
    
    st.plotly_chart(fig_cpa, use_container_width=True)
    
    # Insights summary
    st.divider()
    st.subheader("🎯 Инсайты (30 дней)")
    
    col1, col2, col3 = st.columns(3)
    
    good_count = len(insights_df[insights_df['classification'] == 'good'])
    bad_count = len(insights_df[insights_df['classification'] == 'bad'])
    
    with col1:
        st.metric("✅ Хорошие сегменты", good_count, 
                  help="CPA ≤ 0.67x средней, conv ≥ 2")
    
    with col2:
        st.metric("❌ Проблемные сегменты", bad_count,
                  help="CPA ≥ 1.5x средней")
    
    with col3:
        st.metric("📊 Всего инсайтов", len(insights_df))

# ============================================================================
# PAGE: ИНСАЙТЫ (Insights)
# ============================================================================

def page_insights():
    st.title("🎯 Инсайты. Уровень 2")
    st.subheader("Анализ 11 типов сегментов (30 дней)")
    
    insights_df = load_insights()
    
    if insights_df.empty:
        st.error("❌ Нет инсайтов. Запустите level2_trends.py")
        return
    
    # Filter controls
    col1, col2 = st.columns(2)
    
    with col1:
        classification_filter = st.radio(
            "Фильтр по типу:",
            ["Все", "Хорошие (✅)", "Проблемные (❌)"],
            horizontal=True
        )
    
    with col2:
        segment_types = ["Все"] + sorted(insights_df['segment_type'].unique().tolist())
        segment_filter = st.selectbox("Тип сегмента:", segment_types)
    
    # Apply filters
    filtered_df = insights_df.copy()
    
    if classification_filter == "Хорошие (✅)":
        filtered_df = filtered_df[filtered_df['classification'] == 'good']
    elif classification_filter == "Проблемные (❌)":
        filtered_df = filtered_df[filtered_df['classification'] == 'bad']
    
    if segment_filter != "Все":
        filtered_df = filtered_df[filtered_df['segment_type'] == segment_filter]
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 CPA Ratio (vs средний)")
        
        # Color by classification
        colors = ['#2ECC71' if c == 'good' else '#E74C3C' 
                  for c in filtered_df['classification']]
        
        fig = px.bar(
            filtered_df.sort_values('ratio_to_account', ascending=True),
            x='ratio_to_account',
            y='segment_value',
            color='classification',
            color_discrete_map={'good': '#2ECC71', 'bad': '#E74C3C'},
            title="CPA Ratio (ниже 0.67 = хорошо, выше 1.5 = плохо)",
            labels={'ratio_to_account': 'CPA Ratio', 'segment_value': ''},
            height=500,
            orientation='h'
        )
        fig.add_vline(x=1, line_dash="dash", line_color="gray", 
                      annotation_text="= средняя")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 Расход & Конверсии")
        
        fig = px.scatter(
            filtered_df,
            x='conversions', y='cost',
            color='classification',
            size='cpa',
            hover_data=['segment_type', 'segment_value', 'cpa'],
            color_discrete_map={'good': '#2ECC71', 'bad': '#E74C3C'},
            title="Расход vs Конверсии (размер = CPA)",
            labels={'conversions': 'Конверсии', 'cost': 'Расход (₽)'},
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.divider()
    st.subheader("📋 Таблица инсайтов")
    
    display_df = filtered_df[[
        'segment_type', 'segment_value', 'classification',
        'cost', 'conversions', 'cpa', 'ratio_to_account'
    ]].copy()
    
    display_df.columns = [
        'Тип', 'Значение', 'Класс',
        'Расход (₽)', 'Conv', 'CPA (₽)', 'Ratio'
    ]
    
    display_df['Тип'] = display_df['Тип'].astype(str)
    display_df['Расход (₽)'] = display_df['Расход (₽)'].apply(lambda x: f"{x:,.0f}")
    display_df['CPA (₽)'] = display_df['CPA (₽)'].apply(lambda x: f"{x:,.0f}")
    display_df['Ratio'] = display_df['Ratio'].apply(lambda x: f"{x:.2f}x")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ============================================================================
# PAGE: КАМПАНИИ (Campaigns)
# ============================================================================

def page_campaigns():
    st.title("🚀 Кампании. Уровень 3")
    st.subheader("드릴-даун: какие кампании разъезжают каждый сегмент?")
    
    insights_df = load_insights()
    
    if insights_df.empty:
        st.error("❌ Нет инсайтов для drill-down")
        return
    
    # Select segment to drill into
    st.subheader("Выбери сегмент для анализа")
    
    col1, col2 = st.columns(2)
    
    with col1:
        segment_type = st.selectbox(
            "Тип сегмента:",
            sorted(insights_df['segment_type'].unique())
        )
    
    filtered_by_type = insights_df[insights_df['segment_type'] == segment_type]
    
    with col2:
        segment_value = st.selectbox(
            "Значение:",
            sorted(filtered_by_type['segment_value'].unique())
        )
    
    # Get campaign data
    campaigns_df = load_campaign_insights(segment_type, segment_value)
    
    if campaigns_df.empty:
        st.warning(f"⚠️  Нет данных по кампаниям для {segment_type}={segment_value}")
        st.info("Подсказка: Level 3 extraction еще не запущен. Запустите level3_campaign_30d.py")
        return
    
    # Summary
    st.divider()
    st.subheader(f"📊 Топ кампании: {segment_type} = {segment_value}")
    
    col1, col2, col3 = st.columns(3)
    
    total_campaign_cost = campaigns_df['cost'].sum()
    total_campaign_conv = campaigns_df['conversions'].sum()
    avg_campaign_cpa = total_campaign_cost / total_campaign_conv if total_campaign_conv > 0 else 0
    
    with col1:
        st.metric("💰 Расход (топ 10)", f"{total_campaign_cost:,.0f}₽")
    
    with col2:
        st.metric("🎯 Конверсии", f"{total_campaign_conv:,.0f}")
    
    with col3:
        st.metric("📈 Средний CPA", f"{avg_campaign_cpa:,.0f}₽")
    
    # Visualization
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            campaigns_df.sort_values('cost', ascending=True),
            x='cost', y='campaign_id',
            color='classification',
            color_discrete_map={'good': '#2ECC71', 'bad': '#E74C3C'},
            title="Расход по кампаниям",
            labels={'cost': 'Расход (₽)', 'campaign_id': 'Campaign ID'},
            height=400,
            orientation='h'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(
            campaigns_df,
            x='conversions', y='cpa',
            color='classification',
            size='cost',
            hover_data=['campaign_id', 'campaign_type'],
            color_discrete_map={'good': '#2ECC71', 'bad': '#E74C3C'},
            title="CPA vs Конверсии",
            labels={'conversions': 'Конверсии', 'cpa': 'CPA (₽)'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.divider()
    st.subheader("📋 Таблица кампаний")
    
    display_df = campaigns_df[[
        'campaign_id', 'campaign_type', 'classification',
        'cost', 'conversions', 'cpa', 'ratio_to_account'
    ]].copy()
    
    display_df.columns = [
        'ID', 'Тип', 'Класс',
        'Расход (₽)', 'Conv', 'CPA (₽)', 'Ratio'
    ]
    
    display_df['Расход (₽)'] = display_df['Расход (₽)'].apply(lambda x: f"{x:,.0f}")
    display_df['CPA (₽)'] = display_df['CPA (₽)'].apply(lambda x: f"{x:,.0f}")
    display_df['Ratio'] = display_df['Ratio'].apply(lambda x: f"{x:.2f}x")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ============================================================================
# MAIN NAVIGATION
# ============================================================================

def main():
    st.sidebar.title("📊 Phase 4 Analytics")
    
    page = st.sidebar.radio(
        "Навигация:",
        ["📈 Обзор", "🎯 Инсайты", "🚀 Кампании"],
        label_visibility="collapsed"
    )
    
    st.sidebar.divider()
    
    # Sidebar info
    st.sidebar.subheader("ℹ️ Информация")
    st.sidebar.markdown("""
    **Phase 4: Три уровня анализа**
    
    1. **L1**: Дневные KPI (30 строк)
    2. **L2**: Инсайты по сегментам (33 строки)
    3. **L3**: Drill-down по кампаниям
    
    **Фильтр**: Только сегменты с расходом ≥ среднему CPA
    
    **Классификация**:
    - ✅ Хорошо: CPA ≤ 0.67x, conv ≥ 2
    - ❌ Плохо: CPA ≥ 1.5x
    """)
    
    st.sidebar.divider()
    
    # Refresh button
    if st.sidebar.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()
    
    # Render page
    if "📈 Обзор" in page:
        page_overview()
    elif "🎯 Инсайты" in page:
        page_insights()
    elif "🚀 Кампании" in page:
        page_campaigns()

if __name__ == '__main__':
    main()
