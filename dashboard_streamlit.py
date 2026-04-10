import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime, date
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from analytics.kpi_engine import KPICalculationEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit configuration
st.set_page_config(
    page_title="KPI Dashboard - AI Optimizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .status-ok { color: #10b981; font-weight: bold; }
    .status-warning { color: #f59e0b; font-weight: bold; }
    .status-critical { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ai_optimizer'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def get_accounts():
    """Get available accounts"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT account_id 
            FROM (
                SELECT DISTINCT account_id FROM kpi_daily_summary
                UNION
                SELECT DISTINCT account_id FROM kpi_monthly_plan
            ) t
            ORDER BY account_id
        """)
        accounts = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        logger.info(f"Loaded {len(accounts)} accounts")
        return accounts
    except Exception as e:
        logger.error(f"Error loading accounts: {e}")
        st.error(f"❌ Ошибка подключения к БД: {str(e)}")
        return []

def get_current_plan(account_id):
    """Get current month's KPI plan"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        today = date.today()
        year_month = f"{today.year}-{today.month:02d}"
        
        cur.execute("""
            SELECT budget_rub, leads_target, cpa_target_rub, roi_target
            FROM kpi_monthly_plan
            WHERE account_id = %s AND year_month = %s
        """, (account_id, year_month))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                "budget": result[0],
                "leads": result[1],
                "cpa": result[2],
                "roi": result[3]
            }
        return None
    except Exception as e:
        st.error(f"❌ Ошибка загрузки плана: {str(e)}")
        return None

def save_plan(account_id, year_month, budget, leads, cpa, roi=None):
    """Save KPI plan"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO kpi_monthly_plan (account_id, year_month, budget_rub, leads_target, cpa_target_rub, roi_target, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (account_id, year_month) DO UPDATE SET
                budget_rub = %s,
                leads_target = %s,
                cpa_target_rub = %s,
                roi_target = %s,
                updated_at = NOW()
        """, (account_id, year_month, budget, leads, cpa, roi, budget, leads, cpa, roi))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {str(e)}")
        return False

def get_kpi_status(account_id):
    """Get KPI status and metrics"""
    try:
        conn = get_db_connection()
        engine = KPICalculationEngine(conn)
        status = engine.calculate_kpi_status(account_id)
        engine.close()
        conn.close()
        
        # Handle error response
        if isinstance(status, dict) and 'error' in status:
            return None
        
        return status
    except Exception as e:
        st.error(f"❌ Ошибка расчета KPI: {str(e)}")
        return None

# Main UI
st.title("📊 KPI Dashboard - AI Optimizer")

# Sidebar
with st.sidebar:
    st.header("⚙️ Настройки")
    accounts = get_accounts()
    
    if not accounts:
        st.warning("⚠️ Нет доступных аккаунтов")
        st.stop()
    
    selected_account = st.selectbox(
        "Выберите аккаунт:",
        accounts,
        key="account_select"
    )

# Main content
if selected_account:
    # Get current plan
    current_plan = get_current_plan(selected_account)
    today = date.today()
    current_month = f"{today.year}-{today.month:02d}"
    
    # Create tabs
    tab1, tab2 = st.tabs(["📈 KPI Статус", "⚙️ Установить KPI"])
    
    with tab2:
        st.header(f"Установить KPI на {current_month}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            month_input = st.text_input(
                "Месяц (YYYY-MM):",
                value=current_month,
                help="Формат: 2026-04"
            )
            budget_input = st.number_input(
                "Бюджет (₽):",
                value=float(current_plan['budget']) if current_plan else 100000.0,
                min_value=0.0,
                step=1000.0
            )
        
        with col2:
            leads_input = st.number_input(
                "Целевое количество лидов:",
                value=int(current_plan['leads']) if current_plan else 100,
                min_value=0,
                step=1
            )
            cpa_input = st.number_input(
                "Целевой CPA (₽):",
                value=float(current_plan['cpa']) if current_plan else 1000.0,
                min_value=0.0,
                step=100.0
            )
        
        roi_input = st.number_input(
            "ROI Target (% - опционально):",
            value=float(current_plan['roi']) if current_plan and current_plan['roi'] else 0.0,
            min_value=0.0,
            step=10.0
        )
        
        if st.button("💾 Сохранить KPI", key="save_kpi", use_container_width=True):
            if save_plan(selected_account, month_input, budget_input, leads_input, cpa_input, roi_input if roi_input > 0 else None):
                st.success(f"✅ KPI сохранён для {month_input}")
                st.rerun()
            else:
                st.error("❌ Ошибка при сохранении")
    
    with tab1:
        st.header(f"Статус KPI для {selected_account}")
        
        # Load KPI status
        kpi_status = get_kpi_status(selected_account)
        
        if kpi_status is None:
            st.info("📋 Установите KPI план в соседней вкладке для просмотра метрик")
        else:
            # Metrics Row 1
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                budget_data = kpi_status.get('budget', {})
                st.metric(
                    "💰 Бюджет",
                    f"{budget_data.get('spent', 0):,.0f} ₽",
                    f"План: {budget_data.get('target', 0):,.0f} ₽",
                    delta_color="off"
                )
                st.write(f"Темп: **{budget_data.get('pacing_pct', 0):.0f}%**")
            
            with col2:
                conv_data = kpi_status.get('conversions', {})
                st.metric(
                    "📊 Лиды",
                    f"{conv_data.get('actual', 0)} шт",
                    f"План: {conv_data.get('target', 0)} шт",
                    delta_color="off"
                )
                st.write(f"Темп: **{conv_data.get('pacing_pct', 0):.0f}%**")
            
            with col3:
                cpa_data = kpi_status.get('cpa', {})
                st.metric(
                    "💵 CPA",
                    f"{cpa_data.get('actual', 0):,.0f} ₽",
                    f"План: {cpa_data.get('target', 0):,.0f} ₽",
                    delta_color="off"
                )
                deviation = cpa_data.get('deviation_pct', 0)
                st.write(f"Отклонение: **{deviation:+.0f}%**")
            
            with col4:
                summary = kpi_status.get('summary', {})
                status_color = summary.get('overall_status', 'warning')
                st.metric(
                    "✅ Статус",
                    status_color.upper(),
                    "",
                    delta_color="off"
                )
            
            # Forecast
            st.divider()
            st.subheader("🔮 Прогноз на конец месяца")
            
            col1, col2, col3 = st.columns(3)
            
            forecast = kpi_status.get('forecast', {})
            
            with col1:
                st.metric(
                    "Расход",
                    f"{forecast.get('end_month_spend', 0):,.0f} ₽"
                )
            
            with col2:
                st.metric(
                    "Лиды",
                    f"{forecast.get('end_month_conversions', 0)} шт"
                )
            
            with col3:
                st.metric(
                    "CPA",
                    f"{forecast.get('end_month_cpa', 0):,.0f} ₽"
                )
            
            # Alerts
            alerts = kpi_status.get('summary', {}).get('key_alerts', [])
            if alerts:
                st.divider()
                st.subheader("⚠️ Алерты")
                for alert in alerts:
                    st.warning(alert)

else:
    st.info("👈 Выберите аккаунт в левой панели для начала")
