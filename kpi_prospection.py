import streamlit as st
import traceback
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "crm_data.db"

st.title("KPI Prospection")

# --- Récupération des données ---
with sqlite3.connect(DB_PATH) as conn:
    histo = pd.read_sql_query("SELECT * FROM historique_statuts", conn)
    prospects = pd.read_sql_query("SELECT * FROM prospects", conn)
    clients = pd.read_sql_query("SELECT * FROM clients", conn)

# --- Préparation des données ---
# Dernier statut par prospect (y compris ceux devenus clients)
if not histo.empty:
    histo['date_changement'] = pd.to_datetime(histo['date_changement'], errors='coerce')
    last_statut = histo.sort_values('date_changement').groupby('place_id').tail(1)
else:
    last_statut = pd.DataFrame(columns=['place_id','statut','date_changement'])

# Pour les périodes
now = datetime.now()
today = now.date()
yesterday = today - timedelta(days=1)
start_week = today - timedelta(days=today.weekday())
start_last_week = start_week - timedelta(days=7)
end_last_week = start_week - timedelta(days=1)
start_month = today.replace(day=1)
periods = {
    "Aujourd'hui": (today, today),
    "Hier": (yesterday, yesterday),
    "Cette semaine": (start_week, today),
    "Semaine dernière": (start_last_week, end_last_week),
    "Ce mois": (start_month, today)
}

# --- Appels passés ---
# Tous les place_id ayant au moins un changement de statut (historique) ou présents dans clients
place_ids_appel = set(histo['place_id'].unique()) | set(clients['place_id'].dropna().unique())
# Pour les périodes, on regarde la date du dernier changement de statut
last_statut_period = last_statut.copy()
last_statut_period['date'] = last_statut_period['date_changement'].dt.date

def count_appels_periode(start, end):
    mask = (last_statut_period['date'] >= start) & (last_statut_period['date'] <= end)
    return last_statut_period[mask]['place_id'].nunique() + clients[~clients['place_id'].isin(last_statut_period[mask]['place_id'])]['place_id'].nunique()

kpi_data = {p: count_appels_periode(*d) for p, d in periods.items()}

# --- Clients estimés ---
def count_clients_periode(start, end):
    # On prend la date_conversion du client
    if 'date_conversion' in clients.columns:
        clients['date_conversion_dt'] = pd.to_datetime(clients['date_conversion'], errors='coerce')
        mask = (clients['date_conversion_dt'].dt.date >= start) & (clients['date_conversion_dt'].dt.date <= end)
        return clients[mask]['client_id'].nunique()
    return 0
clients_data = {p: count_clients_periode(*d) for p, d in periods.items()}

# --- Ratio appels/clients ---
def safe_ratio(a, b):
    return f"{a/b:.1f}" if b else "∞"

# --- Section KPI ---
st.subheader("KPI Prospection")
st.write(pd.DataFrame([kpi_data], index=["Appels passés"]))
st.write(pd.DataFrame([clients_data], index=["Clients (transformés)"]))
ratio = safe_ratio(sum(kpi_data.values()), sum(clients_data.values()))
st.metric("Ratio Appels/Clients", ratio)

# --- Affichage des clients signés (même hors prospects) ---
st.subheader("Clients signés (tous)")
if not clients.empty:
    st.dataframe(clients[['name','phone','address','date_conversion']])
else:
    st.info("Aucun client signé.")

# --- Funnel de vente ---
st.subheader("Funnel de vente (statut d'appel)")
if not last_statut.empty:
    total = last_statut['place_id'].nunique()
    funnel = last_statut['statut'].value_counts().reset_index()
    funnel.columns = ['Statut', 'Nombre']
    funnel['%'] = funnel['Nombre'] / total * 100
    st.dataframe(funnel)
else:
    st.info("Aucun prospect avec statut d'appel.")

# --- Pipeline 4 semaines (appels) ---
st.subheader("Pipeline 4 semaines (appels)")
four_weeks_ago = today - timedelta(days=28)
if not last_statut.empty:
    pipeline = last_statut[last_statut['date'] >= four_weeks_ago]
    if not pipeline.empty:
        pipeline_stats = pipeline.groupby(pipeline['date'].apply(lambda d: d.isocalendar()[1])).size()
        st.bar_chart(pipeline_stats)
    else:
        st.info("Aucun appel sur les 4 dernières semaines.")
else:
    st.info("Aucun appel sur les 4 dernières semaines.")

except Exception as e:
    st.error(f"Erreur dans KPI Prospection : {e}")
    st.text(traceback.format_exc()) 