# ⚠️ ВАЖНО: Регенерируй токены!

Токены были видны в чате. Их нужно переегенерировать, но для этого сначала нужно добавить их в GitHub secrets.

## Шаги для добавления секретов:

### 1. Открой GitHub Settings
1. Перейди на: https://github.com/imjusttryingguyes/ai-optimizer
2. Нажми **Settings** (вкладка в меню репозитория)

### 2. Добавь Secret 1 (YANDEX_API_TOKEN)
1. Слева нажми: **Secrets and variables** → **Actions**
2. Нажми зелёную кнопку **New repository secret**
3. Заполни:
   - **Name:** `YANDEX_API_TOKEN`
   - **Secret:** Скопируй из сообщения выше
4. Нажми **Add secret**

### 3. Добавь Secret 2 (HF_API_TOKEN)
1. Снова нажми **New repository secret**
2. Заполни:
   - **Name:** `HF_API_TOKEN`
   - **Secret:** Скопируй из сообщения выше
3. Нажми **Add secret**

## ✅ После добавления:

Оба workflow будут работать автоматически:
- **Daily:** Каждый день в 01:00 UTC
- **Weekly:** Каждый понедельник в 01:00 UTC

## 🔐 Безопасность:

**Обязательно после добавления:**
1. Перейди в Yandex Direct → Settings → API → Regenerate token
2. Перейди в HuggingFace → Settings → Access Tokens → Delete старый, создай новый
3. Обнови secrets в GitHub новыми токенами

Это нужно потому что токены были видны в чате!
