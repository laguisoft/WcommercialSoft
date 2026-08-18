"""Parseur minimal de dump mysqldump/phpMyAdmin, sans dependance a un
serveur MySQL : lit directement les instructions
``INSERT INTO `table` (`col1`, `col2`, ...) VALUES (...), (...);``
et restitue chaque ligne sous forme de dict {colonne: valeur_python}.

Ecrit pour l'import ponctuel d'anciennes bases (cf.
import_legacy_apphar) : gere l'echappement SQL standard (guillemets
doubles ``''`` et backslash), NULL, les entiers/decimaux et les dates,
mais ne pretend pas etre un parseur SQL generique.
"""
import re

_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+`(?P<table>[^`]+)`\s*"
    r"\((?P<columns>[^)]*)\)\s*VALUES\s*",
    re.IGNORECASE,
)


def _parse_string(s, i):
    """s[i] == "'" ; retourne (valeur, index_apres_la_chaine_fermante)."""
    i += 1
    out = []
    n = len(s)
    while i < n:
        c = s[i]
        if c == "'":
            if i + 1 < n and s[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            out.append({
                "n": "\n", "r": "\r", "t": "\t", "0": "\0",
                "\\": "\\", "'": "'", '"': '"', "Z": "\x1a",
            }.get(nxt, nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    raise ValueError("Chaine SQL non terminee (guillemet manquant)")


def _parse_value(s, i):
    """Retourne (valeur_python, index_apres_la_valeur)."""
    if s[i] == "'":
        return _parse_string(s, i)
    if s[i:i + 4].upper() == "NULL" and (i + 4 == len(s) or not s[i + 4].isalnum()):
        return None, i + 4
    j = i
    while j < len(s) and s[j] not in ",)":
        j += 1
    token = s[i:j].strip()
    if token.upper() == "NULL":
        return None, j
    if re.fullmatch(r"-?\d+", token):
        return int(token), j
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token), j
    # Cas non attendu dans ce dump (expression SQL, mot-cle...) : on
    # renvoie le texte brut plutot que d'echouer silencieusement.
    return token, j


def _parse_tuple(s, i):
    assert s[i] == "(", f"'(' attendu a l'offset {i}, trouve {s[i]!r}"
    i += 1
    values = []
    while True:
        while s[i] in " \t\r\n":
            i += 1
        val, i = _parse_value(s, i)
        values.append(val)
        while s[i] in " \t\r\n":
            i += 1
        if s[i] == ",":
            i += 1
            continue
        if s[i] == ")":
            return values, i + 1
        raise ValueError(f"Caractere inattendu a l'offset {i}: {s[i]!r}")


def iter_insert_rows(sql_text, table_name):
    """Genere un dict {colonne: valeur} par ligne inseree dans `table_name`
    via une ou plusieurs instructions INSERT INTO du dump."""
    pos = 0
    while True:
        m = _INSERT_RE.search(sql_text, pos)
        if not m:
            return
        if m.group("table").lower() != table_name.lower():
            pos = m.end()
            continue
        columns = [c.strip(" `") for c in m.group("columns").split(",")]
        i = m.end()
        while True:
            while sql_text[i] in " \t\r\n":
                i += 1
            values, i = _parse_tuple(sql_text, i)
            if len(values) != len(columns):
                raise ValueError(
                    f"{table_name} : {len(values)} valeurs pour {len(columns)} colonnes"
                )
            yield dict(zip(columns, values))
            while sql_text[i] in " \t\r\n":
                i += 1
            if sql_text[i] == ",":
                i += 1
                continue
            if sql_text[i] == ";":
                i += 1
                break
            raise ValueError(f"Caractere inattendu a l'offset {i}: {sql_text[i]!r}")
        pos = i
