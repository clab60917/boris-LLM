import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
import requests

class LLMPentest:
    def __init__(self, model_name: str = "llama3.1:latest"):
        self.model_name = model_name
        self.max_iterations = 15
        self.current_iteration = 0
        self.scan_results: List[Dict] = []
        self.ollama_url = "http://host.docker.internal:11434"
        self.target = None
        self.pentest_type = None  # 'web' ou 'network'
        self.discovered_info = {}
        
        # Configuration du logging
        logging.basicConfig(
            filename=f'logs/pentest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)
        
        self._test_connection()
    
    def generate_report(self) -> str:
        """Génère un rapport détaillé du pentest"""
        report = f"""
# 🔒 Rapport de Pentest Automatisé
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📌 Informations générales
- Cible : {self.target}
- Type de pentest : {self.pentest_type.upper()}
- Nombre de phases exécutées : {self.current_iteration}

## 🛠️ Commandes exécutées et résultats
"""
        for command, output in self.discovered_info.items():
            report += f"\n### {command}\n"
            report += "```\n"
            report += output[:1000] + "..." if len(output) > 1000 else output
            report += "\n```\n"

        report += "\n## 🎯 Vulnérabilités potentielles détectées\n"
        # Analyse des résultats pour détecter les vulnérabilités
        for output in self.discovered_info.values():
            if "vulnerability" in output.lower() or "warning" in output.lower() or "cve" in output.lower():
                vulns = [line for line in output.split('\n') 
                        if any(word in line.lower() 
                              for word in ["vulnerability", "warning", "cve", "exploit", "critical", "high"])]
                for vuln in vulns:
                    report += f"- {vuln}\n"

        return report

    def save_report(self, report: str):
        """Sauvegarde le rapport dans un fichier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/pentest_report_{timestamp}.md"
        os.makedirs("results", exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n📝 Rapport sauvegardé dans : {filename}")
        
        # Afficher aussi le rapport dans la console
        print("\n📊 Résumé du rapport :")
        print("=" * 50)
        print(report)
        print("=" * 50)

    def _test_connection(self):
        """Test la connexion à Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            logging.info("Successfully connected to Ollama")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Ollama: {str(e)}")

    def execute_command(self, command: str) -> Dict:
        """Exécute une commande de pentest de manière sécurisée"""
        logging.info(f"Executing command: {command}")
        try:
            # Liste des commandes autorisées
            allowed_commands = ['nmap', 'nikto', 'gobuster', 'whatweb', 'wfuzz', 'hydra', 'enum4linux', 'dnsrecon', 'sqlmap', 'curl']
            command_base = command.split()[0]
            
            if command_base not in allowed_commands:
                return {
                    "success": False,
                    "output": f"Command not allowed: {command_base}",
                    "error": "Security restriction"
                }

            print(f"\n📋 Résultat de : {command}")
            print("=" * 50)
            
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.stdout:
                print(result.stdout)
            
            if result.stderr and result.returncode != 0:
                print(f"⚠️  Erreurs/Warnings:")
                print(result.stderr)
            
            print("=" * 50)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
                "command": command
            }
        except subprocess.TimeoutExpired:
            print("❌ Commande interrompue (timeout)")
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 5 minutes",
                "command": command
            }
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "command": command
            }

    def parse_llm_response(self, llm_text: str) -> Dict:
        """Parse la réponse du LLM pour extraire les commandes et l'analyse"""
        try:
            # Chercher un JSON valide
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    json_str = llm_text[json_start:json_end]
                    json_data = json.loads(json_str)
                    if all(k in json_data for k in ["commands", "analysis", "continue"]):
                        return json_data
                except json.JSONDecodeError:
                    pass

            # Si pas de JSON valide, extraire les commandes du texte
            commands = []
            analysis = "Analyse automatique des résultats"
            for line in llm_text.split('\n'):
                if line.strip().startswith(('nmap', 'nikto', 'gobuster', 'whatweb', 'ping')):
                    commands.append(line.strip())

            return {
                "commands": commands,
                "analysis": analysis,
                "continue": True
            }

        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return {
                "commands": [],
                "analysis": f"Erreur de parsing: {str(e)}",
                "continue": True
            }

    def enhance_pentest_prompt(self, target: str, iteration_data: Optional[Dict] = None) -> str:
        """Améliore le prompt avec le contexte du pentest"""
        current_phase = "Reconnaissance" if self.current_iteration == 0 else "Énumération" if self.current_iteration < 5 else "Test de vulnérabilités"
        
        base_prompt = f'''Tu es un expert en pentest qui doit analyser cette cible : {target}
Type de pentest : {self.pentest_type.upper()}

CONTEXTE ACTUEL:
- Itération : {self.current_iteration + 1}/{self.max_iterations}
- Phase : {current_phase}
- Informations découvertes : {json.dumps(self.discovered_info, indent=2)}

'''

        if self.pentest_type == "web":
            base_prompt += """INSTRUCTIONS PRÉCISES (WEB):
1. Pour la phase de reconnaissance initiale, utilise :
   - nmap pour le scan de ports web : "nmap -sV -sC -p 80,443,8080,8443 {target}"
   - whatweb pour l'identification web : "whatweb {target}"
   - curl pour les en-têtes : "curl -I http://{target}"

2. Pour la phase d'énumération web, utilise :
   - gobuster pour la découverte de répertoires : "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt"
   - nikto pour le scan de vulnérabilités : "nikto -h http://{target}"
   - wfuzz pour le fuzzing de paramètres

3. Pour le test de vulnérabilités web :
   - sqlmap pour les injections SQL
   - hydra pour les formulaires de login
   - tests XSS et CSRF
   - LFI/RFI tests"""

        else:  # network
            base_prompt += """INSTRUCTIONS PRÉCISES (RÉSEAU/SERVEUR):
1. Pour la phase de reconnaissance initiale, utilise :
   - nmap complet : "nmap -sV -sC -p- {target}"
   - Service enumeration : "nmap -sV --version-intensity 5 {target}"
   - OS detection : "nmap -O {target}"

2. Pour la phase d'énumération serveur :
   - enum4linux pour SMB : "enum4linux -a {target}"
   - Scan UDP : "nmap -sU -p- {target}"
   - DNS enumeration : "dnsrecon -d {target}"

3. Pour les tests de vulnérabilités réseau :
   - Recherche de vulnérabilités : "nmap --script vuln {target}"
   - Test des services trouvés (FTP, SSH, SMB, etc.)
   - Brute force si nécessaire avec hydra

FORMAT DE RÉPONSE REQUIS (EXEMPLE):
{{
    "commands": [
        "nmap -sV -sC -p- {target}",
        "whatweb {target}"
    ],
    "analysis": "Scan initial pour détecter les services et versions",
    "continue": true
}}

IMPORTANT: Commence TOUJOURS par la reconnaissance de base avant de passer aux tests plus avancés.
N'oublie pas que DVWA est une application web vulnérable, concentre-toi sur les vulnérabilités web courantes.'''

        if iteration_data:
            base_prompt += f'''

RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS PRÉCÉDENTES:
{iteration_data.get('error', 'Aucune')}"""

        return base_prompt

    def execute_llm_query(self, prompt: str) -> Dict:
        """Exécute une requête vers le LLM"""
        try:
            logging.info("Sending request to Ollama...")
            print("\n⌛ Analyse en cours...")
            
            context = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2048,
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=context,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            llm_text = response_data.get('response', '')
            logging.info(f"Got response of length: {len(llm_text)}")
            
            return self.parse_llm_response(llm_text)
                
        except Exception as e:
            logging.error(f"Error in execute_llm_query: {str(e)}")
            return {
                "commands": [],
                "analysis": f"Erreur pendant la génération: {str(e)}",
                "continue": True
            }

    def pentest(self, target: str) -> Dict:
        """Point d'entrée principal du processus de pentest"""
        self.target = target
        logging.info(f"Starting pentest for target: {target}")
        
        iteration_data = None
        
        while self.current_iteration < self.max_iterations:
            try:
                # Génération des commandes
                enhanced_prompt = self.enhance_pentest_prompt(target, iteration_data)
                llm_response = self.execute_llm_query(enhanced_prompt)
                
                if not llm_response["commands"]:
                    print("⚠️ Aucune commande générée")
                    break
                
                # Exécution des commandes
                results = []
                for cmd in llm_response["commands"]:
                    result = self.execute_command(cmd)
                    results.append(result)
                    
                    if result["success"]:
                        # Mise à jour des informations découvertes
                        self.discovered_info[cmd] = result["output"]
                
                # Analyse des résultats
                if llm_response.get("analysis"):
                    print("\n📝 Analyse :")
                    print(llm_response["analysis"])
                
                # Décision de continuer
                if not llm_response.get("continue", True):
                    print("\n✨ Pentest terminé!")
                    break
                
                iteration_data = {
                    "output": "\n".join(r["output"] for r in results if r["success"]),
                    "error": "\n".join(r["error"] for r in results if r["error"])
                }
                
                self.current_iteration += 1
                if self.current_iteration < self.max_iterations:
                    print(f"\n🔄 Phase {self.current_iteration + 1}/{self.max_iterations}")
                
            except Exception as e:
                logging.error(f"Error in iteration {self.current_iteration + 1}: {str(e)}")
                print(f"\n⚠️ Erreur : {str(e)}")
                break

        # Générer et sauvegarder le rapport
        report = self.generate_report()
        self.save_report(report)
        
        return {
            "target": target,
            "iterations": self.current_iteration + 1,
            "discovered_info": self.discovered_info,
            "final_analysis": llm_response.get("analysis", "")
        }

if __name__ == "__main__":
    import sys
    import os
    print("🔒 Assistant de Pentest Automatique")
    print("----------------------------------")
    
    try:
        pentester = LLMPentest()
        
        # Choix du type de pentest
        while True:
            print("\n📋 Type de pentest disponibles :")
            print("1. Web (Applications Web)")
            print("2. Réseau/Serveur")
            choice = input("\n🔍 Choisissez le type de pentest (1/2) : ")
            if choice in ['1', '2']:
                pentester.pentest_type = 'web' if choice == '1' else 'network'
                break
            print("❌ Choix invalide. Veuillez choisir 1 ou 2.")
        
        # Sélection de la cible
        target = sys.argv[1] if len(sys.argv) > 1 else os.getenv('TARGET_IP', '172.18.0.2')
        
        print(f"\n🎯 Cible : {target}")
        print(f"🔨 Type : {pentester.pentest_type.upper()}")
        
        print(f"\n⚙️ Démarrage du pentest sur {target}...\n")
        results = pentester.pentest(target)
        
        print("\n📊 Résultats finaux :")
        print(f"✨ Nombre de phases : {results['iterations']}")
        print(f"🎯 Cible : {results['target']}")
        
        if results['final_analysis']:
            print("\n📝 Analyse finale :")
            print(results['final_analysis'])
        
        print("\n💾 Les résultats détaillés sont dans les logs")
        
    except Exception as e:
        print(f"\n❌ Erreur : {str(e)}")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)