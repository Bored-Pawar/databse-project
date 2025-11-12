# modules/database.py - Database Operations Manager

import pandas as pd
from snowflake.snowpark.context import get_active_session
from modules.config import get_table_names
from modules.sql_utils import escape_sql, sql_literal, IDGenerator

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
