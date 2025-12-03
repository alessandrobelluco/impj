# Pianificazione Produzione IMPJ

Applicazione Streamlit per la gestione e pianificazione della produzione.

## 🚀 Deployment su Streamlit Cloud

### Prerequisiti

1. **Account GitHub** con un repository per questo progetto
2. **Account Streamlit Cloud** (gratuito su [share.streamlit.io](https://share.streamlit.io))
3. **GitHub Personal Access Token** per la persistenza dei dati

### Setup Passo-Passo

#### 1. Preparazione Repository GitHub

```bash
# Inizializza git nel progetto (se non già fatto)
git init
git add .
git commit -m "Initial commit"

# Collega al repository remoto
git remote add origin https://github.com/TUO_USERNAME/TUO_REPO.git
git branch -M main
git push -u origin main
```

#### 2. Creazione GitHub Personal Access Token

1. Vai su GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Clicca "Generate new token (classic)"
3. Imposta:
   - **Note**: `Streamlit Planning App`
   - **Expiration**: `No expiration` (o scegli una durata)
   - **Scopes**: Seleziona `repo` (accesso completo ai repository)
4. Genera il token e **copialo** (non potrai rivederlo!)

#### 3. Deploy su Streamlit Cloud

1. Vai su [share.streamlit.io](https://share.streamlit.io)
2. Clicca "New app"
3. Seleziona:
   - **Repository**: il tuo repository GitHub
   - **Branch**: `main`
   - **Main file path**: `main.py`
4. Clicca "Advanced settings"
5. In **Secrets**, aggiungi:

```toml
GITHUB_TOKEN = "ghp_tuo_token_qui"
GITHUB_REPO = "TUO_USERNAME/TUO_REPO"
GITHUB_BRANCH = "main"
```

6. Clicca "Deploy!"

### 🔄 Come Funziona la Persistenza

L'applicazione salva automaticamente le configurazioni (priorità e risorse) su GitHub:

- **File salvati**: `config_priorities.json` e `config_resources.json`
- **Modalità**: I file vengono salvati nel repository GitHub
- **Backup locale**: Viene mantenuta anche una copia locale come fallback
- **Auto-save**: I dati vengono salvati automaticamente quando si genera il programma
- **Salvataggio manuale**: Usa il pulsante "Salva Configurazioni"

### 📁 Struttura File

```
.
├── main.py                    # Applicazione principale
├── github_storage.py          # Modulo per gestione GitHub
├── requirements.txt           # Dipendenze Python
├── logo_impj.png             # Logo aziendale
├── config_priorities.json    # Configurazione priorità (salvato su GitHub)
├── config_resources.json     # Configurazione risorse (salvato su GitHub)
├── .streamlit/
│   └── config.toml           # Configurazione Streamlit
├── .gitignore                # File da escludere da Git
└── README.md                 # Questo file
```

### 🔧 Sviluppo Locale

Per testare l'applicazione localmente:

```bash
# Installa le dipendenze
pip install -r requirements.txt

# Crea file secrets locale (NON committare questo file!)
mkdir .streamlit
touch .streamlit/secrets.toml

# Aggiungi i tuoi secrets in .streamlit/secrets.toml:
# GITHUB_TOKEN = "ghp_..."
# GITHUB_REPO = "username/repo"
# GITHUB_BRANCH = "main"

# Avvia l'applicazione
streamlit run main.py
```

### ⚠️ Note Importanti

1. **Mai committare il token**: Il file `.streamlit/secrets.toml` è in `.gitignore`
2. **Fallback locale**: Se GitHub non è configurato, l'app funziona comunque in modalità locale
3. **Sincronizzazione**: Le modifiche vengono salvate come commit su GitHub
4. **Rate limits**: GitHub ha limiti di API (5000 richieste/ora per utenti autenticati)

### 🐛 Troubleshooting

**GitHub non connesso?**
- Verifica che il token sia valido
- Controlla i permessi del token (deve avere accesso `repo`)
- Verifica il formato `GITHUB_REPO` sia `username/repository`

**File non salvati?**
- Controlla i logs dell'applicazione
- Verifica le permissions del repository
- Assicurati che il branch specificato esista

**Applicazione lenta?**
- Il primo salvataggio su GitHub può richiedere qualche secondo
- Considera di usare un branch dedicato per i dati

### 📞 Supporto

Per problemi o domande, contatta il team di sviluppo.

---

**Versione**: 2.1  
**Ultima modifica**: Dicembre 2024
