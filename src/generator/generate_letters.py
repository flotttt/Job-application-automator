import os
import sys
import time
import json
import subprocess
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

INPUT_CSV = os.getenv("CSV_OUTPUT", "data/input/offres.csv")
OUTPUT_FOLDER = os.getenv("LETTERS_FOLDER", "data/output/letters")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
PROFILE_PATH = "data/candidate_profile.json"


class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    PURPLE = '\033[35m'
    END = '\033[0m'


def colored(text, color):
    return f"{color}{text}{Colors.END}"


def print_header():
    header_lines = [
        "╔══════════════════════════════════════════════════════════════════════╗",
        "║                                                                      ║",
        "║          ✍️  GÉNÉRATEUR DE LETTRES DE MOTIVATION  ✍️                 ║",
        "║                                                                      ║",
        "║              Powered by Ollama AI • Personnalisées                   ║",
        "║                                                                      ║",
        "╚══════════════════════════════════════════════════════════════════════╝"
    ]
    for line in header_lines:
        print(colored(line, Colors.PURPLE + Colors.BOLD))
    print()


def print_progress_bar(current, total, label="", bar_width=40):
    percentage = (current / total * 100) if total > 0 else 0
    filled_length = int(bar_width * current / total) if total > 0 else 0
    progress_bar = colored("█" * filled_length, Colors.GREEN) + colored("░" * (bar_width - filled_length), Colors.GRAY)

    print(f"\r  {progress_bar} {percentage:>5.1f}% | {current}/{total} {label}", end="", flush=True)


def check_ollama_available():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def load_candidate_profile():
    if not os.path.exists(PROFILE_PATH):
        print(colored("\n❌ ERREUR : Profil candidat non trouvé", Colors.RED + Colors.BOLD))
        print(colored(f"   Lance d'abord : python src/generator/setup_profile.py\n", Colors.YELLOW))
        sys.exit(1)

    with open(PROFILE_PATH, 'r', encoding='utf-8') as profile_file:
        return json.load(profile_file)


def select_relevant_projects(profile, job_description, max_projects=2):
    projects = profile.get('projets', [])
    if not projects:
        return []

    job_desc_lower = job_description.lower()
    scored_projects = []

    for project in projects:
        score = 0
        project_text = f"{project.get('nom', '')} {project.get('description', '')}".lower()

        keywords = ['react', 'next', 'node', 'java', 'spring', 'python', 'api', 'data', 'ia', 'test', 'docker',
                    'postgres']
        for keyword in keywords:
            if keyword in job_desc_lower and keyword in project_text:
                score += 1

        scored_projects.append((score, project))

    scored_projects.sort(reverse=True, key=lambda x: x[0])
    return [proj for score, proj in scored_projects[:max_projects]]


def create_prompt(job_offer, profile):
    relevant_projects = select_relevant_projects(profile, job_offer['description'])

    projects_text = ""
    for idx, project in enumerate(relevant_projects, 1):
        projects_text += f"\n  Projet {idx} : {project['nom']}\n  {project['description']}"
        if project.get('lien'):
            projects_text += f"\n  Lien : {project['lien']}"
        projects_text += "\n"

    if not projects_text:
        projects_text = "\n  (Mentionner l'expérience générale en développement)\n"

    prompt = f"""Rédige une lettre de motivation professionnelle et personnalisée pour cette offre d'alternance.

OFFRE D'EMPLOI :
Entreprise : {job_offer['company']}
Poste : {job_offer['title']}
Localisation : {job_offer.get('location', 'Non précisé')}
Description : {job_offer['description'][:900]}

PROFIL DU CANDIDAT :
Nom : {profile['nom']}
Formation EXACTE : {profile['formation']} à {profile['ecole']}, {profile['ville']}
Domaine de compétence : {profile['domaine']}
Durée recherchée : {profile.get('duree', '2 ans')}

Compétences techniques : {profile.get('stack', '')}
Outils de test : {profile.get('testing', '')}

PROJETS PERTINENTS :{projects_text}

Qualités : {profile.get('soft_skills', '')}
Motivation : {profile.get('motivation_generale', 'Progresser techniquement')}
Type d'entreprise : {profile.get('type_entreprise', '')}
Objectifs : {profile.get('objectifs', '')}

STRUCTURE DE LA LETTRE (240-280 mots MAX) :

Madame, Monsieur,

[Paragraphe 1 - Introduction (2-3 lignes)]
Je suis actuellement étudiant en {profile['formation']} à {profile['ecole']} à {profile['ville']}.
Je me permets de vous adresser ma candidature pour une alternance afin de mettre en pratique mes compétences techniques.

[Paragraphe 2 - Projets (6-7 lignes)]
Pendant mon parcours, j'ai travaillé sur plusieurs projets.
[Décrire les projets listés ci-dessus de façon DÉTAILLÉE et CONCRÈTE]
[Mentionner les TECHNOLOGIES utilisées (React, Next.js, etc.)]
[Expliquer les RÉSULTATS obtenus]

[Paragraphe 3 - Motivation finale (3 lignes)]
Je suis motivé à rejoindre {job_offer['company']} pour [trouver une raison PERTINENTE liée à l'offre].
Je serais ravi d'échanger avec vous sur cette opportunité.

Cordialement,
{profile['nom']}

RÈGLES ABSOLUES :
❌ NE PAS dire "cadre technique motivant"
❌ NE PAS inventer des technologies (si l'offre mentionne C# et que le candidat fait du React, ne pas dire "développeur C#")
❌ NE PAS ajouter "Je joins ma CV" ou formules inutiles
❌ NE PAS abréger la formation ("master ia" → utiliser "{profile['formation']}")
✅ Rester factuel et concret
✅ Utiliser EXACTEMENT le nom de la formation fourni
✅ Mentionner les vraies technos du candidat
✅ Phrases courtes et professionnelles
✅ Adapter au VRAI poste de l'offre

Rédige la lettre maintenant."""

    return prompt


def generate_letter_with_ollama(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["ollama", "run", OLLAMA_MODEL],
                input=prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and result.stdout.strip():
                generated_text = result.stdout.strip()
                if len(generated_text) >= 180:
                    return generated_text

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
        except Exception:
            pass

    return None


def sanitize_filename(text, max_length=50):
    sanitized = "".join(char for char in str(text) if char.isalnum() or char in (' ', '_', '-'))
    sanitized = sanitized.strip().replace(" ", "_")
    return sanitized[:max_length]


def save_letter(letter_content, company_name, job_title, output_folder):
    safe_company = sanitize_filename(company_name)
    safe_title = sanitize_filename(job_title, 40)

    filename = f"lettre_{safe_company}_{safe_title}.txt"
    file_path = os.path.join(output_folder, filename)

    with open(file_path, 'w', encoding='utf-8') as letter_file:
        letter_file.write(letter_content)

    return filename


def generate_letters_for_offers(csv_path):
    print_header()

    profile = load_candidate_profile()

    if not check_ollama_available():
        print(colored("\n❌ ERREUR : Ollama n'est pas disponible", Colors.RED + Colors.BOLD))
        print(colored("   Assure-toi qu'Ollama est installé et lancé", Colors.RED))
        print(colored(f"   Modèle requis : {OLLAMA_MODEL}\n", Colors.YELLOW))
        return

    print(colored(f"  🤖 Modèle Ollama : ", Colors.BOLD) + colored(OLLAMA_MODEL, Colors.CYAN))
    print(colored(f"  👤 Candidat : ", Colors.BOLD) + colored(profile.get('nom', 'N/A'), Colors.BLUE))
    print(colored(f"  🎯 Domaine : ", Colors.BOLD) + colored(profile.get('domaine', 'N/A'), Colors.GREEN))
    print(colored(f"  📚 Projets : ", Colors.BOLD) + colored(str(len(profile.get('projets', []))), Colors.PURPLE))

    if not os.path.exists(csv_path):
        print(colored(f"\n❌ ERREUR : Fichier introuvable", Colors.RED + Colors.BOLD))
        print(colored(f"   Chemin : {csv_path}\n", Colors.RED))
        return

    print(colored(f"\n  📂 Source : ", Colors.BOLD) + colored(csv_path, Colors.GRAY))

    offers_dataframe = pd.read_csv(csv_path)
    total_offers = len(offers_dataframe)

    if total_offers == 0:
        print(colored("\n⚠️  Aucune offre à traiter\n", Colors.YELLOW))
        return

    print(colored(f"  📊 Offres à traiter : ", Colors.BOLD) + colored(str(total_offers), Colors.GREEN))

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("\n" + colored("─" * 70, Colors.GRAY))
    print(colored("  ✍️  GÉNÉRATION DES LETTRES EN COURS", Colors.BOLD + Colors.PURPLE))
    print(colored("─" * 70, Colors.GRAY) + "\n")

    successful_generations = 0
    failed_generations = 0
    start_time = time.time()

    for index, job_offer in offers_dataframe.iterrows():
        print_progress_bar(index, total_offers, "lettres")

        prompt = create_prompt(job_offer, profile)
        generated_letter = generate_letter_with_ollama(prompt)

        if generated_letter:
            save_letter(
                generated_letter,
                job_offer.get('company', f'entreprise_{index}'),
                job_offer.get('title', f'poste_{index}'),
                OUTPUT_FOLDER
            )
            successful_generations += 1
        else:
            failed_generations += 1

    print_progress_bar(total_offers, total_offers, "lettres")
    print("\n")

    elapsed_time = round(time.time() - start_time, 1)

    print(colored("─" * 70, Colors.GRAY))
    print("\n" + colored("═" * 70, Colors.GREEN))
    print(colored("  📊 STATISTIQUES DE GÉNÉRATION", Colors.GREEN + Colors.BOLD))
    print(colored("═" * 70, Colors.GREEN))

    print(f"\n  Total traité      : {colored(str(total_offers), Colors.BOLD)}")
    print(
        f"  Lettres générées  : {colored(str(successful_generations), Colors.GREEN + Colors.BOLD)} ({successful_generations / total_offers * 100:.1f}%)")

    if failed_generations > 0:
        print(
            f"  Échecs            : {colored(str(failed_generations), Colors.RED + Colors.BOLD)} ({failed_generations / total_offers * 100:.1f}%)")

    print(
        f"  Temps écoulé      : {colored(f'{elapsed_time}s', Colors.CYAN)} ({elapsed_time / total_offers:.1f}s/lettre)")

    print("\n" + colored("═" * 70, Colors.GREEN))
    print(colored("\n  ✅ GÉNÉRATION TERMINÉE !", Colors.GREEN + Colors.BOLD))
    print(colored(f"  📁 Lettres disponibles : {OUTPUT_FOLDER}\n", Colors.BLUE))


if __name__ == "__main__":
    try:
        target_csv = sys.argv[1] if len(sys.argv) > 1 else "data/output/filtered/offres_alternance.csv"
        generate_letters_for_offers(target_csv)
    except KeyboardInterrupt:
        print(colored("\n\n⚠️  Interruption par l'utilisateur\n", Colors.YELLOW))
        sys.exit(0)
    except Exception as error:
        print(colored(f"\n❌ ERREUR FATALE : {str(error)}\n", Colors.RED + Colors.BOLD))
        raise