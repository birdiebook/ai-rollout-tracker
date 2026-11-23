# Status steg 2

Uppdateras av orkestreraren vid varje milstolpe. Senast: 2026-11-23 22:30 UTC.

## Läge

- **Våg 0** klar: delad data, förregistrering C0 (granskad, R6), sannolikhetsprognoser (påslagna), månadsbrev.
- **Våg 1** nästan klar: allt utom PyPI/npm och GitHub är mergat, inklusive Cloudflare Radar och Wikipedia.
  **Granskning R3 (datum):** inget läckage. Två fel daterade för sent (Meta-skuld, Manifold-urval) rättas av spår X2.
  PyPI/npm är mergat (PyPI-historiken är onsdagsurval, eftersom exakt historik skulle kosta cirka 1,7 TB).
  **Granskning R5 (extraktion):** klar. Nvidias guidance är godkänd för N3. AI-nyckeltal, leasingåtaganden och planer är
  godkända med rättningar (F1–F14, 26 strikta xfail-tester). Rättningarna görs efter att kvoten återställts.
- **Våg 2** kör: N3–N6 och B3. Datasnapshoten är klar och väntar på `DATA_KEY`. Avstämningarna (A5) och D2 är
  förregistrerade.

## Väntar på Johannes

1. **Holdouten** för faktormodellen (C3) och regimmodellen (C4) öppnas först efter ditt godkännande. Den kan bara
   öppnas en gång.
2. **`DATA_KEY`** (datasnapshoten är byggd):
   - skapa en nyckel med `python -c "import secrets; print(secrets.token_urlsafe(32))"` och spara den i en lösenordshanterare;
   - lägg in den som GitHub-secret `DATA_KEY` och som miljövariabel `DATA_KEY` i miljön ai-rollout-tracker;
   - kör sedan "Weekly data fetch" en gång för hand.
3. **Cloudflare Radar har licensen CC BY-NC 4.0.** Serierna visas på hemsidan eftersom sidan är icke-kommersiell. Ska
   sidan någon gång användas kommersiellt måste de dras tillbaka.

4. **Tolkningsfrågor från R5 (F2, F4–F6).** Rekommendation: tillämpa B4:s tolkning 7 som den står. Orkestreraren
   väljer rekommendationen om inget annat sägs.
5. **PyPI-historik i Actions-cachen** (cirka 176 GB av månadskvoten på 1 TB) kan vänta till nästa kvotmånad.

## Viktiga datum

- 2026-11-30: första skarpa ögonblicksbilden och månadsbrevet
- 2026-12-05: första skarpa TSMC-prognosen (B2)
- 2027-01-20: första skarpa capex-prognosen
