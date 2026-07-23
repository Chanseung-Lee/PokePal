"""
build_db.py
Loads the veekun CSV files into a local SQLite database (pokedex.db).
 
Run once from your project root:
    python build_db.py
 
Re-run any time to rebuild from scratch. Every CSV in data/ becomes a table
named after the file (pokemon.csv -> table "pokemon").
"""
 
import csv
import sqlite3
import pathlib
import sys
 
DATA_DIR = pathlib.Path("data")
DB_PATH = pathlib.Path("pokedex.db")
 
# The tables we actually query. The full dump has 150+ CSVs; we only need these
# for the recommender + battle simulator. Set to None to load ALL csv files.
NEEDED_TABLES = {
    "pokemon",
    "pokemon_species",
    "pokemon_stats",
    "stats",
    "pokemon_types",
    "types",
    "type_names",
    "type_efficacy",
    "moves",
    "move_names",
    "move_damage_classes",
    "pokemon_moves",
    "pokemon_move_methods",
    "pokemon_abilities",
    "abilities",
    "ability_names",
    "version_groups",
    "versions",
    "version_names",
    "generations",
}
 
 
def sniff_affinity(values):
    """Decide a column's SQLite type from its values.

    Columns loaded as raw text compare badly (text '9' != integer 9), which
    silently breaks JOINs. So we detect numeric columns and declare them
    INTEGER/REAL, letting SQLite store them as real numbers.
    """
    saw_value = False
    all_int = all_real = True
    for v in values:
        if v == "" or v is None:
            continue
        saw_value = True
        try:
            int(v)
        except ValueError:
            all_int = False
        try:
            float(v)
        except ValueError:
            all_real = False
    if not saw_value:
        return "TEXT"
    if all_int:
        return "INTEGER"
    if all_real:
        return "REAL"
    return "TEXT"


def load_csv(db, csv_path):
    table = csv_path.stem
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return  # empty file
        rows = list(reader)

    # Empty CSV cells become real NULLs, not empty strings.
    rows = [[(v if v != "" else None) for v in row] for row in rows]

    # Pick a type per column so numbers store as numbers.
    affinities = [
        sniff_affinity([row[i] for row in rows]) for i in range(len(header))
    ]
    col_defs = ",".join(f'"{c}" {a}' for c, a in zip(header, affinities))

    placeholders = ",".join("?" * len(header))
    db.execute(f'DROP TABLE IF EXISTS "{table}"')
    db.execute(f'CREATE TABLE "{table}" ({col_defs})')
    db.executemany(
        f'INSERT INTO "{table}" VALUES ({placeholders})',
        rows,
    )
 
 
def main():
    if not DATA_DIR.exists():
        sys.exit(f"Could not find '{DATA_DIR}'. Run this from your project root, "
                 f"with the veekun CSVs in a 'data' folder.")
 
    db = sqlite3.connect(DB_PATH)
    loaded = 0
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        if NEEDED_TABLES is not None and csv_path.stem not in NEEDED_TABLES:
            continue
        load_csv(db, csv_path)
        loaded += 1
 
    # A few indexes so the battle simulator's repeated lookups stay fast.
    db.execute('CREATE INDEX IF NOT EXISTS idx_pm_pokemon ON pokemon_moves(pokemon_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_pstats_pokemon ON pokemon_stats(pokemon_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_ptypes_pokemon ON pokemon_types(pokemon_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_efficacy ON type_efficacy(damage_type_id, target_type_id)')
    db.commit()
    db.close()
 
    print(f"Built {DB_PATH} from {loaded} tables.")
 
 
if __name__ == "__main__":
    main()