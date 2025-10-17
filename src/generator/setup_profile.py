import os
import json


class TerminalColors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    END = '\033[0m'


def colorize_text(text, color):
    return f"{color}{text}{TerminalColors.END}"


def display_header():
    print("\n" + colorize_text("═" * 70, TerminalColors.CYAN))
    print(colorize_text("  🎯 CONFIGURATION DU PROFIL CANDIDAT", TerminalColors.CYAN + TerminalColors.BOLD))
    print(colorize_text("═" * 70, TerminalColors.CYAN) + "\n")


def prompt_user_input(question, default_value="", allow_multiline=False):
    if default_value:
        prompt_text = f"{colorize_text('❯', TerminalColors.CYAN)} {question} {colorize_text(f'(défaut: {default_value})', TerminalColors.GRAY)}\n  "
    else:
        prompt_text = f"{colorize_text('❯', TerminalColors.CYAN)} {question}\n  "

    if allow_multiline:
        print(prompt_text + colorize_text("(Appuie sur Entrée 2 fois pour terminer)", TerminalColors.YELLOW))
        input_lines = []
        while True:
            current_line = input("  ")
            if current_line == "" and len(input_lines) > 0:
                break
            if current_line:
                input_lines.append(current_line)
        return "\n".join(input_lines) if input_lines else default_value
    else:
        user_response = input(prompt_text).strip()
        return user_response if user_response else default_value


def prompt_yes_no(question):
    user_response = input(
        f"{colorize_text('❯', TerminalColors.CYAN)} {question} {colorize_text('(o/n)', TerminalColors.GRAY)} "
    ).lower()
    return user_response in ['o', 'oui', 'y', 'yes']


def collect_project_information():
    projets = []
    i = 1
    max_projects = 5

    while True:
        print(colorize_text(f"\n--- Projet {i} ---", TerminalColors.CYAN))
        if not prompt_yes_no("Ajouter un projet ?"):
            break

        nom = prompt_user_input("Nom du projet")
        description = prompt_user_input("Description courte (1-2 lignes)", allow_multiline=False)
        technologies = prompt_user_input("Technologies utilisées", "React, Node.js")
        contexte = prompt_user_input("Contexte (perso/école/stage/équipe)", "Personnel")
        lien = prompt_user_input("Lien GitHub (optionnel)", "")

        projets.append({
            "nom": nom,
            "description": description,
            "technologies": technologies,
            "contexte": contexte,
            "lien": lien
        })
        i += 1
        if i > max_projects:
            print(colorize_text(f"\n✋ Maximum {max_projects} projets recommandé pour la clarté", TerminalColors.YELLOW))
            break

    return projets


def collect_candidate_profile():
    # — Schéma FR (celui attendu par generate_letters.py) —
    print(colorize_text("\n━━━ INFORMATIONS DE BASE ━━━", TerminalColors.BOLD))
    nom = prompt_user_input("Ton nom complet")
    formation = prompt_user_input("Ta formation actuelle (ex: 1ère année de Master IA/Data)")
    ecole = prompt_user_input("Nom de ton école")
    ville = prompt_user_input("Ville")

    print(colorize_text("\n━━━ TYPE DE POSTE RECHERCHÉ ━━━", TerminalColors.BOLD))
    domaine = prompt_user_input("Domaine ciblé (ex: Développement fullstack, Data Science, Backend...)")
    contrat = prompt_user_input("Type de contrat recherché", "Alternance")
    duree = prompt_user_input("Durée du contrat", "2 ans")

    print(colorize_text("\n━━━ COMPÉTENCES TECHNIQUES ━━━", TerminalColors.BOLD))
    print(colorize_text("Liste toutes tes compétences techniques (langages, frameworks, outils...)\n", TerminalColors.YELLOW))
    stack = prompt_user_input("Stack complète (ex: React, Next.js, Python, Docker, PostgreSQL...)")
    testing = prompt_user_input("Outils de test maîtrisés (optionnel)", "")

    print(colorize_text("\n━━━ PROJETS RÉALISÉS ━━━", TerminalColors.BOLD))
    print(colorize_text("On va lister tes projets les plus pertinents (3-5 projets max)\n", TerminalColors.YELLOW))
    projets = collect_project_information()

    print(colorize_text("\n━━━ COMPÉTENCES TRANSVERSALES ━━━", TerminalColors.BOLD))
    soft_skills = prompt_user_input("Qualités personnelles (séparées par des virgules)",
                                    "Autonomie, curiosité, esprit d'équipe, capacité d'adaptation")
    self_learning = prompt_user_input("Apprentissages autodidactes ou formations complémentaires", "")

    print(colorize_text("\n━━━ MOTIVATIONS ━━━", TerminalColors.BOLD))
    motivation_generale = prompt_user_input("Pourquoi tu cherches ce type de contrat ?", allow_multiline=True)
    type_entreprise = prompt_user_input("Type d'entreprise recherché (startup, PME, grand groupe...)",
                                        "Structure à taille humaine avec polyvalence et autonomie")
    objectifs = prompt_user_input("Tes objectifs pour ce contrat",
                                  "Progresser techniquement et contribuer à des projets concrets")

    # Schéma FR (canonique)
    profile_fr = {
        "nom": nom or "Candidat",
        "formation": formation or "",
        "ecole": ecole or "",
        "ville": ville or "",
        "domaine": domaine or "",
        "contrat": (contrat or "Alternance").lower(),
        "duree": duree or "2 ans",
        "stack": stack or "",
        "testing": testing or "",
        "projets": projets or [],
        "soft_skills": soft_skills or "",
        "motivation_generale": motivation_generale or "",
        "type_entreprise": type_entreprise or "",
        "objectifs": objectifs or ""
    }

    # Alias EN (compatibilité éventuelle avec d’autres scripts)
    profile_en = {
        "full_name": profile_fr["nom"],
        "current_education": profile_fr["formation"],
        "school_name": profile_fr["ecole"],
        "city": profile_fr["ville"],
        "target_domain": profile_fr["domaine"],
        "contract_type": profile_fr["contrat"],
        "contract_duration": profile_fr["duree"],
        "technical_stack": profile_fr["stack"],
        "testing_tools": profile_fr["testing"],
        "projects": [
            {
                "name": p.get("nom", ""),
                "description": p.get("description", ""),
                "technologies": p.get("technologies", ""),
                "context": p.get("contexte", ""),
                "repository_link": p.get("lien", "")
            } for p in profile_fr["projets"]
        ],
        "soft_skills": profile_fr["soft_skills"],
        "self_learning": self_learning or "",
        "general_motivation": profile_fr["motivation_generale"],
        "company_values": profile_fr["type_entreprise"],
        "career_objectives": profile_fr["objectifs"]
    }

    # Fusion (plat) : FR prioritaire, avec alias EN en plus (ça ne gêne pas le générateur)
    merged = {**profile_en, **profile_fr}
    return merged


def save_profile_to_file(profile_data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(profile_data, json_file, indent=2, ensure_ascii=False)


def display_success_summary(profile_data, file_path):
    print("\n" + colorize_text("═" * 70, TerminalColors.GREEN))
    print(colorize_text("  ✅ PROFIL SAUVEGARDÉ AVEC SUCCÈS !", TerminalColors.GREEN + TerminalColors.BOLD))
    print(colorize_text("═" * 70, TerminalColors.GREEN))

    nb_projets = len(profile_data.get('projets') or profile_data.get('projects') or [])
    print(f"\n{colorize_text('📁 Fichier créé :', TerminalColors.BOLD)} {file_path}")
    print(f"{colorize_text('👤 Candidat :', TerminalColors.BOLD)} {profile_data.get('nom') or profile_data.get('full_name')}")
    print(f"{colorize_text('🎯 Domaine ciblé :', TerminalColors.BOLD)} {profile_data.get('domaine') or profile_data.get('target_domain')}")
    print(f"{colorize_text('📊 Projets enregistrés :', TerminalColors.BOLD)} {nb_projets}")

    print(colorize_text("\n💡 Tu peux maintenant générer des lettres personnalisées !", TerminalColors.CYAN))
    print(colorize_text("   Lance : python src/generator/generate_letters.py\n", TerminalColors.GRAY))


def main():
    display_header()

    print(colorize_text("Ce script va te poser des questions pour créer un profil détaillé.", TerminalColors.YELLOW))
    print(colorize_text("Tes réponses seront utilisées pour générer des lettres personnalisées.\n", TerminalColors.YELLOW))

    profile_data = collect_candidate_profile()

    output_file_path = "data/candidate_profile.json"
    save_profile_to_file(profile_data, output_file_path)

    display_success_summary(profile_data, output_file_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colorize_text("\n\n⚠️  Configuration annulée\n", TerminalColors.YELLOW))
    except Exception as error:
        print(colorize_text(f"\n❌ ERREUR : {str(error)}\n", TerminalColors.RED))
        raise