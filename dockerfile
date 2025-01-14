# Utilise une image Python légère
FROM python:3.9-slim

# Définir un répertoire de travail dans le conteneur
WORKDIR /app

# Copier les scripts dans le conteneur
COPY scripts /app/scripts

# Installer les dépendances Python (si nécessaire)
RUN pip install --no-cache-dir -r /app/scripts/requirements.txt

# Commande par défaut pour exécuter un script
ENTRYPOINT ["python3", "/app/scripts/test_script.py"]
