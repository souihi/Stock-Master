``m̀ermaid
sequenceDiagram
    actor Magasinier
    participant UI as Vue Tourets
    participant Core as Backend Python
    participant DB as PostgreSQL

    Note over Magasinier, DB: SCÉNARIO : RETOUR CHANTIER

    Magasinier->>UI: Scanne "LOT-55"
    UI->>Core: Requête SQL (Select by ID)
    Core->>DB: SELECT * FROM ElementsSuivis WHERE id='LOT-55'
    DB-->>Core: Retourne {statut: CHANTIER, long: 500m}
    Core-->>UI: Affiche info Touret

    Magasinier->>UI: Clique "Retour Chantier"
    UI->>Magasinier: Demande "Métrage restant ?"
    Magasinier->>UI: Saisit "420"

    UI->>Core: Valider Action
    Core->>Core: Calcul Conso (500 - 420 = 80m)
    
    par Mise à jour
        Core->>DB: UPDATE ElementsSuivis (long=420, statut=STOCK)
        Core->>DB: INSERT SuiviEvenements (action=RETOUR, conso=80)
    end

    Core-->>UI: Succès
    UI-->>Magasinier: Toast "Retour enregistré !"```