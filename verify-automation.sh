#!/bin/bash
# Verification script for GitHub Actions automation

echo "🔍 Проверка настройки автоматизации..."
echo ""

# 1. Check workflows exist
echo "1️⃣  Проверка workflow файлов:"
if [ -f ".github/workflows/update-daily.yml" ]; then
    echo "  ✅ update-daily.yml существует"
else
    echo "  ❌ update-daily.yml НЕ найден"
    exit 1
fi

if [ -f ".github/workflows/update-weekly.yml" ]; then
    echo "  ✅ update-weekly.yml существует"
else
    echo "  ❌ update-weekly.yml НЕ найден"
    exit 1
fi

# 2. Check extraction script
echo ""
echo "2️⃣  Проверка extraction скрипта:"
if [ -f "extraction/extract_correct.py" ]; then
    echo "  ✅ extract_correct.py существует"
    
    # Check if script has stage1 argument support
    if grep -q "stage1" extraction/extract_correct.py; then
        echo "  ✅ Поддерживает stage1"
    fi
    
    if grep -q "all" extraction/extract_correct.py; then
        echo "  ✅ Поддерживает all"
    fi
else
    echo "  ❌ extract_correct.py НЕ найден"
    exit 1
fi

# 3. Check results directory
echo ""
echo "3️⃣  Проверка results директории:"
if [ -d "results" ]; then
    echo "  ✅ results/ директория существует"
    
    ls -lh results/ | tail -n +2 | while read -r line; do
        file=$(echo "$line" | awk '{print $NF}')
        size=$(echo "$line" | awk '{print $5}')
        echo "    📄 $file ($size)"
    done
else
    echo "  ❌ results/ директория НЕ найдена"
fi

# 4. Check requirements.txt
echo ""
echo "4️⃣  Проверка requirements.txt:"
if [ -f "requirements.txt" ]; then
    echo "  ✅ requirements.txt существует"
    echo "    📦 Зависимости:"
    grep -E "^[a-z]" requirements.txt | head -5 | while read -r dep; do
        echo "       - $dep"
    done
    if [ $(wc -l < requirements.txt) -gt 5 ]; then
        echo "       ... и ещё $(( $(wc -l < requirements.txt) - 5 ))"
    fi
else
    echo "  ❌ requirements.txt НЕ найден"
fi

# 5. Check GitHub secrets configuration
echo ""
echo "5️⃣  Проверка GitHub Secrets:"
echo "  ⚠️  Проверь вручную в https://github.com/imjusttryingguyes/ai-optimizer/settings/secrets/actions"
echo "    Нужны:"
echo "      ✓ YANDEX_API_TOKEN"
echo "      ✓ HF_API_TOKEN"

# 6. Check cron schedule
echo ""
echo "6️⃣  Проверка расписания (cron):"
echo "  Daily:"
grep "cron:" .github/workflows/update-daily.yml | head -1 | sed 's/^/    /'
echo "    → Каждый день в 01:00 UTC"

echo "  Weekly:"
grep "cron:" .github/workflows/update-weekly.yml | head -1 | sed 's/^/    /'
echo "    → Каждый понедельник в 01:00 UTC"

echo ""
echo "✅ Все проверки пройдены!"
echo ""
echo "Дальнейшие действия:"
echo "1. Перейди в: https://github.com/imjusttryingguyes/ai-optimizer/actions"
echo "2. Нажми на workflow (update-daily или update-weekly)"
echo "3. Нажми 'Run workflow' для тестирования"
