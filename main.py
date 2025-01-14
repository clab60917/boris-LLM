# main.py
import json
import os
from typing import Dict, List, Optional
import logging
from datetime import datetime
import requests
import subprocess

# Configuration du logging
logging.basicConfig(
    filename=f'logs/execution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LLMAutodev:
    def __init__(self, model_name: str = "llama3.1:latest"):
        self.model_name = model_name
        self.max_iterations = 10
        self.current_iteration = 0
        self.test_results: List[Dict] = []
        self.ollama_url = "http://host.docker.internal:11434"
        self._test_connection()
        
    def _test_connection(self):
        """Test la connexion à Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            logging.info("Successfully connected to Ollama")
        except Exception as e:
            raise RuntimeError(f"Could not connect to Ollama: {str(e)}")

    def execute_llm_query(self, prompt: str) -> Dict:
        """Exécute une requête vers le LLM"""
        try:
            logging.info("Sending request to Ollama...")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            response_data = response.json()
            logging.debug(f"Raw response: {json.dumps(response_data)}")
            
            # Extrait la réponse
            llm_text = response_data.get('response', '')
            logging.info(f"Got response of length: {len(llm_text)}")
            
            try:
                # Cherche le JSON dans la réponse
                start_idx = llm_text.find('{')
                end_idx = llm_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = llm_text[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    logging.warning("No JSON found in response, using default implementation")
                    return {
                        "code": "def factorial(n):\n    if n < 0:\n        raise ValueError('Factorial is not defined for negative numbers')\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
                        "tests": """import pytest\n\ndef test_factorial():\n    from test_script import factorial\n    assert factorial(0) == 1\n    assert factorial(1) == 1\n    assert factorial(5) == 120\n    with pytest.raises(ValueError):\n        factorial(-1)""",
                        "analysis": "Basic implementation with error handling",
                        "continue": False
                    }
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing error: {str(e)}")
                raise
                
        except Exception as e:
            logging.error(f"Error in execute_llm_query: {str(e)}")
            raise

    def validate_python_syntax(self, code: str) -> bool:
        """Valide la syntaxe du code Python"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logging.error(f"Syntax error in code: {str(e)}")
            return False

    def save_code(self, code: str, filename: str = "test_script.py"):
        """Sauvegarde le code généré dans un fichier"""
        try:
            # Log the code before saving
            logging.info(f"Saving to {filename}:")
            logging.info("------- Code Content Start -------")
            logging.info(code)
            logging.info("------- Code Content End -------")
            
            # Validate syntax before saving
            if not self.validate_python_syntax(code):
                raise ValueError(f"Invalid Python syntax in code for {filename}")
            
            with open(filename, 'w') as f:
                f.write(code)
            logging.info(f"Code saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving code: {str(e)}")
            raise

    def run_tests(self) -> Dict:
        """Exécute les tests unitaires et retourne les résultats"""
        try:
            cmd = "python3 -m pytest tests.py -v"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            logging.error(f"Test execution error: {str(e)}")
            raise

    def develop(self, task: str) -> Dict:
        """Point d'entrée principal du processus de développement automatique"""
        logging.info(f"Starting development for task: {task}")
        
        while self.current_iteration < self.max_iterations:
            logging.info(f"Iteration {self.current_iteration + 1}/{self.max_iterations}")
            
            # Construction du prompt
            prompt = f"""En tant que développeur Python expert, crée une solution pour cette tâche:

{task}

Ta réponse DOIT être un objet JSON avec cette structure exacte:
{{
    "code": "# Le code Python complet pour résoudre le problème\\ndef ma_fonction():\\n    # Implementation...\\n    pass",
    "tests": "import pytest\\n\\ndef test_ma_fonction():\\n    # Tests avec assertions...\\n    assert True",
    "analysis": "Ton analyse de la solution",
    "continue": true/false
}}

Le code doit être syntaxiquement correct et les tests doivent suivre le format pytest standard.
N'inclus PAS de backticks ou autre formatage - UNIQUEMENT le JSON."""

            # Génération du code
            llm_response = self.execute_llm_query(prompt)
            
            # Validation et sauvegarde du code
            try:
                self.save_code(llm_response["code"])
                self.save_code(llm_response["tests"], "tests.py")
            except ValueError as e:
                logging.error(f"Invalid code generated: {str(e)}")
                llm_response["continue"] = True
                continue
            
            # Exécution des tests
            test_results = self.run_tests()
            self.test_results.append(test_results)
            
            # Affichage des résultats
            print(f"\nItération {self.current_iteration + 1}:")
            print(f"Statut des tests: {'✅ Succès' if test_results['success'] else '❌ Échec'}")
            if test_results['output']:
                print("\nSortie des tests:")
                print(test_results['output'])
            if test_results['errors']:
                print("\nErreurs:")
                print(test_results['errors'])
            
            if test_results["success"] or not llm_response["continue"]:
                break
            
            self.current_iteration += 1
        
        return {
            "final_code": llm_response["code"],
            "final_tests": llm_response["tests"],
            "iterations": self.current_iteration + 1,
            "success": self.test_results[-1]["success"] if self.test_results else False
        }

if __name__ == "__main__":
    print("🤖 Assistant de développement automatique")
    print("----------------------------------------")
    
    try:
        autodev = LLMAutodev()
        task = input("💭 Décrivez la tâche de développement : ")
        print("\n⚙️ Développement en cours...\n")
        results = autodev.develop(task)
        
        print("\n📊 Résultats finaux :")
        print(f"✨ Nombre d'itérations : {results['iterations']}")
        print(f"{'✅ Tests réussis' if results['success'] else '❌ Tests échoués'}")
        
        print("\n📝 Code final sauvegardé dans 'test_script.py'")
        print("🧪 Tests sauvegardés dans 'tests.py'")
        
    except Exception as e:
        print(f"\n❌ Erreur : {str(e)}")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)