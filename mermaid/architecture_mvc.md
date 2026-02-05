```mermaid
graph TD
    subgraph CLIENT
        Browser[Navigateur Utilisateur]
    end

    subgraph STREAMLIT_APP ["Application (Python)"]
        Router("app.py - Routeur")
        
        subgraph VIEWS ["Couche Présentation (Views)"]
            V_Comp[comparaison_view.py]
            V_Inv[inventaire_tournant_view.py]
            V_Touret[gestion_tourets_view_py_A_faire]
        end
        
        subgraph COMPONENTS ["Composants UI"]
            Atoms[atoms.py - Cards, CSS, JS]
        end

        subgraph CORE ["Couche Métier (Core)"]
            Processor[processor.py - Logique]
            Utils[utils.py - Parsers]
        end
    end

    subgraph DATA ["Données"]
        Excel[(Fichiers Excel)]
        DB[(PostgreSQL Supabase)]
    end

    Browser --> Router
    Router --> V_Comp & V_Inv & V_Touret
    V_Comp & V_Inv --> Atoms
    V_Comp & V_Inv --> Processor
    Processor --> Utils
    Processor -.-> Excel
    Processor == SQL ==> DB```