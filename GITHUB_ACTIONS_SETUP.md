# Setup GitHub Actions Secrets

Чтобы автоматизированные обновления работали, нужно добавить секреты в GitHub:

## Как добавить secrets:

1. Перейди на страницу репозитория: https://github.com/imjusttryingguyes/ai-optimizer
2. Нажми **Settings** → **Secrets and variables** → **Actions**
3. Нажми **New repository secret** для каждого:

### Secret 1: YANDEX_API_TOKEN
- **Name:** `YANDEX_API_TOKEN`
- **Value:** Твой токен Yandex Direct API
- Получить: https://yandex.com/dev/direct/

### Secret 2: HF_API_TOKEN
- **Name:** `HF_API_TOKEN`
- **Value:** Твой токен HuggingFace
- Получить: https://huggingface.co/settings/tokens

## Проверка:

После добавления секретов, можешь протестировать workflow:

```bash
# Manually trigger daily update
curl -X POST https://api.github.com/repos/imjusttryingguyes/ai-optimizer/actions/workflows/update-daily.yml/dispatches \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"ref":"main"}'
```

## Расписание:

- **Daily:** Каждый день в 01:00 UTC (обновляет Tab 1)
- **Weekly:** Каждый понедельник в 01:00 UTC (обновляет Tabs 1-3)

---

После установки секретов, workflow будет работать автоматически! ✅
