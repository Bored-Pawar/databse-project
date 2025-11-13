"""
================================================================================
PCON MANIFEST SYSTEM - CONSOLIDATED VERSION 2.0
================================================================================
This is a single-file version of the modular PCON Manifest System.
All modules are included in this file, clearly separated by section headers.

SECTIONS:
1. IMPORTS & CONFIGURATION
2. LOGGER MODULE - Error tracking and logging
3. SESSION MANAGER MODULE - Safe session state management
4. SQL UTILS MODULE - SQL utilities and ID generation
5. DATABASE MODULE - All database operations
6. UI COMPONENTS MODULE - All user interface rendering
7. MAIN APPLICATION - Entry point and orchestration

Use Ctrl+F to navigate to specific sections.
================================================================================
"""

# ================================================================================
# SECTION 1: IMPORTS & CONFIGURATION
# ================================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import traceback
import io
from snowflake.snowpark.context import get_active_session


# ---------------- Configuration Constants ----------------

# Database Configuration
DB_NAME = "SSZ_ADMIN_DB"
SCHEMA_NAME = "PCON"

# Table Names
TABLE_MANIFEST = "MANIFEST"
TABLE_MANIFEST_DEST = "MANIFEST_DESTINATIONS"
TABLE_SHIPMENT = "SHIPMENT_DETAIL"
TABLE_SID = "SID"
TABLE_OSD = "OSD"
TABLE_DESTINATIONS = "DESTINATIONS"
TABLE_SHIPPER = "SHIPPER"

# Hazmat options
HAZMAT_OPTIONS = ["", "CL2_GAS", "CL3_FLAMMABLE", "CL8_CORROSIVE", "CL9_MISC"]

# OSD Reason codes
OSD_REASON_CODES = ["Overage", "Short", "Damage", "Other"]


def get_table_names():
    """Returns fully qualified table names"""
    return {
        'manifest': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_MANIFEST}"',
        'manifest_dest': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_MANIFEST_DEST}"',
        'shipment': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_SHIPMENT}"',
        'sid': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_SID}"',
        'osd': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_OSD}"',
        'destinations': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_DESTINATIONS}"',
        'shipper': f'"{DB_NAME}"."{SCHEMA_NAME}"."{TABLE_SHIPPER}"'
    }


def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="PCON Manifest System",
        layout="wide",
        initial_sidebar_state="expanded"
    )


# ================================================================================
# SECTION 2: LOGGER MODULE
# ================================================================================
# Purpose: Comprehensive error tracking and downloadable log files
# Edit this section to modify logging behavior
# ================================================================================

class Logger:
    """Handles all application logging with downloadable log file"""

    def __init__(self):
        self.logs = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0

    def _add_log(self, level: str, message: str, exception: Exception = None):
        """Internal method to add log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'exception': None,
            'traceback': None
        }

        if exception:
            log_entry['exception'] = str(exception)
            log_entry['traceback'] = traceback.format_exc()

        self.logs.append(log_entry)

        # Update counters
        if level == "ERROR":
            self.error_count += 1
        elif level == "WARNING":
            self.warning_count += 1
        elif level == "INFO":
            self.info_count += 1

    def log_error(self, message: str, exception: Exception = None):
        """Log an error"""
        self._add_log("ERROR", message, exception)
        print(f"[ERROR] {message}")
        if exception:
            print(f"Exception: {exception}")

    def log_warning(self, message: str):
        """Log a warning"""
        self._add_log("WARNING", message)
        print(f"[WARNING] {message}")

    def log_info(self, message: str):
        """Log info"""
        self._add_log("INFO", message)
        print(f"[INFO] {message}")

    def has_errors(self) -> bool:
        """Check if any errors have been logged"""
        return self.error_count > 0

    def get_log_file(self) -> str:
        """Generate downloadable log file content"""
        lines = [
            "=" * 80,
            f"PCON Manifest System - Log File",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Logs: {len(self.logs)} (Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count})",
            "=" * 80,
            ""
        ]

        for log in self.logs:
            lines.append(f"[{log['timestamp']}] {log['level']}: {log['message']}")
            if log['exception']:
                lines.append(f"  Exception: {log['exception']}")
            if log['traceback']:
                lines.append(f"  Traceback:")
                for line in log['traceback'].split('\n'):
                    lines.append(f"    {line}")
            lines.append("")

        return "\n".join(lines)

    def clear_logs(self):
        """Clear all logs"""
        self.logs = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0
        self.log_info("Logs cleared")

    def get_recent_errors(self, count: int = 5) -> list:
        """Get recent error messages"""
        errors = [log for log in self.logs if log['level'] == "ERROR"]
        return errors[-count:] if errors else []


# ================================================================================
# SECTION 3: SESSION MANAGER MODULE
# ================================================================================
# Purpose: Safe session state management to prevent widget conflicts
# Edit this section to modify session state behavior
# ================================================================================

class SessionManager:
    """Manages all session state operations safely"""

    def __init__(self):
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize default session state values"""
        defaults = {
            "mode": "create",
            "current_manifest_no": None,
            "last_created_manifest": None,
            "current_stop_drop_no": None,
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def get(self, key: str, default=None):
        """Safely get a session state value"""
        return st.session_state.get(key, default)

    def set(self, key: str, value):
        """Safely set a session state value"""
        st.session_state[key] = value

    def delete(self, key: str):
        """Safely delete a session state key"""
        if key in st.session_state:
            del st.session_state[key]

    def exists(self, key: str) -> bool:
        """Check if a key exists in session state"""
        return key in st.session_state

    # Mode management
    def get_mode(self) -> str:
        return self.get("mode", "create")

    def set_mode(self, mode: str):
        self.set("mode", mode)

    # Manifest management
    def get_current_manifest(self) -> str:
        return self.get("current_manifest_no")

    def set_current_manifest(self, manifest_no: str):
        self.set("current_manifest_no", manifest_no)

    def get_manifest_info(self) -> dict:
        return self.get("last_created_manifest")

    def set_manifest_info(self, info: dict):
        self.set("last_created_manifest", info)

    # Stop management
    def get_current_stop(self) -> str:
        return self.get("current_stop_drop_no")

    def set_current_stop(self, drop_no: str):
        self.set("current_stop_drop_no", drop_no)

    def clear_current_stop(self):
        self.set("current_stop_drop_no", None)

    # Panel toggles (for SID and OSD editors)
    def is_panel_open(self, panel_id: str) -> bool:
        """Check if a specific panel is open"""
        return self.get(f"{panel_id}_open", False)

    def open_panel(self, panel_id: str):
        """Open a specific panel"""
        self.set(f"{panel_id}_open", True)

    def close_panel(self, panel_id: str):
        """Close a specific panel"""
        self.delete(f"{panel_id}_open")

    def toggle_panel(self, panel_id: str):
        """Toggle a panel open/closed"""
        if self.is_panel_open(panel_id):
            self.close_panel(panel_id)
        else:
            self.open_panel(panel_id)

    # Form data management
    def clear_form_data(self, form_prefix: str):
        """Clear all session state keys starting with a prefix"""
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith(form_prefix)]
        for key in keys_to_delete:
            self.delete(key)

    def reset_manifest_state(self):
        """Reset all manifest-related state"""
        keys_to_clear = [
            "mode", "current_manifest_no", "last_created_manifest",
            "current_stop_drop_no",
            "mf_no", "mf_trlr", "mf_seal", "mf_date", "mf_car", "mf_load",
            "stp_order", "stp_dest", "stp_via",
            "f_vendor", "f_sid", "f_bol", "f_pro", "f_po", "f_ibcar",
            "f_skids", "f_boxes", "f_weight", "f_value", "f_notes", "f_haz", "f_haz_desc",
        ]

        for key in keys_to_clear:
            self.delete(key)

        self.set("mode", "create")

    # SID rows management
    def get_sid_rows(self, order_id: str) -> list:
        """Get SID input rows for an order"""
        key = f"sids_{order_id}_rows"
        if not self.exists(key):
            self.set(key, [""])
        return self.get(key)

    def set_sid_rows(self, order_id: str, rows: list):
        """Set SID input rows for an order"""
        self.set(f"sids_{order_id}_rows", rows)

    def clear_sid_editor(self, order_id: str):
        """Clear SID editor state for an order"""
        self.delete(f"sids_{order_id}_open")
        self.delete(f"sids_{order_id}_rows")


# ================================================================================
# SECTION 4: SQL UTILS MODULE
# ================================================================================
# Purpose: SQL utilities, escaping, and AAAA0000 style ID generation
# Edit this section to modify SQL handling or ID generation logic
# ================================================================================

def escape_sql(s: str | None) -> str:
    """Escape single quotes for SQL safety"""
    return "" if s is None else s.replace("'", "''")


def sql_literal(val):
    """Convert Python value to SQL literal"""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)

    s = str(val).strip()
    return "NULL" if s == "" else "'" + escape_sql(s) + "'"


class IDGenerator:
    """Generate AAAA0000 style IDs"""

    def __init__(self, session):
        self.session = session

    def _get_max_code(self, table: str, column: str) -> str | None:
        """Get the maximum code from a table"""
        query = f"""
        SELECT {column} AS CODE
        FROM {table}
        WHERE REGEXP_LIKE({column}, '^[A-Z]{{4}}[0-9]{{4}}$')
        ORDER BY (
          (ASCII(SUBSTR({column},1,1))-65)*26*26*26 +
          (ASCII(SUBSTR({column},2,1))-65)*26*26     +
          (ASCII(SUBSTR({column},3,1))-65)*26        +
          (ASCII(SUBSTR({column},4,1))-65)
        )*10000 + TO_NUMBER(SUBSTR({column},5,4)) DESC
        LIMIT 1
        """

        rows = self.session.sql(query).collect()
        return rows[0]["CODE"] if rows else None

    def _increment_code(self, code: str) -> str:
        """Increment an AAAA0000 style code"""
        letters = list(code[:4])
        digits = int(code[4:]) + 1

        if digits <= 9999:
            return "".join(letters) + f"{digits:04d}"

        # Reset digits and increment letters
        digits = 0
        for i in range(3, -1, -1):
            if letters[i] < 'Z':
                letters[i] = chr(ord(letters[i]) + 1)
                break
            letters[i] = 'A'

        return "".join(letters) + f"{digits:04d}"

    def next_code(self, table: str, column: str) -> str:
        """Get the next available code"""
        last = self._get_max_code(table, column)
        return "AAAA0000" if not last else self._increment_code(last)


# ================================================================================
# SECTION 5: DATABASE MODULE
# ================================================================================
# Purpose: All database CRUD operations using Snowpark
# Edit this section to modify database queries or add new operations
# ================================================================================

class DatabaseManager:
    """Handles all database operations"""

    def __init__(self):
        self.session = get_active_session()
        self.tables = get_table_names()
        self.id_gen = IDGenerator(self.session)

    # ==================== ID Generation ====================

    def next_drop_no(self) -> str:
        return self.id_gen.next_code(self.tables['manifest_dest'], "DROP_NO")

    def next_order_id(self) -> str:
        return self.id_gen.next_code(self.tables['shipment'], "ORDER_ID")

    def next_sid_id(self) -> str:
        return self.id_gen.next_code(self.tables['sid'], "SID_ID")

    def next_osd_index(self) -> str:
        return self.id_gen.next_code(self.tables['osd'], "OSD_INDEX")

    # ==================== Manifest Operations ====================

    def manifest_exists(self, manifest_no: str) -> bool:
        """Check if manifest exists"""
        query = f"SELECT 1 FROM {self.tables['manifest']} WHERE MANIFEST_NO='{escape_sql(manifest_no)}' LIMIT 1"
        return bool(self.session.sql(query).collect())

    def insert_manifest(self, manifest_no: str, trailer_no: str, seal_no: str,
                       ship_date: str, carrier_code: str, pars_load: str):
        """Insert a new manifest"""
        query = f"""
            INSERT INTO {self.tables['manifest']}
              (MANIFEST_NO, TRAILER_NUMBER, SEAL, SHIP_DATE, OB_CARRIER_CODE, PARS_LOAD_NUMBER)
            VALUES (
              '{escape_sql(manifest_no)}',
              {sql_literal(trailer_no)}, {sql_literal(seal_no)}, {sql_literal(ship_date)},
              {sql_literal(carrier_code)}, {sql_literal(pars_load)}
            )
        """
        self.session.sql(query).collect()

    def get_manifest(self, manifest_no: str) -> pd.DataFrame:
        """Get manifest details"""
        query = f"""
            SELECT MANIFEST_NO, TRAILER_NUMBER, SEAL,
                   TO_VARCHAR(SHIP_DATE) AS SHIP_DATE,
                   OB_CARRIER_CODE, PARS_LOAD_NUMBER
            FROM {self.tables['manifest']}
            WHERE MANIFEST_NO='{escape_sql(manifest_no)}'
        """
        return self.session.sql(query).to_pandas()

    def search_manifests(self, manifest_no: str = None, carrier_code: str = None,
                        date_from: str = None, date_to: str = None) -> pd.DataFrame:
        """Search for manifests with filters"""
        conditions = []

        if manifest_no:
            conditions.append(f"MANIFEST_NO ILIKE '%{escape_sql(manifest_no)}%'")
        if carrier_code:
            conditions.append(f"OB_CARRIER_CODE ILIKE '%{escape_sql(carrier_code)}%'")
        if date_from:
            conditions.append(f"SHIP_DATE >= '{date_from}'")
        if date_to:
            conditions.append(f"SHIP_DATE <= '{date_to}'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT MANIFEST_NO, SHIP_DATE, TRAILER_NUMBER, SEAL,
                   OB_CARRIER_CODE, PARS_LOAD_NUMBER
            FROM {self.tables['manifest']}
            WHERE {where_clause}
            ORDER BY SHIP_DATE DESC, MANIFEST_NO DESC
            LIMIT 500
        """
        return self.session.sql(query).to_pandas()

    # ==================== Stop Operations ====================

    def stop_exists(self, drop_no: str) -> bool:
        """Check if stop exists"""
        query = f"SELECT 1 FROM {self.tables['manifest_dest']} WHERE DROP_NO='{escape_sql(drop_no)}' LIMIT 1"
        return bool(self.session.sql(query).collect())

    def insert_stop(self, manifest_no: str, stop_order: int,
                   code_destination: str, shipvia: str) -> str:
        """Insert a new stop and return DROP_NO"""
        drop_no = self.next_drop_no()

        # Double-check uniqueness
        if self.stop_exists(drop_no):
            drop_no = self.next_drop_no()

        query = f"""
            INSERT INTO {self.tables['manifest_dest']}
              (MANIFEST_NO, DROP_NO, STOP_ORDER, CODE_DESTINATION, SHIPVIA)
            VALUES (
              '{escape_sql(manifest_no)}', '{escape_sql(drop_no)}', {int(stop_order)},
              {sql_literal(code_destination)}, {sql_literal(shipvia)}
            )
        """
        self.session.sql(query).collect()
        return drop_no

    def get_stops_for_manifest(self, manifest_no: str) -> pd.DataFrame:
        """Get all stops for a manifest"""
        query = f"""
            SELECT DROP_NO, STOP_ORDER, CODE_DESTINATION, SHIPVIA
            FROM {self.tables['manifest_dest']}
            WHERE MANIFEST_NO = '{escape_sql(manifest_no)}'
            ORDER BY STOP_ORDER
        """
        return self.session.sql(query).to_pandas()

    def delete_stop(self, drop_no: str):
        """Delete a stop and cascade delete related records"""
        # Delete SIDs for all shipments in this stop
        self.session.sql(f"""
            DELETE FROM {self.tables['sid']}
            WHERE ORDER_ID IN (SELECT ORDER_ID FROM {self.tables['shipment']} WHERE DROP_NO='{escape_sql(drop_no)}')
        """).collect()

        # Delete OSDs for all shipments in this stop
        self.session.sql(f"""
            DELETE FROM {self.tables['osd']}
            WHERE ORDER_ID IN (SELECT ORDER_ID FROM {self.tables['shipment']} WHERE DROP_NO='{escape_sql(drop_no)}')
        """).collect()

        # Delete shipments
        self.session.sql(f"DELETE FROM {self.tables['shipment']} WHERE DROP_NO='{escape_sql(drop_no)}'").collect()

        # Delete stop
        self.session.sql(f"DELETE FROM {self.tables['manifest_dest']} WHERE DROP_NO='{escape_sql(drop_no)}'").collect()

    # ==================== Shipment Operations ====================

    def insert_shipment(self, drop_no: str, vendorcode: str, sid: str, bol: str,
                       pro: str, po: str, ib_car: str, skids: int, boxes: int,
                       weight: float, value_amt: float, notes: str,
                       hazmat: bool, haz_desc: str) -> str:
        """Insert a new shipment and return ORDER_ID"""
        order_id = self.next_order_id()

        query = f"""
            INSERT INTO {self.tables['shipment']} (
                ORDER_ID, DROP_NO, VENDORCODE, SID, BOL_NO, PRO_NO, PO_NUMBER,
                IB_CARRIER_CODE, SKIDS, BOXES, WEIGHT_LB, DECLARED_VALUE, NOTES,
                HAZMAT, HAZMAT_DESCRIPTION
            ) VALUES (
                '{escape_sql(order_id)}', '{escape_sql(drop_no)}',
                {sql_literal(vendorcode)}, {sql_literal(sid)}, {sql_literal(bol)},
                {sql_literal(pro)}, {sql_literal(po)}, {sql_literal(ib_car)},
                {sql_literal(skids)}, {sql_literal(boxes)}, {sql_literal(weight)},
                {sql_literal(value_amt)}, {sql_literal(notes)},
                {sql_literal(bool(hazmat))}, {sql_literal(haz_desc)}
            )
        """
        self.session.sql(query).collect()
        return order_id

    def get_shipments_for_drop(self, drop_no: str) -> pd.DataFrame:
        """Get all shipments for a stop"""
        query = f"""
            SELECT
                ORDER_ID,
                VENDORCODE       AS "Vendor Code",
                SID              AS "SID",
                BOL_NO           AS "BOL Number",
                PRO_NO           AS "PRO Number",
                PO_NUMBER        AS "PO Number",
                IB_CARRIER_CODE  AS "Inbound Carrier Code",
                SKIDS            AS "Skids",
                BOXES            AS "Boxes",
                WEIGHT_LB        AS "Weight",
                DECLARED_VALUE   AS "Value",
                NOTES            AS "Notes",
                HAZMAT           AS "Hazmat",
                HAZMAT_DESCRIPTION AS "Hazmat Description"
            FROM {self.tables['shipment']}
            WHERE DROP_NO = '{escape_sql(drop_no)}'
            ORDER BY COALESCE(BOL_NO, ORDER_ID)
        """
        return self.session.sql(query).to_pandas()

    def delete_shipment(self, order_id: str):
        """Delete a shipment and cascade delete related records"""
        self.session.sql(f"DELETE FROM {self.tables['sid']} WHERE ORDER_ID='{escape_sql(order_id)}'").collect()
        self.session.sql(f"DELETE FROM {self.tables['osd']} WHERE ORDER_ID='{escape_sql(order_id)}'").collect()
        self.session.sql(f"DELETE FROM {self.tables['shipment']} WHERE ORDER_ID='{escape_sql(order_id)}'").collect()

    # ==================== SID Operations ====================

    def get_sids_for_order(self, order_id: str) -> pd.DataFrame:
        """Get all SIDs for an order"""
        query = f"SELECT SID_ID, SID_NUMBER FROM {self.tables['sid']} WHERE ORDER_ID='{escape_sql(order_id)}' ORDER BY SID_NUMBER"
        return self.session.sql(query).to_pandas()

    def get_primary_sid(self, order_id: str) -> str | None:
        """Get the primary SID from SHIPMENT_DETAIL"""
        query = f"SELECT SID FROM {self.tables['shipment']} WHERE ORDER_ID='{escape_sql(order_id)}'"
        result = self.session.sql(query).collect()
        return result[0]["SID"] if result else None

    def add_multiple_sids(self, order_id: str, sid_numbers: list[str]) -> int:
        """Add multiple SIDs for an order, returns count of new SIDs added"""
        clean = [s.strip() for s in sid_numbers if s and s.strip()]
        if not clean:
            return 0

        # Get existing SIDs
        existing_query = f"SELECT SID_NUMBER FROM {self.tables['sid']} WHERE ORDER_ID='{escape_sql(order_id)}'"
        existing = set(r["SID_NUMBER"] for r in self.session.sql(existing_query).collect())

        # Filter out duplicates
        new_sids = [s for s in clean if s not in existing]

        # Insert new SIDs
        for sid_num in new_sids:
            sid_id = self.next_sid_id()
            query = f"INSERT INTO {self.tables['sid']}(SID_ID, ORDER_ID, SID_NUMBER) VALUES ('{escape_sql(sid_id)}','{escape_sql(order_id)}','{escape_sql(sid_num)}')"
            self.session.sql(query).collect()

        return len(new_sids)

    def delete_sid(self, sid_id: str):
        """Delete a single SID"""
        self.session.sql(f"DELETE FROM {self.tables['sid']} WHERE SID_ID='{escape_sql(sid_id)}'").collect()

    def set_primary_sid(self, order_id: str, sid_number: str | None):
        """Set the primary SID in SHIPMENT_DETAIL"""
        if sid_number is None or str(sid_number).strip() == "":
            query = f"UPDATE {self.tables['shipment']} SET SID=NULL WHERE ORDER_ID='{escape_sql(order_id)}'"
        else:
            query = f"UPDATE {self.tables['shipment']} SET SID='{escape_sql(str(sid_number))}' WHERE ORDER_ID='{escape_sql(order_id)}'"
        self.session.sql(query).collect()

    # ==================== OSD Operations ====================

    def get_osd_for_order(self, order_id: str) -> pd.DataFrame:
        """Get all OSD entries for an order"""
        query = f"""
            SELECT
                OSD_INDEX,
                REASON_CODE,
                PALLETS_BILLED,
                BOXES_BILLED,
                PALLETS_RECEIVED,
                BOXES_RECEIVED,
                COMMENTS
            FROM {self.tables['osd']}
            WHERE ORDER_ID='{escape_sql(order_id)}'
            ORDER BY OSD_INDEX
        """
        return self.session.sql(query).to_pandas()

    def insert_osd(self, order_id: str, reason_code: str, pallets_billed: int,
                   boxes_billed: int, pallets_received: int, boxes_received: int,
                   comments: str | None) -> str:
        """Insert an OSD entry and return OSD_INDEX"""
        osd_index = self.next_osd_index()

        query = f"""
            INSERT INTO {self.tables['osd']}
                (OSD_INDEX, ORDER_ID, REASON_CODE, PALLETS_BILLED, BOXES_BILLED,
                 PALLETS_RECEIVED, BOXES_RECEIVED, COMMENTS)
            VALUES
                ('{escape_sql(osd_index)}', '{escape_sql(order_id)}', {sql_literal(reason_code)},
                 {sql_literal(pallets_billed)}, {sql_literal(boxes_billed)},
                 {sql_literal(pallets_received)}, {sql_literal(boxes_received)}, {sql_literal(comments)})
        """
        self.session.sql(query).collect()
        return osd_index

    def delete_osd(self, osd_index: str):
        """Delete an OSD entry"""
        self.session.sql(f"DELETE FROM {self.tables['osd']} WHERE OSD_INDEX='{escape_sql(osd_index)}'").collect()


# ================================================================================
# SECTION 6: UI COMPONENTS MODULE
# ================================================================================
# Purpose: All user interface rendering and interaction handling
# Edit this section to modify UI layouts, forms, and user interactions
# ================================================================================

class UIComponents:
    """Handles all UI rendering"""

    def __init__(self, db_manager, logger, session_manager):
        self.db = db_manager
        self.logger = logger
        self.session = session_manager

    # ==================== Navigation ====================

    def render_top_navigation(self):
        """Render the top navigation buttons"""
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("➕ Create Manifest", use_container_width=True, type="primary"):
                self.session.set_mode("create")
                self.session.clear_current_stop()
                self.logger.log_info("Switched to Create mode")
                st.rerun()

        with col2:
            if st.button("🔎 Retrieve Manifest", use_container_width=True):
                self.session.set_mode("retrieve")
                self.session.clear_current_stop()
                self.logger.log_info("Switched to Retrieve mode")
                st.rerun()

        with col3:
            if st.button("💾 Save Manifest & Reset", use_container_width=True):
                self.session.reset_manifest_state()
                self.logger.log_info("Manifest saved and state reset")
                st.success("Manifest saved. Starting fresh…")
                st.rerun()

    # ==================== Create Mode ====================

    def render_create_mode(self):
        """Render the create/edit manifest interface"""
        try:
            st.header("➕ Create Manifest")

            # Manifest creation form
            self._render_manifest_form()

            # Show manifest info if one is active
            manifest_info = self.session.get_manifest_info()
            if manifest_info:
                self._render_manifest_summary(manifest_info)

                # Stop management
                self._render_stop_form()

                # Shipment management for current stop
                current_stop = self.session.get_current_stop()
                if current_stop:
                    self._render_shipment_section(current_stop)

                # All stops overview
                self._render_stops_overview()

        except Exception as e:
            self.logger.log_error("Error in render_create_mode", e)
            st.error("An error occurred. Please check the logs.")

    def _render_manifest_form(self):
        """Render manifest creation form"""
        with st.form("create_manifest"):
            col1, col2, col3 = st.columns(3)

            with col1:
                manifest_no = st.text_input("Manifest Number (PK) *", key="mf_no")
                trailer_no = st.text_input("Trailer Number", key="mf_trlr")

            with col2:
                seal_no = st.text_input("Seal Number", key="mf_seal")
                ship_date = st.date_input("Ship Date", key="mf_date", value=None)

            with col3:
                carrier_code = st.text_input("Outbound Carrier Code", key="mf_car")
                pars_load = st.text_input("PARS / LOAD Number", key="mf_load")

            submitted = st.form_submit_button("Create Manifest")

        if submitted:
            try:
                if not manifest_no.strip():
                    st.error("Manifest Number is required.")
                    self.logger.log_warning("Manifest creation attempted without manifest number")
                    return

                # Check if manifest already exists
                if self.db.manifest_exists(manifest_no):
                    st.error(f"Manifest {manifest_no} already exists.")
                    self.logger.log_warning(f"Duplicate manifest number: {manifest_no}")
                    return

                # Insert manifest
                self.db.insert_manifest(
                    manifest_no, trailer_no, seal_no,
                    ship_date.isoformat() if ship_date else None,
                    carrier_code, pars_load
                )

                # Update session state
                self.session.set_current_manifest(manifest_no)
                self.session.set_manifest_info({
                    "MANIFEST_NO": manifest_no,
                    "TRAILER_NUMBER": trailer_no or "",
                    "SEAL": seal_no or "",
                    "SHIP_DATE": ship_date.isoformat() if ship_date else "",
                    "OB_CARRIER_CODE": carrier_code or "",
                    "PARS_LOAD_NUMBER": pars_load or ""
                })
                self.session.clear_current_stop()

                st.success(f"Manifest {manifest_no} created successfully!")
                self.logger.log_info(f"Created manifest: {manifest_no}")
                st.rerun()

            except Exception as e:
                self.logger.log_error(f"Failed to create manifest {manifest_no}", e)
                st.error(f"Failed to create manifest: {e}")

    def _render_manifest_summary(self, info: dict):
        """Render manifest summary panel"""
        st.subheader("Working on Manifest")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"**Manifest No:** {info['MANIFEST_NO']}")
            st.write(f"**Trailer No:** {info['TRAILER_NUMBER']}")

        with col2:
            st.write(f"**Seal:** {info['SEAL']}")
            st.write(f"**Ship Date:** {info['SHIP_DATE']}")

        with col3:
            st.write(f"**Outbound Carrier:** {info['OB_CARRIER_CODE']}")
            st.write(f"**Load No:** {info['PARS_LOAD_NUMBER']}")

        st.divider()

    def _render_stop_form(self):
        """Render stop creation form"""
        st.subheader("➕ Add Stop")

        col1, col2, col3 = st.columns(3)

        with col1:
            stop_order = st.number_input("Stop Order", min_value=1, value=1, step=1, key="stp_order")

        with col2:
            code_destination = st.text_input("Code Destination", key="stp_dest")

        with col3:
            shipvia = st.text_input("Ship Via", key="stp_via")

        if st.button("Add Stop"):
            try:
                manifest_no = self.session.get_current_manifest()
                if not manifest_no:
                    st.error("No active manifest.")
                    self.logger.log_error("Add stop attempted without active manifest")
                    return

                drop_no = self.db.insert_stop(manifest_no, stop_order, code_destination, shipvia)
                self.session.set_current_stop(drop_no)

                st.success(f"Stop added successfully! (DROP_NO: {drop_no})")
                self.logger.log_info(f"Added stop {drop_no} to manifest {manifest_no}")
                st.rerun()

            except Exception as e:
                self.logger.log_error("Failed to add stop", e)
                st.error(f"Failed to add stop: {e}")

    # ==================== Shipment Section ====================

    def _render_shipment_section(self, drop_no: str):
        """Render shipment management for current stop"""
        try:
            st.divider()
            st.subheader("➕ Add Shipment to Current Stop")

            # Show existing shipments
            self._display_shipments_table(drop_no)

            # Shipment entry form
            self._render_shipment_form(drop_no)

            # Manage existing shipments
            self._render_shipment_management(drop_no)

            # Finish stop button
            if st.button("✅ Finish this Stop & Add Another", type="secondary"):
                self.session.clear_current_stop()
                self.logger.log_info(f"Finished working on stop {drop_no}")
                st.rerun()

        except Exception as e:
            self.logger.log_error(f"Error in shipment section for drop {drop_no}", e)
            st.error("Error rendering shipment section. Check logs.")

    def _display_shipments_table(self, drop_no: str):
        """Display existing shipments for a stop"""
        try:
            shipments = self.db.get_shipments_for_drop(drop_no)
            if not shipments.empty:
                # Hide ORDER_ID column
                display_df = shipments.drop(columns=["ORDER_ID"]).reset_index(drop=True)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        except Exception as e:
            self.logger.log_error(f"Failed to display shipments for drop {drop_no}", e)
            st.warning("Could not load shipments")

    def _render_shipment_form(self, drop_no: str):
        """Render shipment entry form"""
        with st.form("add_shipment", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                vendorcode = st.text_input("Vendor Code", key="f_vendor")
                sid = st.text_input("SID", key="f_sid")
                bol = st.text_input("BOL Number", key="f_bol")

            with col2:
                pro = st.text_input("PRO Number", key="f_pro")
                po = st.text_input("PO Number", key="f_po")
                ib_car = st.text_input("Inbound Carrier Code", key="f_ibcar")

            with col3:
                skids = st.number_input("Skids", min_value=0, value=0, step=1, key="f_skids")
                boxes = st.number_input("Boxes", min_value=0, value=0, step=1, key="f_boxes")
                weight = st.number_input("Weight", min_value=0.0, value=0.0, step=0.1, key="f_weight")

            col4, col5, col6 = st.columns(3)

            with col4:
                value_amt = st.number_input("Value", min_value=0.0, value=0.0, step=0.01, key="f_value")

            with col5:
                notes = st.text_input("Notes (optional)", key="f_notes")

            with col6:
                hazmat = st.checkbox("Hazmat", key="f_haz")

            haz_desc = st.selectbox("Hazmat Description", HAZMAT_OPTIONS, key="f_haz_desc")

            submitted = st.form_submit_button("Add Shipment")

        if submitted:
            try:
                order_id = self.db.insert_shipment(
                    drop_no, vendorcode, sid, bol, pro, po, ib_car,
                    skids, boxes, weight, value_amt, notes, hazmat, haz_desc
                )

                st.success(f"Shipment added successfully! (ORDER_ID: {order_id})")
                self.logger.log_info(f"Added shipment {order_id} to drop {drop_no}")
                st.rerun()

            except Exception as e:
                self.logger.log_error(f"Failed to add shipment to drop {drop_no}", e)
                st.error(f"Failed to add shipment: {e}")

    def _render_shipment_management(self, drop_no: str):
        """Render management interface for existing shipments"""
        try:
            shipments = self.db.get_shipments_for_drop(drop_no)

            if shipments.empty:
                return

            st.subheader("Manage Shipments on This Stop")

            for _, row in shipments.iterrows():
                order_id = row["ORDER_ID"]
                self._render_shipment_item(order_id, row)

        except Exception as e:
            self.logger.log_error(f"Error rendering shipment management for drop {drop_no}", e)
            st.error("Error loading shipment management. Check logs.")

    def _render_shipment_item(self, order_id: str, row: pd.Series):
        """Render a single shipment item with edit/delete options"""
        try:
            title = f"Edit/Delete • SID: {row['SID'] or 'N/A'} • Vendor: {row['Vendor Code'] or 'N/A'}"

            with st.expander(title, expanded=False):
                # Display shipment details
                display_row = row.drop('ORDER_ID').to_frame().T.reset_index(drop=True)
                st.dataframe(display_row, use_container_width=True, hide_index=True)

                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 3])

                with col1:
                    if st.button("Multiple SID/PO", key=f"multi_{order_id}"):
                        self.session.open_panel(f"sids_{order_id}")
                        st.rerun()

                with col2:
                    if st.button("OSD", key=f"osd_{order_id}"):
                        self.session.open_panel(f"osd_{order_id}")
                        st.rerun()

                # Show current SIDs
                self._display_current_sids(order_id)

                # Primary SID selector
                self._render_primary_sid_selector(order_id)

                # SID editor panel
                if self.session.is_panel_open(f"sids_{order_id}"):
                    self._render_sid_editor(order_id)

                # OSD editor panel
                if self.session.is_panel_open(f"osd_{order_id}"):
                    self._render_osd_editor(order_id)

                # Delete shipment button
                st.markdown("---")
                if st.button("🗑️ Delete this shipment", key=f"del_{order_id}"):
                    try:
                        self.db.delete_shipment(order_id)
                        st.success("Shipment deleted successfully!")
                        self.logger.log_info(f"Deleted shipment {order_id}")
                        st.rerun()
                    except Exception as e:
                        self.logger.log_error(f"Failed to delete shipment {order_id}", e)
                        st.error(f"Failed to delete shipment: {e}")

        except Exception as e:
            self.logger.log_error(f"Error rendering shipment item {order_id}", e)
            st.error("Error rendering shipment details")

    # ==================== SID Management ====================

    def _display_current_sids(self, order_id: str):
        """Display current SIDs for an order"""
        try:
            st.caption("All SIDs for this order:")
            sid_df = self.db.get_sids_for_order(order_id)

            if sid_df.empty:
                st.write("— none —")
            else:
                for _, sid_row in sid_df.iterrows():
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(sid_row["SID_NUMBER"])
                    with col2:
                        if st.button("Delete", key=f"sid_del_{sid_row['SID_ID']}"):
                            try:
                                # Clear primary if deleting current primary
                                current_primary = self.db.get_primary_sid(order_id)
                                if current_primary == sid_row["SID_NUMBER"]:
                                    self.db.set_primary_sid(order_id, None)

                                self.db.delete_sid(sid_row["SID_ID"])
                                st.success("SID deleted!")
                                self.logger.log_info(f"Deleted SID {sid_row['SID_ID']} from order {order_id}")
                                st.rerun()
                            except Exception as e:
                                self.logger.log_error(f"Failed to delete SID {sid_row['SID_ID']}", e)
                                st.error("Failed to delete SID")

        except Exception as e:
            self.logger.log_error(f"Error displaying SIDs for order {order_id}", e)
            st.warning("Could not load SIDs")

    def _render_primary_sid_selector(self, order_id: str):
        """Render primary SID selector"""
        try:
            sid_df = self.db.get_sids_for_order(order_id)
            sid_options = ["(none)"] + (sid_df["SID_NUMBER"].tolist() if not sid_df.empty else [])

            current_primary = self.db.get_primary_sid(order_id)

            # Determine index
            if not current_primary or current_primary not in sid_options:
                default_idx = 0
            else:
                default_idx = sid_options.index(current_primary)

            selected = st.selectbox(
                "Primary SID",
                sid_options,
                index=default_idx,
                key=f"prim_{order_id}"
            )

            if st.button("Save Primary SID", key=f"prim_save_{order_id}"):
                try:
                    new_primary = None if selected == "(none)" else selected
                    self.db.set_primary_sid(order_id, new_primary)
                    st.success("Primary SID updated!")
                    self.logger.log_info(f"Updated primary SID for order {order_id} to {new_primary}")
                    st.rerun()
                except Exception as e:
                    self.logger.log_error(f"Failed to update primary SID for order {order_id}", e)
                    st.error("Failed to update primary SID")

        except Exception as e:
            self.logger.log_error(f"Error rendering primary SID selector for order {order_id}", e)
            st.warning("Could not load primary SID selector")

    def _render_sid_editor(self, order_id: str):
        """Render SID editor panel - FIXED: No more typo errors!"""
        try:
            st.markdown("**Add multiple SIDs**")

            # Get current rows
            sid_rows = self.session.get_sid_rows(order_id)

            # Render input fields
            for i in range(len(sid_rows)):
                col1, col2 = st.columns([6, 1])

                with col1:
                    # Use a unique key for each input
                    new_value = st.text_input(
                        f"SID #{i+1}",
                        value=sid_rows[i],
                        key=f"sids_input_{order_id}_{i}"
                    )
                    # Update the value in the list
                    sid_rows[i] = new_value

                with col2:
                    if st.button("✖", key=f"sids_rm_{order_id}_{i}"):
                        sid_rows.pop(i)
                        self.session.set_sid_rows(order_id, sid_rows)
                        st.rerun()

            # Update session with current values
            self.session.set_sid_rows(order_id, sid_rows)

            # Add row button
            if st.button("＋ Add another", key=f"sids_addrow_{order_id}"):
                sid_rows.append("")
                self.session.set_sid_rows(order_id, sid_rows)
                st.rerun()

            # Save/Cancel buttons
            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Save SIDs", key=f"sids_save_{order_id}"):
                    try:
                        added_count = self.db.add_multiple_sids(order_id, sid_rows)

                        # Auto-set primary if none exists
                        current_primary = self.db.get_primary_sid(order_id)
                        if not current_primary:
                            sids = self.db.get_sids_for_order(order_id)
                            if not sids.empty:
                                self.db.set_primary_sid(order_id, sids.iloc[0]["SID_NUMBER"])

                        # Close panel and clear state
                        self.session.clear_sid_editor(order_id)

                        st.success(f"Saved {added_count} new SID(s)!")
                        self.logger.log_info(f"Added {added_count} SIDs to order {order_id}")
                        st.rerun()

                    except Exception as e:
                        self.logger.log_error(f"Failed to save SIDs for order {order_id}", e)
                        st.error("Failed to save SIDs")

            with col2:
                if st.button("Cancel", key=f"sids_cancel_{order_id}"):
                    self.session.clear_sid_editor(order_id)
                    st.rerun()

        except Exception as e:
            self.logger.log_error(f"Error in SID editor for order {order_id}", e)
            st.error("Error in SID editor")

    # ==================== OSD Management ====================

    def _render_osd_editor(self, order_id: str):
        """Render OSD editor panel - FIXED: No more form errors!"""
        try:
            st.markdown("**OSD Entry**")

            # Display existing OSD entries
            osd_df = self.db.get_osd_for_order(order_id)

            if osd_df.empty:
                st.write("No OSD rows yet.")
            else:
                st.dataframe(osd_df, use_container_width=True, hide_index=True)

                for _, osd_row in osd_df.iterrows():
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.caption(
                            f"{osd_row['REASON_CODE']} • "
                            f"PB:{osd_row['PALLETS_BILLED']} BB:{osd_row['BOXES_BILLED']} "
                            f"PR:{osd_row['PALLETS_RECEIVED']} BR:{osd_row['BOXES_RECEIVED']}"
                        )
                    with col2:
                        if st.button("Delete", key=f"osd_del_{osd_row['OSD_INDEX']}"):
                            try:
                                self.db.delete_osd(osd_row["OSD_INDEX"])
                                st.success("OSD row deleted!")
                                self.logger.log_info(f"Deleted OSD {osd_row['OSD_INDEX']}")
                                st.rerun()
                            except Exception as e:
                                self.logger.log_error(f"Failed to delete OSD {osd_row['OSD_INDEX']}", e)
                                st.error("Failed to delete OSD")

            # OSD entry form - CRITICAL: Don't use form inside expander with session state
            st.markdown("**Add New OSD Entry**")

            reason_code = st.selectbox(
                "Reason Code",
                OSD_REASON_CODES,
                key=f"osd_rc_{order_id}"
            )

            col1, col2 = st.columns(2)
            with col1:
                pallets_billed = st.number_input(
                    "Pallets Billed",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"osd_pb_{order_id}"
                )
                boxes_billed = st.number_input(
                    "Boxes Billed",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"osd_bb_{order_id}"
                )

            with col2:
                pallets_received = st.number_input(
                    "Pallets Received",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"osd_pr_{order_id}"
                )
                boxes_received = st.number_input(
                    "Boxes Received",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"osd_br_{order_id}"
                )

            comments = st.text_input("Comments", key=f"osd_cm_{order_id}")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Add OSD Row", key=f"osd_add_{order_id}"):
                    try:
                        self.db.insert_osd(
                            order_id,
                            reason_code,
                            pallets_billed,
                            boxes_billed,
                            pallets_received,
                            boxes_received,
                            comments or None
                        )

                        st.success("OSD row added!")
                        self.logger.log_info(f"Added OSD entry to order {order_id}")

                        # Close panel to reset form
                        self.session.close_panel(f"osd_{order_id}")
                        st.rerun()

                    except Exception as e:
                        self.logger.log_error(f"Failed to add OSD for order {order_id}", e)
                        st.error("Failed to add OSD row")

            with col2:
                if st.button("Close OSD", key=f"osd_close_{order_id}"):
                    self.session.close_panel(f"osd_{order_id}")
                    st.rerun()

        except Exception as e:
            self.logger.log_error(f"Error in OSD editor for order {order_id}", e)
            st.error("Error in OSD editor")

    # ==================== Stops Overview ====================

    def _render_stops_overview(self):
        """Render overview of all stops in current manifest"""
        try:
            manifest_no = self.session.get_current_manifest()
            if not manifest_no:
                return

            st.divider()
            st.subheader("📍 Stops in this Manifest")

            stops = self.db.get_stops_for_manifest(manifest_no)

            if stops.empty:
                st.info("No stops added yet.")
                return

            # Display stops table (hide DROP_NO)
            display_df = stops.rename(columns={
                "STOP_ORDER": "Stop Order",
                "CODE_DESTINATION": "Code Destination",
                "SHIPVIA": "Ship Via"
            }).drop(columns=["DROP_NO"]).reset_index(drop=True)

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Expandable details for each stop
            for _, stop_row in stops.iterrows():
                drop_no = stop_row["DROP_NO"]
                title = f"Stop {int(stop_row['STOP_ORDER'])} • {stop_row['CODE_DESTINATION'] or 'N/A'} • {stop_row['SHIPVIA'] or 'N/A'}"

                with st.expander(title, expanded=False):
                    shipments = self.db.get_shipments_for_drop(drop_no)

                    if shipments.empty:
                        st.write("No shipments on this stop.")
                    else:
                        display_shipments = shipments.drop(columns=["ORDER_ID"]).reset_index(drop=True)
                        st.dataframe(display_shipments, use_container_width=True, hide_index=True)

                    # Delete stop button
                    if st.button("🗑️ Delete This Stop (and its shipments)", key=f"dropdel_{drop_no}"):
                        try:
                            self.db.delete_stop(drop_no)

                            # Clear current stop if it was this one
                            if self.session.get_current_stop() == drop_no:
                                self.session.clear_current_stop()

                            st.success("Stop deleted successfully!")
                            self.logger.log_info(f"Deleted stop {drop_no}")
                            st.rerun()

                        except Exception as e:
                            self.logger.log_error(f"Failed to delete stop {drop_no}", e)
                            st.error("Failed to delete stop")

        except Exception as e:
            self.logger.log_error("Error rendering stops overview", e)
            st.error("Error loading stops overview")

    # ==================== Retrieve Mode ====================

    def render_retrieve_mode(self):
        """Render manifest retrieval/search interface"""
        try:
            st.header("🔎 Retrieve Manifest")

            with st.form("retrieve_manifest"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    manifest_query = st.text_input("Manifest No (exact or partial)")

                with col2:
                    date_from = st.date_input("Ship Date From", value=None, key="mf_from")

                with col3:
                    date_to = st.date_input("Ship Date To", value=None, key="mf_to")

                carrier_query = st.text_input("Outbound Carrier Code (exact or partial)")

                submitted = st.form_submit_button("Search")

            if submitted:
                try:
                    # Convert dates to ISO format
                    date_from_str = date_from.isoformat() if date_from else None
                    date_to_str = date_to.isoformat() if date_to else None

                    # Search manifests
                    results = self.db.search_manifests(
                        manifest_query,
                        carrier_query,
                        date_from_str,
                        date_to_str
                    )

                    if results.empty:
                        st.warning("No manifests found matching your criteria.")
                        self.logger.log_info("Manifest search returned no results")
                    else:
                        st.caption(f"Found {len(results)} manifest(s)")
                        st.dataframe(results, use_container_width=True, hide_index=True)

                        # Allow selection
                        chosen = st.selectbox(
                            "Pick a manifest to work on",
                            results["MANIFEST_NO"].tolist(),
                            key="mf_pick"
                        )

                        if st.button("Set as Current Manifest"):
                            try:
                                # Load manifest details
                                manifest_df = self.db.get_manifest(chosen)

                                if not manifest_df.empty:
                                    manifest_dict = manifest_df.iloc[0].to_dict()

                                    self.session.set_current_manifest(chosen)
                                    self.session.set_manifest_info({
                                        "MANIFEST_NO": manifest_dict.get("MANIFEST_NO", ""),
                                        "TRAILER_NUMBER": manifest_dict.get("TRAILER_NUMBER", ""),
                                        "SEAL": manifest_dict.get("SEAL", ""),
                                        "SHIP_DATE": manifest_dict.get("SHIP_DATE", ""),
                                        "OB_CARRIER_CODE": manifest_dict.get("OB_CARRIER_CODE", ""),
                                        "PARS_LOAD_NUMBER": manifest_dict.get("PARS_LOAD_NUMBER", ""),
                                    })

                                    self.session.set_mode("create")
                                    self.session.clear_current_stop()

                                    st.success(f"Current manifest set to {chosen}")
                                    self.logger.log_info(f"Retrieved and set manifest {chosen}")
                                    st.rerun()

                            except Exception as e:
                                self.logger.log_error(f"Failed to load manifest {chosen}", e)
                                st.error("Failed to load manifest")

                except Exception as e:
                    self.logger.log_error("Error during manifest search", e)
                    st.error("Search failed. Check logs.")

        except Exception as e:
            self.logger.log_error("Error in render_retrieve_mode", e)
            st.error("An error occurred in retrieve mode. Check logs.")


# ================================================================================
# SECTION 7: MAIN APPLICATION
# ================================================================================
# Purpose: Application entry point and orchestration
# Edit this section to modify app initialization or main flow
# ================================================================================

# Setup page configuration
setup_page()

# Initialize logger
if 'logger' not in st.session_state:
    st.session_state.logger = Logger()

logger = st.session_state.logger

# Initialize database manager
try:
    db = DatabaseManager()
    logger.log_info("Database manager initialized successfully")
except Exception as e:
    logger.log_error("Failed to initialize database manager", e)
    st.error("Failed to connect to database. Check logs.")
    st.stop()

# Initialize session manager
session_mgr = SessionManager()

# Initialize UI components
ui = UIComponents(db, logger, session_mgr)


def main():
    """Main application function"""
    try:
        st.title("PCON Manifest System")

        # Show error log download button in sidebar
        with st.sidebar:
            st.subheader("📋 System Logs")
            if logger.has_errors():
                st.error(f"⚠️ {logger.error_count} errors logged")
            else:
                st.success("✅ No errors")

            log_data = logger.get_log_file()
            st.download_button(
                label="📥 Download Log File",
                data=log_data,
                file_name=f"manifest_system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

            if st.button("🗑️ Clear Logs"):
                logger.clear_logs()
                st.rerun()

        # Top navigation
        ui.render_top_navigation()

        # Render appropriate mode
        mode = session_mgr.get_mode()

        if mode == "create":
            ui.render_create_mode()
        elif mode == "retrieve":
            ui.render_retrieve_mode()

        logger.log_info(f"Successfully rendered {mode} mode")

    except Exception as e:
        logger.log_error("Critical error in main application", e)
        st.error("A critical error occurred. Please download the log file for details.")
        st.exception(e)


if __name__ == "__main__":
    main()