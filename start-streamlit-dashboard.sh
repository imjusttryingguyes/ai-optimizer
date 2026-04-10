#!/bin/bash

# Start Streamlit KPI Dashboard

cd "$(dirname "$0")" || exit 1

echo "🚀 Запуск Streamlit KPI Dashboard..."
echo "📍 Дашборд будет доступен по адресу: http://localhost:8501"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

streamlit run dashboard_streamlit.py \
    --client.toolbarPosition=top \
    --client.showErrorDetails=true \
    --logger.level=info
