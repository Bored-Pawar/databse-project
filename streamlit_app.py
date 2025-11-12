# streamlit_app.py - Main Application Entry Point

import streamlit as st
from datetime import datetime
import traceback
import io

# Import all modules
from modules.config import setup_page, get_table_names
from modules.logger import Logger
from modules.database import DatabaseManager
from modules.ui_components import UIComponents
from modules.session_manager import SessionManager

# ============================ Setup =============================
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

# ============================ Main App ==============================
def main():
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
