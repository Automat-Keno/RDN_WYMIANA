"""
Zoptymalizowany procesor danych do przetwarzania CSV bez zapisywania plików lokalnie
"""

import csv
import io
import datetime
import pytz
from typing import List, Dict, Any, Optional
from unidecode import unidecode
from database.mongo_connector import OptimizedMongoConnector


class OptimizedDataProcessor:
    """Zoptymalizowany procesor danych do przetwarzania CSV w pamięci."""

    def __init__(self, url_template: str, data_start: str, int_cols: List[str], 
                 float_cols: List[str], date_cols: List[str], 
                 fields_to_utc: List[str] = None, fields_to_add_hour: Dict[str, str] = None,
                 date_format: str = None, mongo_connector: OptimizedMongoConnector = None,
                 kolekcja_mongo: str = None):
        self.url_template = url_template
        self.data_start = data_start
        self.int_cols = int_cols
        self.float_cols = float_cols
        self.date_cols = date_cols
        self.fields_to_utc = fields_to_utc or []
        self.fields_to_add_hour = fields_to_add_hour or {}
        self.date_format = date_format
        self.mongo_connector = mongo_connector
        self.kolekcja_mongo = kolekcja_mongo
        
        # Konwersja daty startowej
        self.data_start_dt = datetime.datetime.strptime(data_start, '%Y-%m-%d')
        
    def format_date_for_url(self, date_string: str) -> str:
        """Konwertuje datę z formatu 'yyyy-MM-dd' na '%Y%m%d'."""
        try:
            date_obj = datetime.datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.strftime('%Y%m%d')
        except ValueError:
            raise ValueError(f"Nieprawidłowy format daty: {date_string}")

    def convert_to_utc(self, local_date: datetime.datetime) -> datetime.datetime:
        """Konwertuje datę lokalną na UTC."""
        warsaw_tz = pytz.timezone('Europe/Warsaw')
        local_date = warsaw_tz.localize(local_date)
        return local_date.astimezone(pytz.UTC)

    def process_csv_content(self, csv_content: bytes) -> List[Dict[str, Any]]:
        """Przetwarza zawartość CSV w pamięci."""
        processed_data = []
        
        # Dekodowanie zawartości z kodowania windows-1252
        try:
            content_str = csv_content.decode('windows-1252')
        except UnicodeDecodeError:
            # Fallback do UTF-8
            content_str = csv_content.decode('utf-8', errors='ignore')
        
        # Przetwarzanie CSV z pamięci
        csv_reader = csv.DictReader(io.StringIO(content_str), delimiter=';')
        
        for row in csv_reader:
            processed_row = self._process_row(row)
            if processed_row:
                processed_data.append(processed_row)
        
        return processed_data

    def _process_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Przetwarza pojedynczy wiersz danych."""
        try:
            # Konwersja kolumn int
            for column in self.int_cols:
                value = row.get(column, '')
                if value == '-':
                    row[column] = None
                elif column == 'Godzina':
                    if value == "2A":
                        row[column] = 2
                    else:
                        row[column] = int(value) - 1
                else:
                    if value == '':
                        row[column] = None
                    elif value is not None:
                        row[column] = int(value.replace('\xa0', ''))

            # Konwersja kolumn float
            for column in self.float_cols:
                value = row.get(column, '')
                if value == '-':
                    row[column] = None
                elif value:
                    row[column] = float(value.replace(',', '.'))

            # Konwersja kolumn dat
            for column in self.date_cols:
                if row[column]:
                    local_date = datetime.datetime.strptime(row[column], self.date_format)
                    
                    if column in self.fields_to_utc:
                        row[column] = self.convert_to_utc(local_date)
                    
                    if column in self.fields_to_add_hour:
                        add_hour_field = self.fields_to_add_hour[column]
                        if row[add_hour_field] is not None:
                            local_date += datetime.timedelta(hours=row[add_hour_field])
                            row[column] = self.convert_to_utc(local_date)

            # Normalizacja nazw kolumn
            processed_row = {unidecode(key.replace(" ", "_")): value for key, value in row.items()}
            return processed_row
            
        except Exception as e:
            print(f"Błąd podczas przetwarzania wiersza: {e}")
            return None

    def save_to_mongo(self, data: List[Dict[str, Any]]) -> bool:
        """Zapisuje dane do MongoDB z optymalizacją."""
        try:
            if not self.mongo_connector:
                print("Błąd: Brak połączenia z MongoDB")
                return False

            data_start_utc = self.convert_to_utc(self.data_start_dt)
            filtr = {'data_cet': data_start_utc}

            # Sprawdzenie czy rekord już istnieje
            existing_record = self.mongo_connector.find_document(self.kolekcja_mongo, filtr)
            
            if existing_record is None:
                # Wstawienie nowego rekordu
                new_document = {
                    'data_cet': data_start_utc,
                    'data_wstawienia': datetime.datetime.now(pytz.UTC),
                    'dane': data
                }
                self.mongo_connector.insert_document(self.kolekcja_mongo, new_document)
                print(f"✅ Wstawiono nowy rekord dla daty {self.data_start}")
            else:
                # Aktualizacja istniejącego rekordu
                update_data = {
                    '$set': {
                        'czas_aktualizacji': datetime.datetime.now(pytz.UTC),
                        'dane': data
                    }
                }
                self.mongo_connector.update_document(self.kolekcja_mongo, filtr, update_data)
                print(f"✅ Zaktualizowano rekord dla daty {self.data_start}")
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd podczas zapisu do MongoDB: {e}")
            return False

    def process_and_save(self) -> bool:
        """Główna metoda - pobiera, przetwarza i zapisuje dane."""
        try:
            # Pobieranie danych
            from downloader.file_downloader import OptimizedFileDownloader
            downloader = OptimizedFileDownloader(self.url_template, self.data_start)
            csv_content = downloader.download()
            
            if not csv_content:
                print("❌ Nie udało się pobrać danych")
                return False
            
            # Przetwarzanie danych
            print("🔄 Przetwarzanie danych...")
            processed_data = self.process_csv_content(csv_content)
            
            if not processed_data:
                print("❌ Brak danych do przetworzenia")
                return False
            
            print(f"📊 Przetworzono {len(processed_data)} wierszy danych")
            
            # Zapis do bazy danych
            return self.save_to_mongo(processed_data)
            
        except Exception as e:
            print(f"❌ Błąd podczas przetwarzania: {e}")
            return False 