FROM python:3.9-slim-buster

# Installation des dépendances système de base
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    gnupg \
    wget \
    curl \
    git

# Ajout du dépôt Kali (pour certains outils de pentest)
RUN wget -q -O - https://archive.kali.org/archive-key.asc | apt-key add \
    && echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" >> /etc/apt/sources.list

# Installation des outils de pentest
RUN apt-get update && apt-get install -y \
    nmap \
    nikto \
    whatweb \
    wfuzz \
    sqlmap \
    dirb \
    gobuster \
    hydra \
    sslscan \
    dirbuster \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Création et configuration des répertoires pour wordlists
RUN mkdir -p /usr/share/wordlists
WORKDIR /usr/share/wordlists

# Téléchargement de wordlists de base
RUN wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
    && wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/big.txt \
    && wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/top-100.txt

# Configuration du projet
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Test des outils installés
RUN nmap --version \
    && whatweb --version \
    && gobuster version \
    && sqlmap --version

CMD ["python3", "main.py"]