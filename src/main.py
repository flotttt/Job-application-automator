import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

SCRAPER_SCRIPT_PATH = os.getenv("SCRAPER_SCRIPT", "src/scraper/scrape.js")
FILTER_SCRIPT_PATH = os.getenv("FILTER_SCRIPT", "src/analyzer/filter_offers.py")
LETTERS_SCRIPT_PATH = os.getenv("LETTERS_SCRIPT", "src/generator/generate_letters.py")
PROFILE_SCRIPT_PATH = "src/generator/setup_profile.py"
CANDIDATE_PROFILE_PATH = "data/candidate_profile.json"


class TerminalColors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    PURPLE = '\033[35m'
    END = '\033[0m'


def colorize_text(text, color):
    return f"{color}{text}{TerminalColors.END}"


def display_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          🚀  JOB APPLICATION AUTOMATOR  🚀                           ║
║                                                                      ║
║     Scraping • Filtrage • Génération de lettres automatisée          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(colorize_text(banner, TerminalColors.CYAN + TerminalColors.BOLD))


def display_menu():
    print(colorize_text("\n╭──────────────────────────────────────────────╮", TerminalColors.CYAN))
    print(colorize_text("│  📋 MODES DISPONIBLES                        │", TerminalColors.CYAN + TerminalColors.BOLD))
    print(colorize_text("├──────────────────────────────────────────────┤", TerminalColors.CYAN))
    print(colorize_text("│                                              │", TerminalColors.CYAN))
    print(colorize_text("│  1. ", TerminalColors.CYAN) + colorize_text("full", TerminalColors.GREEN + TerminalColors.BOLD) + colorize_text(
        "    → Pipeline complet               │", TerminalColors.CYAN))
    print(colorize_text("│  2. ", TerminalColors.CYAN) + colorize_text("scrape", TerminalColors.BLUE + TerminalColors.BOLD) + colorize_text(
        "  → Scraping uniquement            │", TerminalColors.CYAN))
    print(colorize_text("│  3. ", TerminalColors.CYAN) + colorize_text("filter", TerminalColors.PURPLE + TerminalColors.BOLD) + colorize_text(
        "  → Filtrage des offres            │", TerminalColors.CYAN))
    print(colorize_text("│  4. ", TerminalColors.CYAN) + colorize_text("letters", TerminalColors.YELLOW + TerminalColors.BOLD) + colorize_text(
        " → Génération de lettres          │", TerminalColors.CYAN))
    print(colorize_text("│  5. ", TerminalColors.CYAN) + colorize_text("setup", TerminalColors.RED + TerminalColors.BOLD) + colorize_text(
        "   → Configuration du profil        │", TerminalColors.CYAN))
    print(colorize_text("│                                              │", TerminalColors.CYAN))
    print(colorize_text("╰──────────────────────────────────────────────╯", TerminalColors.CYAN))


def display_step_header(step_number, total_steps, step_name, emoji):
    print("\n" + colorize_text("═" * 70, TerminalColors.CYAN))
    print(colorize_text(f"  {emoji}  ÉTAPE {step_number}/{total_steps} : {step_name}", TerminalColors.CYAN + TerminalColors.BOLD))
    print(colorize_text("═" * 70, TerminalColors.CYAN) + "\n")


def execute_command(command_string, description, shell_type="python"):
    start_timestamp = time.time()

    try:
        if shell_type == "node":
            process_result = subprocess.run(
                ["node"] + command_string.split()[1:],
                check=False,
                capture_output=False
            )
        else:
            process_result = subprocess.run(
                command_string.split(),
                check=False,
                capture_output=False
            )

        elapsed_seconds = round(time.time() - start_timestamp, 1)

        if process_result.returncode == 0:
            print(colorize_text(f"\n✅ {description} terminé en {elapsed_seconds}s", TerminalColors.GREEN + TerminalColors.BOLD))
            return True
        else:
            print(colorize_text(f"\n❌ {description} a échoué après {elapsed_seconds}s", TerminalColors.RED + TerminalColors.BOLD))
            return False

    except KeyboardInterrupt:
        print(colorize_text(f"\n\n⚠️  Interruption par l'utilisateur", TerminalColors.YELLOW + TerminalColors.BOLD))
        elapsed_seconds = round(time.time() - start_timestamp, 1)
        print(colorize_text(f"💾 Progression sauvegardée ({elapsed_seconds}s écoulées)", TerminalColors.CYAN))
        return False
    except Exception as error:
        elapsed_seconds = round(time.time() - start_timestamp, 1)
        print(colorize_text(f"\n❌ Erreur : {str(error)} (après {elapsed_seconds}s)", TerminalColors.RED))
        return False


def verify_profile_exists():
    if not os.path.exists(CANDIDATE_PROFILE_PATH):
        print(colorize_text("\n⚠️  ATTENTION : Profil candidat non configuré !", TerminalColors.YELLOW + TerminalColors.BOLD))
        print(colorize_text("   Pour générer des lettres, tu dois d'abord créer ton profil.", TerminalColors.YELLOW))

        user_response = input(colorize_text("\n❯ Configurer maintenant ? (o/n) ", TerminalColors.CYAN)).lower()
        if user_response in ['o', 'oui', 'y', 'yes']:
            return execute_command(f"python {PROFILE_SCRIPT_PATH}", "Configuration du profil")
        else:
            print(colorize_text("   → Skip de la génération de lettres\n", TerminalColors.GRAY))
            return False
    return True


def run_full_pipeline():
    display_banner()
    print(colorize_text("  🎯 Mode : ", TerminalColors.BOLD) + colorize_text("PIPELINE COMPLET", TerminalColors.GREEN + TerminalColors.BOLD))
    print(colorize_text("  📊 Étapes : Scraping → Filtrage → Lettres", TerminalColors.GRAY))

    total_steps = 3
    pipeline_start_time = time.time()

    display_step_header(1, total_steps, "SCRAPING DES OFFRES", "🕷️")
    is_success = execute_command(f"node {SCRAPER_SCRIPT_PATH}", "Scraping", "node")
    if not is_success:
        print(colorize_text("\n⚠️  Pipeline interrompu après le scraping", TerminalColors.YELLOW))
        return

    display_step_header(2, total_steps, "FILTRAGE DES OFFRES", "🔍")
    is_success = execute_command(f"python {FILTER_SCRIPT_PATH}", "Filtrage")
    if not is_success:
        print(colorize_text("\n⚠️  Pipeline interrompu après le filtrage", TerminalColors.YELLOW))
        return

    display_step_header(3, total_steps, "GÉNÉRATION DES LETTRES", "✍️")
    if verify_profile_exists():
        filtered_csv_path = "data/output/filtered/offres_alternance.csv"
        is_success = execute_command(f"python {LETTERS_SCRIPT_PATH} {filtered_csv_path}", "Génération des lettres")

    total_elapsed_time = round(time.time() - pipeline_start_time, 1)

    print("\n" + colorize_text("═" * 70, TerminalColors.GREEN))
    print(colorize_text("  🎉 PIPELINE TERMINÉ !", TerminalColors.GREEN + TerminalColors.BOLD))
    print(colorize_text("═" * 70, TerminalColors.GREEN))
    print(colorize_text(f"\n  ⏱️  Temps total : {total_elapsed_time}s", TerminalColors.CYAN))
    print(colorize_text("  📁 Résultats disponibles dans data/output/\n", TerminalColors.BLUE))


def run_scrape_only():
    display_banner()
    print(colorize_text("  🎯 Mode : ", TerminalColors.BOLD) + colorize_text("SCRAPING UNIQUEMENT", TerminalColors.BLUE + TerminalColors.BOLD))

    display_step_header(1, 1, "SCRAPING DES OFFRES", "🕷️")
    execute_command(f"node {SCRAPER_SCRIPT_PATH}", "Scraping", "node")


def run_filter_only():
    display_banner()
    print(colorize_text("  🎯 Mode : ", TerminalColors.BOLD) + colorize_text("FILTRAGE UNIQUEMENT", TerminalColors.PURPLE + TerminalColors.BOLD))

    display_step_header(1, 1, "FILTRAGE DES OFFRES", "🔍")
    execute_command(f"python {FILTER_SCRIPT_PATH}", "Filtrage")


def run_letters_only():
    display_banner()
    print(colorize_text("  🎯 Mode : ", TerminalColors.BOLD) + colorize_text("LETTRES UNIQUEMENT", TerminalColors.YELLOW + TerminalColors.BOLD))

    if not verify_profile_exists():
        return

    display_step_header(1, 1, "GÉNÉRATION DES LETTRES", "✍️")
    filtered_csv_path = "data/output/filtered/offres_alternance.csv"

    if not os.path.exists(filtered_csv_path):
        print(colorize_text(f"❌ Fichier introuvable : {filtered_csv_path}", TerminalColors.RED))
        print(colorize_text("   Lance d'abord le filtrage avec : python src/main.py filter\n", TerminalColors.YELLOW))
        return

    execute_command(f"python {LETTERS_SCRIPT_PATH} {filtered_csv_path}", "Génération des lettres")


def run_setup_only():
    display_banner()
    print(colorize_text("  🎯 Mode : ", TerminalColors.BOLD) + colorize_text("CONFIGURATION DU PROFIL", TerminalColors.RED + TerminalColors.BOLD))

    display_step_header(1, 1, "CONFIGURATION", "⚙️")
    execute_command(f"python {PROFILE_SCRIPT_PATH}", "Configuration du profil")


def main():
    if len(sys.argv) > 1:
        selected_mode = sys.argv[1].lower()
    else:
        display_banner()
        display_menu()

        user_choice = input(colorize_text("\n❯ Choisis un mode (1-5) : ", TerminalColors.CYAN + TerminalColors.BOLD)).strip()

        mode_mapping = {
            "1": "full",
            "2": "scrape",
            "3": "filter",
            "4": "letters",
            "5": "setup"
        }

        selected_mode = mode_mapping.get(user_choice, user_choice)

    available_modes = {
        "full": run_full_pipeline,
        "scrape": run_scrape_only,
        "filter": run_filter_only,
        "letters": run_letters_only,
        "setup": run_setup_only
    }

    if selected_mode in available_modes:
        try:
            available_modes[selected_mode]()
        except KeyboardInterrupt:
            print(colorize_text("\n\n⚠️  Interruption détectée", TerminalColors.YELLOW))
            print(colorize_text("💾 Progression sauvegardée\n", TerminalColors.CYAN))
            sys.exit(0)
    else:
        print(colorize_text(f"\n❌ Mode inconnu : {selected_mode}", TerminalColors.RED))
        print(colorize_text("   Modes valides : full, scrape, filter, letters, setup\n", TerminalColors.YELLOW))
        sys.exit(1)


if __name__ == "__main__":
    main()