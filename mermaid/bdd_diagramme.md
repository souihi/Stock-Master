```mermaid
classDiagram
    %% --- ZONE 1 : ADMINISTRATION (Mis à jour) ---
    class Entreprise {
        +UUID id (PK)
        +String nom
    }

    class Site {
        +UUID id (PK)
        +UUID entreprise_id (FK)
        +String nom
        +String ville
    }

    class Utilisateur {
        +UUID id (PK)
        +UUID site_id (FK)
        +String nom
        +String email
        +String mot_de_passe
        %% Le champ 'role' a été supprimé ici
    }

    class Role {
        +UUID id (PK)
        +String nom_role
        +String description
    }

    class UtilisateurRole {
        +UUID utilisateur_id (PK, FK)
        +UUID role_id (PK, FK)
    }

    Entreprise "1" -- "0..*" Site : possède
    Site "1" -- "0..*" Utilisateur : emploie
    
    %% Relation Many-to-Many via la table de liaison
    Utilisateur "1" -- "0..*" UtilisateurRole : a
    Role "1" -- "0..*" UtilisateurRole : est_attribue_a

    %% --- ZONE 2 : CONFIGURATION ---
    class Projet {
        +UUID id (PK)
        +UUID site_id (FK)
        +String nom_projet
    }

    class ConfigurationProjet {
        +UUID id (PK)
        +UUID projet_id (FK)
        +JSON colonnes_import_excel
        +JSON criteres_unicite
        +JSON config_suivi_objets
    }

    Site "1" -- "0..*" Projet : héberge
    Projet "1" -- "0..1" ConfigurationProjet : pilote

    %% --- ZONE 3 : STOCK ---
    class Stock {
        +UUID id (PK)
        +UUID projet_id (FK)
        +String code_article
        +Decimal quantite_reelle
        +String emplacement
        +JSON infos_sup
    }

    Projet "1" -- "0..*" Stock : contient

    %% --- ZONE 4 : AUDIT ---
    class AuditGeneral {
        +UUID id (PK)
        +UUID projet_id (FK)
        +String statut
        +JSON config_snapshot
    }

    class AuditLigne {
        +UUID id (PK)
        +UUID audit_id (FK)
        +String code_article
        +JSON identifiant_supplementaire
        +Decimal qte_stock_db
        +Decimal qte_fichier_orange
        +Decimal ecart
        +String action_requise
    }

    Projet "1" -- "0..*" AuditGeneral : archive
    AuditGeneral "1" *-- "0..*" AuditLigne : détaille

    %% --- ZONE 5 : INVENTAIRE ---
    class InventaireSession {
        +UUID id (PK)
        +UUID projet_id (FK)
        +String statut
        +String mode_source
        +JSON config_snapshot
    }

    class InventaireLigne {
        +UUID id (PK)
        +UUID session_id (FK)
        +String code_article
        +Decimal qte_scanne
    }

    Projet "1" -- "0..*" InventaireSession : organise
    InventaireSession "1" *-- "0..*" InventaireLigne : compile

    %% --- ZONE 6 : SUIVI DE VIE ---
    class ElementsSuivis {
        +UUID id (PK)
        +UUID projet_id (FK)
        +String identifiant_unique
        +String code_article 
        +String statut
        +JSON attributs_courants
    }

    class SuiviEvenements {
        +UUID id (PK)
        +UUID element_id (FK)
        +String type_action
        +JSON donnees_action
        +UUID utilisateur_id (FK)
        +DateTime date
    }

    Projet "1" -- "0..*" ElementsSuivis : suit
    ElementsSuivis "1" -- "0..*" SuiviEvenements : historique``