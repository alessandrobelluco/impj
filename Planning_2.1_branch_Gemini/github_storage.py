"""
Modulo per gestire il salvataggio e recupero di file JSON su GitHub.
Utilizzato per la persistenza dei dati in Streamlit Cloud.
"""

import json
import base64
import streamlit as st
from github import Github, GithubException


class GitHubStorage:
    """Gestisce il salvataggio e recupero di file JSON su un repository GitHub."""
    
    def __init__(self, token, repo_name, branch='main'):
        """
        Inizializza la connessione a GitHub.
        
        Args:
            token (str): Personal Access Token di GitHub
            repo_name (str): Nome del repository nel formato 'owner/repo'
            branch (str): Branch da utilizzare (default: 'main')
        """
        self.token = token
        self.repo_name = repo_name
        self.branch = branch
        self.github = None
        self.repo = None
        
    def connect(self):
        """Stabilisce la connessione con GitHub."""
        try:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(self.repo_name)
            return True
        except Exception as e:
            st.error(f"Errore connessione GitHub: {e}")
            return False
    
    def save_json(self, data, filename, commit_message=None):
        """
        Salva un dizionario Python come file JSON su GitHub.
        
        Args:
            data (dict/list): Dati da salvare
            filename (str): Nome del file (es: 'config_priorities.json')
            commit_message (str): Messaggio di commit (opzionale)
            
        Returns:
            bool: True se il salvataggio è riuscito, False altrimenti
        """
        if not self.repo:
            if not self.connect():
                return False
        
        try:
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
            
            if commit_message is None:
                commit_message = f"Update {filename}"
            
            # Verifica se il file esiste già
            try:
                contents = self.repo.get_contents(filename, ref=self.branch)
                # File esistente - aggiorna
                self.repo.update_file(
                    contents.path,
                    commit_message,
                    json_content,
                    contents.sha,
                    branch=self.branch
                )
            except GithubException as e:
                if e.status == 404:
                    # File non esiste - crea nuovo
                    self.repo.create_file(
                        filename,
                        commit_message,
                        json_content,
                        branch=self.branch
                    )
                else:
                    raise
            
            return True
            
        except Exception as e:
            st.error(f"Errore salvataggio {filename} su GitHub: {e}")
            return False
    
    def load_json(self, filename):
        """
        Carica un file JSON da GitHub.
        
        Args:
            filename (str): Nome del file da caricare
            
        Returns:
            dict/list: Dati caricati, None se il file non esiste o si verifica un errore
        """
        if not self.repo:
            if not self.connect():
                return None
        
        try:
            contents = self.repo.get_contents(filename, ref=self.branch)
            json_content = base64.b64decode(contents.content).decode('utf-8')
            return json.loads(json_content)
            
        except GithubException as e:
            if e.status == 404:
                # File non esiste ancora
                return None
            else:
                st.error(f"Errore caricamento {filename} da GitHub: {e}")
                return None
                
        except Exception as e:
            st.error(f"Errore parsing {filename}: {e}")
            return None
    
    def file_exists(self, filename):
        """
        Verifica se un file esiste nel repository.
        
        Args:
            filename (str): Nome del file da verificare
            
        Returns:
            bool: True se il file esiste, False altrimenti
        """
        if not self.repo:
            if not self.connect():
                return False
        
        try:
            self.repo.get_contents(filename, ref=self.branch)
            return True
        except GithubException:
            return False


def init_github_storage():
    """
    Inizializza il sistema di storage GitHub usando i secrets di Streamlit.
    
    Returns:
        GitHubStorage: Istanza configurata o None se i secrets non sono disponibili
    """
    try:
        # Leggi i secrets da Streamlit
        github_token = st.secrets.get("GITHUB_TOKEN")
        github_repo = st.secrets.get("GITHUB_REPO")
        github_branch = st.secrets.get("GITHUB_BRANCH", "main")
        
        if not github_token or not github_repo:
            st.warning("""
            ⚠️ Configurazione GitHub mancante.
            
            Per abilitare la persistenza dei dati:
            1. Vai su GitHub Settings > Developer settings > Personal access tokens
            2. Genera un nuovo token con permessi 'repo'
            3. In Streamlit Cloud, vai su App settings > Secrets
            4. Aggiungi:
               ```
               GITHUB_TOKEN = "your_token_here"
               GITHUB_REPO = "owner/repo-name"
               GITHUB_BRANCH = "main"
               ```
            """)
            return None
        
        storage = GitHubStorage(github_token, github_repo, github_branch)
        if storage.connect():
            return storage
        return None
        
    except Exception as e:
        st.error(f"Errore inizializzazione GitHub storage: {e}")
        return None
