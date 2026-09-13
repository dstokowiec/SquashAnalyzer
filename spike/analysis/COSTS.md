# Rejestr kosztów API — spike analizy wideo (F-01)

**Budżet: 50,00 zł** — twardy stop. Wiersz, po którym suma narastająca przekroczyłaby budżet, nie jest uruchamiany; werdykt powstaje z danych częściowych.

Zasady:

- Każde wywołanie płatnego API dopisuje jeden wiersz (także nieudane, jeśli zostały naliczone).
- Tokeny i koszt USD liczone z `usage_metadata` odpowiedzi według cennika z dnia wywołania; kurs USD→PLN z dnia wywołania.
- Kandydat A (lokalny compute) nie generuje wierszy.

| Data | Kandydat / segment | Model | Tokeny wej. | Tokeny wyj. | Koszt USD | Kurs USD→PLN | Koszt zł | Suma narastająco zł |
| ---- | ------------------ | ----- | ----------- | ----------- | --------- | ------------ | -------- | ------------------- |
