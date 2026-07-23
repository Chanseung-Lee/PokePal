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
 
 
def load_csv(db, csv_path):
    table = csv_path.stem
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return  # empty file
        cols = ",".join(f'"{c}"' for c in header)
        placeholders = ",".join("?" * len(header))
        db.execute(f'DROP TABLE IF EXISTS "{table}"')
        db.execute(f'CREATE TABLE "{table}" ({cols})')
        db.executemany(
            f'INSERT INTO "{table}" VALUES ({placeholders})',
            reader,
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