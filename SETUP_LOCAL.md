# 🔧 Konfiguracja Lokalna

## Dla Developmentu

Aby uruchomić kod lokalnie z Twoimi danymi dostępowymi do bazy MongoDB:

### Krok 1: Stwórz plik konfiguracyjny lokalnie

Skopiuj `config.local.example.json` do `config.local.json`:

```bash
cp config.local.example.json config.local.json
```

### Krok 2: Uzupełnij dane dostępowe

Edytuj `config.local.json` i uzupełnij swoje rzeczywiste dane dostępowe:

```json
{
    "database": {
        "host": "91.185.184.123",
        "port": 27017,
        "username": "mo1608_prod",
        "password": "TWOJE_HASŁO",  ← UZUPEŁNIJ TUTAJ
        "db_name": "mo1608_prod"
    },
    ...
}
```

### Krok 3: Uruchom kod

Teraz możesz uruchomić kod lokalnie:

```bash
python main.py
```

Kod automatycznie wykryje plik `config.local.json` i będzie go używać.

---

## 🔒 Bezpieczeństwo

⚠️ **WAŻNE:**
- Plik `config.local.json` jest w `.gitignore` i **NIE będzie commitowany** do gita
- Zawsze przeglądaj `.gitignore` aby się upewnić że wrażliwe pliki są chronione
- Nigdy nie pushuj haseł do repozytorium!

---

## 🚀 W produkcji (GitHub Actions)

W GitHub Actions będą używane zmienne środowiskowe `MONGODB_*` zamiast `config.local.json`.

To jest bezpieczne ponieważ sekrety są przechowywane w ustawieniach repozytorium.

