#!/bin/bash

# Start Streamlit KPI Dashboard

cd "$(dirname "$0")" || exit 1

echo "🚀 Запуск Streamlit KPI Dashboard..."
echo "📍 Дашборд будет доступен по адресу:"
echo "   - Локально:  http://localhost:8501"
echo "   - По сети:   http://127.0.0.1:8501"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

streamlit run dashboard_streamlit.py \
    --server.address 0.0.0.0 \
    --client.showErrorDetails=true \
    --logger.level=info
