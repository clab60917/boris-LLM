FROM kalilinux/kali-rolling

# Mise à jour du système
RUN apt-get update && apt-get upgrade -y

# Installation des dépendances Python et venv
RUN apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Installation des outils de pentest
RUN apt-get update && apt-get install -y \
    nmap \
    nikto \
    gobuster \
    whatweb \
    dirb \
    wfuzz \
    hydra \
    metasploit-framework \
    sqlmap \
    john \
    hashcat \
    wordlists \
    smbclient \
    enum4linux \
    dnsutils \
    ffuf \
    curl \
    wget \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Configuration du workspace
WORKDIR /app

# Création et activation de l'environnement virtuel
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installation des dépendances Python dans l'environnement virtuel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Pour éviter les problèmes de permissions
RUN chmod +x /app/main.py

CMD ["python3", "main.py"]