# 🚀 Quick Installation Guide

## Step 1: Download All Files

Download the entire `manifest_system_modular` folder which contains:
```
manifest_system_modular/
├── streamlit_app.py
├── README.md
├── INSTALL.md (this file)
└── modules/
    ├── __init__.py
    ├── config.py
    ├── logger.py
    ├── session_manager.py
    ├── sql_utils.py
    ├── database.py
    └── ui_components.py
```

## Step 2: Upload to Snowflake

### Option A: Using Snowflake UI

1. Go to your Snowflake Streamlit app
2. Delete the old `streamlit_app.py` if it exists
3. Upload the new `streamlit_app.py`
4. Create a folder called `modules`
5. Upload all files from the `modules/` folder into this folder

### Option B: Using Snowflake CLI (if available)

```bash
snow streamlit deploy --replace
```

## Step 3: Verify Installation

Your file structure in Snowflake should look like:

```
Your_Streamlit_App/
├── streamlit_app.py         ← Main file
└── modules/                 ← Folder
    ├── __init__.py
    ├── config.py
    ├── logger.py
    ├── session_manager.py
    ├── sql_utils.py
    ├── database.py
    └── ui_components.py
```

## Step 4: Run the App

1. Click "Run" or refresh your Streamlit app
2. You should see "PCON Manifest System" at the top
3. Check the sidebar - it should show "System Logs" section
4. If you see any errors, download the log file

## Step 5: Test

Test each feature:
- ✅ Create a manifest
- ✅ Add a stop
- ✅ Add a shipment
- ✅ Add multiple SIDs
- ✅ Add OSD entries
- ✅ Retrieve a manifest

## ⚠️ Common Installation Issues

### Issue: "No module named 'modules'"

**Cause:** The `modules/` folder is not in the right location

**Fix:**
1. Make sure `modules/` is a folder (not individual files)
2. It should be at the same level as `streamlit_app.py`

### Issue: "ImportError: cannot import name 'X'"

**Cause:** Missing file in the `modules/` folder

**Fix:** Make sure ALL 7 files are uploaded to the `modules/` folder:
- `__init__.py`
- `config.py`
- `logger.py`
- `session_manager.py`
- `sql_utils.py`
- `database.py`
- `ui_components.py`

### Issue: App shows errors immediately

**Cause:** Database connection issue

**Fix:**
1. Check that you're using Snowflake's native Streamlit (not external)
2. Verify database and schema names in `modules/config.py`:
   ```python
   DB_NAME = "SSZ_ADMIN_DB"  # ← Check this
   SCHEMA_NAME = "PCON"      # ← Check this
   ```

## 🎉 Success!

If everything works, you should see:
- No errors on page load
- "System Logs" in sidebar showing "✅ No errors"
- All three navigation buttons working
- Forms accepting input without errors

## 📝 Next Steps

1. Read the full README.md for detailed documentation
2. Test all features to ensure everything works
3. If you encounter bugs, download the log file
4. The logs will show you exactly what went wrong!

## 🆘 Need Help?

If something's not working:
1. Download the log file from the sidebar
2. Look for ERROR entries
3. The traceback will show which file/line has the issue
4. You can then pinpoint the problem quickly!

---

**Remember:** This modular structure makes debugging 100x easier than the old single-file version! 🎯
