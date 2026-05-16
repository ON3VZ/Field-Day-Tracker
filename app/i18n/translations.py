"""
app/i18n/translations.py
========================
Centralised UI string registry for N1MM Field Day Tracker.

All user-visible strings are defined here.  The rest of the code must
import and use the ``t()`` helper rather than hard-coding any label.

Supported languages
-------------------
- ``en``  English  (default)
- ``nl``  Dutch / Nederlands
- ``fr``  French / Français
- ``es``  Spanish / Español

Usage
-----
    from app.i18n.translations import t, set_language

    set_language("nl")
    print(t("app_title"))        # → "N1MM Velddag Tracker"
    print(t("btn_save"))         # → "Opslaan"

Adding a new string
-------------------
1. Add the key + English value to the ``_STRINGS`` dict.
2. Add translations for nl / fr / es in the same dict.
3. Never hard-code a UI label anywhere else.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Supported language codes
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "nl", "fr", "es")
DEFAULT_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# String registry
# Format:  "key": {"en": "...", "nl": "...", "fr": "...", "es": "..."}
# ---------------------------------------------------------------------------
_STRINGS: dict[str, dict[str, str]] = {

    # ── Application ─────────────────────────────────────────────────────
    "app_title": {
        "en": "N1MM Field Day Tracker",
        "nl": "N1MM Velddag Tracker",
        "fr": "N1MM Suivi Journée Terrain",
        "es": "N1MM Rastreador de Field Day",
    },
    "app_subtitle": {
        "en": "Station × Band tracking for Field Day events",
        "nl": "Station × Band overzicht voor velddagen",
        "fr": "Suivi Station × Bande pour les journées terrain",
        "es": "Seguimiento Estación × Banda para Field Day",
    },
    "no_active_fieldday": {
        "en": "No active field day. Create or open one to begin.",
        "nl": "Geen actieve velddag. Maak er een aan of open een bestaande.",
        "fr": "Aucune journée terrain active. Créez-en une ou ouvrez-en une.",
        "es": "No hay Field Day activo. Crea o abre uno para empezar.",
    },

    # ── Menu – File ──────────────────────────────────────────────────────
    "menu_file": {
        "en": "File",
        "nl": "Bestand",
        "fr": "Fichier",
        "es": "Archivo",
    },
    "menu_new_fieldday": {
        "en": "New Field Day…",
        "nl": "Nieuwe velddag…",
        "fr": "Nouvelle journée terrain…",
        "es": "Nuevo Field Day…",
    },
    "menu_open_fieldday": {
        "en": "Open Field Day…",
        "nl": "Velddag openen…",
        "fr": "Ouvrir une journée terrain…",
        "es": "Abrir Field Day…",
    },
    "menu_switch_fieldday": {
        "en": "Switch Field Day…",
        "nl": "Wissel velddag…",
        "fr": "Changer de journée terrain…",
        "es": "Cambiar Field Day…",
    },
    "menu_edit_fieldday": {
        "en": "Edit Field Day Settings…",
        "nl": "Velddaginstellingen bewerken…",
        "fr": "Modifier les paramètres de la journée terrain…",
        "es": "Editar configuración del Field Day…",
    },
    "menu_import_csv": {
        "en": "Import Station CSV…",
        "nl": "Station-CSV importeren…",
        "fr": "Importer CSV stations…",
        "es": "Importar CSV de estaciones…",
    },
    "menu_export_csv": {
        "en": "Export CSV…",
        "nl": "Exporteren als CSV…",
        "fr": "Exporter en CSV…",
        "es": "Exportar CSV…",
    },
    "menu_export_pdf": {
        "en": "Export PDF Report…",
        "nl": "PDF-rapport exporteren…",
        "fr": "Exporter rapport PDF…",
        "es": "Exportar informe PDF…",
    },
    "menu_quit": {
        "en": "Quit",
        "nl": "Afsluiten",
        "fr": "Quitter",
        "es": "Salir",
    },

    # ── Menu – View ──────────────────────────────────────────────────────
    "menu_view": {
        "en": "View",
        "nl": "Weergave",
        "fr": "Affichage",
        "es": "Ver",
    },
    "menu_refresh": {
        "en": "Refresh Matrix",
        "nl": "Matrix vernieuwen",
        "fr": "Actualiser la matrice",
        "es": "Actualizar matriz",
    },

    # ── Menu – Tools ─────────────────────────────────────────────────────
    "menu_tools": {
        "en": "Tools",
        "nl": "Extra",
        "fr": "Outils",
        "es": "Herramientas",
    },
    "menu_settings": {
        "en": "Settings…",
        "nl": "Instellingen…",
        "fr": "Paramètres…",
        "es": "Configuración…",
    },
    "menu_manual_sync": {
        "en": "Manual Sync / Recalculate",
        "nl": "Handmatige sync / herberekening",
        "fr": "Synchronisation manuelle / recalcul",
        "es": "Sincronización manual / recalcular",
    },
    "menu_add_station": {
        "en": "Add Station Manually…",
        "nl": "Station handmatig toevoegen…",
        "fr": "Ajouter une station manuellement…",
        "es": "Agregar estación manualmente…",
    },

    # ── Menu – Help ──────────────────────────────────────────────────────
    "menu_help": {
        "en": "Help",
        "nl": "Help",
        "fr": "Aide",
        "es": "Ayuda",
    },
    "menu_about": {
        "en": "About…",
        "nl": "Over…",
        "fr": "À propos…",
        "es": "Acerca de…",
    },

    # ── Buttons ──────────────────────────────────────────────────────────
    "btn_save": {
        "en": "Save",
        "nl": "Opslaan",
        "fr": "Enregistrer",
        "es": "Guardar",
    },
    "btn_cancel": {
        "en": "Cancel",
        "nl": "Annuleren",
        "fr": "Annuler",
        "es": "Cancelar",
    },
    "btn_ok": {
        "en": "OK",
        "nl": "OK",
        "fr": "OK",
        "es": "Aceptar",
    },
    "btn_close": {
        "en": "Close",
        "nl": "Sluiten",
        "fr": "Fermer",
        "es": "Cerrar",
    },
    "btn_import": {
        "en": "Import",
        "nl": "Importeren",
        "fr": "Importer",
        "es": "Importar",
    },
    "btn_export": {
        "en": "Export",
        "nl": "Exporteren",
        "fr": "Exporter",
        "es": "Exportar",
    },
    "btn_sync": {
        "en": "Sync / Recalculate",
        "nl": "Sync / Herberekenen",
        "fr": "Synchroniser / Recalculer",
        "es": "Sincronizar / Recalcular",
    },
    "btn_add": {
        "en": "Add",
        "nl": "Toevoegen",
        "fr": "Ajouter",
        "es": "Agregar",
    },
    "btn_remove": {
        "en": "Remove",
        "nl": "Verwijderen",
        "fr": "Supprimer",
        "es": "Eliminar",
    },
    "btn_browse": {
        "en": "Browse…",
        "nl": "Bladeren…",
        "fr": "Parcourir…",
        "es": "Examinar…",
    },

    # ── Status bar / Connection status ───────────────────────────────────
    "status_connected": {
        "en": "N1MM: Connected",
        "nl": "N1MM: Verbonden",
        "fr": "N1MM : Connecté",
        "es": "N1MM: Conectado",
    },
    "status_stale": {
        "en": "N1MM: No recent data",
        "nl": "N1MM: Geen recente data",
        "fr": "N1MM : Aucune donnée récente",
        "es": "N1MM: Sin datos recientes",
    },
    "status_waiting": {
        "en": "N1MM: Waiting…",
        "nl": "N1MM: Wachten…",
        "fr": "N1MM : En attente…",
        "es": "N1MM: Esperando…",
    },
    "status_error": {
        "en": "N1MM: Error",
        "nl": "N1MM: Fout",
        "fr": "N1MM : Erreur",
        "es": "N1MM: Error",
    },
    "last_received": {
        "en": "Last received:",
        "nl": "Laatste ontvangen:",
        "fr": "Dernier reçu :",
        "es": "Último recibido:",
    },
    "never": {
        "en": "Never",
        "nl": "Nooit",
        "fr": "Jamais",
        "es": "Nunca",
    },

    # ── Field Day form labels ────────────────────────────────────────────
    "lbl_fieldday_name": {
        "en": "Field Day Name",
        "nl": "Naam velddag",
        "fr": "Nom de la journée terrain",
        "es": "Nombre del Field Day",
    },
    "lbl_location": {
        "en": "Location",
        "nl": "Locatie",
        "fr": "Lieu",
        "es": "Ubicación",
    },
    "lbl_event_callsign": {
        "en": "Event Callsign",
        "nl": "Evenement-callsign",
        "fr": "Indicatif de l'événement",
        "es": "Indicativo del evento",
    },
    "lbl_organizer": {
        "en": "Organizer / Club",
        "nl": "Organisator / Club",
        "fr": "Organisateur / Club",
        "es": "Organizador / Club",
    },
    "lbl_start_utc": {
        "en": "Start (UTC)",
        "nl": "Start (UTC)",
        "fr": "Début (UTC)",
        "es": "Inicio (UTC)",
    },
    "lbl_end_utc": {
        "en": "End (UTC)",
        "nl": "Einde (UTC)",
        "fr": "Fin (UTC)",
        "es": "Fin (UTC)",
    },
    "lbl_display_timezone": {
        "en": "Display Timezone",
        "nl": "Weergavetijdzone",
        "fr": "Fuseau horaire d'affichage",
        "es": "Zona horaria de visualización",
    },
    "lbl_selected_bands": {
        "en": "Selected Bands",
        "nl": "Geselecteerde banden",
        "fr": "Bandes sélectionnées",
        "es": "Bandas seleccionadas",
    },
    "lbl_remarks": {
        "en": "Remarks",
        "nl": "Opmerkingen",
        "fr": "Remarques",
        "es": "Observaciones",
    },
    "lbl_operator_notes": {
        "en": "Operator Notes",
        "nl": "Operatornotities",
        "fr": "Notes opérateur",
        "es": "Notas del operador",
    },
    "lbl_n1mm_host": {
        "en": "N1MM UDP Host",
        "nl": "N1MM UDP Host",
        "fr": "Hôte UDP N1MM",
        "es": "Host UDP N1MM",
    },
    "lbl_n1mm_port": {
        "en": "N1MM UDP Port",
        "nl": "N1MM UDP Poort",
        "fr": "Port UDP N1MM",
        "es": "Puerto UDP N1MM",
    },
    "lbl_freshness_threshold": {
        "en": "Freshness Threshold (seconds)",
        "nl": "Versheidsdrempel (seconden)",
        "fr": "Seuil de fraîcheur (secondes)",
        "es": "Umbral de frescura (segundos)",
    },

    # ── Settings labels ──────────────────────────────────────────────────
    "lbl_ui_language": {
        "en": "Interface Language",
        "nl": "Interfacetaal",
        "fr": "Langue de l'interface",
        "es": "Idioma de la interfaz",
    },
    "lbl_strict_matching": {
        "en": "Strict Callsign Matching",
        "nl": "Strikte callsign-matching",
        "fr": "Correspondance stricte des indicatifs",
        "es": "Coincidencia estricta de indicativos",
    },
    "lbl_strict_matching_hint": {
        "en": "When OFF: ON3VZ/P matches ON3VZ. When ON: exact match only.",
        "nl": "UIT: ON3VZ/P matcht met ON3VZ. AAN: alleen exacte match.",
        "fr": "Désactivé : ON3VZ/P correspond à ON3VZ. Activé : correspondance exacte uniquement.",
        "es": "Desactivado: ON3VZ/P coincide con ON3VZ. Activado: solo coincidencia exacta.",
    },
    "lbl_export_folder": {
        "en": "Export Folder",
        "nl": "Exportmap",
        "fr": "Dossier d'export",
        "es": "Carpeta de exportación",
    },
    "lbl_status_colors": {
        "en": "Status Colours",
        "nl": "Statuskleuren",
        "fr": "Couleurs des statuts",
        "es": "Colores de estado",
    },

    # ── Matrix view labels ───────────────────────────────────────────────
    "col_station": {
        "en": "Station",
        "nl": "Station",
        "fr": "Station",
        "es": "Estación",
    },
    "col_name": {
        "en": "Name",
        "nl": "Naam",
        "fr": "Nom",
        "es": "Nombre",
    },
    "col_club": {
        "en": "Club",
        "nl": "Club",
        "fr": "Club",
        "es": "Club",
    },
    "col_remarks": {
        "en": "Remarks",
        "nl": "Opmerkingen",
        "fr": "Remarques",
        "es": "Observaciones",
    },
    "filter_all": {
        "en": "All",
        "nl": "Alle",
        "fr": "Tout",
        "es": "Todos",
    },
    "filter_worked": {
        "en": "Fully Worked",
        "nl": "Volledig gewerkt",
        "fr": "Entièrement travaillé",
        "es": "Completamente trabajados",
    },
    "filter_unworked": {
        "en": "Not Worked",
        "nl": "Niet gewerkt",
        "fr": "Non travaillé",
        "es": "No trabajados",
    },
    "filter_partial": {
        "en": "Partially Worked",
        "nl": "Gedeeltelijk gewerkt",
        "fr": "Partiellement travaillé",
        "es": "Parcialmente trabajados",
    },
    "lbl_search": {
        "en": "Search:",
        "nl": "Zoeken:",
        "fr": "Rechercher :",
        "es": "Buscar:",
    },
    "lbl_band_filter": {
        "en": "Band:",
        "nl": "Band:",
        "fr": "Bande :",
        "es": "Banda:",
    },

    # ── Override context menu ────────────────────────────────────────────
    "override_mark_worked": {
        "en": "Mark as Worked (manual)",
        "nl": "Markeren als gewerkt (manueel)",
        "fr": "Marquer comme travaillé (manuel)",
        "es": "Marcar como trabajado (manual)",
    },
    "override_mark_not_worked": {
        "en": "Mark as Not Worked (manual)",
        "nl": "Markeren als niet gewerkt (manueel)",
        "fr": "Marquer comme non travaillé (manuel)",
        "es": "Marcar como no trabajado (manual)",
    },
    "override_exclude": {
        "en": "Exclude from Statistics",
        "nl": "Uitsluiten van statistieken",
        "fr": "Exclure des statistiques",
        "es": "Excluir de estadísticas",
    },
    "override_clear": {
        "en": "Clear Override (use automatic status)",
        "nl": "Override wissen (automatische status gebruiken)",
        "fr": "Effacer la substitution (utiliser le statut automatique)",
        "es": "Borrar sustitución (usar estado automático)",
    },

    # ── Status display names ─────────────────────────────────────────────
    "status_not_worked": {
        "en": "Not Worked",
        "nl": "Niet gewerkt",
        "fr": "Non travaillé",
        "es": "No trabajado",
    },
    "status_worked_n1mm": {
        "en": "Worked (N1MM)",
        "nl": "Gewerkt (N1MM)",
        "fr": "Travaillé (N1MM)",
        "es": "Trabajado (N1MM)",
    },
    "status_manual_worked": {
        "en": "Worked (Manual)",
        "nl": "Gewerkt (manueel)",
        "fr": "Travaillé (manuel)",
        "es": "Trabajado (manual)",
    },
    "status_manual_not_worked": {
        "en": "Not Worked (Manual)",
        "nl": "Niet gewerkt (manueel)",
        "fr": "Non travaillé (manuel)",
        "es": "No trabajado (manual)",
    },
    "status_excluded": {
        "en": "Excluded",
        "nl": "Uitgesloten",
        "fr": "Exclu",
        "es": "Excluido",
    },

    # ── Dialogs / Messages ───────────────────────────────────────────────
    "dlg_new_fieldday_title": {
        "en": "New Field Day",
        "nl": "Nieuwe velddag",
        "fr": "Nouvelle journée terrain",
        "es": "Nuevo Field Day",
    },
    "dlg_edit_fieldday_title": {
        "en": "Edit Field Day Settings",
        "nl": "Velddaginstellingen bewerken",
        "fr": "Modifier la journée terrain",
        "es": "Editar Field Day",
    },
    "dlg_settings_title": {
        "en": "Settings",
        "nl": "Instellingen",
        "fr": "Paramètres",
        "es": "Configuración",
    },
    "dlg_about_title": {
        "en": "About N1MM Field Day Tracker",
        "nl": "Over N1MM Velddag Tracker",
        "fr": "À propos de N1MM Suivi Journée Terrain",
        "es": "Acerca de N1MM Rastreador de Field Day",
    },
    "dlg_about_text": {
        "en": (
            "N1MM Field Day Tracker\n\n"
            "Tracks which participating stations have been worked\n"
            "on which bands during a Field Day event.\n\n"
            "Integrates with N1MM Logger+ via UDP broadcasts.\n"
            "All data stored locally — no database, no server."
        ),
        "nl": (
            "N1MM Velddag Tracker\n\n"
            "Bijhouden welke deelnemende stations op welke banden\n"
            "gewerkt zijn tijdens een velddag.\n\n"
            "Integratie met N1MM Logger+ via UDP-broadcasts.\n"
            "Alle data lokaal opgeslagen — geen database, geen server."
        ),
        "fr": (
            "N1MM Suivi Journée Terrain\n\n"
            "Suivi des stations participantes travaillées\n"
            "sur chaque bande lors d'une journée terrain.\n\n"
            "Intégration avec N1MM Logger+ via UDP.\n"
            "Toutes les données stockées localement."
        ),
        "es": (
            "N1MM Rastreador de Field Day\n\n"
            "Seguimiento de las estaciones participantes trabajadas\n"
            "en cada banda durante un Field Day.\n\n"
            "Integración con N1MM Logger+ vía UDP.\n"
            "Todos los datos almacenados localmente."
        ),
    },
    "msg_fieldday_saved": {
        "en": "Field day settings saved.",
        "nl": "Velddaginstellingen opgeslagen.",
        "fr": "Paramètres de la journée terrain enregistrés.",
        "es": "Configuración del Field Day guardada.",
    },
    "msg_import_success": {
        "en": "Import successful: {count} stations loaded.",
        "nl": "Import geslaagd: {count} stations geladen.",
        "fr": "Import réussi : {count} stations chargées.",
        "es": "Importación exitosa: {count} estaciones cargadas.",
    },
    "msg_import_warning_missing": {
        "en": "Warning: {count} station(s) from the previous list are no longer in the new CSV. Remove them?",
        "nl": "Waarschuwing: {count} station(s) uit de vorige lijst staan niet meer in de nieuwe CSV. Verwijderen?",
        "fr": "Avertissement : {count} station(s) de la liste précédente ne sont plus dans le nouveau CSV. Supprimer ?",
        "es": "Advertencia: {count} estación(es) de la lista anterior ya no están en el nuevo CSV. ¿Eliminar?",
    },
    "msg_sync_complete": {
        "en": "Sync complete. {worked} worked, {unworked} unworked, {excluded} excluded.",
        "nl": "Sync voltooid. {worked} gewerkt, {unworked} niet gewerkt, {excluded} uitgesloten.",
        "fr": "Synchronisation terminée. {worked} travaillé(s), {unworked} non travaillé(s), {excluded} exclu(s).",
        "es": "Sincronización completa. {worked} trabajados, {unworked} no trabajados, {excluded} excluidos.",
    },
    "msg_end_before_start": {
        "en": "End time must be after start time.",
        "nl": "Eindtijd moet na de starttijd liggen.",
        "fr": "L'heure de fin doit être après l'heure de début.",
        "es": "La hora de fin debe ser posterior a la hora de inicio.",
    },
    "msg_name_required": {
        "en": "Field day name is required.",
        "nl": "Naam velddag is verplicht.",
        "fr": "Le nom de la journée terrain est obligatoire.",
        "es": "El nombre del Field Day es obligatorio.",
    },
    "msg_confirm_delete_stations": {
        "en": "Remove {count} station(s) that are no longer in the CSV?",
        "nl": "{count} station(s) verwijderen die niet meer in de CSV staan?",
        "fr": "Supprimer {count} station(s) absente(s) du nouveau CSV ?",
        "es": "¿Eliminar {count} estación(es) que ya no están en el CSV?",
    },

    # ── Statistics labels ────────────────────────────────────────────────
    "stat_total_stations": {
        "en": "Total Stations",
        "nl": "Totaal stations",
        "fr": "Total stations",
        "es": "Total estaciones",
    },
    "stat_total_bands": {
        "en": "Selected Bands",
        "nl": "Geselecteerde banden",
        "fr": "Bandes sélectionnées",
        "es": "Bandas seleccionadas",
    },
    "stat_total_combinations": {
        "en": "Total Combinations",
        "nl": "Totaal combinaties",
        "fr": "Combinaisons totales",
        "es": "Combinaciones totales",
    },
    "stat_worked": {
        "en": "Worked",
        "nl": "Gewerkt",
        "fr": "Travaillé(s)",
        "es": "Trabajados",
    },
    "stat_unworked": {
        "en": "Not Worked",
        "nl": "Niet gewerkt",
        "fr": "Non travaillé(s)",
        "es": "No trabajados",
    },
    "stat_manual_overrides": {
        "en": "Manual Overrides",
        "nl": "Manuele overrides",
        "fr": "Substitutions manuelles",
        "es": "Sustituciones manuales",
    },
    "stat_excluded": {
        "en": "Excluded",
        "nl": "Uitgesloten",
        "fr": "Exclus",
        "es": "Excluidos",
    },
    "stat_fully_worked": {
        "en": "Fully Worked Stations",
        "nl": "Volledig gewerkte stations",
        "fr": "Stations entièrement travaillées",
        "es": "Estaciones completamente trabajadas",
    },
    "stat_partially_worked": {
        "en": "Partially Worked Stations",
        "nl": "Gedeeltelijk gewerkte stations",
        "fr": "Stations partiellement travaillées",
        "es": "Estaciones parcialmente trabajadas",
    },
    "stat_not_worked_stations": {
        "en": "Not Worked Stations",
        "nl": "Niet gewerkte stations",
        "fr": "Stations non travaillées",
        "es": "Estaciones no trabajadas",
    },

    # ── Errors ───────────────────────────────────────────────────────────
    "err_invalid_csv": {
        "en": "Invalid CSV file. Ensure it has a 'callsign' column.",
        "nl": "Ongeldige CSV. Zorg voor een 'callsign'-kolom.",
        "fr": "Fichier CSV invalide. Assurez-vous qu'il contient une colonne 'callsign'.",
        "es": "Archivo CSV no válido. Asegúrese de que tenga una columna 'callsign'.",
    },
    "err_invalid_port": {
        "en": "UDP port must be a number between 1024 and 65535.",
        "nl": "UDP-poort moet een getal zijn tussen 1024 en 65535.",
        "fr": "Le port UDP doit être un nombre entre 1024 et 65535.",
        "es": "El puerto UDP debe ser un número entre 1024 y 65535.",
    },
    "err_file_not_found": {
        "en": "File not found: {path}",
        "nl": "Bestand niet gevonden: {path}",
        "fr": "Fichier introuvable : {path}",
        "es": "Archivo no encontrado: {path}",
    },
    "err_corrupt_data": {
        "en": "Data file is corrupt or unreadable: {path}",
        "nl": "Gegevensbestand is corrupt of onleesbaar: {path}",
        "fr": "Le fichier de données est corrompu ou illisible : {path}",
        "es": "El archivo de datos está corrupto o no es legible: {path}",
    },
    "err_udp_socket": {
        "en": "Could not open UDP socket on {host}:{port}. Check settings.",
        "nl": "Kon geen UDP-socket openen op {host}:{port}. Controleer de instellingen.",
        "fr": "Impossible d'ouvrir le socket UDP sur {host}:{port}. Vérifiez les paramètres.",
        "es": "No se pudo abrir el socket UDP en {host}:{port}. Compruebe la configuración.",
    },

    # ── Misc ─────────────────────────────────────────────────────────────
    "lbl_active_fieldday": {
        "en": "Active Field Day:",
        "nl": "Actieve velddag:",
        "fr": "Journée terrain active :",
        "es": "Field Day activo:",
    },
    "lbl_period": {
        "en": "Period:",
        "nl": "Periode:",
        "fr": "Période :",
        "es": "Período:",
    },
    "lbl_yes": {
        "en": "Yes",
        "nl": "Ja",
        "fr": "Oui",
        "es": "Sí",
    },
    "lbl_no": {
        "en": "No",
        "nl": "Nee",
        "fr": "Non",
        "es": "No",
    },
    "lbl_n1mm_setup_hint": {
        "en": (
            "In N1MM Logger+: Config → Configure Ports → Broadcast Data tab\n"
            "Enable 'Contact' and set destination to 127.0.0.1:12060\n"
            "Use contest: FDREG1"
        ),
        "nl": (
            "In N1MM Logger+: Config → Configure Ports → tabblad Broadcast Data\n"
            "Schakel 'Contact' in en stel bestemming in op 127.0.0.1:12060\n"
            "Gebruik contest: FDREG1"
        ),
        "fr": (
            "Dans N1MM Logger+ : Config → Configure Ports → onglet Broadcast Data\n"
            "Activez 'Contact' et définissez la destination sur 127.0.0.1:12060\n"
            "Utilisez le concours : FDREG1"
        ),
        "es": (
            "En N1MM Logger+: Config → Configure Ports → pestaña Broadcast Data\n"
            "Active 'Contact' y establezca el destino en 127.0.0.1:12060\n"
            "Utilice el concurso: FDREG1"
        ),
    },
}

# ---------------------------------------------------------------------------
# Module-level active language state
# ---------------------------------------------------------------------------
_active_language: str = DEFAULT_LANGUAGE


def set_language(language_code: str) -> None:
    """Set the active UI language.

    Parameters
    ----------
    language_code:
        Two-letter language code, one of ``SUPPORTED_LANGUAGES``.
        Silently falls back to ``DEFAULT_LANGUAGE`` if unknown.
    """
    global _active_language
    if language_code in SUPPORTED_LANGUAGES:
        _active_language = language_code
    else:
        _active_language = DEFAULT_LANGUAGE


def get_language() -> str:
    """Return the currently active language code."""
    return _active_language


def t(key: str, **kwargs: object) -> str:
    """Translate a UI string key to the active language.

    Falls back to English if the key is not translated for the active
    language.  Falls back to the raw key string if the key is entirely
    unknown (so missing keys surface visibly without crashing).

    Parameters
    ----------
    key:
        Translation key from ``_STRINGS``.
    **kwargs:
        Optional format arguments, e.g. ``t("msg_import_success", count=5)``.

    Returns
    -------
    str
        Translated and (optionally) formatted string.
    """
    entry = _STRINGS.get(key)
    if entry is None:
        # Unknown key — return the key itself so it is visible during dev
        return f"[{key}]"
    text = entry.get(_active_language) or entry.get(DEFAULT_LANGUAGE) or f"[{key}]"
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # Return unformatted rather than crash
    return text


def language_display_names() -> dict[str, str]:
    """Return human-readable names for each supported language."""
    return {
        "en": "English",
        "nl": "Nederlands",
        "fr": "Français",
        "es": "Español",
    }
