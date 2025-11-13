# modules/ui_components.py - User Interface Components

import streamlit as st
import pandas as pd
from modules.config import HAZMAT_OPTIONS, OSD_REASON_CODES

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

                # Stop selector dropdown and working stop section
                self._render_stop_selector()

                # Shipment management for selected stop
                selected_stop = self.session.get_selected_stop()
                if selected_stop:
                    self._render_working_stop_header(selected_stop)
                    self._render_shipment_section(selected_stop)

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
                # Automatically select the newly added stop for editing
                self.session.set_selected_stop(drop_no)

                st.success(f"Stop added successfully! (DROP_NO: {drop_no})")
                self.logger.log_info(f"Added stop {drop_no} to manifest {manifest_no}")
                st.rerun()

            except Exception as e:
                self.logger.log_error("Failed to add stop", e)
                st.error(f"Failed to add stop: {e}")

    def _render_stop_selector(self):
        """Render dropdown to select which stop to work on"""
        try:
            manifest_no = self.session.get_current_manifest()
            if not manifest_no:
                return

            stops = self.db.get_stops_for_manifest(manifest_no)

            if stops.empty:
                return

            st.divider()
            st.subheader("🎯 Select Stop to Work On")

            # Create dropdown options: "Stop 1 • CODE_DEST • SHIPVIA (DROP_NO)"
            stop_options = {}
            for _, stop_row in stops.iterrows():
                drop_no = stop_row["DROP_NO"]
                stop_order = int(stop_row['STOP_ORDER'])
                code_dest = stop_row['CODE_DESTINATION'] or 'N/A'
                shipvia = stop_row['SHIPVIA'] or 'N/A'

                label = f"Stop {stop_order} • {code_dest} • {shipvia} ({drop_no})"
                stop_options[label] = drop_no

            # Get current selection
            current_selected = self.session.get_selected_stop()

            # Find the index of current selection
            default_index = 0
            if current_selected:
                for idx, drop_no in enumerate(stop_options.values()):
                    if drop_no == current_selected:
                        default_index = idx
                        break

            col1, col2 = st.columns([4, 1])

            with col1:
                selected_label = st.selectbox(
                    "Choose a stop to add/edit shipments:",
                    options=list(stop_options.keys()),
                    index=default_index,
                    key="stop_selector"
                )

            with col2:
                if st.button("Select Stop", type="primary"):
                    selected_drop_no = stop_options[selected_label]
                    self.session.set_selected_stop(selected_drop_no)
                    self.logger.log_info(f"Selected stop {selected_drop_no} for editing")
                    st.rerun()

        except Exception as e:
            self.logger.log_error("Error in stop selector", e)
            st.error("Error loading stop selector")

    def _render_working_stop_header(self, drop_no: str):
        """Render header showing which stop we're currently working on"""
        try:
            manifest_no = self.session.get_current_manifest()
            if not manifest_no:
                return

            stops = self.db.get_stops_for_manifest(manifest_no)
            stop_row = stops[stops["DROP_NO"] == drop_no]

            if stop_row.empty:
                return

            stop_info = stop_row.iloc[0]

            st.divider()

            # Header similar to manifest summary
            col_title, col_btn = st.columns([4, 1])
            with col_title:
                st.subheader("🚚 Working on Stop")
            with col_btn:
                if st.button("❌ Clear Selection", key="clear_stop_selection"):
                    self.session.clear_selected_stop()
                    self.logger.log_info(f"Cleared stop selection")
                    st.rerun()

            # Display stop info
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Stop Order:** {int(stop_info['STOP_ORDER'])}")
                st.write(f"**DROP_NO:** {drop_no}")

            with col2:
                st.write(f"**Code Destination:** {stop_info['CODE_DESTINATION'] or 'N/A'}")

            with col3:
                st.write(f"**Ship Via:** {stop_info['SHIPVIA'] or 'N/A'}")

        except Exception as e:
            self.logger.log_error(f"Error rendering working stop header for {drop_no}", e)
            st.error("Error displaying stop information")

    # ==================== Shipment Section ====================

    def _render_shipment_section(self, drop_no: str):
        """Render shipment management for selected stop"""
        try:
            # Show existing shipments
            self._display_shipments_table(drop_no)

            # Shipment entry form
            self._render_shipment_form(drop_no)

            # Manage existing shipments
            self._render_shipment_management(drop_no)

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
        """Render SID editor panel"""
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
        """Render OSD editor panel"""
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
