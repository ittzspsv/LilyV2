import ast
from ..sLilyDatabaseAccess import LilyDatabaseAccess

class BloxFruitsDatabase(LilyDatabaseAccess):
    def __init__(self):
        super().__init__()
        self.item_dict: dict[str, dict] = {}
        self._cache_ready = False

    async def load_cache(self):
        rows = await self.fetch_all("SELECT * FROM BF_ItemValues")

        self.item_dict.clear()

        for row in rows:
            row = dict(row)

            name = row.get("name")
            if not name:
                continue

            name_lower = name.lower()

            try:
                aliases = ast.literal_eval(row.get("aliases") or "[]")
                if not isinstance(aliases, list):
                    aliases = []
            except:
                aliases = []

            row["aliases"] = aliases
            row["name_lower"] = name_lower
            row["category"] = (row.get("category") or "").lower()
            row["physical_value"] = row.get("physical_value") or 0
            row["permanent_value"] = row.get("permanent_value") or 0

            self.item_dict[name_lower] = row

        self._cache_ready = True

    @property   
    def get_alias_map(self):
        return {
            alias.lower(): name
            for name, data in self.item_dict.items()
            for alias in data.get("aliases", [])
            if alias
        }
    
    @property
    def get_fruit_names(self):
        return set(self.item_dict.keys())
    
    @property
    def get_fruit_names_sorted(self):
        return sorted(self.item_dict.keys(), key=len, reverse=True)
    
    @property
    def get_item_list_minimal(self):
        return [
            {
                "name": data["name"],
                "name_lower": data["name_lower"],
                "category": data["category"],
                "physical_value": data["physical_value"],
                "permanent_value": data["permanent_value"]
            }
            for data in self.item_dict.values()
        ]
    
    async def fetch_fruit_details(self, fruit_name: str) -> dict:
        if isinstance(fruit_name, str):
            fruit_name = ' '.join(i if i[0].isdigit() else i.capitalize() for i in fruit_name.split())
            data = self.item_dict.get(fruit_name, {}) or self.item_dict.get(fruit_name.title(), {})

            return data
        else:
            return {}  