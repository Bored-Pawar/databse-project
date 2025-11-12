# modules/sql_utils.py - SQL Utilities and Helpers

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
