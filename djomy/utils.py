import calendar


def ajouter_mois(date, mois):
    """Retourne `date` décalée de `mois` mois, en bornant le jour au dernier jour du mois cible."""
    mois_total = date.month - 1 + mois
    annee = date.year + mois_total // 12
    mois_resultant = mois_total % 12 + 1
    jour = min(date.day, calendar.monthrange(annee, mois_resultant)[1])
    return date.replace(year=annee, month=mois_resultant, day=jour)
