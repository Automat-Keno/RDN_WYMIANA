"""
Zoptymalizowany downloader do pobierania plików CSV z obsługą retry i walidacją
"""

import requests
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Union
from requests.exceptions import RequestException, Timeout, ConnectionError


class OptimizedFileDownloader:
    """Zoptymalizowany downloader do pobierania plików CSV."""

    # Konfiguracja retry dla plików PSE RDN_PWM
    # Pliki pojawiają się między 13:15-13:30 CET, najpóźniej do 14:30
    INITIAL_RETRY_DELAY = 300  # 5 minut na początku
    MAX_RETRY_DELAY = 1800     # Maksymalnie 30 minut między próbami
    MAX_RETRIES = 18           # Maksymalnie 18 prób (do 14:30)
    TIMEOUT = 60               # 60 sekund timeout

    def __init__(self, url_template: str, data_start: str, data_end: Optional[str] = None):
        self.url_template = url_template
        self.data_start = self.format_date_for_url(data_start)
        self.data_start_dashed = self.format_date_dashed(data_start)
        self.data_end = self.format_date_for_url(data_end) if data_end else None

    @property
    def url(self) -> str:
        """Generuje pełny URL na podstawie podanych danych."""
        if self.data_end:
            return self.url_template.format(
                data_start=self.data_start, 
                data_end=self.data_end,
                data_start_dashed=self.data_start_dashed
            )
        return self.url_template.format(
            data_start=self.data_start,
            data_start_dashed=self.data_start_dashed
        )

    @staticmethod
    def format_date_for_url(date_string: str) -> str:
        """Konwertuje datę z formatu 'yyyy-MM-dd' na '%Y%m%d'."""
        if re.match(r'\d{8}', date_string):
            return date_string
        
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.strftime('%Y%m%d')
        except ValueError:
            raise ValueError(f"Nieprawidłowy format daty: {date_string}")
    
    @staticmethod
    def format_date_dashed(date_string: str) -> str:
        """Konwertuje datę na format 'YYYY-MM-DD' (z myślnikami)."""
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Nieprawidłowy format daty: {date_string}")

    def validate_response(self, response: requests.Response) -> bool:
        """Waliduje odpowiedź serwera."""
        if response.status_code == 404:
            print(f"📭 Plik jeszcze niedostępny (404) - prawdopodobnie PSE jeszcze nie opublikowało danych")
            return False
        elif response.status_code != 200:
            print(f"❌ Błąd HTTP: {response.status_code}")
            return False
        
        content_type = response.headers.get('content-type', '').lower()
        if 'csv' not in content_type and 'text' not in content_type:
            print(f"⚠️  Ostrzeżenie: Nieoczekiwany content-type: {content_type}")
        
        if len(response.content) < 100:  # Sprawdzenie czy plik nie jest pusty
            print("⚠️  Ostrzeżenie: Pobrany plik wydaje się być pusty")
            return False
        
        return True

    def calculate_retry_delay(self, attempt: int) -> int:
        """Oblicza opóźnienie przed kolejną próbą (exponential backoff)."""
        if attempt <= 3:
            return self.INITIAL_RETRY_DELAY  # Pierwsze 3 próby co 5 minut
        elif attempt <= 6:
            return 600  # Próby 4-6 co 10 minut
        elif attempt <= 9:
            return 900  # Próby 7-9 co 15 minut
        elif attempt <= 12:
            return 1200  # Próby 10-12 co 20 minut
        else:
            return self.MAX_RETRY_DELAY  # Ostatnie próby co 30 minut

    def download(self) -> Optional[bytes]:
        """Pobiera plik z określonego URL z inteligentnym retry."""
        retries = 0
        start_time = datetime.now()
        
        print(f"🚀 Rozpoczynam pobieranie pliku: {self.url}")
        print(f"⏰ Czas rozpoczęcia: {start_time.strftime('%H:%M:%S')}")
        print(f"🔍 DEBUG: data_start={self.data_start}, data_end={self.data_end}")
        
        while retries < self.MAX_RETRIES:
            try:
                print(f"📥 Próba {retries + 1}/{self.MAX_RETRIES}: {self.url}")
                
                response = requests.get(
                    self.url,
                    timeout=self.TIMEOUT,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; PSE-Data-Collector/1.0)'
                    }
                )
                
                if self.validate_response(response):
                    elapsed_time = datetime.now() - start_time
                    print(f"✅ Pobrano {len(response.content)} bajtów po {elapsed_time.total_seconds()/60:.1f} minutach")
                    
                    # DEBUG: Sprawdź liczbę wierszy w pliku
                    try:
                        content_str = response.content.decode('windows-1252')
                        lines = content_str.strip().split('\n')
                        print(f"🔍 DEBUG: Pobrano {len(lines)} linii (łącznie z headerem)")
                        print(f"🔍 DEBUG: Liczba wierszy danych: {len(lines) - 1}")
                    except:
                        pass
                    
                    return response.content
                else:
                    if response.status_code == 404:
                        print(f"📭 Plik jeszcze niedostępny - czekam przed kolejną próbą...")
                    else:
                        print(f"❌ Nieprawidłowa odpowiedź serwera")
                    
            except Timeout:
                print(f"⏰ Timeout podczas pobierania (próba {retries + 1}/{self.MAX_RETRIES})")
            except ConnectionError as e:
                print(f"🔌 Błąd połączenia (próba {retries + 1}/{self.MAX_RETRIES}): {e}")
            except RequestException as e:
                print(f"❌ Błąd żądania (próba {retries + 1}/{self.MAX_RETRIES}): {e}")
            except Exception as e:
                print(f"❌ Nieoczekiwany błąd (próba {retries + 1}/{self.MAX_RETRIES}): {e}")
            
            retries += 1
            if retries < self.MAX_RETRIES:
                delay = self.calculate_retry_delay(retries)
                next_attempt = datetime.now() + timedelta(seconds=delay)
                print(f"⏳ Czekam {delay/60:.1f} minut przed kolejną próbą...")
                print(f"🕐 Następna próba o: {next_attempt.strftime('%H:%M:%S')}")
                time.sleep(delay)
        
        elapsed_time = datetime.now() - start_time
        print(f"❌ Przekroczono maksymalną liczbę prób ({self.MAX_RETRIES})")
        print(f"⏱️  Całkowity czas oczekiwania: {elapsed_time.total_seconds()/3600:.1f} godzin")
        print(f"💡 Plik może być dostępny później - sprawdź ręcznie lub uruchom ponownie")
        return None 