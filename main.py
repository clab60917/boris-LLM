import json
import os
import logging
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress
from rich import print as rprint

class LLMPentest:
    def __init__(self, model_name: str = "llama3.1:latest"):
        self.model_name = model_name
        self.max_iterations = 20
        self.current_iteration = 0
        self.scan_results = []
        self.ollama_url = "http://host.docker.internal:11434"
        self.target = None
        self.target_port = None
        self.pentest_type = None
        self.discovered_info = {}
        self.console = Console()
        
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
            command = command.replace("{port}", str(self.target_port))
            
            allowed_commands = [
                'nmap', 'nikto', 'gobuster', 'whatweb', 'wfuzz', 
                'curl', 'wget', 'dirb', 'sqlmap'
            ]
            
            command_base = command.split()[0]
            
            if command_base not in allowed_commands:
                return {
                    "success": False,
                    "output": f"Command not allowed: {command_base}",
                    "error": "Security restriction"
                }

            with self.console.status(f"[bold blue]Exécution de : {command}[/]"):
                result = subprocess.run(
                    command.split(),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            
            rprint(f"\n[cyan]📋 Résultat de : {command}[/]")
            rprint("=" * 50)
            
            if result.stdout:
                rprint(result.stdout)
            
            if result.stderr and result.returncode != 0:
                rprint(f"[yellow]⚠️  Erreurs/Warnings:[/]")
                rprint(result.stderr)
            
            rprint("=" * 50)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command execution timed out",
                "command": command
            }
        except Exception as e:
            rprint(f"[red]❌ Erreur : {str(e)}[/]")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "command": command
            }

    def parse_llm_response(self, llm_text: str) -> Dict:
        try:
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    json_str = llm_text[json_start:json_end]
                    json_data = json.loads(json_str)
                    if all(k in json_data for k in ["analysis", "commands"]):
                        fixed_commands = []
                        for cmd in json_data["commands"]:
                            cmd = cmd.replace("{target}", self.target)
                            cmd = cmd.replace("{port}", str(self.target_port))
                            
                            # Appliquer les corrections spécifiques aux commandes
                            if cmd.startswith("gobuster"):
                                if "dir" not in cmd:
                                    cmd = cmd.replace("gobuster", "gobuster dir")
                                if "-w" not in cmd:
                                    cmd += " -w /usr/share/wordlists/common.txt"
                            elif cmd.startswith("nikto"):
                                if "-h" not in cmd:
                                    cmd += f" -h {self.target}:{self.target_port}"
                            elif cmd.startswith("wfuzz"):
                                if "-w" not in cmd:
                                    cmd += " -w /usr/share/wordlists/common.txt"
                                cmd = cmd.replace("FUZZ", f":{self.target_port}/FUZZ")
                            
                            fixed_commands.append(cmd)
                        
                        json_data["commands"] = fixed_commands
                        return json_data
                except json.JSONDecodeError:
                    pass

            commands = []
            analysis = "Analyse automatique des résultats"
            for line in llm_text.split('\n'):
                if any(cmd in line.lower() for cmd in [
                    'nmap', 'nikto', 'gobuster', 'whatweb', 'wfuzz', 
                    'curl', 'dirb', 'sqlmap'
                ]):
                    cmd = line.strip()
                    cmd = cmd.replace("{target}", self.target)
                    cmd = cmd.replace("{port}", str(self.target_port))
                    commands.append(self._fix_command(cmd))

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

    def _fix_command(self, cmd: str) -> str:
        cmd_parts = cmd.split()
        tool = cmd_parts[0]
        cmd = cmd.replace("{port}", str(self.target_port))

        if tool == "gobuster" and "dir" not in cmd:
            cmd = f"gobuster dir {' '.join(cmd_parts[1:])}"
        if "-w" not in cmd and tool in ["gobuster", "wfuzz"]:
            cmd += " -w /usr/share/wordlists/common.txt"
        if tool == "nikto" and "-h" not in cmd:
            cmd += f" -h {self.target}:{self.target_port}"
        if tool == "nmap" and "-p" not in cmd:
            cmd += f" -p {self.target_port}"
        if tool in ["curl", "whatweb"] and ":" not in cmd:
            cmd = cmd.replace(self.target, f"{self.target}:{self.target_port}")

        return cmd
    def enhance_pentest_prompt(self, target: str, iteration_data: Optional[Dict] = None) -> str:
        current_phase = "Reconnaissance" if self.current_iteration < 5 else \
                       "Énumération approfondie" if self.current_iteration < 10 else \
                       "Test des vulnérabilités" if self.current_iteration < 15 else "Exploitation"

        base_prompt = f'''Tu es un expert en pentest qui analyse cette cible : {target}:{self.target_port}
Type de test : {self.pentest_type.upper()}

CONTEXTE:
- Itération : {self.current_iteration + 1}/{self.max_iterations}
- Phase actuelle : {current_phase}
- Découvertes précédentes : {json.dumps(self.discovered_info, indent=2)}

STRATÉGIE DE TEST PROGRESSIVE:

Phase 1 - Reconnaissance (Iterations 1-5):
- Scan des ports ouverts autour du port {self.target_port}
- Identification des services et versions
- Découverte des technologies web
- Analyse initiale de la surface d'attaque

Phase 2 - Énumération approfondie (Iterations 6-10):
- Découverte approfondie du contenu web
- Analyse des réponses HTTP
- Test des méthodes HTTP autorisées
- Recherche de fichiers sensibles

Phase 3 - Test des vulnérabilités (Iterations 11-15):
- Test des injections SQL
- Recherche de XSS potentiels
- Vérification des paramètres web
- Test des formulaires découverts
- Analyse des points d'authentification

Phase 4 - Exploitation (Iterations 16-20):
- Exploitation des vulnérabilités trouvées
- Tests de validation des failles
- Documentation des problèmes de sécurité

COMMANDES DISPONIBLES:

Reconnaissance:
nmap -sV -p{self.target_port} {target}
nmap -A -p{self.target_port} {target}
whatweb http://{target}:{self.target_port}
curl -I http://{target}:{self.target_port}

Énumération Web:
nikto -h {target}:{self.target_port}
gobuster dir -u http://{target}:{self.target_port}
wfuzz -c -z file,/usr/share/wordlists/common.txt http://{target}:{self.target_port}/FUZZ
dirb http://{target}:{self.target_port}

Test des vulnérabilités:
sqlmap -u "http://{target}:{self.target_port}" --batch --forms
curl -X OPTIONS http://{target}:{self.target_port}

FORMAT DE RÉPONSE REQUIS:
{{
  "analysis": "Description détaillée des découvertes",
  "commands": ["commande1", "commande2"],
  "continue": true,
  "interesting_findings": ["découverte1", "découverte2"]
}}

IMPORTANT:
- Adapte les commandes en fonction des réponses précédentes
- Concentre-toi sur le port {self.target_port} et les ports proches
- Évite les tests destructifs
- Documente chaque découverte importante'''

        if iteration_data:
            base_prompt += f'''

RÉSULTATS PRÉCÉDENTS:
{iteration_data.get('output', '')}

ERREURS:
{iteration_data.get('error', '')}'''

        return base_prompt

    def execute_llm_query(self, prompt: str) -> Dict:
        try:
            rprint("\n[blue]⌛ Analyse en cours...[/]")
            
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

    def pentest(self, target: str, port: int) -> Dict:
        self.target = target
        self.target_port = port
        self.current_iteration = 0  # Reset iteration counter for new target
        self.discovered_info = {}   # Reset discoveries for new target
        
        logging.info(f"Starting pentest for target: {target}:{port}")
        rprint(f"[green]🎯 Starting pentest for target: {target}:{port}[/]")
        
        iteration_data = None
        all_findings = []
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Running pentest phases...", total=self.max_iterations)
            
            while self.current_iteration < self.max_iterations:
                try:
                    llm_response = self.execute_llm_query(
                        self.enhance_pentest_prompt(target, iteration_data)
                    )
                    
                    if not llm_response["commands"]:
                        rprint("[yellow]⚠️ Aucune commande générée[/]")
                        break
                    
                    rprint("\n[cyan]📝 Analyse :[/]")
                    rprint(llm_response["analysis"])
                    
                    if llm_response.get("interesting_findings"):
                        rprint("\n[green]🎯 Découvertes :[/]")
                        for finding in llm_response["interesting_findings"]:
                            rprint(f"[green]- {finding}[/]")
                            all_findings.append(finding)

                    results = []
                    for cmd in llm_response["commands"]:
                        result = self.execute_command(cmd)
                        results.append(result)
                        if result["success"]:
                            self.discovered_info[cmd] = result["output"]

                    if not llm_response.get("continue", True):
                        rprint("\n[green]✅ Pentest terminé![/]")
                        break
                    
                    iteration_data = {
                        "output": "\n".join(r["output"] for r in results if r["success"]),
                        "error": "\n".join(r["error"] for r in results if r["error"])
                    }
                    
                except Exception as e:
                    logging.error(f"Error in iteration {self.current_iteration + 1}: {str(e)}")
                    rprint(f"\n[red]⚠️ Erreur : {str(e)}[/red]")
                    break
                
                self.current_iteration += 1
                progress.update(task, advance=1)
                
                if self.current_iteration < self.max_iterations:
                    rprint(f"\n[blue]🔄 Phase {self.current_iteration + 1}/{self.max_iterations}[/]")
        
        return {
            "target": f"{target}:{port}",
            "iterations": self.current_iteration + 1,
            "findings": all_findings,
            "discovered_info": self.discovered_info
        }
    def generate_report(self, final_report: Dict) -> str:
        report = f'''# 🔒 Rapport de Pentest
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📌 Informations
- Cible : {final_report['target']}
- Phases exécutées : {final_report['iterations']}

## 🎯 Découvertes
'''
        if final_report['findings']:
            for finding in final_report['findings']:
                report += f"- {finding}\n"
        else:
            report += "Aucune découverte critique identifiée.\n"
        
        report += "\n## 🔍 Détails des Tests\n"
        
        phase_categories = {
            "Reconnaissance": ["nmap", "whatweb", "curl"],
            "Énumération": ["nikto", "gobuster", "wfuzz", "dirb"],
            "Tests de vulnérabilité": ["sqlmap"]
        }
        
        for phase_name, commands in phase_categories.items():
            report += f"\n### {phase_name}\n"
            phase_results = False
            
            for cmd, output in final_report['discovered_info'].items():
                if any(tool in cmd.lower() for tool in commands):
                    report += f"\n#### `{cmd}`\n```\n{output}\n```\n"
                    phase_results = True
            
            if not phase_results:
                report += "Aucun résultat pour cette phase.\n"
        
        return report

    def save_report(self, report: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/pentest_report_{timestamp}.md"
        os.makedirs("results", exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report)
        
        rprint(f"\n[green]📝 Rapport sauvegardé dans : {filename}[/]")
        rprint("\n[cyan]📊 Résumé du rapport :[/]")
        rprint("=" * 50)
        rprint(report)
        rprint("=" * 50)


if __name__ == "__main__":
    rprint("[cyan]🔒 Assistant de Pentest Automatique[/]")
    rprint("----------------------------------")
    
    try:
        pentester = LLMPentest()
        
        rprint("\n[cyan]📋 Modes disponibles :[/]")
        rprint("1. Mode Test (environnement Docker)")
        rprint("2. Mode Réel (IP externe)")
        
        while True:
            mode_choice = input("\n[cyan]🔍 Choisissez le mode (1/2) : [/]")
            if mode_choice in ['1', '2']:
                break
            rprint("[red]❌ Choix invalide. Veuillez choisir 1 ou 2.[/]")

        if mode_choice == '1':  # Mode Test
            rprint("\n[cyan]📋 Cibles disponibles :[/]")
            rprint("1. Target 1 (172.18.0.2:80)")
            rprint("2. Target 2 (172.18.0.4:80)")
            rprint("3. Les deux")
            
            while True:
                choice = input("\n[cyan]🔍 Choisissez la cible (1/2/3) : [/]")
                if choice in ['1', '2', '3']:
                    pentester.pentest_type = 'web'
                    break
                rprint("[red]❌ Choix invalide. Veuillez choisir 1, 2 ou 3.[/]")

            if choice == '1':
                target = os.getenv('TARGET1_IP', '172.18.0.2')
                results = pentester.pentest(target, 80)
                report = pentester.generate_report(results)
                pentester.save_report(report)
            
            elif choice == '2':
                target = os.getenv('TARGET2_IP', '172.18.0.4')
                results = pentester.pentest(target, 80)
                report = pentester.generate_report(results)
                pentester.save_report(report)
            
            else:  # Les deux cibles
                targets = [
                    (os.getenv('TARGET1_IP', '172.18.0.2'), 80),
                    (os.getenv('TARGET2_IP', '172.18.0.4'), 80)
                ]
                
                all_results = []
                for target, port in targets:
                    rprint(f"\n[green]🎯 Testing: {target}:{port}[/]")
                    results = pentester.pentest(target, port)
                    all_results.append(results)
                
                combined_report = "# 🔒 Rapport Multi-Cibles\n\n"
                for result in all_results:
                    report = pentester.generate_report(result)
                    combined_report += f"\n\n{'='*50}\n\n{report}"
                pentester.save_report(combined_report)

        else:  # Mode Réel
            while True:
                target_ip = input("\n[cyan]🎯 Entrez l'IP cible : [/]")
                if all(o.isdigit() and 0 <= int(o) <= 255 for o in target_ip.split('.')):
                    break
                rprint("[red]❌ IP invalide. Format attendu : xxx.xxx.xxx.xxx[/]")
            
            while True:
                try:
                    port = int(input("\n[cyan]🔍 Entrez le port (défaut: 80) : [/]") or "80")
                    if 1 <= port <= 65535:
                        break
                    rprint("[red]❌ Port invalide. Doit être entre 1 et 65535.[/]")
                except ValueError:
                    rprint("[red]❌ Port invalide. Entrez un nombre.[/]")
            
            pentester.pentest_type = 'web'
            results = pentester.pentest(target_ip, port)
            report = pentester.generate_report(results)
            pentester.save_report(report)
        
    except Exception as e:
        rprint(f"\n[red]❌ Erreur : {str(e)}[/]")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)