import pandas as pd
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from github_storage import init_github_storage

# FILE DI CONFIGURAZIONE
CONFIG_RESOURCES = 'config_resources.json'
CONFIG_PRIORITIES = 'config_priorities.json'
CONFIG_CYCLE_TIMES = 'config_cycle_times.json'

# Inizializza GitHub Storage
@st.cache_resource
def get_github_storage():
    """Inizializza e restituisce l'istanza di GitHub Storage (cached)."""
    return init_github_storage()

def save_config(data, filename):
    """Salva configurazione su GitHub (se disponibile) o localmente come fallback."""
    github_storage = get_github_storage()
    
    if github_storage:
        # Salva su GitHub
        success = github_storage.save_json(data, filename, f"Update {filename}")
        if success:
            # Salva anche localmente come backup
            try:
                with open(filename, 'w') as f:
                    json.dump(data, f)
            except:
                pass  # Ignora errori di salvataggio locale
            return True
        return False
    else:
        # Fallback: salva solo localmente
        try:
            with open(filename, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            st.error(f"Errore nel salvataggio di {filename}: {e}")
            return False

def load_config(filename):
    """Carica configurazione da GitHub (se disponibile) o localmente come fallback."""
    github_storage = get_github_storage()
    
    if github_storage:
        # Prova a caricare da GitHub
        data = github_storage.load_json(filename)
        if data is not None:
            return data
    
    # Fallback: carica da file locale se esiste
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Errore nel caricamento di {filename}: {e}")
            return None
    
    return None


st.set_page_config(layout='wide')

# Inizializza session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'tempo_ciclo_collo' not in st.session_state:
    st.session_state.tempo_ciclo_collo = None
if 'tempi_ciclo_reparto' not in st.session_state:
    st.session_state.tempi_ciclo_reparto = None

# Mostra stato connessione GitHub
github_storage = get_github_storage()
if github_storage:
    st.sidebar.success("✅ Connesso a GitHub - Persistenza attiva")
else:
    st.sidebar.warning("⚠️ GitHub non configurato - Modalità locale")

head_sx, head_dx = st.columns([4,1])

with head_sx:
    st.title('Sviluppo ore di produzione')

with head_dx:
    st.image('https://github.com/alessandrobelluco/impj/blob/main/Planning_git/logo_impj.png?raw=True')

st.divider()

#df = pd.read_excel('/Users/Alessandro/Desktop/APP/IMPJ/sviluppo_ore/IMABPJ - Cruscotto Programmazione Produzione.xlsx')



t1, t2 = st.tabs(['Overview','Programmazione'])

with t1:
    st.subheader('Caricamento dati')
    path = st.file_uploader('Caricare "IMABPJ Cruscotto Programmazione Produzione.xlsx')
    if not path:
        st.stop()

    st.session_state.df = pd.read_excel(path)

    # Carica tempi ciclo salvati all'avvio
    if st.session_state.tempi_ciclo_reparto is None:
        saved_cycle_times = load_config(CONFIG_CYCLE_TIMES)
        if saved_cycle_times:
            st.session_state.tempi_ciclo_reparto = pd.DataFrame(saved_cycle_times)

    colli_gg = 400
    h_c = 11
    st.session_state.tempo_ciclo_collo = 7.5/(colli_gg/h_c)

    st.divider()
    st.write("Attivando l'opzione Modifica parametri è possibile modificare i valori di produttività e numero di operatori" )
    if st.toggle('Modifica parametri'):
        colli_gg = st.number_input('Colli/giorno', value=400, min_value=350, max_value=600, step=1)
        h_c = st.number_input('Operatori fabbrica', value=11, min_value=5, max_value=20, step=1)
        st.session_state.tempo_ciclo_collo = 7.5/(colli_gg/h_c)
        
        st.divider()
        st.write('**Tempi Ciclo per Reparto (minuti/collo)**')
        st.write('Personalizza il tempo ciclo per ogni reparto. Default: 12.5 minuti/collo')
        
        # Estrai reparti unici dal dataframe
        if 'REPARTO_ARTICOLO' in st.session_state.df.columns:
            df_temp = st.session_state.df.copy()
            df_temp['REPARTO_ARTICOLO'] = df_temp['REPARTO_ARTICOLO'].ffill()
            reparti_unici = sorted(df_temp['REPARTO_ARTICOLO'].dropna().unique())
            
            # Crea dataframe per tempi ciclo
            tempi_ciclo_df = pd.DataFrame({
                'Reparto': reparti_unici,
                'Tempo Ciclo (min/collo)': 12.5
            })
            
            # Carica configurazione salvata se esiste
            saved_cycle_times = load_config(CONFIG_CYCLE_TIMES)
            if saved_cycle_times:
                saved_df = pd.DataFrame(saved_cycle_times)
                if 'Reparto' in saved_df.columns and 'Tempo Ciclo (min/collo)' in saved_df.columns:
                    # Aggiorna con i valori salvati
                    tempi_ciclo_df = tempi_ciclo_df.set_index('Reparto')
                    saved_df = saved_df.set_index('Reparto')
                    tempi_ciclo_df.update(saved_df)
                    tempi_ciclo_df = tempi_ciclo_df.reset_index()
            
            edited_cycle_times = st.data_editor(
                tempi_ciclo_df,
                use_container_width=True,
                hide_index=True,
                key='cycle_times_editor',
                column_config={
                    'Reparto': st.column_config.TextColumn('Reparto', disabled=True),
                    'Tempo Ciclo (min/collo)': st.column_config.NumberColumn(
                        'Tempo Ciclo (min/collo)',
                        min_value=0.1,
                        max_value=120.0,
                        step=0.5,
                        format='%.2f',
                        help='Tempo necessario per produrre un collo (in minuti)'
                    )
                }
            )
            
            col_save1, col_save2 = st.columns([1, 1])
            with col_save1:
                if st.button('Salva Tempi Ciclo', use_container_width=True):
                    if save_config(edited_cycle_times.to_dict('records'), CONFIG_CYCLE_TIMES):
                        st.session_state.tempi_ciclo_reparto = edited_cycle_times
                        st.toast('Tempi ciclo salvati con successo')
            
            # Salva in session state per uso successivo
            st.session_state.tempi_ciclo_reparto = edited_cycle_times

    # FUNZIONI ==============================================================================================================================

    def multifiltro(df, campo, selected ):
        df = df[[any(elemento in check for elemento in selected) for check in df[campo].astype(str)]]
        return df

    # FILTRO ================================================================================================================================

    # Crea copia completa per calcolo metriche producibilità
    df_completo = st.session_state.df.copy()
    df_completo['COMMESSA'] = df_completo['COMMESSA'].ffill()
    df_completo['ANNO'] = df_completo['ANNO'].ffill()
    df_completo['WEEK'] = df_completo['WEEK'].ffill()
    df_completo['LANCIO'] = df_completo['LANCIO'].ffill()
    df_completo['GEST'] = df_completo['GEST'].ffill()
    df_completo['STATO'] = df_completo['STATO'].ffill()
    
    df = st.session_state.df.copy()
    df['COMMESSA'] = df['COMMESSA'].ffill()
    df['ANNO'] = df['ANNO'].ffill()
    df['WEEK'] = df['WEEK'].ffill()
    df['LANCIO'] = df['LANCIO'].ffill()
    df['GEST'] = df['GEST'].ffill()
    df['STATO'] = df['STATO'].ffill()


    if st.checkbox('Solo produzione interna'):
        df = df[(df.GEST == '1) GRIGIO - PROD INT')].reset_index(drop=True)
        df_completo = df_completo[(df_completo.GEST == '1) GRIGIO - PROD INT')].reset_index(drop=True)

    else:
        df = df[(df.GEST == '1) GRIGIO - PROD INT') | (df.GEST  == '3) AZZURRO - ACQ')].reset_index(drop=True)
        df_completo = df_completo[(df_completo.GEST == '1) GRIGIO - PROD INT') | (df_completo.GEST  == '3) AZZURRO - ACQ')].reset_index(drop=True)

    df['MONT_SMONT'] = df['MONT_SMONT'].ffill()
    df_completo['MONT_SMONT'] = df_completo['MONT_SMONT'].ffill()

    df = df[df.STATO == 'INEVASO - PRODUCIBILE'].reset_index(drop=True)
    df['QTA_PRODOTTA'] = df['QTA_PRODOTTA'].fillna(0)

    df = df[df.columns[:15]]
    
    # Salva df filtrato in session state SOLO se non esiste (inizializzazione)
    if 'df_filtrato' not in st.session_state:
        st.session_state.df_filtrato = df

    st.divider()

    st.subheader('Selezione commesse e lanci')
    sx_fil, cx_fil, dx_fil = st.columns([1,1,3])

    with sx_fil:
        selected_comm = st.multiselect('Selezionare commesse', options=df.COMMESSA.unique())
        if selected_comm == []:
            selected_comm = df.COMMESSA.unique()

        df = multifiltro(df, 'COMMESSA', selected_comm)

    with cx_fil:
        selected_lancio = st.multiselect('Selezionare lanci', options=df.LANCIO.astype(int).astype(str).unique())
        if selected_lancio == []:
            selected_lancio = df.LANCIO.astype(int).astype(str).unique()

        df = multifiltro(df, 'LANCIO', selected_lancio)
        df_completo = multifiltro(df_completo, 'LANCIO', selected_lancio)
        
    with dx_fil:
        st.write('') # Spacer
        st.write('') # Spacer
        if st.button('Applica Filtro alla Programmazione', type='primary'):
            st.session_state.df_filtrato = df
            st.toast('Filtro applicato alla tab Programmazione')

    df['Ore_STD'] = df['QTA_RESIDUA_PADRE'] * st.session_state.tempo_ciclo_collo
    
    # Metriche Producibilità per Lancio
    st.divider()
    st.subheader('Analisi Producibilità per Lancio')
    
    if not df_completo.empty and 'QTA_RESIDUA_PADRE' in df_completo.columns:
        # Prepara colonna QTA per entrambi i dataframe
        df_completo['QTA_PRODOTTA'] = df_completo['QTA_PRODOTTA'].fillna(0)
        
        # Calcola colli totali per lancio (tutti gli stati)
        colli_totali_lancio = df_completo.groupby('LANCIO')['QTA_RESIDUA_PADRE'].sum()
        
        # Calcola colli producibili per lancio (solo INEVASO - PRODUCIBILE)
        colli_producibili_lancio = df.groupby('LANCIO')['QTA_RESIDUA_PADRE'].sum()
        
        # Crea dataframe riepilogativo
        lanci_selezionati = sorted(selected_lancio)
        metriche_cols = st.columns(min(len(lanci_selezionati), 4))
        
        for idx, lancio in enumerate(lanci_selezionati):
            lancio_int = int(lancio)
            
            totale = colli_totali_lancio.get(lancio_int, 0)
            producibili = colli_producibili_lancio.get(lancio_int, 0)
            non_producibili = totale - producibili
            
            perc_producibili = (producibili / totale * 100) if totale > 0 else 0
            perc_non_producibili = (non_producibili / totale * 100) if totale > 0 else 0
            
            col = metriche_cols[idx % len(metriche_cols)]
            
            with col:
                st.metric(f"Lancio {lancio}", f"{totale:.0f} colli")
                st.write(f"✅ Producibili: **{producibili:.0f}** ({perc_producibili:.1f}%)")
                st.write(f"⚠️ Non producibili: **{non_producibili:.0f}** ({perc_non_producibili:.1f}%)")
                st.progress(perc_producibili / 100)
    else:
        st.info('Selezionare lanci per visualizzare le metriche di producibilità')

    st.subheader('Dettaglio colli')
    df
    
    # Pulsante download
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dettaglio Colli')
    st.download_button(
        label="📥 Scarica Dettaglio Colli in Excel",
        data=buffer.getvalue(),
        file_name=f"dettaglio_colli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.subheader('Metriche riassuntive')
    st.divider()
    ore_1, ore_2, ore_3, ore_4 = st.columns([1,1,1,1])

    ore_1.metric('Totale colli mancanti', value = df['QTA_RESIDUA_PADRE'].astype(int).sum())

    ore_tot = df['Ore_STD'].sum()
    ore_2.metric('Ore totali necessarie', value = f'{ore_tot:.1f}')
    ore_2.write(f'Le ore necessarie sono calcolate considerando una produttività di {colli_gg} colli/giorno del reparto')

    lead_time = ore_tot/(h_c*8)
    ore_3.metric('Giorni necessari al completamento', value=f'{lead_time:.1f}')
    ore_3.write(f'I giorni necessari sono calcolati consideranto {h_c} persone')

    if lead_time < 1:
        ore_disp = (1-lead_time) * h_c * 7.5
        ore_4.metric('Ore uomo residue della giornata', value=f'{ore_disp:.1f}')

    st.divider()

with t2:
    st.subheader('Programmazione Produzione')
    
    # Verifica che i dati siano stati caricati
    if st.session_state.df is None or 'df_filtrato' not in st.session_state:
        st.warning('Caricare prima i dati nella tab "Overview"')
        st.stop()
    
    df = st.session_state.df_filtrato.copy()
    
    # Calcola ore necessarie usando i tempi ciclo per reparto se disponibili
    if st.session_state.tempi_ciclo_reparto is not None and not st.session_state.tempi_ciclo_reparto.empty:
        # Crea dizionario reparto -> tempo ciclo (converti da minuti a ore dividendo per 60)
        tempi_ciclo_dict = dict(zip(
            st.session_state.tempi_ciclo_reparto['Reparto'],
            st.session_state.tempi_ciclo_reparto['Tempo Ciclo (min/collo)'] / 60
        ))
        
        # Applica il tempo ciclo specifico per reparto
        df['Tempo_Ciclo_Ore'] = df['REPARTO_ARTICOLO'].map(tempi_ciclo_dict)
        # Usa default se reparto non trovato
        df['Tempo_Ciclo_Ore'] = df['Tempo_Ciclo_Ore'].fillna(12.5 / 60)
        df['Ore_Necessarie'] = df['QTA_RESIDUA_PADRE'] * df['Tempo_Ciclo_Ore']
    else:
        # Usa tempo ciclo standard se non configurato
        df['Ore_Necessarie'] = df['QTA_RESIDUA_PADRE'] * st.session_state.tempo_ciclo_collo
    
    # Sezione 0: Analisi Carico di Lavoro
    st.subheader('Analisi Carico di Lavoro per Reparto')
    st.write('Questa tabella mostra il carico di lavoro totale richiesto per ogni reparto, utile per pianificare le risorse')
    
    if 'REPARTO_ARTICOLO' in df.columns:
        # Aggrega per reparto
        carico_reparto = df.groupby('REPARTO_ARTICOLO').agg({
            'Ore_Necessarie': 'sum',
            'QTA_RESIDUA_PADRE': 'sum'
        }).reset_index()
        
        carico_reparto.columns = ['Reparto', 'Ore Totali', 'Colli Totali']
        
        # Calcola persone equivalenti (assumendo 6 giorni lavorativi, 8 ore/giorno)
        giorni_disponibili = 6  # Lun-Sab
        ore_per_persona = giorni_disponibili * 7.5
        
        carico_reparto['Persone Equivalenti (6gg)'] = (carico_reparto['Ore Totali'] / ore_per_persona).round(1)
        carico_reparto['Persone/Giorno (se distribuite)'] = (carico_reparto['Ore Totali'] / (giorni_disponibili * 7.5)).round(1)
        
        # Mostra tabella con colori
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(
                carico_reparto,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Ore Totali': st.column_config.NumberColumn('Ore Totali', format='%.1f'),
                    'Colli Totali': st.column_config.NumberColumn('Colli Totali', format='%.0f'),
                    'Persone Equivalenti (6gg)': st.column_config.NumberColumn(
                        'Persone Equivalenti (6gg)',
                        help='Numero di persone necessarie se lavorano tutti i 6 giorni',
                        format='%.1f'
                    ),
                    'Persone/Giorno (se distribuite)': st.column_config.NumberColumn(
                        'Persone/Giorno Media',
                        help='Numero medio di persone al giorno se il carico è distribuito uniformemente',
                        format='%.1f'
                    )
                }
            )
        
        with col2:
            st.metric('Totale Ore Necessarie', f"{carico_reparto['Ore Totali'].sum():.1f}")
            st.metric('Totale Colli', f"{carico_reparto['Colli Totali'].sum():.0f}")
            persone_totali = carico_reparto['Persone Equivalenti (6gg)'].sum()
            st.metric('Persone Totali Necessarie', f"{persone_totali:.1f}")
        
        st.info('**Suggerimento**: Usa i valori "Persone/Giorno Media" come riferimento per compilare la tabella risorse sottostante')
        
        # Pulsante download
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            carico_reparto.to_excel(writer, index=False, sheet_name='Carico Lavoro Reparto')
        st.download_button(
            label="📥 Scarica Carico Lavoro in Excel",
            data=buffer.getvalue(),
            file_name=f"carico_lavoro_reparto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_carico_reparto"
        )

        st.divider()
        
        # Sezione 2: Tabella Priorità (SPOSTATA QUI)
        st.subheader('Impostazione Priorità Commesse')
        st.write('Indicare nella colonna priorità (1=priorità alta, 2=media, 3=bassa, ecc.)')
        
        prio = df[['COMMESSA', 'LANCIO', 'ANNO']].drop_duplicates().reset_index(drop=True)
        prio['Priorità'] = None
        prio = prio[['Priorità','COMMESSA', 'LANCIO', 'ANNO']]

        # Carica priorità salvate
        saved_priorities = load_config(CONFIG_PRIORITIES)
        if saved_priorities:
            saved_prio_df = pd.DataFrame(saved_priorities)
            if 'COMMESSA' in saved_prio_df.columns and 'LANCIO' in saved_prio_df.columns and 'Priorità' in saved_prio_df.columns:
                # Crea chiave composta per il mapping
                # Assicuriamoci che i tipi siano stringa per il confronto
                saved_prio_df['key'] = saved_prio_df['COMMESSA'].astype(str) + '_' + saved_prio_df['LANCIO'].astype(str)
                prio['key'] = prio['COMMESSA'].astype(str) + '_' + prio['LANCIO'].astype(str)
                
                prio_map = saved_prio_df.set_index('key')['Priorità'].to_dict()
                prio['Priorità'] = prio['key'].map(prio_map)
                
                # Rimuovi colonna key temporanea
                prio = prio.drop(columns=['key'])
        
        edited_prio = st.data_editor(
            prio, 
            use_container_width=True, 
            hide_index=True, 
            key='prio_editor',
            column_config={
                'Priorità': st.column_config.NumberColumn('Priorità', min_value=1, step=1, help="1=Alta, 2=Media, ...")
            }
        )

        st.divider()
        st.subheader('Dettaglio Carico per Commessa/Lancio')
        
        # Tabella dettagliata
        dettaglio_carico = df.groupby(['COMMESSA', 'LANCIO', 'REPARTO_ARTICOLO']).agg({
            'QTA_RESIDUA_PADRE': 'sum',
            'Ore_Necessarie': 'sum'
        }).reset_index()
        
        dettaglio_carico.columns = ['Commessa', 'Lancio', 'Reparto', 'Colli Totali', 'Ore Totali']
        
        # Aggiungi Priorità alla tabella dettagliata per ordinamento
        # Crea dizionario priorità corrente (inclusi edit non salvati)
        current_prio_map = {}
        for _, row in edited_prio.iterrows():
            if pd.notna(row['Priorità']):
                key = (str(row['COMMESSA']), str(row['LANCIO']))
                current_prio_map[key] = row['Priorità']
        
        def get_prio_detail(row):
            key = (str(row['Commessa']), str(row['Lancio']))
            val = current_prio_map.get(key, 999) # 999 per priorità bassa se non definita
            try:
                return float(val)
            except (ValueError, TypeError):
                return 999.0
            
        dettaglio_carico['Priorità'] = dettaglio_carico.apply(get_prio_detail, axis=1)
        # Ordina per Priorità (ASC) e poi per Ore Totali (DESC)
        dettaglio_carico = dettaglio_carico.sort_values(['Priorità', 'Ore Totali'], ascending=[True, False]).reset_index(drop=True)
        
        # Calcolo FTE (7.5 ore/giorno)
        dettaglio_carico['FTE (7.5h)'] = dettaglio_carico['Ore Totali'] / 7.5
        
        # Mostra tabella con dataframe
        st.dataframe(
            dettaglio_carico,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Priorità': st.column_config.NumberColumn('Priorità', format='%.0f'),
                'Colli Totali': st.column_config.NumberColumn('Colli Totali', format='%.0f'),
                'Ore Totali': st.column_config.NumberColumn('Ore Totali', format='%.1f'),
                'FTE (7.5h)': st.column_config.NumberColumn('FTE (7.5h)', format='%.1f')
            }
        )
        
        # Pulsante download
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            dettaglio_carico.to_excel(writer, index=False, sheet_name='Dettaglio Carico')
        st.download_button(
            label="📥 Scarica Dettaglio Carico in Excel",
            data=buffer.getvalue(),
            file_name=f"dettaglio_carico_commessa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_dettaglio_carico"
        )
    
    st.divider()
    
    # Sezione 1: Tabella Risorse per Reparto/Giorno
    st.subheader('Pianificazione Risorse per Reparto')
    st.write('Inserire il numero di operatori disponibili per ogni reparto in ogni giorno della settimana')
    
    # Estrai reparti unici
    if 'REPARTO_ARTICOLO' in df.columns:
        # Ordina i reparti per carico di lavoro totale (come nella tabella dettaglio)
        reparto_workload = df.groupby('REPARTO_ARTICOLO')['Ore_Necessarie'].sum().sort_values(ascending=False)
        reparti = reparto_workload.index.tolist()
    else:
        st.error('Colonna REPARTO_ARTICOLO non trovata nel dataframe')
        st.stop()
    
    # Crea tabella risorse
    giorni_settimana = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato']
    
    risorse_df = pd.DataFrame({
        'Reparto': reparti
    })
    
    # Aggiungi colonne per ogni giorno
    for giorno in giorni_settimana:
        risorse_df[giorno] = 0.0

    # Carica configurazione salvata se esiste
    saved_resources = load_config(CONFIG_RESOURCES)
    if saved_resources:
        # Converte la lista di dizionari in DataFrame
        saved_df = pd.DataFrame(saved_resources)
        # Unisci con il dataframe corrente per mantenere la struttura corretta
        # (in caso i reparti siano cambiati)
        if 'Reparto' in saved_df.columns:
            risorse_df = risorse_df.set_index('Reparto')
            saved_df = saved_df.set_index('Reparto')
            risorse_df.update(saved_df)
            risorse_df = risorse_df.reset_index()
    
    edited_risorse = st.data_editor(
        risorse_df, 
        use_container_width=True, 
        hide_index=True,
        key='risorse_editor',
        column_config={
            'Reparto': st.column_config.TextColumn('Reparto', disabled=True),
            **{giorno: st.column_config.NumberColumn(giorno, min_value=0, max_value=50, step=0.1, format='%.1f') for giorno in giorni_settimana}
        }
    )
     buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_risorse.to_excel(writer, index=False, sheet_name='Dettaglio Colli')
    st.download_button(
        label="📥 Scarica Risorse_reparti in Excel",
        data=buffer.getvalue(),
        file_name=f"dettaglio_risorse_reparti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )    
    # Calcola e mostra totali
    totali = edited_risorse[giorni_settimana].sum()
    df_totali = pd.DataFrame([totali]).reset_index(drop=True)
    df_totali.insert(0, 'Reparto', 'TOTALE')
    
    st.dataframe(
        df_totali,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Reparto': st.column_config.TextColumn('Reparto', disabled=True),
            **{giorno: st.column_config.NumberColumn(giorno, disabled=True, format='%.1f') for giorno in giorni_settimana}
        }
    )
    

    
    st.divider()
    
    # Sezione 3: Genera Programma di Produzione
    st.subheader('Generazione Programma di Produzione')
    
    # Selezione giorno di inizio
    st.write('Seleziona il giorno da cui iniziare la pianificazione:')
    giorno_inizio = st.selectbox(
        'Giorno di Inizio',
        options=giorni_settimana,
        index=0,
        help='Seleziona il primo giorno della settimana da cui iniziare la pianificazione'
    )
    
    col_btn_1, col_btn_2 = st.columns([1,1])
    with col_btn_1:
        gen_btn = st.button('Genera Programma', type='primary', use_container_width=True)
    with col_btn_2:
        if st.button('Salva Configurazioni', use_container_width=True):
            # Salva Risorse
            if save_config(edited_risorse.to_dict('records'), CONFIG_RESOURCES):
                st.toast('Risorse salvate')
            # Salva Priorità
            if save_config(edited_prio.to_dict('records'), CONFIG_PRIORITIES):
                st.toast('Priorità salvate')

    if gen_btn:
        # Autosave quando si genera
        save_config(edited_risorse.to_dict('records'), CONFIG_RESOURCES)
        save_config(edited_prio.to_dict('records'), CONFIG_PRIORITIES)
        
        # Prepara dati per schedulazione
        df_schedule = df.copy()
        
        # Aggiungi priorità al dataframe
        prio_dict = {}
        for _, row in edited_prio.iterrows():
            if pd.notna(row['Priorità']):
                # Chiave composta (Commessa, Lancio)
                key = (str(row['COMMESSA']), str(row['LANCIO']))
                prio_dict[key] = row['Priorità']
        
        # Funzione helper per mappare
        def get_prio(row):
            key = (str(row['COMMESSA']), str(row['LANCIO']))
            return prio_dict.get(key, None)

        df_schedule['Priorità'] = df_schedule.apply(get_prio, axis=1)
        
        # Ordina per priorità (NaN vanno alla fine)
        df_schedule = df_schedule.sort_values('Priorità', na_position='last').reset_index(drop=True)
        
        # Calcola ore necessarie per ogni riga
        df_schedule['Ore_Necessarie'] = df_schedule['QTA_RESIDUA_PADRE'] * st.session_state.tempo_ciclo_collo
        
        # Prepara dizionario capacità per reparto/giorno
        capacita = {}
        for _, row in edited_risorse.iterrows():
            reparto = row['Reparto']
            for giorno in giorni_settimana:
                num_operatori = row[giorno]
                ore_disponibili = num_operatori * 7.5  # 7.5 ore per operatore
                capacita[(reparto, giorno)] = ore_disponibili
        
        # Algoritmo di assegnazione con SPLITTING
        schedule_rows = []
        
        # Filtra i giorni disponibili in base al giorno di inizio selezionato
        start_index = giorni_settimana.index(giorno_inizio)
        giorni_disponibili = giorni_settimana[start_index:]
        
        # Traccia capacità residua
        capacita_residua = capacita.copy()
        
        for idx, row in df_schedule.iterrows():
            reparto = row['REPARTO_ARTICOLO']
            ore_rimanenti = row['Ore_Necessarie']
            
            assegnato_almeno_una_volta = False
            
            # Cerca giorni con capacità (solo nei giorni disponibili)
            for giorno in giorni_disponibili:
                key = (reparto, giorno)
                cap_disp = capacita_residua.get(key, 0)
                
                if cap_disp > 0 and ore_rimanenti > 0.01: # Tolleranza per float
                    # Calcola quanto possiamo assegnare
                    ore_da_assegnare = min(ore_rimanenti, cap_disp)
                    
                    # Crea nuova riga per l'assegnazione parziale
                    new_row = row.copy()
                    new_row['Giorno_Assegnato'] = giorno
                    new_row['Ore_Assegnate'] = ore_da_assegnare
                    new_row['Status'] = 'Assegnato'
                    schedule_rows.append(new_row)
                    
                    # Aggiorna contatori
                    capacita_residua[key] -= ore_da_assegnare
                    ore_rimanenti -= ore_da_assegnare
                    assegnato_almeno_una_volta = True
                
                if ore_rimanenti <= 0.01:
                    break
            
            # Se rimangono ore non assegnate
            if ore_rimanenti > 0.01:
                unassigned_row = row.copy()
                unassigned_row['Giorno_Assegnato'] = None
                unassigned_row['Ore_Assegnate'] = 0
                unassigned_row['Ore_Mancanti'] = ore_rimanenti
                if assegnato_almeno_una_volta:
                    unassigned_row['Status'] = 'Parziale'
                else:
                    unassigned_row['Status'] = 'Non Assegnato'
                schedule_rows.append(unassigned_row)
        
        # Ricostruisci il DataFrame dai risultati splittati
        df_schedule = pd.DataFrame(schedule_rows)
        
        # Salva in session state
        st.session_state.programma_produzione = df_schedule
        
        # Mostra risultati
        st.success('Programma di produzione generato')
        
        # Statistiche
        col1, col2, col3 = st.columns(3)
        
        # Calcolo metriche basate sui COLLI (Items)
        totale_colli = df['QTA_RESIDUA_PADRE'].sum()
        
        # Calcola colli assegnati per ogni riga schedulata
        colli_assegnati = 0
        if not df_schedule.empty:
            # Evitiamo divisione per zero
            mask_valid = df_schedule['Ore_Necessarie'] > 0
            if mask_valid.any():
                colli_assegnati = (
                    df_schedule.loc[mask_valid, 'Ore_Assegnate'] / 
                    df_schedule.loc[mask_valid, 'Ore_Necessarie'] * 
                    df_schedule.loc[mask_valid, 'QTA_RESIDUA_PADRE']
                ).sum()
        
        colli_mancanti = totale_colli - colli_assegnati
        
        col1.metric('Totale Colli', f"{totale_colli:.0f}")
        col2.metric('Colli Assegnati', f"{colli_assegnati:.0f}", delta=f"{(colli_assegnati/totale_colli*100):.1f}%" if totale_colli > 0 else "0%")
        col3.metric('Colli Non Assegnati', f"{colli_mancanti:.0f}", delta=f"-{(colli_mancanti/totale_colli*100):.1f}%" if colli_mancanti > 0 else "0%")
        
        # Metrica Completamento Lanci
        st.divider()
        st.subheader('Previsione Completamento Lanci')
        
        if not df_schedule.empty and 'LANCIO' in df_schedule.columns and 'Giorno_Assegnato' in df_schedule.columns:
            # Mappa giorni a indici per ordinamento
            days_map = {day: i for i, day in enumerate(giorni_settimana)}
            
            # Ottieni lista univoca dei lanci
            unique_launches = df_schedule['LANCIO'].unique()
            
            # Visualizza metriche
            cols = st.columns(len(unique_launches))
            
            for i, lancio in enumerate(unique_launches):
                # Filtra dataframe per questo lancio
                df_lancio = df_schedule[df_schedule['LANCIO'] == lancio]
                
                # Controlla se ci sono righe non assegnate
                if (df_lancio['Status'] != 'Assegnato').any():
                    metric_value = "Non completato"
                else:
                    # Trova il giorno massimo di assegnazione
                    df_lancio = df_lancio.copy()
                    df_lancio['day_idx'] = df_lancio['Giorno_Assegnato'].map(days_map)
                    max_day_idx = df_lancio['day_idx'].max()
                    
                    if pd.notna(max_day_idx):
                        metric_value = giorni_settimana[int(max_day_idx)]
                    else:
                        metric_value = "N/A"
                
                # Gestisci il caso in cui ci siano troppi lanci per le colonne
                col = cols[i % len(cols)] if len(cols) > 0 else st
                col.metric(f"Lancio {lancio}", metric_value)
        
        # Dettaglio Colli Non Assegnati
        st.divider()
        st.subheader('Dettaglio Colli Non Assegnati')
        
        df_non_assegnati = df_schedule[df_schedule['Status'] != 'Assegnato']
        
        if not df_non_assegnati.empty:
            # Calcola i colli non assegnati per lancio e reparto
            # Per gli ordini splittati, i colli non assegnati sono proporzionali alle ore non assegnate
            df_non_assegnati['Colli_Non_Assegnati'] = df_non_assegnati.apply(
                lambda x: ((x['Ore_Necessarie'] - x['Ore_Assegnate']) / x['Ore_Necessarie'] * x['QTA_RESIDUA_PADRE']) 
                if x['Ore_Necessarie'] > 0 else x['QTA_RESIDUA_PADRE'], 
                axis=1
            )
            
            dettaglio_non_assegnati = df_non_assegnati.groupby(['LANCIO', 'REPARTO_ARTICOLO']).agg({
                'Colli_Non_Assegnati': 'sum'
            }).reset_index()
            
            dettaglio_non_assegnati.columns = ['Lancio', 'Reparto', 'Colli Non Assegnati']
            dettaglio_non_assegnati = dettaglio_non_assegnati.sort_values(['Lancio', 'Reparto']).reset_index(drop=True)
            
            st.dataframe(
                dettaglio_non_assegnati,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Colli Non Assegnati': st.column_config.NumberColumn('Colli Non Assegnati', format='%.1f')
                }
            )
            
            # Pulsante download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                dettaglio_non_assegnati.to_excel(writer, index=False, sheet_name='Colli Non Assegnati')
            st.download_button(
                label="📥 Scarica Colli Non Assegnati in Excel",
                data=buffer.getvalue(),
                file_name=f"colli_non_assegnati_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_non_assegnati"
            )
        else:
            st.success('Tutti i colli sono stati assegnati!')

        st.divider()
        
        # Mostra programma
        st.subheader('Programma di Produzione')
        
        # Filtro per status
        status_options = df_schedule['Status'].unique().tolist()
        default_status = ['Assegnato'] if 'Assegnato' in status_options else status_options
        
        status_filter = st.multiselect(
            'Filtra per Status',
            options=status_options,
            default=default_status
        )
        
        df_display = df_schedule[df_schedule['Status'].isin(status_filter)]
        
        # Riordina colonne per migliore visualizzazione
        cols_to_show = ['Status', 'Giorno_Assegnato', 'Priorità', 'LANCIO', 'COMMESSA', 'REPARTO_ARTICOLO', 
                       'QTA_RESIDUA_PADRE', 'Ore_Necessarie', 'Ore_Assegnate']
        
        # Aggiungi altre colonne disponibili
        for col in df_display.columns:
            if col not in cols_to_show:
                cols_to_show.append(col)
        
        # Filtra solo colonne esistenti
        cols_to_show = [col for col in cols_to_show if col in df_display.columns]
        
        st.dataframe(
            df_display[cols_to_show],
            use_container_width=True,
            hide_index=True
        )
        
        # Pulsante download
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_display[cols_to_show].to_excel(writer, index=False, sheet_name='Programma Produzione')
        st.download_button(
            label="📥 Scarica Programma di Produzione in Excel",
            data=buffer.getvalue(),
            file_name=f"programma_produzione_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_programma"
        )

        
        # Riepilogo per giorno
        st.divider()
        st.subheader('Riepilogo Carico per Giorno e Reparto')
        
        df_assegnati = df_schedule[df_schedule['Status'] == 'Assegnato']
        
        if len(df_assegnati) > 0:
            # Calcola colli proporzionali alle ore assegnate per evitare duplicazioni nelle somme
            # Colli_Assegnati = (Ore_Assegnate / Ore_Necessarie) * QTA_RESIDUA_PADRE
            # Gestione divisione per zero con numpy o semplice check
            df_assegnati['Colli_Assegnati'] = df_assegnati.apply(
                lambda x: (x['Ore_Assegnate'] / x['Ore_Necessarie'] * x['QTA_RESIDUA_PADRE']) 
                if x['Ore_Necessarie'] > 0 else 0, 
                axis=1
            )

            riepilogo = df_assegnati.groupby(['Giorno_Assegnato', 'REPARTO_ARTICOLO']).agg({
                'Ore_Assegnate': 'sum',
                'Colli_Assegnati': 'sum'
            }).reset_index()
            
            riepilogo.columns = ['Giorno', 'Reparto', 'Ore Totali', 'Colli Totali']
            
            # Ordina per giorno (Lunedì -> Sabato) e poi per reparto
            day_order = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato']
            riepilogo['Giorno'] = pd.Categorical(riepilogo['Giorno'], categories=day_order, ordered=True)
            
            # Crea un mapping per l'ordine dei reparti (stesso ordine della tabella risorse)
            reparto_order = {reparto: i for i, reparto in enumerate(reparti)}
            riepilogo['Reparto_Order'] = riepilogo['Reparto'].map(reparto_order)
            
            # Ordina per giorno e poi per reparto
            riepilogo = riepilogo.sort_values(['Giorno', 'Reparto_Order']).reset_index(drop=True)
            riepilogo = riepilogo.drop(columns=['Reparto_Order'])
            
            # Aggiungi capacità e utilizzo
            def get_capacita(row):
                key = (row['Reparto'], row['Giorno'])
                return capacita.get(key, 0)
            
            def get_utilizzo(row):
                cap = get_capacita(row)
                if cap > 0:
                    return (row['Ore Totali'] / cap) * 100
                return 0
            
            riepilogo['Capacità (ore)'] = riepilogo.apply(get_capacita, axis=1)
            riepilogo['Utilizzo %'] = riepilogo.apply(get_utilizzo, axis=1)
            
            # Mostra tabella con dataframe
            st.dataframe(
                riepilogo,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Giorno': st.column_config.TextColumn('Giorno'),
                    'Reparto': st.column_config.TextColumn('Reparto'),
                    'Ore Totali': st.column_config.NumberColumn('Ore Totali', format='%.1f'),
                    'Colli Totali': st.column_config.NumberColumn('Colli Totali', format='%.0f'),
                    'Capacità (ore)': st.column_config.NumberColumn('Capacità (ore)', format='%.1f'),
                    'Utilizzo %': st.column_config.NumberColumn('Utilizzo %', format='%.2f %%')
                }
            )
            
            # Pulsante download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                riepilogo.to_excel(writer, index=False, sheet_name='Riepilogo Giorno Reparto')
            st.download_button(
                label="📥 Scarica Riepilogo Carico in Excel",
                data=buffer.getvalue(),
                file_name=f"riepilogo_carico_giorno_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_riepilogo"
            )
        else:
            st.info('Nessun codice assegnato da visualizzare')
    
    # Mostra programma esistente se già generato
    elif 'programma_produzione' in st.session_state and st.session_state.programma_produzione is not None:
        st.info('Programma già generato. Clicca "Genera Programma" per rigenerarlo con nuovi parametri.')










