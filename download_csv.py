#!/usr/bin/env python3
"""
Skrypt do pobrania pliku CSV z PSE
"""

import requests
import os
from datetime import datetime, timedelta

def main():
    """Pobierz plik CSV."""
    print("=" * 70)
    print("📥 POBIERANIE PLIKU CSV Z PSE")
    print("=" * 70)
    
    # Domyślnie pobierz dla jutrzejszej daty
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime('%Y%m%d')
    
    url = f"https://www.pse.pl/getcsv/-/export/csv/PL_PWM_RDN/data/{date_str}"
    
    print(f"\n📅 Data: {tomorrow.strftime('%Y-%m-%d')}")
    print(f"🔗 URL: {url}")
    
    try:
        print("\n⏳ Pobieram...")
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Błąd: Status {response.status_code}")
            return 1
        
        # Nazwa pliku
        filename = f"PL_PWM_RDN_{date_str}.csv"
        
        # Zapisz
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        # Informacje
        file_size = os.path.getsize(filename)
        
        print(f"✅ Pobrano {file_size} bajtów")
        print(f"💾 Zapisano do: {os.path.abspath(filename)}")
        
        # Pokaż zawartość
        content_str = response.content.decode('windows-1252')
        lines = content_str.strip().split('\n')
        
        print(f"\n📊 Plik zawiera:")
        print(f"   - {len(lines)} linii (łącznie z headerem)")
        print(f"   - {len(lines) - 1} wierszy danych")
        
        # Pokaż header
        print(f"\n📋 Header:")
        print(f"   {lines[0]}")
        
        # Pokaż pierwsze 3 wiersze
        print(f"\n📝 Pierwsze 3 wiersze:")
        for i, line in enumerate(lines[1:4], 1):
            print(f"   {i}. {line[:80]}...")
        
        return 0
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

