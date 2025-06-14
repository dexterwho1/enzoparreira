import streamlit as st
import traceback

try:
    import sqlite3
    import pandas as pd
    from datetime import datetime, timedelta

    DB_PATH = "crm_data.db"

    st.title("KPI Prospection")

    # Récupération des données
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM prospects", conn)

    # Vérification colonne date_dernier_appel
    if 'date_dernier_appel' not in df.columns:
        st.warning("Aucune donnée d'appel trouvée (colonne 'date_dernier_appel' manquante)")
        st.stop()

    # Conversion robuste de la date
    df['date_dernier_appel_dt'] = pd.to_datetime(df['date_dernier_appel'], errors='coerce')

    # Fonctions utilitaires pour les périodes
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    start_week = today - timedelta(days=today.weekday())
    start_last_week = start_week - timedelta(days=7)
    end_last_week = start_week - timedelta(days=1)
    start_month = today.replace(day=1)

    # Helper pour filtrer par date
    def filter_by_period(df, col, start, end):
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        # On ne garde que les lignes avec une date valide
        mask = (df[col].notna()) & (df[col] >= start_dt) & (df[col] <= end_dt)
        return df[mask]

    # Appels passés = toute ligne avec une date_dernier_appel non vide dans la période
    def count_calls(df, start, end):
        return filter_by_period(df, 'date_dernier_appel_dt', start, end).shape[0]

    # RDV générés = statut_appel == 'r1' ou 'signé' dans la période
    def count_rdv(df, start, end):
        filt = filter_by_period(df, 'date_dernier_appel_dt', start, end)
        return filt[filt['statut_appel'].isin(['r1', 'signé'])].shape[0]

    # Clients estimés = statut_appel == 'signé' dans la période
    def count_clients(df, start, end):
        filt = filter_by_period(df, 'date_dernier_appel_dt', start, end)
        return filt[filt['statut_appel'] == 'signé'].shape[0]

    # CA estimé (exemple: 0€ car pas de montant dans prospects)
    def ca_estime(df, start, end):
        return 0

    # Taux appel → RDV
    def taux_appel_rdv(appels, rdv):
        return f"{(rdv/appels*100):.0f}%" if appels else "0%"

    # Taux RDV → client
    def taux_rdv_client(rdv, clients):
        return f"{(clients/rdv*100):.0f}%" if rdv else "0%"

    # KPI par période
    periods = {
        "Aujourd'hui": (today, today),
        "Hier": (yesterday, yesterday),
        "Cette semaine": (start_week, today),
        "Semaine dernière": (start_last_week, end_last_week),
        "Ce mois": (start_month, today)
    }

    st.subheader("KPI Prospection")
    kpi_data = {p: count_calls(df, *d) for p, d in periods.items()}
    st.write(pd.DataFrame([kpi_data], index=["Appels passés"]))

    rdv_data = {p: count_rdv(df, *d) for p, d in periods.items()}
    st.write(pd.DataFrame([rdv_data], index=["RDV générés"]))

    clients_data = {p: count_clients(df, *d) for p, d in periods.items()}
    st.write(pd.DataFrame([clients_data], index=["Clients estimés"]))

    ca_data = {p: ca_estime(df, *d) for p, d in periods.items()}
    st.write(pd.DataFrame([ca_data], index=["CA estimé (€)"]))

    # Taux globaux
    appels_total = count_calls(df, start_month, today)
    rdv_total = count_rdv(df, start_month, today)
    clients_total = count_clients(df, start_month, today)

    st.metric("Taux appel → RDV", taux_appel_rdv(appels_total, rdv_total))
    st.metric("Taux RDV → client", taux_rdv_client(rdv_total, clients_total))

    # Comparaison par catégorie principale
    st.subheader("Comparaison par catégorie principale")
    if 'main_category' in df.columns:
        cat_stats = df.groupby('main_category').agg({
            'place_id': 'count',
            'statut_appel': lambda x: (x == 'signé').sum()
        }).rename(columns={'place_id': 'Appels', 'statut_appel': 'Clients signés'})
        st.dataframe(cat_stats)
    else:
        st.info("Aucune catégorie principale trouvée dans les données.")

    # Pipeline 4 semaines (appels)
    st.subheader("Pipeline 4 semaines (appels)")
    four_weeks_ago = today - timedelta(days=28)
    four_weeks_ago_dt = pd.to_datetime(four_weeks_ago)
    pipeline = df[df['date_dernier_appel_dt'] >= four_weeks_ago_dt]
    if not pipeline.empty:
        pipeline_stats = pipeline.groupby(pipeline['date_dernier_appel_dt'].dt.isocalendar().week).size()
        st.bar_chart(pipeline_stats)
    else:
        st.info("Aucun appel sur les 4 dernières semaines.")

except Exception as e:
    st.error(f"Erreur dans KPI Prospection : {e}")
    st.text(traceback.format_exc()) 