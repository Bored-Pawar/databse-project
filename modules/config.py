# modules/config.py - Configuration and Constants

import streamlit as st

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

# Hazmat options
HAZMAT_OPTIONS = ["", "CL2_GAS", "CL3_FLAMMABLE", "CL8_CORROSIVE", "CL9_MISC"]

# OSD Reason codes
OSD_REASON_CODES = ["Overage", "Short", "Damage", "Other"]
