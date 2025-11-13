# modules/session_manager.py - Session State Management

import streamlit as st

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

    # Selected stop management (for dropdown-based stop selection)
    def get_selected_stop(self) -> str:
        return self.get("selected_stop_drop_no")

    def set_selected_stop(self, drop_no: str):
        self.set("selected_stop_drop_no", drop_no)

    def clear_selected_stop(self):
        self.set("selected_stop_drop_no", None)
    
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
