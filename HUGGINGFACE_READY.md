# 🚀 HuggingFace Deployment Ready

All files are prepared and ready for deployment to HuggingFace Spaces.

## 📦 What's Ready

```
deployment/
├── app.py                       (Entry point)
├── dashboard.py                 (Streamlit app - 12 KB)
├── requirements.txt             (Dependencies)
├── .streamlit/config.toml       (Streamlit config)
└── results/
    ├── account_kpi.json         (Stage 1 data)
    ├── insights.json            (Stage 2 data)
    └── campaigns.json           (Stage 3 data)
```

**Total size**: ~92 KB (includes all JSON data)

---

## 🎯 Target Space

https://huggingface.co/spaces/SamShal1/phase4-analytics

---

## 🔧 How to Deploy

### Option 1: Web UI (Easiest)

1. Go to: https://huggingface.co/spaces/SamShal1/phase4-analytics
2. Click **Files** tab at top
3. Click **Upload files** button
4. Select and upload from `deployment/`:
   - `dashboard.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `results/account_kpi.json`
   - `results/insights.json`
   - `results/campaigns.json`
5. Click Upload → Done!
6. Space auto-reloads (~30 sec) → Dashboard goes live ✨

**Note**: Make sure to preserve the folder structure:
- `.streamlit/config.toml` must be in `.streamlit/` folder
- All JSON files must be in `results/` folder

### Option 2: Using Git CLI

Requires: HuggingFace token (create at https://huggingface.co/settings/tokens)

```bash
# 1. Export token
export HF_TOKEN="hf_xxxxx..."

# 2. Clone Space repo
git clone https://oauth2:${HF_TOKEN}@huggingface.co/spaces/SamShal1/phase4-analytics hf-space
cd hf-space

# 3. Copy files
cp ../deployment/dashboard.py .
cp ../deployment/requirements.txt .
cp -r ../deployment/.streamlit .
mkdir -p results
cp ../deployment/results/*.json results/

# 4. Commit and push
git add .
git commit -m "Update dashboard with Stage 3 analysis"
git push

# 5. Done! Space auto-reloads
```

### Option 3: Automated Script

```bash
export HF_TOKEN="hf_xxxxx..."
bash deployment/.deploy-hf.sh
```

---

## 📊 What's Inside

### Dashboard Tabs

1. **Overview** 📈
   - Daily metrics (31 days)
   - Total cost and conversions
   - Average CPA trend

2. **Insights** 🔍
   - 11 segment types (AdFormat, Device, Gender, Age, etc.)
   - Performance by segment
   - Identifies global opportunities

3. **Campaigns** 🎯
   - 7 campaigns with detailed breakdown
   - 10 segments per campaign
   - Campaign-specific insights

### Data

- **Period**: 2026-03-11 to 2026-04-10 (31 days)
- **Total Cost**: 3,171,798.08 RUB
- **Total Conversions**: 376 (goal-filtered)
- **Average CPA**: 8,435.63 RUB
- **Data Quality**: 100% verified (no garbage)

---

## ✅ Verification Checklist

After uploading, verify:

- [ ] Files are visible in Space → Files tab
- [ ] No error in Space → Logs (Settings → Logs)
- [ ] Dashboard loads: https://huggingface.co/spaces/SamShal1/phase4-analytics
- [ ] Can see 3 tabs: Overview, Insights, Campaigns
- [ ] Data loads correctly in each tab
- [ ] Can interact with filters (if present)

---

## 🔄 Updating Data

To refresh dashboard with new data:

1. Run extraction script to generate new JSON files:
   ```bash
   python3 extraction/extract_correct.py
   ```

2. Copy new results:
   ```bash
   cp results/*.json deployment/results/
   ```

3. Upload new results/\*.json files to Space (same process as above)

4. Space auto-reloads with fresh data

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard not loading | Check Logs (Settings → Logs for errors) |
| Blank page | Refresh browser (Cmd/Ctrl + Shift + R) |
| Data not showing | Verify all 3 JSON files in results/ folder |
| Module errors | Check requirements.txt has all deps |
| Font/styling issues | Clear browser cache |

---

## 📝 Next Steps

1. ✅ Deploy to HF Spaces (now)
2. ⏳ Share dashboard URL with stakeholders
3. ⏳ Set up automated daily extractions (cron job)
4. ⏳ Add real-time data updates

---

**Status**: ✅ Ready for deployment
**Space**: https://huggingface.co/spaces/SamShal1/phase4-analytics
**GitHub**: https://github.com/imjusttryingguyes/ai-optimizer

