<p align="center"><img src="custom_components/homemail/brand/icon@2x.png" width="128" alt=""><br><img src="docs/wordmark.svg" height="56" alt="Home-mail"></p>

# Home-mail

*Home + E-mail: de **E** van Home is de **E** van E-mail.*

**Je mail, opgehaald door je eigen Home Assistant.** Een overzichtelijke mail-app in de stijl van iOS Mail, die in Home Assistant woont: als zijbalk-paneel, als dashboardkaart en als losse web-app op het beginscherm van je telefoon.

[English](README.md)

## Waarom

- **Privacy** – je mail gaat van je provider rechtstreeks naar je eigen Home Assistant. Geen mail-app van derden, geen clouddienst ertussen, geen volgpixels (die worden eruit gefilterd).
- **Batterij** – de telefoon hoeft geen mailservers af te vragen. Dat doet Home Assistant thuis; de telefoon laat alleen zien wat er is.
- **Meldingen direct binnen** – Home Assistant geeft bij elke nieuwe mail een event, dus je kunt elk apparaat een melding sturen, een lamp laten knipperen of het laten omroepen.
- **Alles op één plek** – al je accounts (Gmail, iCloud, Outlook, eigen domein) in één inbox, naast de rest van je huis.

## Mogelijkheden

- Alle inkomende, inbox per account en alle mappen (Concepten, Verstuurd, Spam, Prullenmand, Archief, eigen mappen) met tellers
- Veilig lezen: HTML wordt opgeschoond en zonder scripts getoond; externe afbeeldingen aan/uit; volgpixels verwijderd
- Vegen zoals op iOS: archiveren, verwijderen, gelezen/ongelezen; vlag; terug naar inkomend
- Schrijven, beantwoorden, allen beantwoorden en doorsturen (met bijlagen van het origineel), handtekening en kleur per account
- Adressuggesties uit je inbox en verzonden mail
- Zoeken (op de server; bij Gmail werkt de Gmail-zoeksyntax)
- Per account een sensor met het aantal ongelezen berichten, en een event `homemail_new_mail`
- Per account kies je welke Home Assistant-gebruikers het mogen gebruiken (standaard: alleen beheerders)
- Engels en Nederlands

## Installatie

### 1. Installeren met HACS

1. Open in Home Assistant **HACS**, menu ⋮ → **Aangepaste repositories**.
2. Voeg `https://github.com/dadalouis/Home-mail` toe met type **Integratie**.
3. Zoek **Home-mail**, klik **Downloaden** en **herstart Home Assistant**.

### 2. Mailaccount toevoegen

**Instellingen → Apparaten en diensten → Integratie toevoegen → Home-mail.** Kies je provider en vul adres en wachtwoord in. Home-mail test het inloggen (ontvangen *én* versturen) voordat er iets wordt opgeslagen. Meer accounts voeg je op dezelfde manier toe.

**Gmail en iCloud** accepteren je gewone wachtwoord niet meer in andere mail-apps. Ze vragen eenmalig een *app-wachtwoord*; Home-mail laat de stappen zien met directe links:

1. Zet verificatie in 2 stappen aan ([Google](https://myaccount.google.com/signinoptions/twosv)); een bevestiging op je telefoon is genoeg.
2. Maak een app-wachtwoord ([Google](https://myaccount.google.com/apppasswords) / [Apple](https://account.apple.com/account/manage)) met de naam "Home Assistant".
3. Plak het in Home-mail. Spaties mogen.

De meeste andere providers (eigen domein, mail van je internetprovider) werken met je gewone wachtwoord.

### 3. De app openen

- **Zijbalk**: er verschijnt een item **Home-mail**.
- **Dashboardkaart**: voeg een kaart `custom:homemail-card` toe (het mooist in een weergave van het type *Paneel*).
- **Beginscherm van je telefoon**: open `https://<jouw-home-assistant>/homemail-files/app.html` in Safari/Chrome, log in met je Home Assistant-account en kies *Deel → Zet op beginscherm*.

### 4. Meldingen (optioneel)

- **Companion-app**: importeer de blueprint (`blueprints/automation/homemail/new_mail_notification.yaml`) en kies je telefoon.
- **Web-push naar de beginscherm-app**: stel de Home Assistant-integratie [HTML5 push](https://www.home-assistant.io/integrations/html5/) in; de web-app toont dan een knop "Meldingen aan" en een rood getal met het aantal ongelezen mails.
- **Eigen automations**: trigger op het event `homemail_new_mail`.

## Toegang van buitenaf

Home-mail gebruikt je gewone Home Assistant-adres en -login, dus het werkt overal waar Home Assistant werkt. Voor meldingen, het rode getal en de beginscherm-app is **HTTPS** nodig (Nabu Casa, eigen domein via bijvoorbeeld Cloudflare Tunnel, of een VPN naar een https-adres). Via alleen `http://<ip>:8123` thuis kun je wel lezen en versturen.

## Hoe het werkt

- Elk mailaccount is een eigen koppeling. Het wachtwoord staat alleen in je eigen Home Assistant en wordt nooit gelogd.
- Mail wordt op verzoek rechtstreeks van de IMAP-server gehaald; behalve de ongelezen-teller komt er niets in de states of de database.
- De app praat via de websocket-API (`homemail/*`) met Home Assistant. Elke opdracht controleert of de ingelogde gebruiker dat account mag gebruiken.
- Elke inbox wordt elke 60 seconden gecontroleerd (instelbaar per account) met één lichte `STATUS`-opdracht.

## Over

Home-mail begon als eigen project: een Home Assistant-gebruiker wilde een mail-app op de telefoon die mail niet aan nog een clouddienst geeft en de batterij spaart, en bouwde die samen met Claude (de AI-assistent van Anthropic).

## Licentie

MIT
