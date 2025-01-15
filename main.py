import json
import os
import logging
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional

class LLMPentest:
    def __init__(self, model_name: str = "llama3.1:latest"):
        self.model_name = model_name
        self.max_iterations = 15
        self.current_iteration = 0
        self.scan_results = []
        self.ollama_url = "http://host.docker.internal:11434"
        self.target = None
        self.pentest_type = None
        self.discovered_info = {}
        
        logging.basicConfig(
            filename=f'logs/pentest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)
        
        self._test_connection()

    def _test_connection(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            logging.info("Successfully connected to Ollama")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Ollama: {str(e)}")

    def execute_command(self, command: str) -> Dict:
        try:
            command = command.replace("{target}", self.target)
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
                timeout=300
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
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "command": command
            }

    def parse_llm_response(self, llm_text: str) -> Dict:
        try:
            # Chercher un JSON valide
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    json_str = llm_text[json_start:json_end]
                    json_data = json.loads(json_str)
                    if all(k in json_data for k in ["analysis", "commands"]):
                        # S'assurer que les commandes ont les bons paramètres
                        fixed_commands = []
                        for cmd in json_data["commands"]:
                            cmd = cmd.replace("{target}", self.target)  # Remplacer {target} par l'IP
                            # Correction des commandes spécifiques
                            if cmd.startswith("gobuster"):
                                if "dir" not in cmd:
                                    cmd = cmd.replace("gobuster", "gobuster dir")
                                if "-w" not in cmd:
                                    cmd += " -w /usr/share/wordlists/dirb/common.txt"
                            elif cmd.startswith("nikto"):
                                if "-h" not in cmd:
                                    cmd += f" -h {self.target}"
                            fixed_commands.append(cmd)
                        json_data["commands"] = fixed_commands
                        return json_data
                except json.JSONDecodeError:
                    pass

            # Si pas de JSON valide, extraire les commandes du texte
            commands = []
            analysis = "Analyse automatique des résultats"
            for line in llm_text.split('\n'):
                if any(cmd in line.lower() for cmd in ['nmap', 'nikto', 'gobuster', 'whatweb', 'wfuzz', 'hydra']):
                    cmd = line.strip().replace("{target}", self.target)
                    # Appliquer les mêmes corrections
                    if "gobuster" in cmd and "dir" not in cmd:
                        cmd = cmd.replace("gobuster", "gobuster dir")
                        if "-w" not in cmd:
                            cmd += " -w /usr/share/wordlists/dirb/common.txt"
                    elif "nikto" in cmd and "-h" not in cmd:
                        cmd += f" -h {self.target}"
                    commands.append(cmd)

            return {
                "analysis": analysis,
                "commands": commands,
                "continue": True,
                "interesting_findings": []
            }

        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return {
                "analysis": f"Erreur de parsing: {str(e)}",
                "commands": [],
                "continue": True,
                "interesting_findings": []
            }

    def enhance_pentest_prompt(self, target: str, iteration_data: Optional[Dict] = None) -> str:
        base_prompt = f'''Tu es un expert en pentest qui analyse cette cible : {target}
Type de pentest : {self.pentest_type.upper()}

CONTEXTE:
- Itération : {self.current_iteration + 1}/{self.max_iterations}
- Phase : {"Reconnaissance" if self.current_iteration == 0 else "Énumération avancée" if self.current_iteration < 5 else "Exploitation"}
- Découvertes précédentes : {json.dumps(self.discovered_info, indent=2)}

STRATÉGIE DE TEST PROGRESSIVE:
Phase 1 - Reconnaissance:
- Scan des ports et services
- Identification des technologies
- Découverte de base des fichiers/dossiers

Phase 2 - Énumération avancée:
- Tests de vulnérabilités connues
- Recherche de fichiers sensibles avec différentes wordlists
- Analyse des en-têtes de sécurité
- Test des méthodes HTTP
- Énumération des versions précises

Phase 3 - Exploitation:
- Tests d\'injection SQL
- Test des failles d\'authentification
- Exploitation des vulnérabilités trouvées
- Élévation de privilèges

COMMANDES DISPONIBLES ET EXEMPLES:
Reconnaissance:
- nmap -sV -sC -p- {target}
- nmap -A -T4 -p- {target}
- whatweb -a 3 {target}
- curl -I -X OPTIONS {target}

Énumération web:
- nikto -h http://{target} -C all -Tuning 123457
- gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/big.txt -x php,txt,html,bak
- wfuzz -c -z file,/usr/share/wordlists/dirb/common.txt --hc 404 http://{target}/FUZZ
- dirb http://{target} /usr/share/wordlists/dirb/common.txt -X .php,.txt,.bak

Tests spécifiques:
- sqlmap -u "http://{target}/index.php" --batch --forms --dbs
- hydra -L /usr/share/wordlists/user.txt -P /usr/share/wordlists/pass.txt {target} http-post-form
- curl -X TRACE {target}
- nmap --script=vuln {target}

FORMAT DE RÉPONSE REQUIS:
{{
  "analysis": "Description détaillée des découvertes et de leur impact",
  "commands": ["commande1", "commande2"],
  "continue": true,
  "interesting_findings": ["découverte1", "découverte2"],
  "next_phase": "Description de la prochaine phase de tests"
}}

IMPORTANT:
- Adapte tes tests selon les découvertes précédentes
- Utilise des wordlists variées
- Teste tous les services découverts
- Vérifie les vulnérabilités connues
- Augmente progressivement l\'intensité des tests'''

        if iteration_data:
            base_prompt += f'''

RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS:
{iteration_data.get('error', '')}

        return base_prompt

        if iteration_data:
            base_prompt += f"""

RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS:
{iteration_data.get('error', '')}"""

        return base_prompt

IMPORTANT:
- Toujours commencer par un scan de base
- Adapter les commandes suivantes selon les résultats
- Utilisez les commandes exactement comme dans les exemples
- Ne modifiez pas la structure du JSON'''

        if iteration_data:
            base_prompt += f'''

RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS:
{iteration_data.get('error', '')}"""

        return base_prompt
        if iteration_data:
            base_prompt += f"""
RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS:
{iteration_data.get('error', '')}
'''
        return base_prompt

    def execute_llm_query(self, prompt: str) -> Dict:
        try:
            print("\n⌛ Analyse en cours...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2048,
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            
            llm_text = response.json().get('response', '')
            logging.info(f"Got response of length: {len(llm_text)}")
            
            return self.parse_llm_response(llm_text)
                
        except Exception as e:
            logging.error(f"Error in execute_llm_query: {str(e)}")
            return {
                "analysis": f"Erreur : {str(e)}",
                "commands": [],
                "continue": True,
                "interesting_findings": []
            }

    def pentest(self, target: str) -> Dict:
        self.target = target
        logging.info(f"Starting pentest for target: {target}")
        print(f"Starting pentest for target: {target}")
        
        iteration_data = None
        all_findings = []
        
        while self.current_iteration < self.max_iterations:
            try:
                llm_response = self.execute_llm_query(
                    self.enhance_pentest_prompt(target, iteration_data)
                )
                
                if not llm_response["commands"]:
                    print("⚠️ Aucune commande générée")
                    break
                
                print("\n📝 Analyse :")
                print(llm_response["analysis"])
                
                if llm_response.get("interesting_findings"):
                    print("\n🎯 Découvertes :")
                    for finding in llm_response["interesting_findings"]:
                        print(f"- {finding}")
                        all_findings.append(finding)

                results = []
                for cmd in llm_response["commands"]:
                    result = self.execute_command(cmd)
                    results.append(result)
                    if result["success"]:
                        self.discovered_info[cmd] = result["output"]

                if not llm_response.get("continue", True):
                    print("\n✅ Pentest terminé!")
                    break
                
                iteration_data = {
                    "output": "\n".join(r["output"] for r in results if r["success"]),
                    "error": "\n".join(r["error"] for r in results if r["error"])
                }
                
            except Exception as e:
                logging.error(f"Error in iteration {self.current_iteration + 1}: {str(e)}")
                print(f"\n⚠️ Erreur : {str(e)}")
                break
            
            self.current_iteration += 1
            if self.current_iteration < self.max_iterations:
                print(f"\n🔄 Phase {self.current_iteration + 1}/{self.max_iterations}")
        
        return {
            "target": target,
            "iterations": self.current_iteration + 1,
            "findings": all_findings,
            "discovered_info": self.discovered_info
        }

    def generate_report(self, final_report: Dict) -> str:
        report = f'''# 🔒 Rapport de Pentest Automatisé
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📌 Informations
- Cible : {final_report['target']}
- Type : {self.pentest_type.upper()}
- Phases : {final_report['iterations']}

## 🎯 Découvertes
'''
        for finding in final_report['findings']:
            report += f"- {finding}\n"
        
        report += "\n## 📋 Détails des commandes\n"
        for cmd, output in final_report['discovered_info'].items():
            report += f"\n### `{cmd}`\n```\n{output}\n```\n"
        
        return report

    def save_report(self, report: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/pentest_report_{timestamp}.md"
        os.makedirs("results", exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n📝 Rapport sauvegardé dans : {filename}")
        
        print("\n📊 Résumé du rapport :")
        print("=" * 50)
        print(report)
        print("=" * 50)

if __name__ == "__main__":
    print("🔒 Assistant de Pentest Automatique")
    print("----------------------------------")
    
    try:
        pentester = LLMPentest()
        
        print("\n📋 Type de pentest disponibles :")
        print("1. Web (Applications Web)")
        print("2. Réseau/Serveur")
        
        while True:
            choice = input("\n🔍 Choisissez le type de pentest (1/2) : ")
            if choice in ['1', '2']:
                pentester.pentest_type = 'web' if choice == '1' else 'network'
                break
            print("❌ Choix invalide. Veuillez choisir 1 ou 2.")
        
        target = os.getenv('TARGET_IP', '172.18.0.2')
        print(f"\n🎯 Cible : {target}")
        print(f"🔨 Type : {pentester.pentest_type.upper()}")
        
        results = pentester.pentest(target)
        report = pentester.generate_report(results)
        pentester.save_report(report)
        
    except Exception as e:
        print(f"\n❌ Erreur : {str(e)}")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)