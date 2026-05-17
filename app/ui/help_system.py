"""
app/ui/help_system.py
=====================
Context-sensitive help system for N1MM Field Day Tracker.

Every screen, dialog and important field has a help text.
Help is available via:
  - F1 key on any dialog or the main window
  - A "?" button on every dialog
  - Help menu → topic selection

Usage
-----
    from app.ui.help_system import show_help, HelpTopic

    # Show help for a specific topic in a dialog
    show_help(parent_widget, HelpTopic.CSV_IMPORT)

    # Bind F1 to contextual help on a Tkinter widget
    bind_f1(widget, HelpTopic.FIELD_DAY_SETTINGS)

Adding a new topic
------------------
1. Add a value to :class:`HelpTopic`.
2. Add entries in all 4 languages to :data:`_HELP_TEXTS`.
"""

from __future__ import annotations

from enum import Enum
from app.i18n.translations import t, get_language


# ---------------------------------------------------------------------------
# Help topics
# ---------------------------------------------------------------------------

class HelpTopic(str, Enum):
    """Identifiers for all help topics in the application."""

    # Main window
    MAIN_WINDOW         = "main_window"
    MATRIX_VIEW         = "matrix_view"
    CONNECTION_STATUS   = "connection_status"

    # Field day
    FIELD_DAY_SETTINGS  = "field_day_settings"
    FIELD_DAY_PERIOD    = "field_day_period"
    FIELD_DAY_BANDS     = "field_day_bands"

    # Stations & import
    CSV_IMPORT          = "csv_import"
    CSV_COLUMN_MAPPING  = "csv_column_mapping"
    MANUAL_STATION      = "manual_station"

    # N1MM integration
    N1MM_SETUP          = "n1mm_setup"
    N1MM_UDP            = "n1mm_udp"
    CALLSIGN_MATCHING   = "callsign_matching"

    # Overrides
    MANUAL_OVERRIDE     = "manual_override"

    # Settings
    SETTINGS            = "settings"
    LANGUAGE_SETTING    = "language_setting"
    STATUS_COLORS       = "status_colors"

    # Export
    CSV_EXPORT          = "csv_export"
    PDF_EXPORT          = "pdf_export"

    # Sync
    SYNC                = "sync"


# ---------------------------------------------------------------------------
# Help text registry
# ---------------------------------------------------------------------------
# Format: topic → language → text

_HELP_TEXTS: dict[str, dict[str, str]] = {

    HelpTopic.MAIN_WINDOW: {
        "en": (
            "Main Window\n\n"
            "The main window shows the Station × Band matrix for the active field day.\n\n"
            "• Header bar: shows the active field day name and period.\n"
            "• Matrix: rows = stations, columns = selected bands.\n"
            "• Status bar: N1MM connection status + timestamp of last received contact.\n\n"
            "Use the File menu to create or open a field day.\n"
            "Use the Tools menu for sync, adding stations, and settings."
        ),
        "nl": (
            "Hoofdvenster\n\n"
            "Het hoofdvenster toont de Station × Band matrix voor de actieve velddag.\n\n"
            "• Koptekst: toont de naam en periode van de actieve velddag.\n"
            "• Matrix: rijen = stations, kolommen = geselecteerde banden.\n"
            "• Statusbalk: N1MM-verbindingsstatus + tijdstip laatste ontvangen contact.\n\n"
            "Gebruik het menu Bestand om een velddag aan te maken of te openen.\n"
            "Gebruik het menu Extra voor sync, stations toevoegen en instellingen."
        ),
        "fr": (
            "Fenêtre principale\n\n"
            "La fenêtre principale affiche la matrice Station × Bande pour la journée terrain active.\n\n"
            "• En-tête : nom et période de la journée terrain active.\n"
            "• Matrice : lignes = stations, colonnes = bandes sélectionnées.\n"
            "• Barre d'état : statut connexion N1MM + horodatage du dernier contact reçu.\n\n"
            "Utilisez le menu Fichier pour créer ou ouvrir une journée terrain.\n"
            "Utilisez le menu Outils pour synchroniser, ajouter des stations et accéder aux paramètres."
        ),
        "es": (
            "Ventana principal\n\n"
            "La ventana principal muestra la matriz Estación × Banda para el Field Day activo.\n\n"
            "• Encabezado: nombre y período del Field Day activo.\n"
            "• Matriz: filas = estaciones, columnas = bandas seleccionadas.\n"
            "• Barra de estado: estado de conexión N1MM + marca de tiempo del último contacto.\n\n"
            "Use el menú Archivo para crear o abrir un Field Day.\n"
            "Use el menú Herramientas para sincronizar, agregar estaciones y configurar."
        ),
    },

    HelpTopic.MATRIX_VIEW: {
        "en": (
            "Matrix View\n\n"
            "The matrix shows which stations have been worked on which bands.\n\n"
            "CELL COLOURS (default):\n"
            "  White       = Not worked\n"
            "  Green       = Worked (logged by N1MM)\n"
            "  Dark green  = Worked (manually marked)\n"
            "  Yellow/Amber= Not worked (manually marked)\n"
            "  Grey        = Excluded from statistics\n\n"
            "ACTIONS:\n"
            "  • Right-click any cell → set manual override\n"
            "  • Search box → filter by callsign\n"
            "  • Filter buttons → All / Fully Worked / Not Worked / Partial\n"
            "  • Band filter → show only one band column\n\n"
            "The matrix updates automatically when N1MM logs a contact.\n"
            "Use Tools → Manual Sync to force a recalculation."
        ),
        "nl": (
            "Matrixweergave\n\n"
            "De matrix toont welke stations op welke banden gewerkt zijn.\n\n"
            "CELKLEUREN (standaard):\n"
            "  Wit         = Niet gewerkt\n"
            "  Groen       = Gewerkt (gelogd door N1MM)\n"
            "  Donkergroen = Gewerkt (manueel ingesteld)\n"
            "  Geel/Amber  = Niet gewerkt (manueel ingesteld)\n"
            "  Grijs       = Uitgesloten van statistieken\n\n"
            "ACTIES:\n"
            "  • Rechtsklik op cel → manuele override instellen\n"
            "  • Zoekvak → filter op callsign\n"
            "  • Filterknopen → Alle / Volledig / Niet gewerkt / Gedeeltelijk\n"
            "  • Bandfilter → toon slechts één bandkolom\n\n"
            "De matrix wordt automatisch bijgewerkt als N1MM een contact logt.\n"
            "Gebruik Extra → Handmatige sync om te herberekenen."
        ),
        "fr": (
            "Vue Matrice\n\n"
            "La matrice montre quelles stations ont été travaillées sur quelles bandes.\n\n"
            "COULEURS DES CELLULES (défaut) :\n"
            "  Blanc       = Non travaillé\n"
            "  Vert        = Travaillé (enregistré par N1MM)\n"
            "  Vert foncé  = Travaillé (marqué manuellement)\n"
            "  Jaune/Ambre = Non travaillé (marqué manuellement)\n"
            "  Gris        = Exclu des statistiques\n\n"
            "ACTIONS :\n"
            "  • Clic droit sur une cellule → définir une substitution manuelle\n"
            "  • Zone de recherche → filtrer par indicatif\n"
            "  • Boutons de filtre → Tout / Entier / Non travaillé / Partiel\n"
            "  • Filtre de bande → afficher une seule colonne de bande"
        ),
        "es": (
            "Vista de Matriz\n\n"
            "La matriz muestra qué estaciones han sido trabajadas en qué bandas.\n\n"
            "COLORES DE CELDA (predeterminado):\n"
            "  Blanco      = No trabajado\n"
            "  Verde       = Trabajado (registrado por N1MM)\n"
            "  Verde oscuro= Trabajado (marcado manualmente)\n"
            "  Amarillo    = No trabajado (marcado manualmente)\n"
            "  Gris        = Excluido de estadísticas\n\n"
            "ACCIONES:\n"
            "  • Clic derecho en celda → establecer sustitución manual\n"
            "  • Cuadro de búsqueda → filtrar por indicativo\n"
            "  • Botones de filtro → Todos / Completo / No trabajado / Parcial\n"
            "  • Filtro de banda → mostrar solo una columna de banda"
        ),
    },

    HelpTopic.N1MM_SETUP: {
        "en": (
            "N1MM Logger+ Setup\n\n"
            "This application receives contact data from N1MM Logger+ in real time\n"
            "via UDP broadcasts.\n\n"
            "STEPS IN N1MM LOGGER+:\n"
            "1. Go to Config → Configure Ports, Mode Control, Audio, Other\n"
            "2. Click the 'Broadcast Data' tab\n"
            "3. Find the 'Contact' row and check 'Enable'\n"
            "4. Set the Destination to: 127.0.0.1:12060\n"
            "5. Click OK\n\n"
            "IMPORTANT:\n"
            "  • Use contest: FDREG1\n"
            "  • The host (127.0.0.1) and port (12060) must match the\n"
            "    settings in this application (Tools → Settings).\n"
            "  • N1MM must be running on the same PC as this application,\n"
            "    or on a reachable network address.\n\n"
            "TROUBLESHOOTING:\n"
            "  • Check Windows Firewall is not blocking UDP port 12060.\n"
            "  • Log a test QSO in N1MM and watch the status bar update.\n"
            "  • If status stays 'Waiting', verify the Broadcast Data settings."
        ),
        "nl": (
            "N1MM Logger+ instellen\n\n"
            "Deze applicatie ontvangt contactgegevens van N1MM Logger+ via UDP-broadcasts.\n\n"
            "STAPPEN IN N1MM LOGGER+:\n"
            "1. Ga naar Config → Configure Ports, Mode Control, Audio, Other\n"
            "2. Klik op het tabblad 'Broadcast Data'\n"
            "3. Zoek de rij 'Contact' en vink 'Enable' aan\n"
            "4. Stel de bestemming in op: 127.0.0.1:12060\n"
            "5. Klik op OK\n\n"
            "BELANGRIJK:\n"
            "  • Gebruik contest: FDREG1\n"
            "  • Host (127.0.0.1) en poort (12060) moeten overeenkomen\n"
            "    met de instellingen in deze app (Extra → Instellingen).\n"
            "  • N1MM moet draaien op dezelfde pc als deze applicatie,\n"
            "    of op een bereikbaar netwerkadres.\n\n"
            "PROBLEEMOPLOSSING:\n"
            "  • Controleer of Windows Firewall poort 12060 niet blokkeert.\n"
            "  • Log een test-QSO in N1MM en kijk of de statusbalk bijwerkt.\n"
            "  • Als status 'Wachten' blijft, controleer dan de Broadcast Data-instellingen."
        ),
        "fr": (
            "Configuration de N1MM Logger+\n\n"
            "Cette application reçoit les données de contact de N1MM Logger+ via UDP.\n\n"
            "ÉTAPES DANS N1MM LOGGER+ :\n"
            "1. Allez dans Config → Configure Ports, Mode Control, Audio, Other\n"
            "2. Cliquez sur l'onglet 'Broadcast Data'\n"
            "3. Trouvez la ligne 'Contact' et cochez 'Enable'\n"
            "4. Définissez la destination : 127.0.0.1:12060\n"
            "5. Cliquez sur OK\n\n"
            "IMPORTANT :\n"
            "  • Utilisez le concours : FDREG1\n"
            "  • L'hôte (127.0.0.1) et le port (12060) doivent correspondre\n"
            "    aux paramètres de cette application (Outils → Paramètres)."
        ),
        "es": (
            "Configuración de N1MM Logger+\n\n"
            "Esta aplicación recibe datos de contacto de N1MM Logger+ vía UDP.\n\n"
            "PASOS EN N1MM LOGGER+:\n"
            "1. Vaya a Config → Configure Ports, Mode Control, Audio, Other\n"
            "2. Haga clic en la pestaña 'Broadcast Data'\n"
            "3. Encuentre la fila 'Contact' y marque 'Enable'\n"
            "4. Establezca el destino: 127.0.0.1:12060\n"
            "5. Haga clic en OK\n\n"
            "IMPORTANTE:\n"
            "  • Use el concurso: FDREG1\n"
            "  • El host (127.0.0.1) y el puerto (12060) deben coincidir\n"
            "    con la configuración de esta aplicación (Herramientas → Configuración)."
        ),
    },

    HelpTopic.CSV_IMPORT: {
        "en": (
            "Station CSV Import\n\n"
            "The CSV file determines which stations participate in the field day.\n"
            "N1MM contacts from stations NOT in this list are silently ignored.\n\n"
            "REQUIRED COLUMN:\n"
            "  callsign   – the amateur radio callsign\n\n"
            "OPTIONAL COLUMNS:\n"
            "  name       – operator name\n"
            "  club       – club abbreviation\n"
            "  remarks    – free-text notes (visible in matrix)\n\n"
            "EXAMPLE:\n"
            "  callsign,name,club,remarks\n"
            "  ON3VZ,Cornelis,WLD,\n"
            "  ON4ABC,,,\n\n"
            "COLUMN NAMES:\n"
            "  If your CSV uses different column headers (e.g. 'Roepnaam'\n"
            "  instead of 'callsign'), configure the mapping in\n"
            "  Tools → Settings → CSV Column Mapping.\n\n"
            "RE-IMPORT:\n"
            "  • Existing manual overrides are always preserved.\n"
            "  • Manually added stations are always kept.\n"
            "  • Stations absent from the new CSV are flagged — you will\n"
            "    be asked before they are removed.\n\n"
            "SUPPORTED DELIMITERS: comma, semicolon, tab, pipe."
        ),
        "nl": (
            "Station CSV-import\n\n"
            "Het CSV-bestand bepaalt welke stations deelnemen aan de velddag.\n"
            "N1MM-contacten van stations die NIET in deze lijst staan worden genegeerd.\n\n"
            "VERPLICHTE KOLOM:\n"
            "  callsign   – het radioamateurroepnaam\n\n"
            "OPTIONELE KOLOMMEN:\n"
            "  name       – naam van de operator\n"
            "  club       – clubafkorting\n"
            "  remarks    – vrije opmerkingen (zichtbaar in matrix)\n\n"
            "VOORBEELD:\n"
            "  callsign,name,club,remarks\n"
            "  ON3VZ,Cornelis,WLD,\n"
            "  ON4ABC,,,\n\n"
            "KOLOMNAMEN:\n"
            "  Als uw CSV andere kolomkoppen gebruikt (bv. 'Roepnaam'\n"
            "  in plaats van 'callsign'), stel de mapping in via\n"
            "  Extra → Instellingen → CSV-kolomtoewijzing.\n\n"
            "HERIMPORT:\n"
            "  • Bestaande manuele overrides worden altijd bewaard.\n"
            "  • Manueel toegevoegde stations worden altijd behouden.\n"
            "  • Stations die niet meer in de nieuwe CSV staan worden\n"
            "    gemarkeerd — u wordt gevraagd voor ze worden verwijderd."
        ),
        "fr": (
            "Importation CSV des stations\n\n"
            "Le fichier CSV détermine quelles stations participent à la journée terrain.\n"
            "Les contacts N1MM de stations absentes de cette liste sont ignorés.\n\n"
            "COLONNE OBLIGATOIRE :\n"
            "  callsign   – l'indicatif radioamateur\n\n"
            "COLONNES OPTIONNELLES :\n"
            "  name       – nom de l'opérateur\n"
            "  club       – abréviation du club\n"
            "  remarks    – notes libres (visibles dans la matrice)\n\n"
            "NOMS DE COLONNES :\n"
            "  Si votre CSV utilise des en-têtes différents, configurez\n"
            "  le mapping dans Outils → Paramètres → Mapping colonnes CSV."
        ),
        "es": (
            "Importación CSV de estaciones\n\n"
            "El archivo CSV determina qué estaciones participan en el Field Day.\n"
            "Los contactos N1MM de estaciones no incluidas en esta lista se ignoran.\n\n"
            "COLUMNA OBLIGATORIA:\n"
            "  callsign   – el indicativo de radioaficionado\n\n"
            "COLUMNAS OPCIONALES:\n"
            "  name       – nombre del operador\n"
            "  club       – abreviatura del club\n"
            "  remarks    – notas libres (visibles en la matriz)\n\n"
            "NOMBRES DE COLUMNAS:\n"
            "  Si su CSV usa encabezados diferentes, configure el mapeo\n"
            "  en Herramientas → Configuración → Mapeo de columnas CSV."
        ),
    },

    HelpTopic.CSV_COLUMN_MAPPING: {
        "en": (
            "CSV Column Mapping\n\n"
            "This setting lets you tell the application which column in your\n"
            "CSV file corresponds to each internal field.\n\n"
            "INTERNAL FIELD → CSV COLUMN NAME\n"
            "  callsign  → the column containing the amateur callsign\n"
            "  name      → the column containing the operator's name\n"
            "  club      → the column containing the club name\n"
            "  remarks   → the column containing free-text notes\n\n"
            "EXAMPLES:\n"
            "  Dutch CSV:   Roepnaam, Naam, Club, Opmerkingen\n"
            "  French CSV:  Indicatif, Nom, Club, Remarques\n"
            "  Custom CSV:  Call, Operator, Org, Notes\n\n"
            "Only the callsign mapping is required.\n"
            "Leave other mappings blank to ignore that column.\n\n"
            "TIP: Click 'Detect Columns' to preview the headers\n"
            "found in your CSV file before mapping them."
        ),
        "nl": (
            "CSV-kolomtoewijzing\n\n"
            "Met deze instelling geeft u aan welke kolom in uw CSV-bestand\n"
            "overeenkomt met elk intern veld.\n\n"
            "INTERN VELD → CSV-KOLOMNAAM\n"
            "  callsign  → de kolom met het roepnaam\n"
            "  name      → de kolom met de naam van de operator\n"
            "  club      → de kolom met de clubnaam\n"
            "  remarks   → de kolom met vrije notities\n\n"
            "VOORBEELDEN:\n"
            "  Nederlandstalige CSV: Roepnaam, Naam, Club, Opmerkingen\n"
            "  Eigen CSV: Call, Operator, Org, Notities\n\n"
            "Alleen de callsign-toewijzing is verplicht.\n"
            "Laat andere toewijzingen leeg om die kolom te negeren."
        ),
        "fr": (
            "Mappage des colonnes CSV\n\n"
            "Ce paramètre vous permet d'indiquer quelle colonne de votre\n"
            "fichier CSV correspond à chaque champ interne.\n\n"
            "CHAMP INTERNE → NOM DE COLONNE CSV\n"
            "  callsign  → colonne contenant l'indicatif\n"
            "  name      → colonne contenant le nom de l'opérateur\n"
            "  club      → colonne contenant le club\n"
            "  remarks   → colonne contenant les notes libres\n\n"
            "Seul le mappage de l'indicatif est obligatoire."
        ),
        "es": (
            "Mapeo de columnas CSV\n\n"
            "Esta configuración le permite indicar qué columna de su\n"
            "archivo CSV corresponde a cada campo interno.\n\n"
            "CAMPO INTERNO → NOMBRE DE COLUMNA CSV\n"
            "  callsign  → columna que contiene el indicativo\n"
            "  name      → columna con el nombre del operador\n"
            "  club      → columna con el club\n"
            "  remarks   → columna con notas libres\n\n"
            "Solo el mapeo del indicativo es obligatorio."
        ),
    },

    HelpTopic.FIELD_DAY_SETTINGS: {
        "en": (
            "Field Day Settings\n\n"
            "NAME: Unique identifier for this field day. Used as folder name.\n"
            "  Allowed characters: letters, digits, underscore, hyphen.\n\n"
            "LOCATION: Free-text location description.\n\n"
            "EVENT CALLSIGN: The callsign used on air during this event.\n\n"
            "ORGANIZER / CLUB: Name of the organizing club or person.\n\n"
            "START / END (UTC): The field day period in UTC.\n"
            "  Only QSOs logged between start and end will count.\n"
            "  End must be after start. The period can span multiple days.\n\n"
            "DISPLAY TIMEZONE: How times are shown in the UI (e.g. Europe/Brussels).\n"
            "  All internal storage and matching remains in UTC.\n\n"
            "SELECTED BANDS: Check the bands active for this field day.\n"
            "  Default: 160m, 80m, 40m.\n\n"
            "N1MM HOST/PORT: Override the global UDP settings for this field day.\n"
            "  Leave at 0 / empty to use the global settings."
        ),
        "nl": (
            "Velddaginstellingen\n\n"
            "NAAM: Unieke identifier voor deze velddag. Wordt gebruikt als mapnaam.\n"
            "  Toegestane tekens: letters, cijfers, underscore, koppelteken.\n\n"
            "LOCATIE: Vrije beschrijving van de locatie.\n\n"
            "EVENEMENT-CALLSIGN: Het callsign dat tijdens dit evenement op de lucht is.\n\n"
            "ORGANISATOR / CLUB: Naam van de organiserende club of persoon.\n\n"
            "START / EINDE (UTC): De velddagperiode in UTC.\n"
            "  Alleen QSO's tussen start en einde tellen mee.\n"
            "  Einde moet na start liggen. De periode kan meerdere dagen beslaan.\n\n"
            "WEERGAVETIJDZONE: Hoe tijden worden getoond in de UI (bv. Europe/Brussels).\n"
            "  Interne opslag en vergelijking blijft altijd in UTC.\n\n"
            "GESELECTEERDE BANDEN: Vink de banden aan die actief zijn voor deze velddag.\n"
            "  Standaard: 160m, 80m, 40m."
        ),
        "fr": (
            "Paramètres de la journée terrain\n\n"
            "NOM : Identifiant unique. Utilisé comme nom de dossier.\n"
            "  Caractères autorisés : lettres, chiffres, tiret, underscore.\n\n"
            "LIEU : Description libre de l'emplacement.\n\n"
            "INDICATIF DE L'ÉVÉNEMENT : L'indicatif utilisé sur l'air.\n\n"
            "DÉBUT / FIN (UTC) : La période de la journée terrain en UTC.\n"
            "  Seuls les QSOs entre le début et la fin sont comptabilisés.\n"
            "  La fin doit être après le début. La période peut s'étendre sur plusieurs jours.\n\n"
            "BANDES SÉLECTIONNÉES : Cochez les bandes actives pour cette journée."
        ),
        "es": (
            "Configuración del Field Day\n\n"
            "NOMBRE: Identificador único. Se usa como nombre de carpeta.\n"
            "  Caracteres permitidos: letras, dígitos, guion, guion bajo.\n\n"
            "UBICACIÓN: Descripción libre de la ubicación.\n\n"
            "INDICATIVO DEL EVENTO: El indicativo usado en el aire.\n\n"
            "INICIO / FIN (UTC): El período del Field Day en UTC.\n"
            "  Solo se cuentan los QSO entre inicio y fin.\n"
            "  El fin debe ser posterior al inicio. El período puede abarcar varios días.\n\n"
            "BANDAS SELECCIONADAS: Marque las bandas activas para este Field Day."
        ),
    },

    HelpTopic.CALLSIGN_MATCHING: {
        "en": (
            "Callsign Matching\n\n"
            "The application matches N1MM contacts against the station list\n"
            "using the normalised callsign.\n\n"
            "STRICT MATCHING (OFF by default):\n"
            "  When OFF: common suffixes are stripped before matching.\n"
            "    ON3VZ, ON3VZ/P, ON3VZ/M, ON3VZ/QRP all match each other.\n"
            "  When ON: exact match only.\n"
            "    ON3VZ/P does NOT match ON3VZ.\n\n"
            "SUFFIXES STRIPPED (non-strict mode):\n"
            "  /P  (portable)    /M  (mobile)\n"
            "  /MM (maritime)    /AM (aeronautical)\n"
            "  /QRP              /0 … /9 (district)\n\n"
            "DXCC PREFIXES (e.g. F/ON3VZ) are never stripped.\n\n"
            "Both the original and normalised callsign are always stored.\n\n"
            "Configure in: Tools → Settings → Strict Callsign Matching."
        ),
        "nl": (
            "Callsign-matching\n\n"
            "De applicatie matcht N1MM-contacten met de stationslijst\n"
            "op basis van het genormaliseerde callsign.\n\n"
            "STRIKTE MATCHING (standaard UIT):\n"
            "  UIT: gangbare suffixen worden verwijderd voor matching.\n"
            "    ON3VZ, ON3VZ/P, ON3VZ/M, ON3VZ/QRP matchen allemaal.\n"
            "  AAN: alleen exacte match.\n"
            "    ON3VZ/P matcht NIET met ON3VZ.\n\n"
            "VERWIJDERDE SUFFIXEN (niet-strikt):\n"
            "  /P (draagbaar)  /M (mobiel)\n"
            "  /MM (maritiem)  /AM (luchtvaart)\n"
            "  /QRP            /0 … /9 (district)\n\n"
            "DXCC-prefixen (bv. F/ON3VZ) worden nooit verwijderd."
        ),
        "fr": (
            "Correspondance des indicatifs\n\n"
            "L'application fait correspondre les contacts N1MM avec la liste de stations\n"
            "en utilisant l'indicatif normalisé.\n\n"
            "CORRESPONDANCE STRICTE (désactivée par défaut) :\n"
            "  Désactivée : les suffixes courants sont supprimés avant la comparaison.\n"
            "    ON3VZ, ON3VZ/P, ON3VZ/M, ON3VZ/QRP correspondent tous.\n"
            "  Activée : correspondance exacte uniquement.\n\n"
            "SUFFIXES SUPPRIMÉS : /P, /M, /MM, /AM, /QRP, /0–/9"
        ),
        "es": (
            "Coincidencia de indicativos\n\n"
            "La aplicación hace coincidir los contactos N1MM con la lista de estaciones\n"
            "usando el indicativo normalizado.\n\n"
            "COINCIDENCIA ESTRICTA (desactivada por defecto):\n"
            "  Desactivada: se eliminan sufijos comunes antes de comparar.\n"
            "    ON3VZ, ON3VZ/P, ON3VZ/M, ON3VZ/QRP coinciden entre sí.\n"
            "  Activada: solo coincidencia exacta.\n\n"
            "SUFIJOS ELIMINADOS: /P, /M, /MM, /AM, /QRP, /0–/9"
        ),
    },

    HelpTopic.MANUAL_OVERRIDE: {
        "en": (
            "Manual Overrides\n\n"
            "A manual override lets you set the status of a specific\n"
            "station + band combination, regardless of what N1MM logged.\n\n"
            "OVERRIDE TYPES:\n"
            "  Mark as Worked    – forces 'worked' status (dark green)\n"
            "  Mark as Not Worked– forces 'not worked' status (yellow)\n"
            "  Exclude           – removes from statistics (grey)\n"
            "  Clear Override    – returns to automatic N1MM status\n\n"
            "HOW TO SET:\n"
            "  Right-click any cell in the matrix → choose override type.\n\n"
            "PRIORITY:\n"
            "  Manual overrides ALWAYS take priority over N1MM data.\n"
            "  Even if N1MM logs the same contact again, the override\n"
            "  stays in effect until you explicitly clear it.\n\n"
            "SCOPE:\n"
            "  Overrides apply per callsign + band.\n"
            "  e.g. ON3VZ on 40m can be overridden independently\n"
            "  from ON3VZ on 80m."
        ),
        "nl": (
            "Manuele overrides\n\n"
            "Een manuele override laat u de status instellen van een specifieke\n"
            "station + band combinatie, ongeacht wat N1MM heeft gelogd.\n\n"
            "OVERRIDE-TYPES:\n"
            "  Markeren als gewerkt     – forceert 'gewerkt' (donkergroen)\n"
            "  Markeren als niet gewerkt– forceert 'niet gewerkt' (geel)\n"
            "  Uitsluiten               – verwijderd uit statistieken (grijs)\n"
            "  Override wissen          – keert terug naar automatische N1MM-status\n\n"
            "HOE INSTELLEN:\n"
            "  Rechtsklik op een cel in de matrix → kies het override-type.\n\n"
            "PRIORITEIT:\n"
            "  Manuele overrides hebben ALTIJD voorrang op N1MM-data.\n\n"
            "BEREIK:\n"
            "  Overrides gelden per callsign + band.\n"
            "  bv. ON3VZ op 40m kan onafhankelijk worden ingesteld van ON3VZ op 80m."
        ),
        "fr": (
            "Substitutions manuelles\n\n"
            "Une substitution manuelle vous permet de définir le statut d'une\n"
            "combinaison station + bande, indépendamment de ce que N1MM a enregistré.\n\n"
            "TYPES DE SUBSTITUTION :\n"
            "  Marquer comme travaillé     → statut 'travaillé' (vert foncé)\n"
            "  Marquer comme non travaillé → statut 'non travaillé' (jaune)\n"
            "  Exclure                     → exclu des statistiques (gris)\n"
            "  Effacer la substitution     → retour au statut automatique N1MM\n\n"
            "PRIORITÉ :\n"
            "  Les substitutions manuelles ont TOUJOURS la priorité sur N1MM."
        ),
        "es": (
            "Sustituciones manuales\n\n"
            "Una sustitución manual le permite establecer el estado de una\n"
            "combinación estación + banda, independientemente de lo que N1MM registró.\n\n"
            "TIPOS DE SUSTITUCIÓN:\n"
            "  Marcar como trabajado     → estado 'trabajado' (verde oscuro)\n"
            "  Marcar como no trabajado  → estado 'no trabajado' (amarillo)\n"
            "  Excluir                   → excluido de estadísticas (gris)\n"
            "  Borrar sustitución        → vuelve al estado automático N1MM\n\n"
            "PRIORIDAD:\n"
            "  Las sustituciones manuales SIEMPRE tienen prioridad sobre N1MM."
        ),
    },

    HelpTopic.SETTINGS: {
        "en": (
            "Settings\n\n"
            "UI LANGUAGE: Switch between English, Dutch, French, Spanish.\n\n"
            "N1MM UDP HOST: IP address this app listens on.\n"
            "  Use 127.0.0.1 for N1MM on the same PC.\n\n"
            "N1MM UDP PORT: Port number (default 12060).\n"
            "  Must match N1MM's Broadcast Data destination.\n\n"
            "FRESHNESS THRESHOLD: Seconds before connection shown as stale.\n"
            "  If no N1MM message arrives within this time, status turns grey.\n\n"
            "STRICT CALLSIGN MATCHING: See Callsign Matching help.\n\n"
            "STATUS COLOURS: Customise the colour of each status in the matrix.\n\n"
            "CSV COLUMN MAPPING: Map your CSV headers to internal field names.\n\n"
            "EXPORT FOLDER: Default folder for CSV and PDF exports.\n\n"
            "Settings are saved immediately and survive application restarts."
        ),
        "nl": (
            "Instellingen\n\n"
            "UI-TAAL: Wissel tussen Engels, Nederlands, Frans, Spaans.\n\n"
            "N1MM UDP HOST: IP-adres waarop deze app luistert.\n"
            "  Gebruik 127.0.0.1 voor N1MM op dezelfde pc.\n\n"
            "N1MM UDP POORT: Poortnummer (standaard 12060).\n"
            "  Moet overeenkomen met de Broadcast Data-bestemming in N1MM.\n\n"
            "VERSHEIDSDREMPEL: Seconden voor verbinding als verouderd wordt getoond.\n\n"
            "STRIKTE CALLSIGN-MATCHING: Zie help over callsign-matching.\n\n"
            "STATUSKLEUREN: Pas de kleur aan voor elke status in de matrix.\n\n"
            "CSV-KOLOMTOEWIJZING: Koppel uw CSV-kolomkoppen aan interne veldnamen.\n\n"
            "Instellingen worden onmiddellijk opgeslagen en blijven behouden na herstart."
        ),
        "fr": (
            "Paramètres\n\n"
            "LANGUE : Basculer entre anglais, néerlandais, français, espagnol.\n\n"
            "HÔTE UDP N1MM : Adresse IP d'écoute (127.0.0.1 pour même PC).\n\n"
            "PORT UDP N1MM : Numéro de port (défaut 12060).\n\n"
            "SEUIL DE FRAÎCHEUR : Secondes avant d'afficher la connexion comme périmée.\n\n"
            "COULEURS DES STATUTS : Personnalisez les couleurs de chaque statut.\n\n"
            "MAPPAGE CSV : Associez vos en-têtes CSV aux noms de champs internes."
        ),
        "es": (
            "Configuración\n\n"
            "IDIOMA: Cambiar entre inglés, neerlandés, francés, español.\n\n"
            "HOST UDP N1MM: Dirección IP de escucha (127.0.0.1 para el mismo PC).\n\n"
            "PUERTO UDP N1MM: Número de puerto (predeterminado 12060).\n\n"
            "UMBRAL DE FRESCURA: Segundos antes de mostrar la conexión como obsoleta.\n\n"
            "COLORES DE ESTADO: Personalice el color de cada estado en la matriz.\n\n"
            "MAPEO CSV: Asocie sus encabezados CSV con los nombres de campos internos."
        ),
    },

    HelpTopic.SYNC: {
        "en": (
            "Sync / Recalculate\n\n"
            "AUTOMATIC SYNC:\n"
            "  Every time N1MM sends a contact via UDP, the matrix updates\n"
            "  automatically in real time.\n\n"
            "MANUAL SYNC (Tools → Manual Sync / Recalculate):\n"
            "  Re-processes all stored QSOs from scratch.\n"
            "  Use this to:\n"
            "    • Correct the matrix after changing settings\n"
            "    • Recover after a crash or missed UDP packets\n"
            "    • Verify the matrix is consistent with stored data\n\n"
            "SYNC RULES (always applied):\n"
            "  1. Manual overrides always win over N1MM data.\n"
            "  2. QSOs outside the field day period are ignored.\n"
            "  3. Unknown callsigns (not in station list) are ignored.\n"
            "  4. Status is per callsign + band (not per QSO count).\n"
            "  5. All timestamps are compared in UTC."
        ),
        "nl": (
            "Sync / Herberekenen\n\n"
            "AUTOMATISCHE SYNC:\n"
            "  Elke keer dat N1MM een contact stuurt via UDP, wordt de matrix\n"
            "  automatisch in realtime bijgewerkt.\n\n"
            "HANDMATIGE SYNC (Extra → Handmatige sync / Herberekening):\n"
            "  Verwerkt alle opgeslagen QSO's opnieuw van het begin.\n"
            "  Gebruik dit om:\n"
            "    • De matrix te corrigeren na het wijzigen van instellingen\n"
            "    • Te herstellen na een crash of gemiste UDP-pakketten\n"
            "    • Te verifiëren dat de matrix consistent is met opgeslagen data\n\n"
            "SYNCREGELS (altijd van toepassing):\n"
            "  1. Manuele overrides winnen altijd van N1MM-data.\n"
            "  2. QSO's buiten de velddagperiode worden genegeerd.\n"
            "  3. Onbekende callsigns worden genegeerd.\n"
            "  4. Status is per callsign + band (niet per QSO-aantal).\n"
            "  5. Alle timestamps worden vergeleken in UTC."
        ),
        "fr": (
            "Synchronisation / Recalcul\n\n"
            "SYNC AUTOMATIQUE :\n"
            "  La matrice se met à jour automatiquement à chaque contact N1MM.\n\n"
            "SYNC MANUELLE (Outils → Synchronisation manuelle) :\n"
            "  Retraite tous les QSOs stockés depuis le début.\n\n"
            "RÈGLES DE SYNC :\n"
            "  1. Les substitutions manuelles ont toujours la priorité.\n"
            "  2. Les QSOs hors période sont ignorés.\n"
            "  3. Les indicatifs inconnus sont ignorés.\n"
            "  4. Le statut est par indicatif + bande.\n"
            "  5. Tous les horodatages sont comparés en UTC."
        ),
        "es": (
            "Sincronización / Recalcular\n\n"
            "SINCRONIZACIÓN AUTOMÁTICA:\n"
            "  La matriz se actualiza automáticamente con cada contacto N1MM.\n\n"
            "SINCRONIZACIÓN MANUAL (Herramientas → Sincronización manual):\n"
            "  Reprocesa todos los QSO almacenados desde el principio.\n\n"
            "REGLAS DE SINCRONIZACIÓN:\n"
            "  1. Las sustituciones manuales siempre tienen prioridad.\n"
            "  2. Los QSO fuera del período se ignoran.\n"
            "  3. Los indicativos desconocidos se ignoran.\n"
            "  4. El estado es por indicativo + banda.\n"
            "  5. Todas las marcas de tiempo se comparan en UTC."
        ),
    },

    HelpTopic.CSV_EXPORT: {
        "en": (
            "CSV Export\n\n"
            "Exports the full station × band status to a CSV file.\n\n"
            "COLUMNS EXPORTED:\n"
            "  callsign, normalized_callsign, band, status, source,\n"
            "  mode, frequency, worked_timestamp_utc,\n"
            "  manual_override, remarks\n\n"
            "The CSV can be opened in Excel or any spreadsheet application.\n\n"
            "Export folder: configured in Tools → Settings → Export Folder."
        ),
        "nl": (
            "CSV-export\n\n"
            "Exporteert de volledige station × band status naar een CSV-bestand.\n\n"
            "GEËXPORTEERDE KOLOMMEN:\n"
            "  callsign, normalized_callsign, band, status, source,\n"
            "  mode, frequency, worked_timestamp_utc,\n"
            "  manual_override, remarks\n\n"
            "De CSV kan worden geopend in Excel of een ander spreadsheetprogramma.\n\n"
            "Exportmap: instelbaar via Extra → Instellingen → Exportmap."
        ),
        "fr": (
            "Export CSV\n\n"
            "Exporte le statut complet station × bande vers un fichier CSV.\n\n"
            "COLONNES EXPORTÉES :\n"
            "  callsign, normalized_callsign, band, status, source,\n"
            "  mode, frequency, worked_timestamp_utc, manual_override, remarks"
        ),
        "es": (
            "Exportación CSV\n\n"
            "Exporta el estado completo estación × banda a un archivo CSV.\n\n"
            "COLUMNAS EXPORTADAS:\n"
            "  callsign, normalized_callsign, band, status, source,\n"
            "  mode, frequency, worked_timestamp_utc, manual_override, remarks"
        ),
    },

    HelpTopic.PDF_EXPORT: {
        "en": (
            "PDF Report Export\n\n"
            "Generates a professional PDF report of the field day.\n\n"
            "REPORT CONTENTS:\n"
            "  • Title and field day details (name, location, callsign, period)\n"
            "  • Summary statistics:\n"
            "      Total stations, bands, combinations\n"
            "      Worked / unworked / excluded counts\n"
            "      Fully / partially / not worked stations\n"
            "  • Legend (colour key)\n"
            "  • Full station × band matrix\n\n"
            "Export folder: configured in Tools → Settings → Export Folder."
        ),
        "nl": (
            "PDF-rapportexport\n\n"
            "Genereert een professioneel PDF-rapport van de velddag.\n\n"
            "RAPPORTINHOUD:\n"
            "  • Titel en velddaggegevens (naam, locatie, callsign, periode)\n"
            "  • Samenvattende statistieken:\n"
            "      Totaal stations, banden, combinaties\n"
            "      Gewerkt / niet gewerkt / uitgesloten\n"
            "      Volledig / gedeeltelijk / niet gewerkte stations\n"
            "  • Legenda (kleurcode)\n"
            "  • Volledige station × band matrix"
        ),
        "fr": (
            "Export rapport PDF\n\n"
            "Génère un rapport PDF professionnel de la journée terrain.\n\n"
            "CONTENU DU RAPPORT :\n"
            "  • Titre et détails de la journée terrain\n"
            "  • Statistiques récapitulatives\n"
            "  • Légende (code couleur)\n"
            "  • Matrice complète station × bande"
        ),
        "es": (
            "Exportación de informe PDF\n\n"
            "Genera un informe PDF profesional del Field Day.\n\n"
            "CONTENIDO DEL INFORME:\n"
            "  • Título y detalles del Field Day\n"
            "  • Estadísticas resumidas\n"
            "  • Leyenda (código de colores)\n"
            "  • Matriz completa estación × banda"
        ),
    },

    HelpTopic.CONNECTION_STATUS: {
        "en": (
            "Connection Status\n\n"
            "The status bar shows whether N1MM Logger+ is sending data.\n\n"
            "  Waiting…    – No data received yet since app started.\n"
            "  Connected   – Data received within the freshness threshold.\n"
            "  No recent data – Last packet older than the freshness threshold.\n"
            "  Error       – UDP socket could not be opened.\n\n"
            "The timestamp shows when the last N1MM contact was received.\n\n"
            "Freshness threshold: set in Tools → Settings."
        ),
        "nl": (
            "Verbindingsstatus\n\n"
            "De statusbalk toont of N1MM Logger+ data verstuurt.\n\n"
            "  Wachten…       – Nog geen data ontvangen.\n"
            "  Verbonden      – Data ontvangen binnen de versheidsdrempel.\n"
            "  Geen recente data – Laatste pakket ouder dan de versheidsdrempel.\n"
            "  Fout           – UDP-socket kon niet worden geopend.\n\n"
            "Versheidsdrempel: instelbaar via Extra → Instellingen."
        ),
        "fr": (
            "Statut de connexion\n\n"
            "La barre d'état indique si N1MM Logger+ envoie des données.\n\n"
            "  En attente…       – Aucune donnée reçue.\n"
            "  Connecté          – Données reçues dans le seuil de fraîcheur.\n"
            "  Aucune donnée récente – Dernier paquet trop ancien.\n"
            "  Erreur            – Socket UDP non disponible."
        ),
        "es": (
            "Estado de conexión\n\n"
            "La barra de estado muestra si N1MM Logger+ está enviando datos.\n\n"
            "  Esperando…       – Ningún dato recibido aún.\n"
            "  Conectado        – Datos recibidos dentro del umbral de frescura.\n"
            "  Sin datos recientes – Último paquete demasiado antiguo.\n"
            "  Error            – Socket UDP no disponible."
        ),
    },

    HelpTopic.FIELD_DAY_PERIOD: {
        "en": (
            "Field Day Period\n\n"
            "The start and end times define the scoring window.\n\n"
            "  • Only QSOs logged between start and end (inclusive) count.\n"
            "  • Times are entered and stored in UTC.\n"
            "  • The period can span multiple calendar days.\n"
            "  • End must be strictly after start.\n\n"
            "The display timezone (e.g. Europe/Brussels) only affects how\n"
            "times are shown in the UI — all matching is done in UTC."
        ),
        "nl": (
            "Velddagperiode\n\n"
            "Start- en eindtijden bepalen het scoringsvenster.\n\n"
            "  • Alleen QSO's gelogd tussen start en einde (inclusief) tellen mee.\n"
            "  • Tijden worden ingevoerd en opgeslagen in UTC.\n"
            "  • De periode kan meerdere kalenderdagen beslaan.\n"
            "  • Einde moet strikt na start liggen.\n\n"
            "De weergavetijdzone beïnvloedt alleen de weergave — matching gebeurt in UTC."
        ),
        "fr": (
            "Période de la journée terrain\n\n"
            "Les heures de début et de fin définissent la fenêtre de pointage.\n\n"
            "  • Seuls les QSOs enregistrés entre le début et la fin comptent.\n"
            "  • Les heures sont stockées en UTC.\n"
            "  • La période peut s'étendre sur plusieurs jours calendaires.\n"
            "  • La fin doit être strictement après le début."
        ),
        "es": (
            "Período del Field Day\n\n"
            "Las horas de inicio y fin definen la ventana de puntuación.\n\n"
            "  • Solo cuentan los QSO registrados entre inicio y fin (inclusive).\n"
            "  • Las horas se almacenan en UTC.\n"
            "  • El período puede abarcar varios días calendario.\n"
            "  • El fin debe ser estrictamente posterior al inicio."
        ),
    },

    HelpTopic.FIELD_DAY_BANDS: {
        "en": (
            "Band Selection\n\n"
            "Select which bands are active for this field day.\n\n"
            "  • Only selected bands appear as columns in the matrix.\n"
            "  • N1MM QSOs on non-selected bands are stored but not shown.\n"
            "  • Default selection: 160m, 80m, 40m.\n\n"
            "AVAILABLE BANDS:\n"
            "  160m, 80m, 40m, 30m, 20m, 15m, 12m, 10m, 6m, 2m, 70cm\n\n"
            "You can change the band selection after the field day has started.\n"
            "Run Manual Sync afterwards to recalculate the matrix."
        ),
        "nl": (
            "Bandselectie\n\n"
            "Selecteer welke banden actief zijn voor deze velddag.\n\n"
            "  • Alleen geselecteerde banden verschijnen als kolommen in de matrix.\n"
            "  • N1MM QSO's op niet-geselecteerde banden worden opgeslagen maar niet getoond.\n"
            "  • Standaardselectie: 160m, 80m, 40m.\n\n"
            "BESCHIKBARE BANDEN:\n"
            "  160m, 80m, 40m, 30m, 20m, 15m, 12m, 10m, 6m, 2m, 70cm"
        ),
        "fr": (
            "Sélection des bandes\n\n"
            "Sélectionnez les bandes actives pour cette journée terrain.\n\n"
            "  • Seules les bandes sélectionnées apparaissent dans la matrice.\n"
            "  • Les QSOs N1MM sur d'autres bandes sont stockés mais non affichés.\n"
            "  • Sélection par défaut : 160m, 80m, 40m.\n\n"
            "BANDES DISPONIBLES : 160m, 80m, 40m, 30m, 20m, 15m, 12m, 10m, 6m, 2m, 70cm"
        ),
        "es": (
            "Selección de bandas\n\n"
            "Seleccione qué bandas están activas para este Field Day.\n\n"
            "  • Solo las bandas seleccionadas aparecen como columnas en la matriz.\n"
            "  • Los QSO de N1MM en otras bandas se almacenan pero no se muestran.\n"
            "  • Selección predeterminada: 160m, 80m, 40m.\n\n"
            "BANDAS DISPONIBLES: 160m, 80m, 40m, 30m, 20m, 15m, 12m, 10m, 6m, 2m, 70cm"
        ),
    },

    HelpTopic.MANUAL_STATION: {
        "en": (
            "Add Station Manually\n\n"
            "You can add a station to the participant list without importing a CSV.\n\n"
            "  • Enter the callsign and optional name, club, remarks.\n"
            "  • Manually added stations are marked with source='manual'.\n"
            "  • They are NEVER removed automatically during a CSV re-import.\n"
            "  • They can be removed explicitly via the station list editor.\n\n"
            "Use this for:\n"
            "  • Last-minute additions not yet in the CSV\n"
            "  • Special stations (club call, guest operator)\n"
            "  • Correcting a missing callsign without re-importing"
        ),
        "nl": (
            "Station manueel toevoegen\n\n"
            "U kunt een station toevoegen aan de deelnemerslijst zonder CSV-import.\n\n"
            "  • Voer het callsign in en optioneel naam, club, opmerkingen.\n"
            "  • Manueel toegevoegde stations worden gemarkeerd als source='manual'.\n"
            "  • Ze worden NOOIT automatisch verwijderd bij een CSV-herimport.\n"
            "  • Ze kunnen expliciet worden verwijderd via de stationslijsteditor."
        ),
        "fr": (
            "Ajouter une station manuellement\n\n"
            "Vous pouvez ajouter une station sans importer un CSV.\n\n"
            "  • Entrez l'indicatif et optionnellement nom, club, remarques.\n"
            "  • Les stations ajoutées manuellement ont source='manual'.\n"
            "  • Elles ne sont JAMAIS supprimées automatiquement lors d'un re-import CSV."
        ),
        "es": (
            "Agregar estación manualmente\n\n"
            "Puede agregar una estación sin importar un CSV.\n\n"
            "  • Ingrese el indicativo y opcionalmente nombre, club, observaciones.\n"
            "  • Las estaciones agregadas manualmente tienen source='manual'.\n"
            "  • NUNCA se eliminan automáticamente durante una reimportación CSV."
        ),
    },

    HelpTopic.N1MM_UDP: {
        "en": (
            "N1MM UDP Settings\n\n"
            "UDP HOST (default: 127.0.0.1)\n"
            "  The IP address this application listens on.\n"
            "  Use 127.0.0.1 when N1MM runs on the same PC.\n"
            "  Use 0.0.0.0 to listen on all network interfaces.\n\n"
            "UDP PORT (default: 12060)\n"
            "  Must match the destination port configured in\n"
            "  N1MM → Config → Broadcast Data → Contact destination.\n\n"
            "FRESHNESS THRESHOLD (default: 30 seconds)\n"
            "  If no N1MM packet arrives within this time, the status\n"
            "  changes from 'Connected' to 'No recent data'.\n\n"
            "CONNECTION STATUSES:\n"
            "  Waiting        – Listening, no data received yet\n"
            "  Connected      – Data received within threshold\n"
            "  No recent data – No data for longer than threshold\n"
            "  Error          – UDP socket could not be opened\n\n"
            "Changes take effect after restarting the listener\n"
            "(use Tools → Settings → Save to restart automatically)."
        ),
        "nl": (
            "N1MM UDP-instellingen\n\n"
            "UDP HOST (standaard: 127.0.0.1)\n"
            "  Het IP-adres waarop deze applicatie luistert.\n"
            "  Gebruik 127.0.0.1 als N1MM op dezelfde pc draait.\n"
            "  Gebruik 0.0.0.0 om op alle netwerkinterfaces te luisteren.\n\n"
            "UDP POORT (standaard: 12060)\n"
            "  Moet overeenkomen met de bestemmingspoort in\n"
            "  N1MM → Config → Broadcast Data → Contact-bestemming.\n\n"
            "VERSHEIDSDREMPEL (standaard: 30 seconden)\n"
            "  Als er geen N1MM-pakket binnenkomt binnen deze tijd,\n"
            "  verandert de status van 'Verbonden' naar 'Geen recente data'.\n\n"
            "VERBINDINGSSTATUSSEN:\n"
            "  Wachten        – Luistert, nog geen data ontvangen\n"
            "  Verbonden      – Data ontvangen binnen de drempel\n"
            "  Geen recente data – Geen data langer dan de drempel\n"
            "  Fout           – UDP-socket kon niet worden geopend"
        ),
        "fr": (
            "Paramètres UDP N1MM\n\n"
            "HÔTE UDP (défaut : 127.0.0.1)\n"
            "  Adresse IP d'écoute. Utilisez 127.0.0.1 si N1MM est sur le même PC.\n\n"
            "PORT UDP (défaut : 12060)\n"
            "  Doit correspondre au port de destination dans\n"
            "  N1MM → Config → Broadcast Data → destination Contact.\n\n"
            "SEUIL DE FRAÎCHEUR (défaut : 30 secondes)\n"
            "  Si aucun paquet N1MM n'arrive dans ce délai, le statut\n"
            "  passe de 'Connecté' à 'Aucune donnée récente'.\n\n"
            "STATUTS DE CONNEXION :\n"
            "  En attente       – Écoute, aucune donnée reçue\n"
            "  Connecté         – Données reçues dans le seuil\n"
            "  Aucune donnée récente – Pas de données depuis trop longtemps\n"
            "  Erreur           – Socket UDP non disponible"
        ),
        "es": (
            "Configuración UDP N1MM\n\n"
            "HOST UDP (predeterminado: 127.0.0.1)\n"
            "  IP de escucha. Use 127.0.0.1 si N1MM está en el mismo PC.\n\n"
            "PUERTO UDP (predeterminado: 12060)\n"
            "  Debe coincidir con el puerto de destino en\n"
            "  N1MM → Config → Broadcast Data → destino Contact.\n\n"
            "UMBRAL DE FRESCURA (predeterminado: 30 segundos)\n"
            "  Si no llega ningún paquete N1MM en este tiempo, el estado\n"
            "  cambia de 'Conectado' a 'Sin datos recientes'.\n\n"
            "ESTADOS DE CONEXIÓN:\n"
            "  Esperando        – Escuchando, sin datos recibidos\n"
            "  Conectado        – Datos recibidos dentro del umbral\n"
            "  Sin datos recientes – Sin datos por más tiempo que el umbral\n"
            "  Error            – Socket UDP no disponible"
        ),
    },

    HelpTopic.LANGUAGE_SETTING: {
        "en": (
            "Interface Language\n\n"
            "Switch the application language between:\n"
            "  • English (en)\n"
            "  • Nederlands / Dutch (nl)\n"
            "  • Français / French (fr)\n"
            "  • Español / Spanish (es)\n\n"
            "The language change takes effect immediately.\n"
            "Internal data (file names, JSON keys, log messages) always\n"
            "remain in English regardless of the UI language."
        ),
        "nl": (
            "Interfacetaal\n\n"
            "Wissel de applicatietaal tussen:\n"
            "  • English / Engels (en)\n"
            "  • Nederlands (nl)\n"
            "  • Français / Frans (fr)\n"
            "  • Español / Spaans (es)\n\n"
            "De taalwijziging is onmiddellijk van kracht.\n"
            "Interne data (bestandsnamen, JSON-sleutels) blijft altijd in het Engels."
        ),
        "fr": (
            "Langue de l'interface\n\n"
            "Basculez entre :\n"
            "  • English / Anglais (en)\n"
            "  • Nederlands / Néerlandais (nl)\n"
            "  • Français (fr)\n"
            "  • Español / Espagnol (es)\n\n"
            "Le changement de langue prend effet immédiatement."
        ),
        "es": (
            "Idioma de la interfaz\n\n"
            "Cambie entre:\n"
            "  • English / Inglés (en)\n"
            "  • Nederlands / Neerlandés (nl)\n"
            "  • Français / Francés (fr)\n"
            "  • Español (es)\n\n"
            "El cambio de idioma surte efecto inmediatamente."
        ),
    },

    HelpTopic.STATUS_COLORS: {
        "en": (
            "Status Colours\n\n"
            "Customise the background colour of each status in the matrix.\n\n"
            "STATUSES:\n"
            "  Not Worked          – default White\n"
            "  Worked (N1MM)       – default Green\n"
            "  Worked (Manual)     – default Dark Green\n"
            "  Not Worked (Manual) – default Yellow/Amber\n"
            "  Excluded            – default Grey\n\n"
            "Colours are specified as hex values (#RRGGBB).\n"
            "Click a colour swatch to open the colour picker.\n\n"
            "Changes take effect immediately in the matrix."
        ),
        "nl": (
            "Statuskleuren\n\n"
            "Pas de achtergrondkleur aan voor elke status in de matrix.\n\n"
            "STATUSSEN:\n"
            "  Niet gewerkt        – standaard Wit\n"
            "  Gewerkt (N1MM)      – standaard Groen\n"
            "  Gewerkt (Manueel)   – standaard Donkergroen\n"
            "  Niet gewerkt (Man.) – standaard Geel/Amber\n"
            "  Uitgesloten         – standaard Grijs\n\n"
            "Kleuren worden opgegeven als hexadecimale waarden (#RRGGBB).\n"
            "Klik op een kleurvlak om de kleurkiezer te openen."
        ),
        "fr": (
            "Couleurs des statuts\n\n"
            "Personnalisez la couleur de fond de chaque statut dans la matrice.\n\n"
            "STATUTS :\n"
            "  Non travaillé       – Blanc par défaut\n"
            "  Travaillé (N1MM)    – Vert par défaut\n"
            "  Travaillé (Manuel)  – Vert foncé par défaut\n"
            "  Non travaillé (Man.)– Jaune/Ambre par défaut\n"
            "  Exclu               – Gris par défaut"
        ),
        "es": (
            "Colores de estado\n\n"
            "Personalice el color de fondo de cada estado en la matriz.\n\n"
            "ESTADOS:\n"
            "  No trabajado        – Blanco por defecto\n"
            "  Trabajado (N1MM)    – Verde por defecto\n"
            "  Trabajado (Manual)  – Verde oscuro por defecto\n"
            "  No trabajado (Man.) – Amarillo por defecto\n"
            "  Excluido            – Gris por defecto"
        ),
    },
}


def get_help_text(topic: HelpTopic) -> str:
    """Return the help text for *topic* in the active UI language."""
    lang = get_language()
    entry = _HELP_TEXTS.get(topic.value, {})
    return entry.get(lang) or entry.get("en") or f"[No help available for: {topic.value}]"


def show_help(parent: object, topic: HelpTopic) -> None:
    """Show a modal help dialog for *topic*.

    Parameters
    ----------
    parent:
        Parent Tkinter widget (used to position the dialog).
    topic:
        The help topic to display.
    """
    text = get_help_text(topic)
    _HelpDialog(parent, topic, text)


def bind_f1(widget: object, topic: HelpTopic) -> None:
    """Bind the F1 key on *widget* to show help for *topic*."""
    widget.bind("<F1>", lambda _e: show_help(widget, topic))  # type: ignore[attr-defined]


def add_help_button(
    parent: object,
    topic: HelpTopic,
    **grid_kwargs,
) -> object:
    """Create and place a '?' help button that opens the help dialog.

    Parameters
    ----------
    parent:
        Container widget.
    topic:
        Help topic shown when the button is clicked.
    **grid_kwargs:
        Keyword arguments forwarded to ``button.grid()``.

    Returns
    -------
    tk.Button
        The created button (already placed via grid).
    """
    import tkinter as tk  # lazy import so module is testable without display
    btn = tk.Button(
        parent,  # type: ignore[arg-type]
        text="?",
        width=2,
        font=("Segoe UI", 9, "bold"),
        fg="#1e3a5f",
        relief=tk.FLAT,
        cursor="question_arrow",
        command=lambda: show_help(parent, topic),
    )
    btn.grid(**grid_kwargs)
    return btn


# ---------------------------------------------------------------------------
# Internal dialog
# ---------------------------------------------------------------------------

class _HelpDialog:
    """Simple scrollable help dialog."""

    def __init__(self, parent: object, topic: HelpTopic, text: str) -> None:
        import tkinter as tk
        from tkinter import scrolledtext

        self._win = tk.Toplevel(parent)  # type: ignore[arg-type]
        self._win.title(f"Help — {topic.value.replace('_', ' ').title()}")
        self._win.resizable(True, True)
        self._win.geometry("520x400")
        self._win.grab_set()  # modal

        txt = scrolledtext.ScrolledText(
            self._win,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=12,
            pady=8,
            relief=tk.FLAT,
            state=tk.NORMAL,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        txt.insert(tk.END, text)
        txt.config(state=tk.DISABLED)

        tk.Button(
            self._win,
            text=t("btn_close"),
            command=self._win.destroy,
            width=10,
        ).pack(pady=(0, 8))

        self._win.bind("<Escape>", lambda _: self._win.destroy())
        self._win.bind("<F1>", lambda _: self._win.destroy())

        self._win.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2  # type: ignore[attr-defined]
        py = parent.winfo_rooty() + (parent.winfo_height() - 400) // 2  # type: ignore[attr-defined]
        self._win.geometry(f"+{max(px, 0)}+{max(py, 0)}")
