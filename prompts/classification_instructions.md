# Klassifizierungslogik

**Entscheidung nach Kriterien, nicht nach „Unsicherheit“:**  
Prüfe: Erfüllt diese E-Mail die **definierenden Kriterien** einer Kategorie **eindeutig**?  
- **Ja** (z. B. echte Rechnung mit Betrag/Zahlungsziel, echter Newsletter von Anbieter mit Werbung/Update) → das passende Label (ggf. 1–3, wenn mehrere passen).  
- **Nein** (keine Kategorie passt eindeutig: Test, persönlich, unklar, Weiterleitung ohne Kontext) → **nur Sonstiges**. Sonstiges wird **nie** mit anderen Labels kombiniert – genau ein Label.

Jedes Label ist für einen **bestimmten E-Mail-Typ** gedacht. Ein Label nur vergeben, wenn die Mail die Kriterien dieser Kategorie **eindeutig** erfüllt – nicht, weil ein Stichwort vorkommt.

**Grundprinzip:**  
Frage: „Erfüllt diese Mail die Kriterien dieser Kategorie eindeutig?“  
- **Ja** → passendes Label.  
- **Nein** (oder keine Kategorie trifft zu) → **nur** Sonstiges, kein zweites Label.

Beispiele helfen, aber neue Mails (andere Absender, andere Formulierungen) müssen anhand der **Kriterien** eingeordnet werden, nicht anhand von Stichwörtern.

---

## Definierende Kriterien pro Label

**Banking**  
- *Wofür die Kategorie da ist:* Kommunikation von Bank/Finanzdienstleister zu Kunde (Konto, Karte, Transaktionen).  
- *Kriterien:* Absender bzw. Inhalt beziehen sich eindeutig auf Bankgeschäft, Kontobewegungen, Kartenabbuchungen, Überweisungen.  
- *Nicht:* AGB, Datenschutz, Cloud-Anbieter, allgemeine rechtliche Hinweise.

**Streaming**  
- *Wofür die Kategorie da ist:* Abo- und Inhalte-Hinweise von Video-/Musik-Streaming-Anbietern (Serien, Filme, Musik).  
- *Kriterien:* Absender/Inhalt eindeutig Streaming-Dienst (Netflix, Spotify, Prime, Disney+ etc.); Thema Abo, Inhalte, Nutzung.  
- *Nicht:* Fahrdienste (Bolt, Uber), andere Apps, allgemeine Werbung.

**Rechnung**  
- *Wofür die Kategorie da ist:* Rechnungsstellung, Zahlungsaufforderung, Faktura.  
- *Kriterien:* Inhalt dient erkennbar der Rechnungsstellung (Betrag, Zahlungsziel, Rechnungsnummer, Faktura).  
- *Nicht:* Nur Erwähnung von „Rechnung“ in anderem Kontext (z. B. Support-Anfrage).

**Warnung**  
- *Wofür die Kategorie da ist:* Sicherheitsrelevante oder fehlerbezogene Meldungen (Login, Konto, System).  
- *Kriterien:* Inhalt ist erkennbar Fehlermeldung, Sicherheitshinweis oder Warnung (z. B. verdächtige Anmeldung, „Falls Sie das nicht waren“).  
- *Nicht:* Allgemeine Info-Mails ohne Sicherheits-/Fehlerbezug.

**Shopping**  
- *Wofür die Kategorie da ist:* Bestell- und Lieferprozess (Bestellung, Versand, Tracking).  
- *Kriterien:* Inhalt bezieht sich auf konkrete Bestellung, Versand, Sendungsverfolgung, Shop-Transaktion.  
- *Nicht:* Nur allgemeine Werbung ohne Bestell-/Versandbezug.

**Social Media**  
- *Wofür die Kategorie da ist:* Systemseitige Benachrichtigungen von Social-Media-Plattformen (Mentions, DMs, Likes, etc.).  
- *Kriterien:* Absender/Inhalt eindeutig von einer solchen Plattform (LinkedIn, X/Twitter, Instagram, Facebook, YouTube) als Benachrichtigung.  
- *Nicht:* Newsletter von Medien, die nur „sozial“ klingen.

**Support**  
- *Wofür die Kategorie da ist:* Anfragen oder Antworten im Kontext Hilfe, Ticket, Bug, technischer Kundenservice.  
- *Kriterien:* Inhalt ist erkennbar Support-Dialog (Problem, Rückfrage, Ticket, Lösung).  
- *Nicht:* Allgemeine Produktinfos oder Werbung.

**Newsletter**  
- *Wofür die Kategorie da ist:* Gezielter Massenversand mit Marketing- oder Informationszweck (Angebote, Updates, Promos) von Anbietern/Marken an viele Empfänger.  
- *Kriterien:* Typische Newsletter-Situation: Absender ist Anbieter/Marke; Inhalt ist Werbung, regelmäßige Updates, Aktionen oder redaktionelle Rundmail; oft Abmeldelink oder klar werbend/mehrwertorientiert.  
- *Nicht:* Persönliche 1:1-Mail, Test-Mail, interne Notiz, Mail ohne erkennbaren Newsletter-/Marketing-Charakter. „Test“ oder „Testmail“ ohne weiteren Kontext erfüllt **keine** Newsletter-Kriterien → Sonstiges.

**Versicherung**  
- *Wofür die Kategorie da ist:* Versicherungsbezogene Kommunikation (Police, Beitrag, Schaden, Vertrag).  
- *Kriterien:* Absender/Inhalt eindeutig versicherungsbezogen (Versicherer, Beitrag, Schadensmeldung, Vertragsinfo).  
- *Nicht:* Allgemeine rechtliche Updates, AGB, Cloud-Anbieter.

**Sonstiges**  
- *Wofür die Kategorie da ist:* Alles, was **keine** der obigen Kategorien **eindeutig** erfüllt.  
- *Kriterien:* Die Mail erfüllt die definierenden Kriterien keiner anderen Kategorie (z. B. persönlich, Test, Weiterleitung ohne Kontext, rechtliche/AGB/Cloud-Hinweise, unklarer Inhalt).  
- **Sonstiges wird nie mit anderen Labels kombiniert** – wenn Sonstiges, dann nur dieses eine Label.

---

## Regeln (kurz)

- Nur erlaubte Labels. Spezifische Labels: nur wenn die **Kriterien** der Kategorie **eindeutig** erfüllt sind (dann 1–3 Labels möglich).  
- Keine Kategorie passt eindeutig (Test, persönlich, unklar) → **nur** Sonstiges, kein zweites Label.

## Beispiele (zur Orientierung, Logik liegt in den Kriterien)

| Typische Mail | Label |
|---------------|--------|
| Rechnung mit Betrag, Zahlungsziel | Rechnung |
| „Neue Anmeldung erkannt“ / Sicherheitshinweis | Warnung |
| Versandbestätigung, Tracking | Shopping |
| [Legal Update] reCAPTCHA / Cloud-Anbieter | Sonstiges |
| Bolt/Uber Werbung, Angebote der Woche | Newsletter |
| „Testmail“ / „Das ist nur ein Test“ (persönlich) | Sonstiges |
| Problem beim Login, Ticket-Anfrage | Support |
| LinkedIn/X/Instagram-Benachrichtigung | Social Media |
| Bank-Konto, Transaktion | Banking |
| Netflix/Spotify Abo, neue Folgen | Streaming |
| Versicherung Beitrag, Schaden | Versicherung |

Priorisierung bei mehreren passenden Labels: Rechnung > Support > Banking/Versicherung > Shopping/Streaming/Newsletter/Social Media > Sonstiges. Warnung zusätzlich setzen, wenn Sicherheits-/Fehlermeldung erkennbar.
