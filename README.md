# Boris-LLM

## Description
Boris-LLM est un assistant automatisé de pentest qui utilise l'intelligence artificielle pour effectuer des tests de pénétration de manière autonome. L'outil s'appuie sur un modèle de langage local (via Ollama) pour analyser progressivement une cible, choisir les tests appropriés, et générer des rapports détaillés.

## 🌟 Caractéristiques
- Tests automatisés et adaptatifs
- Analyse progressive et intelligente
- Support des tests Web et Réseau
- Rapports détaillés en Markdown
- Environnement isolé via Docker
- Intégration avec Ollama (LLM local)

## 🛠️ Prérequis
- Docker et Docker Compose
- Ollama installé et configurant sur la machine hôte
- Au moins 8 Go de RAM disponible (ici 32 pour un fonctionnement correct)
- Le modèle llama3.1:lastest chargé dans Ollama (benchmark en cours avec phi4-mini)

## 📦 Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/clab60917/boris-llm.git
cd boris-llm
```

2. S'assurer qu'Ollama est en cours d'exécution avec le modèle approprié :
```bash
ollama pull llama3.1:lastest
ollama run llama3.1:lastest
```

3. Construire l'environnement Docker :
```bash
docker-compose build
```

## 🚀 Utilisation

1. Démarrer les services :
```bash
docker-compose up -d
```

2. Lancer le pentester :
```bash
docker exec -it llm-pentest python3 main.py
```

3. Choisir le type de pentest :
   - Web (Applications Web)
   - Réseau/Serveur

4. Le système effectuera automatiquement :
   - Reconnaissance initiale
   - Énumération approfondie
   - Tests de vulnérabilités
   - Génération de rapport

## 📊 Structure du Projet
```
llm-pentester/
├── docker-compose.yml      # Configuration Docker
├── Dockerfile             # Configuration de l'environnement
├── requirements.txt       # Dépendances Python
├── main.py               # Script principal
├── logs/                 # Logs d'exécution
└── results/              # Rapports générés
```

## 🛡️ Outils Intégrés
- nmap
- nikto
- gobuster
- whatweb
- wfuzz
- hydra
- sqlmap
- dirb
- et plus encore...

## 📝 Format des Rapports
Les rapports sont générés au format Markdown et incluent :
- Informations sur la cible
- Découvertes majeures
- Détails des tests effectués
- Résultats des scans
- Vulnérabilités potentielles
- Recommandations

## ⚙️ Configuration

### Modification des Wordlists
Les wordlists par défaut sont situées dans :
```
/usr/share/wordlists/
```

### Ajout de Nouveaux Outils
1. Ajouter l'outil dans le Dockerfile
2. Ajouter la commande dans la liste `allowed_commands`
3. Mettre à jour le prompt LLM

## 🔐 Sécurité
- Tous les tests sont exécutés dans un conteneur Docker isolé
- Les permissions sont limitées
- Les commandes sont filtrées
- Les résultats sont stockés localement

## ⚠️ Avertissements
- Utilisez uniquement sur des systèmes que vous êtes autorisé à tester
- Certains tests peuvent être intrusifs
- Les performances dépendent de la puissance de la machine hôte
- Le modèle LLM peut nécessiter des ajustements

## 🐛 Résolution des Problèmes

### Erreurs Communes
1. **Ollama non accessible** :
   ```
   Could not connect to Ollama
   ```
   → Vérifier qu'Ollama est en cours d'exécution sur la machine hôte

2. **Erreurs de mémoire** :
   → Augmenter les ressources Docker allouées

3. **Commandes non trouvées** :
   → Vérifier l'installation des outils dans le Dockerfile

## 📈 Améliorations Futures
- [ ] Support de plus de types de tests
- [ ] Intégration de nouveaux outils
- [ ] Amélioration de l'analyse des résultats
- [ ] Interface Web
- [ ] Support de cibles multiples
- [ ] Rapports personnalisables

## 🤝 Contribution
Les contributions sont les bienvenues ! Pour contribuer :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commit vos changements
4. Push sur la branche
5. Créer une Pull Request

## 📄 Licence
Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## 👥 Contact
- Créé par : clab60917

## 🙏 Remerciements
- Équipe Ollama pour le LLM local