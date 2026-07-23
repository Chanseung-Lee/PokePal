"""
data_access.py
A small query layer over pokedex.db. This is the only file that knows SQL;
the recommender and battle simulator call these functions instead.
 
Quick demo:
    python data_access.py
"""
 
import sqlite3
 
DB_PATH = "pokedex.db"
ENGLISH = 9  # local_language_id for English in the veekun data
 
 
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    return con
 
 
def get_pokemon_id(con, name):
    """Look up a Pokemon's internal id by its identifier, e.g. 'charizard'."""
    row = con.execute(
        "SELECT id FROM pokemon WHERE identifier = ?", (name.lower(),)
    ).fetchone()
    return row["id"] if row else None
 
 
def get_base_stats(con, pokemon_id):
    """Return {'hp': 78, 'attack': 84, ...} for a Pokemon."""
    rows = con.execute(
        """
        SELECT s.identifier AS stat, ps.base_stat AS value
        FROM pokemon_stats ps
        JOIN stats s ON s.id = ps.stat_id
        WHERE ps.pokemon_id = ?
        """,
        (pokemon_id,),
    ).fetchall()
    return {r["stat"]: int(r["value"]) for r in rows}
 
 
def get_types(con, pokemon_id):
    """Return a list of type names, e.g. ['fire', 'flying']."""
    rows = con.execute(
        """
        SELECT t.identifier AS type
        FROM pokemon_types pt
        JOIN types t ON t.id = pt.type_id
        WHERE pt.pokemon_id = ?
        ORDER BY pt.slot
        """,
        (pokemon_id,),
    ).fetchall()
    return [r["type"] for r in rows]
 
 
def get_learnset(con, pokemon_id, version_group, max_level=100):
    """
    Level-up moves a Pokemon can know by `max_level` in a given game.
 
    version_group is an identifier like 'red-blue', 'sword-shield', 'x-y'.
    Returns move dicts with name, level, power, accuracy, type, damage_class.
    """
    rows = con.execute(
        """
        SELECT mn.name           AS name,
               pm.level          AS level,
               m.power           AS power,
               m.accuracy        AS accuracy,
               m.pp              AS pp,
               t.identifier      AS type,
               dc.identifier     AS damage_class
        FROM pokemon_moves pm
        JOIN pokemon_move_methods mm ON mm.id = pm.pokemon_move_method_id
        JOIN version_groups vg       ON vg.id = pm.version_group_id
        JOIN moves m                 ON m.id = pm.move_id
        JOIN move_names mn           ON mn.move_id = m.id AND mn.local_language_id = ?
        JOIN types t                 ON t.id = m.type_id
        JOIN move_damage_classes dc  ON dc.id = m.damage_class_id
        WHERE pm.pokemon_id = ?
          AND mm.identifier = 'level-up'
          AND vg.identifier = ?
          AND CAST(pm.level AS INTEGER) <= ?
        ORDER BY CAST(pm.level AS INTEGER), mn.name
        """,
        (ENGLISH, pokemon_id, version_group, max_level),
    ).fetchall()
    return [dict(r) for r in rows]
 
 
def type_multiplier(con, attacking_type, defending_types):
    """
    Damage multiplier for an attack type vs. one or two defending types.
    e.g. type_multiplier(con, 'water', ['fire']) -> 2.0
         type_multiplier(con, 'electric', ['ground']) -> 0.0
 
    The veekun table stores factors as 0/50/100/200 (percent), so we / 100.
    """
    mult = 1.0
    for def_type in defending_types:
        row = con.execute(
            """
            SELECT te.damage_factor AS factor
            FROM type_efficacy te
            JOIN types att ON att.id = te.damage_type_id
            JOIN types dfn ON dfn.id = te.target_type_id
            WHERE att.identifier = ? AND dfn.identifier = ?
            """,
            (attacking_type, def_type),
        ).fetchone()
        if row is not None:
            mult *= int(row["factor"]) / 100.0
    return mult
 
 
if __name__ == "__main__":
    con = connect()
 
    pid = get_pokemon_id(con, "charizard")
    print("charizard id:", pid)
    print("base stats:", get_base_stats(con, pid))
    print("types:", get_types(con, pid))
 
    print("\nSuper-effective check:")
    print("  water -> charizard(fire/flying):",
          type_multiplier(con, "water", get_types(con, pid)))
    print("  electric -> charizard:",
          type_multiplier(con, "electric", get_types(con, pid)))
 
    print("\nFirst few level-up moves in red-blue by level 20:")
    for m in get_learnset(con, pid, "red-blue", max_level=20):
        print(f"  Lv{m['level']:>2} {m['name']:<15} "
              f"{m['type']:<8} pow={m['power']}")
 
    con.close()
 