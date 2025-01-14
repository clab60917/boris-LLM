import subprocess
import os
import shutil

# Chemins des répertoires
SCRIPTS_DIR = "scripts"
RESULTS_DIR = "results"

# Interagir avec Ollama pour générer un script
def query_llama(prompt):
    result = subprocess.run(
        ["ollama", "generate", "--prompt", prompt],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# Enregistrer un script dans le répertoire Docker
def save_script(script_content, filename="test_script.py"):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    filepath = os.path.join(SCRIPTS_DIR, filename)
    with open(filepath, "w") as file:
        file.write(script_content)
    return filepath

# Exécuter le conteneur Docker avec le script
def execute_script_in_docker():
    result = subprocess.run(
        ["docker", "run", "--rm", "python-script-runner"],
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr

# Vérifier les tests
def run_tests(output):
    # Exemple simple de test
    return "Success" in output

def main():
    prompt = "Écrire un script Python qui additionne deux nombres et affiche le résultat"
    iteration = 0

    while True:
        print(f"--- Iteration {iteration} ---")
        
        # Générer le script via Ollama
        script = query_llama(prompt)
        print(f"Script généré :\n{script}")
        
        # Enregistrer le script
        save_script(script)
        
        # Exécuter le script dans Docker
        stdout, stderr = execute_script_in_docker()
        print(f"Résultat :\n{stdout}\nErreur :\n{stderr}")

        # Tester le résultat
        if stderr:
            prompt = f"Le script suivant a échoué :\n{script}\nErreur : {stderr}\nCorrige le script."
        elif run_tests(stdout):
            print("Succès ! Le script a passé tous les tests.")
            break
        else:
            prompt = f"Le script suivant n'a pas passé les tests :\n{script}\nSortie : {stdout}\nCorrige le script."
        
        iteration += 1

if __name__ == "__main__":
    main()
