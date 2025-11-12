# 🏗️ System Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       STREAMLIT_APP.PY                          │
│                     (Main Entry Point)                          │
│                                                                 │
│  - Initializes all components                                   │
│  - Handles top-level errors                                     │
│  - Orchestrates the application                                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ├──────────────────┬───────────────────┬───────────────┐
                   │                  │                   │               │
                   ▼                  ▼                   ▼               ▼
        ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   CONFIG.PY      │  │  LOGGER.PY   │  │ SESSION_     │  │ SQL_UTILS.PY │
        │                  │  │              │  │ MANAGER.PY   │  │              │
        │ • DB Settings    │  │ • Error Log  │  │              │  │ • SQL Escape │
        │ • Table Names    │  │ • Info Log   │  │ • State Get  │  │ • ID Gen     │
        │ • Constants      │  │ • Warnings   │  │ • State Set  │  │ • Increment  │
        └──────────────────┘  │ • Download   │  │ • Panels     │  └──────────────┘
                              └──────────────┘  └──────────────┘
                                     │                 │                 │
                                     └────────┬────────┴─────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │   DATABASE.PY    │
                                     │                  │
                                     │ • Manifest Ops   │
                                     │ • Stop Ops       │
                                     │ • Shipment Ops   │
                                     │ • SID Ops        │
                                     │ • OSD Ops        │
                                     └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │ UI_COMPONENTS.PY │
                                     │                  │
                                     │ • Navigation     │
                                     │ • Forms          │
                                     │ • Data Display   │
                                     │ • Interactions   │
                                     └──────────────────┘
```

## Data Flow

### Creating a Manifest

```
User Input
    │
    ▼
UI Components (render_manifest_form)
    │
    ▼
Session Manager (validate & store)
    │
    ▼
Database Manager (insert_manifest)
    │
    ├─► SQL Utils (escape inputs, generate IDs)
    │
    ├─► Logger (log success/errors)
    │
    └─► Snowflake Database
            │
            ▼
        Success/Error
            │
            ▼
        UI Components (show message)
            │
            ▼
        User sees result
```

### Adding SIDs (Fixed!)

```
User clicks "Multiple SID/PO"
    │
    ▼
Session Manager (open_panel)
    │
    ▼
UI Components (render_sid_editor)
    │
    ├─► Session Manager (get_sid_rows)
    │   └─► Returns current rows ["SID1", "SID2", ...]
    │
    ▼
User enters/edits SIDs
    │
    ▼
User clicks "Save SIDs"
    │
    ▼
Database Manager (add_multiple_sids)
    │
    ├─► Filters duplicates
    ├─► Generates SID_IDs
    ├─► Inserts into database
    │
    ▼
Session Manager (clear_sid_editor)
    │
    ▼
Logger (log success)
    │
    ▼
UI Components (show success & rerun)
```

### Adding OSD (Fixed!)

```
User clicks "OSD"
    │
    ▼
Session Manager (open_panel)
    │
    ▼
UI Components (render_osd_editor)
    │
    ├─► Database Manager (get_osd_for_order)
    │   └─► Shows existing OSD entries
    │
    ▼
User fills OSD form (NO st.form!)
    │
    ├─► Reason Code: selectbox
    ├─► Pallets/Boxes: number_input
    └─► Comments: text_input
    │
    ▼
User clicks "Add OSD Row"
    │
    ▼
Database Manager (insert_osd)
    │
    ├─► Generates OSD_INDEX
    ├─► Inserts into database
    │
    ▼
Session Manager (close_panel)  ← Closes panel to reset form!
    │
    ▼
Logger (log success)
    │
    ▼
UI Components (show success & rerun)
```

## Module Responsibilities

### 1. **streamlit_app.py**
**Role:** Application orchestrator  
**Does:**
- Imports all modules
- Sets up page config
- Initializes components
- Catches top-level errors
- Shows sidebar with logs

**Doesn't:**
- Handle business logic
- Interact with database directly
- Manage session state directly
- Render complex UI

---

### 2. **config.py**
**Role:** Central configuration  
**Does:**
- Define database/schema names
- Define table names
- Define constants (HAZMAT options, OSD codes)
- Provide helper functions (get_table_names)

**Doesn't:**
- Contain any business logic
- Interact with database
- Store state

---

### 3. **logger.py**
**Role:** Error tracking and reporting  
**Does:**
- Log errors with full traceback
- Log warnings
- Log info messages
- Generate downloadable log files
- Track error counts

**Doesn't:**
- Handle errors (just logs them)
- Interact with database
- Render UI

---

### 4. **session_manager.py**
**Role:** Safe state management  
**Does:**
- Get/set/delete session state safely
- Manage mode (create/retrieve)
- Manage current manifest/stop
- Track panel open/close state
- Clear form data
- Reset application state

**Doesn't:**
- Render UI
- Interact with database
- Generate IDs

---

### 5. **sql_utils.py**
**Role:** SQL utilities  
**Does:**
- Escape SQL strings
- Convert Python values to SQL literals
- Generate AAAA0000 style IDs
- Increment IDs

**Doesn't:**
- Execute queries (just builds them)
- Manage state
- Render UI

---

### 6. **database.py**
**Role:** Data access layer  
**Does:**
- All database operations
- CRUD for manifests
- CRUD for stops
- CRUD for shipments
- CRUD for SIDs
- CRUD for OSDs
- Cascade deletes

**Uses:**
- sql_utils (for escaping & IDs)
- Snowpark session (for queries)

**Doesn't:**
- Render UI
- Manage session state
- Handle user input

---

### 7. **ui_components.py**
**Role:** Presentation layer  
**Does:**
- Render all UI elements
- Handle user interactions
- Display data
- Show forms
- Manage panels (SID/OSD editors)

**Uses:**
- database.py (for data)
- session_manager.py (for state)
- logger.py (for errors)

**Doesn't:**
- Execute SQL directly
- Generate IDs
- Manage state directly

---

## Error Handling Flow

```
Something goes wrong
    │
    ▼
Exception is raised
    │
    ▼
Caught in try-except block
    │
    ├─► Logger.log_error(message, exception)
    │       │
    │       ├─► Adds to logs list
    │       ├─► Increments error count
    │       ├─► Stores full traceback
    │       └─► Prints to console
    │
    ├─► st.error("User-friendly message")
    │       └─► Shows error to user
    │
    └─► Application continues (no crash!)
        │
        └─► User can download log file to debug
```

## Why This Architecture Works

### 1. **Separation of Concerns**
Each module has ONE job:
- Config = settings
- Logger = tracking
- Session = state
- SQL Utils = SQL helpers
- Database = data
- UI = presentation
- Main = orchestration

### 2. **Loose Coupling**
Modules don't depend on each other's internals:
- UI doesn't know HOW database works
- Database doesn't know HOW UI renders
- Logger doesn't know WHAT it's logging
- Each can be replaced independently

### 3. **High Cohesion**
Related functionality stays together:
- All SID operations in database.py
- All state operations in session_manager.py
- All UI rendering in ui_components.py

### 4. **Testability**
Each module can be tested alone:
```python
# Test ID generation
utils = IDGenerator(session)
assert utils._increment_code("AAAA9999") == "AAAB0000"

# Test logging
logger = Logger()
logger.log_error("test", Exception("test"))
assert logger.error_count == 1

# Test session
session = SessionManager()
session.set("test", "value")
assert session.get("test") == "value"
```

### 5. **Maintainability**
Easy to find and fix issues:
- UI bug? → Check ui_components.py
- Database error? → Check database.py
- State issue? → Check session_manager.py
- SQL problem? → Check sql_utils.py

---

## Comparison: Old vs New

### Old Architecture (Single File)
```
streamlit_app.py (600+ lines)
├─ Imports
├─ Config variables
├─ Helper functions
├─ More helper functions
├─ Database functions
├─ More database functions
├─ UI code
├─ More UI code
├─ Even more UI code
└─ Everything mixed together!
```

**Problems:**
- Hard to navigate
- Functions scattered
- No clear structure
- Changes break things
- Hard to debug

### New Architecture (Modular)
```
streamlit_app.py (80 lines)
└─ Main entry point

modules/
├─ config.py (40 lines) → Settings
├─ logger.py (100 lines) → Logging
├─ session_manager.py (120 lines) → State
├─ sql_utils.py (80 lines) → SQL helpers
├─ database.py (250 lines) → Data operations
└─ ui_components.py (400 lines) → UI rendering
```

**Benefits:**
- Easy to navigate
- Clear structure
- Isolated changes
- Easy to debug
- Professional quality

---

## Performance Characteristics

### Memory Usage
- Lightweight - only loads what's needed
- Session state managed centrally
- No memory leaks

### Database Queries
- Efficient - only queries when needed
- Proper escaping prevents injection
- Uses Snowpark's optimizations

### UI Rendering
- Fast - only reruns when necessary
- Forms clear properly
- No unnecessary state updates

---

**This architecture follows industry best practices and makes the code:**
- ✅ Easy to understand
- ✅ Easy to modify
- ✅ Easy to test
- ✅ Easy to debug
- ✅ Easy to extend

**Professional. Clean. Maintainable.** 🎯
