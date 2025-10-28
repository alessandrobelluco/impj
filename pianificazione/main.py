import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout='wide')

st.title('Elaborazione colli producibili')

#FUNZIONI ================================================================

def upload_multiplo(messaggio):
    path_list = st.sidebar.file_uploader(messaggio,accept_multiple_files=True)
    if not path_list:
            st.stop()
    df_list = []
    for path in path_list:
            df = pd.read_excel(path)
            df['mese']=int(str(path.name)[:2])
            df_list.append(df)
    return df_list

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


#CARICAMENTO DATI===========================================================

df_list =  upload_multiplo('Carica file da accodare')
bom = pd.concat(df_list)

path_mancanti = st.sidebar.file_uploader('Caricare Mancanti')
if not path_mancanti:
    st.stop()   
df_mancanti = pd.read_csv(path_mancanti, sep=';', skiprows=1)#,on_bad_lines='skip')


#ELABORAZIONE ===============================================================

colonne = df_mancanti.columns
df_mancanti['Articolo'] =  [articolo.replace(' ','') for articolo in df_mancanti.Articolo.astype(str)]
df_mancanti = df_mancanti.melt(id_vars=["Ragione sociale","Articolo","Descrizione"], value_vars=colonne[14:])
df_mancanti = df_mancanti[(df_mancanti.value!=0) & (df_mancanti.variable != 'Fabbisogni Totale')].reset_index(drop=True)

df_colli = df_mancanti[[codice[:2] == '3N' for codice in df_mancanti.Articolo]]
df_componenti = df_mancanti[[codice[:2] != '3N' for codice in df_mancanti.Articolo]]
df_componenti['Articolo'] = [articolo.replace(' ','') for articolo in df_componenti.Articolo.astype(str)]

#elaborazione BOM
bom['CI'] = bom['QUANTI'] / bom['QTA_PADRE']
bom_reparti = bom[['COLLO','COD_REPARTO','DES_REPARTO']].drop_duplicates()

art_bom = list(bom.FILIO.unique())


#dalla bom estraggo solo i componenti mancanti
comp_mancanti = list(df_componenti.Articolo.unique())
bom_comp_mancanti = bom[[any(codice in test for codice in comp_mancanti) for test in bom.FILIO]]
bom_comp_mancanti = bom_comp_mancanti[['COLLO','FILIO','COD_REPARTO','DES_REPARTO','CI']].drop_duplicates()

# Estraggo la lista dei colli 3N producibili con il loro reparto
colli_con_mancanti = list(bom_comp_mancanti.COLLO.unique())

df_colli_producibili = df_colli[[all(codice not in test for codice in colli_con_mancanti) for test in df_colli.Articolo]]
df_colli_producibili = df_colli_producibili.merge(bom_reparti, how='left', left_on = 'Articolo', right_on='COLLO')

df_colli_con_mancanti = df_colli[[any(codice in test for codice in colli_con_mancanti) for test in df_colli.Articolo]]

# recupero i componenti
df_colli_con_mancanti = df_colli_con_mancanti.merge(bom_comp_mancanti[['COLLO','FILIO','CI','COD_REPARTO','DES_REPARTO']], how='left', left_on='Articolo', right_on='COLLO')

df_colli_con_mancanti.rename(columns={'value':'Colli_mancanti'}, inplace=True)
df_colli_con_mancanti = df_colli_con_mancanti.merge(df_componenti[['Articolo','variable','value']], how='left', left_on=['FILIO','variable'], right_on=['Articolo','variable'])
df_colli_con_mancanti = df_colli_con_mancanti[df_colli_con_mancanti.value.astype(str) != 'nan']

df_colli_con_mancanti.rename(columns={
      'Articolo_x':'Collo_3N',
      'variable':'Lancio',
      'FILIO':'Componente',
      'value':'qty_mancante_componente'
}, inplace=True)

df_colli_con_mancanti = df_colli_con_mancanti[['Ragione sociale','COD_REPARTO','DES_REPARTO','Collo_3N','Descrizione','Lancio','Componente','CI','qty_mancante_componente']]

st.divider()
st.subheader(':green[Colli producibili]')
df_colli_producibili['COD_REPARTO'] = df_colli_producibili['COD_REPARTO'].fillna('Non disponibile')
df_colli_producibili['DES_REPARTO'] = df_colli_producibili['DES_REPARTO'].fillna('Non disponibile')
df_colli_producibili.rename(columns={
      'variable':'Lancio',
      'value':'Colli_mancanti',
     
}, inplace=True)
df_colli_producibili = df_colli_producibili[['Ragione sociale','Articolo','Descrizione','COD_REPARTO','DES_REPARTO','Lancio','Colli_mancanti']]
df_colli_producibili
scarica_excel(df_colli_producibili, 'Colli_producibili.xlsx')

st.divider()
st.subheader(':red[Colli con componenti mancanti]')

anagrafica = df_componenti[['Articolo', 'Descrizione', 'Ragione sociale']].drop_duplicates()
anagrafica.rename(columns={'Ragione sociale':'Fornitore', 'Descrizione':'Descrizione_componente'},inplace=True)

df_colli_con_mancanti = df_colli_con_mancanti.merge(anagrafica, how='left', left_on='Componente', right_on='Articolo')
df_colli_con_mancanti.drop(columns='Articolo', inplace=True)
'qty_mancante_componente indica quanti pezzi mancano per quel container, un componente può andare su più 3N, per quello la quantità può essere molto più alta dei colli'
df_colli_con_mancanti
scarica_excel(df_colli_con_mancanti, 'Colli_con_mancanti.xlsx')



