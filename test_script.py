# Le code Python complet pour résoudre le problème
import datetime
def jours_de_vie(naissance, date): 
    # Récupérer la différence entre les deux dates
    diff = date - naissance
    return diff.days
ma_fonction = jours_de_vie(datetime.datetime(2001, 1, 13), datetime.datetime(2025, 1, 14))
def ma_fonction():
    return jours_de_vie(datetime.datetime(2001, 1, 13), datetime.datetime(2025, 1, 14))
    print(jours_de_vie)