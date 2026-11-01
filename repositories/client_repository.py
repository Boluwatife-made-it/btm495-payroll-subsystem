"""
Client Repository (Data Access Management / DAM Layer)
Encapsulates SQL queries and persistence for the Client aggregate (Chapter 7 C.5).
"""

from database.db import db
from models.client import Client

class ClientRepository:
    @staticmethod
    def get_all():
        """Fetches all client organizations ordered by client ID."""
        sql = "SELECT * FROM clients ORDER BY client_id ASC"
        rows = db.query_all(sql)
        return [Client.from_row(r).to_dict() for r in rows]

    @staticmethod
    def get_by_id(client_id: int):
        """Fetches a single client by primary key."""
        sql = "SELECT * FROM clients WHERE client_id = ?"
        row = db.query_one(sql, (client_id,))
        return Client.from_row(row) if row else None
