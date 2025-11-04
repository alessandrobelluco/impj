import pandas as pd
import streamlit as st
import BytesIo


st.set_page_config(layout='wide')

head_sx, head_dx = st.columns([4,1])

with head_sx:
    st.title('Sviluppo ore di produzione')

with head_dx:
    st.image('https://github.com/alessandrobelluco/impj/blob/main/Sviluppo_ore/logo_impj.png?raw=True')

st.divider()

#df = pd.read_excel('/Users/Alessandro/Desktop/APP/IMPJ/sviluppo_ore/IMABPJ - Cruscotto Programmazione Produzione.xlsx')

st.subheader('Caricamento dati')
path = st.file_uploader('Caricare "IMABPJ Cruscotto Programmazione Produzione.xlsx')
if not path:
    st.stop()

df = pd.read_excel(path)


colli_gg = 400
h_c = 11
tempo_ciclo_collo = 8/(colli_gg/h_c)

st.divider()
st.write("Attivando l'opzione Modifica parametri è possibile modificare i valori di produttività e numero di operatori" )
if st.toggle('Modifica parametri'):
    colli_gg = st.number_input('Colli/giorno', value=400, min_value=350, max_value=600, step=1)
    h_c = st.number_input('Operatori fabbrica', value=11, min_value=5, max_value=20, step=1)

# FUNZIONI ==============================================================================================================================

def multifiltro(df, campo, selected ):
    df = df[[any(elemento in check for elemento in selected) for check in df[campo].astype(str)]]
    return df

def scarica_excel(df, filename):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1',index=False)
    writer.close()

    st.download_button(
        label="Download Excel workbook",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.ms-excel"
    )



# FILTRO ================================================================================================================================

df['COMMESSA'] = df['COMMESSA'].ffill()
df['ANNO'] = df['ANNO'].ffill()
df['WEEK'] = df['WEEK'].ffill()
df['LANCIO'] = df['LANCIO'].ffill()
df['GEST'] = df['GEST'].ffill()
df['STATO'] = df['STATO'].ffill()


if st.checkbox('Solo produzione interna'):
    df = df[(df.GEST == '1) GRIGIO - PROD INT')].reset_index(drop=True)

else:
    df = df[(df.GEST == '1) GRIGIO - PROD INT') | (df.GEST  == '3) AZZURRO - ACQ')].reset_index(drop=True)

df['MONT_SMONT'] = df['MONT_SMONT'].ffill()

df = df[df.STATO == 'INEVASO - PRODUCIBILE'].reset_index(drop=True)
df['QTA_PRODOTTA'] = df['QTA_PRODOTTA'].fillna(0)

df = df[df.columns[:15]]

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

df['Ore_STD'] = df['QTA_RESIDUA_PADRE'] * tempo_ciclo_collo

st.subheader('Dettaglio colli')
df

st.subheader('Metriche riassuntive')
st.divider()
ore_1, ore_2, ore_3, ore_4 = st.columns([1,1,1,1])

ore_1.metric('Totale colli producibili', value = df['QTA_RESIDUA_PADRE'].astype(int).sum())

ore_tot = df['Ore_STD'].sum()
ore_2.metric('Ore totali necessarie', value = f'{ore_tot:.1f}')
ore_2.write(f'Le ore necessarie sono calcolate considerando una produttività di {colli_gg} colli/giorno del reparto')

lead_time = ore_tot/(h_c*8)
ore_3.metric('Giorni necessari al completamento', value=f'{lead_time:.1f}')
ore_3.write(f'I giorni necessari sono calcolati consideranto {h_c} persone')

if lead_time < 1:
    ore_disp = (1-lead_time) * h_c * 8
    ore_4.metric('Ore uomo residue della giornata', value=f'{ore_disp:.1f}')

st.divider()
