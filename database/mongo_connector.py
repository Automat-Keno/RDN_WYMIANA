"""
Zoptymalizowany łącznik MongoDB z connection pooling i lepszą obsługą błędów
"""

import datetime
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure


class OptimizedMongoConnector:
    """Zoptymalizowany łącznik MongoDB z connection pooling."""

    def __init__(self, host: str = 'localhost', port: int = 27017, 
                 username: Optional[str] = None, password: Optional[str] = None, 
                 db_name: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_name = db_name
        
        self.client = None
        self.db = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Buduje connection string dla MongoDB."""
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}?authSource={self.db_name}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.db_name}"

    def connect(self) -> bool:
        """Nawiązuje połączenie z bazą MongoDB z connection pooling."""
        try:
            self.client = MongoClient(
                self._connection_string,
                serverSelectionTimeoutMS=5000,  # 5 sekund timeout
                connectTimeoutMS=10000,         # 10 sekund timeout połączenia
                socketTimeoutMS=30000,          # 30 sekund timeout socket
                maxPoolSize=10,                 # Maksymalny rozmiar pool
                minPoolSize=1,                  # Minimalny rozmiar pool
                maxIdleTimeMS=30000,            # 30 sekund idle time
                retryWrites=True,               # Retry dla operacji zapisu
                retryReads=True                 # Retry dla operacji odczytu
            )
            
            # Test połączenia
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            
            print("✅ Połączenie z MongoDB nawiązane pomyślnie")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ Błąd połączenia z MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas łączenia z MongoDB: {e}")
            return False

    def disconnect(self):
        """Zamyka połączenie z bazą MongoDB."""
        if self.client:
            self.client.close()
            print("🔌 Połączenie z MongoDB zamknięte")

    def ensure_connection(self) -> bool:
        """Upewnia się, że połączenie jest aktywne."""
        if not self.client:
            return self.connect()
        
        try:
            # Test połączenia
            self.client.admin.command('ping')
            return True
        except:
            print("⚠️  Połączenie utracone, próba ponownego połączenia...")
            return self.connect()

    def insert_document(self, collection_name: str, document: Dict[str, Any]) -> bool:
        """Wstawia dokument do kolekcji z obsługą błędów."""
        try:
            if not self.ensure_connection():
                return False
            
            collection = self.db[collection_name]
            result = collection.insert_one(document)
            print(f"✅ Wstawiono dokument z ID: {result.inserted_id}")
            return True
            
        except OperationFailure as e:
            print(f"❌ Błąd operacji MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas wstawiania: {e}")
            return False

    def find_document(self, collection_name: str, filtr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Znajduje dokument w kolekcji."""
        try:
            if not self.ensure_connection():
                return None
            
            collection = self.db[collection_name]
            return collection.find_one(filtr)
            
        except OperationFailure as e:
            print(f"❌ Błąd operacji MongoDB: {e}")
            return None
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas wyszukiwania: {e}")
            return None

    def find_documents(self, collection_name: str, filtr: Dict[str, Any], 
                      projection_fields: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Znajduje dokumenty w kolekcji."""
        try:
            if not self.ensure_connection():
                return []
            
            collection = self.db[collection_name]
            cursor = collection.find(filtr, projection_fields)
            return list(cursor)
            
        except OperationFailure as e:
            print(f"❌ Błąd operacji MongoDB: {e}")
            return []
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas wyszukiwania: {e}")
            return []

    def update_document(self, collection_name: str, filtr: Dict[str, Any], 
                       nowe_dane: Dict[str, Any]) -> bool:
        """Aktualizuje dokument w kolekcji."""
        try:
            if not self.ensure_connection():
                return False
            
            collection = self.db[collection_name]
            result = collection.update_one(filtr, nowe_dane)
            
            if result.matched_count > 0:
                print(f"✅ Zaktualizowano {result.modified_count} dokumentów")
                return True
            else:
                print("⚠️  Nie znaleziono dokumentów do aktualizacji")
                return False
                
        except OperationFailure as e:
            print(f"❌ Błąd operacji MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas aktualizacji: {e}")
            return False

    def delete_documents_older_than_days(self, collection_name: str, days: int = 3) -> bool:
        """Usuwa dokumenty starsze niż określona liczba dni."""
        try:
            if not self.ensure_connection():
                return False
            
            collection = self.db[collection_name]
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            filtr = {"data_cet": {"$lt": cutoff_date}}
            
            result = collection.delete_many(filtr)
            print(f"🗑️  Usunięto {result.deleted_count} starych dokumentów")
            return True
            
        except OperationFailure as e:
            print(f"❌ Błąd operacji MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd podczas usuwania: {e}")
            return False 