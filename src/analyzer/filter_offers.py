import os
import re
import sys
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter

load_dotenv()

INPUT_CSV_PATH = os.getenv("CSV_OUTPUT", "data/input/offres.csv")
OUTPUT_FOLDER = os.getenv("FILTERED_FOLDER", "data/output/filtered")
LOG_FILE_PATH = "data/filter.log"


class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'
    PURPLE = '\033[35m'
    END = '\033[0m'


def colored(text, color):
    return f"{color}{text}{Colors.END}"


def print_header():
    header_lines = [
        "╔══════════════════════════════════════════════════════════════════════╗",
        "║                                                                      ║",
        "║              🔍  ANALYSEUR INTELLIGENT D'OFFRES  🔍                  ║",
        "║                                                                      ║",
        "║           Filtrage • Classification • Statistiques                   ║",
        "║                                                                      ║",
        "╚══════════════════════════════════════════════════════════════════════╝"
    ]
    for line in header_lines:
        print(colored(line, Colors.CYAN + Colors.BOLD))
    print()


def print_progress_bar(label, current_value, total_value, bar_color=Colors.CYAN, bar_width=40):
    percentage = (current_value / total_value * 100) if total_value > 0 else 0
    filled_length = int(bar_width * current_value / total_value) if total_value > 0 else 0
    progress_bar = colored("█" * filled_length, bar_color) + colored("░" * (bar_width - filled_length), Colors.GRAY)

    value_display = colored(f"{current_value:>3}", Colors.BOLD)
    percentage_display = colored(f"{percentage:>5.1f}%", bar_color)

    print(f"  {label:<20} {progress_bar} {percentage_display}  ({value_display}/{total_value})")


def print_mini_bar(percentage, bar_color=Colors.CYAN, bar_width=20):
    filled_length = int(bar_width * percentage / 100)
    return colored("█" * filled_length, bar_color) + colored("░" * (bar_width - filled_length), Colors.GRAY)


SCHOOL_KEYWORDS = [
    "ynov", "afpa", "openclassrooms", "ifocop", "cesi", "pigier", "epitech",
    "ecole", "école", "campus", "groupe alternance", "formapi", "greta", "akalis",
    "ifa", "institut", "maestris", "aftral", "icademie", "nextadvance",
    "m2i formation", "idrac", "isefac", "cfa", "groupe afec", "alternance academy",
    "centre de formation", "organisme de formation", "école de commerce"
]

CONTRACT_KEYWORDS = {
    'alternance': [
        'alternance', 'apprentissage', 'contrat pro',
        'contrat de professionnalisation', 'contrat d\'apprentissage'
    ],
    'stage': ['stage', 'stagiaire', 'convention de stage'],
    'cdi': ['cdi', 'temps plein', 'contrat durée indéterminée', 'contrat à durée indéterminée'],
    'cdd': ['cdd', 'contrat durée déterminée', 'contrat à durée déterminée', 'mission'],
    'freelance': ['freelance', 'indépendant', 'auto-entrepreneur', 'consultant']
}

CONTRACT_EMOJIS = {
    'alternance': '🎓',
    'stage': '📚',
    'cdi': '💼',
    'cdd': '📝',
    'freelance': '💻',
    'non_precise': '❓'
}

CONTRACT_COLORS = {
    'alternance': Colors.GREEN,
    'stage': Colors.BLUE,
    'cdi': Colors.PURPLE,
    'cdd': Colors.YELLOW,
    'freelance': Colors.CYAN,
    'non_precise': Colors.GRAY
}


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)


def detect_school(company_name, job_description):
    combined_text = f"{company_name} {job_description}".lower()
    matched_keywords = []

    for keyword in SCHOOL_KEYWORDS:
        if keyword in combined_text:
            matched_keywords.append(keyword)

    is_school_offer = len(matched_keywords) > 0
    return is_school_offer, matched_keywords


def detect_contract_type(contract_field, job_description):
    combined_text = f"{contract_field} {job_description}".lower()

    for contract_type, keywords_list in CONTRACT_KEYWORDS.items():
        for keyword in keywords_list:
            if re.search(rf'\b{re.escape(keyword)}\b', combined_text):
                return contract_type

    return 'non_precise'


def animate_dots(message, animation_duration=1):
    import time
    for dot_count in range(3):
        dots = '.' * (dot_count + 1)
        print(f"\r  {colored(message + dots, Colors.YELLOW)}", end="", flush=True)
        time.sleep(animation_duration / 3)
    print(f"\r  {colored('✓', Colors.GREEN)} {colored(message, Colors.GREEN)}")


def filter_offers(csv_input_path):
    print_header()

    if not os.path.exists(csv_input_path):
        print(colored(f"\n❌ ERREUR : Fichier introuvable", Colors.RED + Colors.BOLD))
        print(colored(f"   Chemin : {csv_input_path}\n", Colors.RED))
        log_message(f"ERREUR : Fichier introuvable : {csv_input_path}")
        return

    print(colored("  📂 Source :", Colors.BOLD), colored(csv_input_path, Colors.BLUE))

    animate_dots("Chargement des données")
    dataframe = pd.read_csv(csv_input_path)
    total_offers = len(dataframe)

    print(colored(f"\n  📊 Nombre d'offres détectées : ", Colors.BOLD) +
          colored(f"{total_offers}", Colors.GREEN + Colors.BOLD))

    print("\n" + colored("─" * 70, Colors.GRAY))
    print(colored("  🔬 ANALYSE EN COURS", Colors.BOLD + Colors.CYAN))
    print(colored("─" * 70, Colors.GRAY))

    animate_dots("Détection des organismes de formation", 0.8)

    school_detection_results = dataframe.apply(
        lambda row: detect_school(
            str(row.get('company', '')),
            str(row.get('description', ''))
        ),
        axis=1
    )

    dataframe['is_school'] = school_detection_results.apply(lambda result: result[0])
    dataframe['school_keywords'] = school_detection_results.apply(lambda result: result[1])

    animate_dots("Classification des types de contrats", 0.8)

    dataframe['contract_type'] = dataframe.apply(
        lambda row: detect_contract_type(
            str(row.get('contract', '')),
            str(row.get('description', ''))
        ),
        axis=1
    )

    print(colored("\n  ✓ Analyse terminée avec succès\n", Colors.GREEN + Colors.BOLD))

    school_offers = dataframe[dataframe['is_school']]
    real_job_offers = dataframe[~dataframe['is_school']]

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print(colored("─" * 70, Colors.GRAY))
    print(colored("  💾 EXPORTATION DES FICHIERS", Colors.BOLD + Colors.CYAN))
    print(colored("─" * 70, Colors.GRAY) + "\n")

    school_output_path = os.path.join(OUTPUT_FOLDER, "offres_ecoles.csv")
    school_offers.to_csv(school_output_path, index=False)
    print(f"  🎓 {colored('Organismes de formation', Colors.YELLOW):<35} → " +
          f"{colored('offres_ecoles.csv', Colors.GRAY)} ({len(school_offers)} offres)")
    log_message(f"Écoles: {len(school_offers)} offres → {school_output_path}")

    contract_stats = {}
    for contract_type in list(CONTRACT_KEYWORDS.keys()) + ['non_precise']:
        filtered_by_contract = real_job_offers[real_job_offers['contract_type'] == contract_type]
        offer_count = len(filtered_by_contract)
        contract_stats[contract_type] = offer_count

        if offer_count > 0:
            contract_output_path = os.path.join(OUTPUT_FOLDER, f"offres_{contract_type}.csv")
            filtered_by_contract.to_csv(contract_output_path, index=False)

            emoji = CONTRACT_EMOJIS.get(contract_type, '📄')
            color = CONTRACT_COLORS.get(contract_type, Colors.CYAN)

            print(f"  {emoji} {colored(contract_type.upper(), color):<35} → " +
                  f"{colored(f'offres_{contract_type}.csv', Colors.GRAY)} ({offer_count} offres)")
            log_message(f"{contract_type}: {offer_count} offres → {contract_output_path}")

    print("\n" + colored("═" * 70, Colors.GREEN))
    print(colored("  📊 TABLEAU DE BORD STATISTIQUES", Colors.GREEN + Colors.BOLD))
    print(colored("═" * 70, Colors.GREEN))

    overview_title = "Vue d'ensemble"
    print(f"\n  {colored(overview_title, Colors.BOLD + Colors.UNDERLINE)}\n")
    print(f"  Total analysé     : {colored(str(total_offers), Colors.BOLD)}")
    print(f"  Offres valides    : {colored(str(len(real_job_offers)), Colors.GREEN + Colors.BOLD)} " +
          f"({len(real_job_offers) / total_offers * 100:.1f}%)")
    print(f"  Écoles filtrées   : {colored(str(len(school_offers)), Colors.RED + Colors.BOLD)} " +
          f"({len(school_offers) / total_offers * 100:.1f}%)")

    if len(school_offers) > 0:
        top_schools_title = "Top organismes détectés"
        print(f"\n  {colored(top_schools_title, Colors.BOLD + Colors.UNDERLINE)}\n")

        all_keywords = [kw for kw_list in school_offers['school_keywords'] for kw in kw_list]
        top_schools = Counter(all_keywords).most_common(5)

        for rank, (school_name, detection_count) in enumerate(top_schools, 1):
            percentage = (detection_count / len(school_offers)) * 100
            mini_bar = print_mini_bar(percentage, Colors.RED, 15)
            print(f"    {rank}. {school_name:<20} {mini_bar}  {detection_count} fois")

    contract_distribution_title = "Répartition des contrats"
    print(f"\n  {colored(contract_distribution_title, Colors.BOLD + Colors.UNDERLINE)}\n")

    sorted_contract_stats = sorted(contract_stats.items(), key=lambda item: item[1], reverse=True)

    for contract_type, offer_count in sorted_contract_stats:
        if offer_count > 0:
            emoji = CONTRACT_EMOJIS.get(contract_type, '📄')
            color = CONTRACT_COLORS.get(contract_type, Colors.CYAN)
            print_progress_bar(
                f"{emoji} {contract_type.upper()}",
                offer_count,
                len(real_job_offers),
                color
            )

    print("\n" + colored("─" * 70, Colors.GRAY))

    alternance_count = len(real_job_offers[real_job_offers['contract_type'] == 'alternance'])
    alternance_percentage = (alternance_count / len(real_job_offers) * 100) if len(real_job_offers) > 0 else 0

    print(f"\n  {colored('🎯 OBJECTIF : Alternances trouvées', Colors.BOLD)}")
    print(f"\n  {colored(str(alternance_count), Colors.GREEN + Colors.BOLD)} alternances sur " +
          f"{len(real_job_offers)} offres réelles ({alternance_percentage:.1f}%)")

    if alternance_count > 0:
        quality_score = (alternance_count / total_offers) * 100
        if quality_score >= 30:
            verdict = colored("Excellent scraping ! 🎉", Colors.GREEN + Colors.BOLD)
        elif quality_score >= 15:
            verdict = colored("Bon résultat 👍", Colors.CYAN + Colors.BOLD)
        else:
            verdict = colored("Affiner la recherche 🔍", Colors.YELLOW + Colors.BOLD)

        print(f"  Qualité du scraping : {verdict}")

    print("\n" + colored("═" * 70, Colors.GREEN))
    print(colored("\n  ✅ TRAITEMENT TERMINÉ AVEC SUCCÈS !", Colors.GREEN + Colors.BOLD))
    print(colored(f"  📁 Fichiers disponibles : {OUTPUT_FOLDER}\n", Colors.BLUE))

    log_message("Filtrage terminé avec succès")


if __name__ == "__main__":
    try:
        filter_offers(INPUT_CSV_PATH)
    except KeyboardInterrupt:
        print(colored("\n\n⚠️  Interruption par l'utilisateur\n", Colors.YELLOW))
        sys.exit(0)
    except Exception as error:
        print(colored(f"\n❌ ERREUR FATALE : {str(error)}\n", Colors.RED + Colors.BOLD))
        log_message(f"ERREUR FATALE : {str(error)}")
        raise