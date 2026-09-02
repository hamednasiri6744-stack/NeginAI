from __future__ import annotations

import json

from app.config import get_settings
from app.database import sql_connection


def main() -> None:
    sql = """
SELECT OBJECT_DEFINITION(OBJECT_ID(N'NGT.NGT_GetProductsPriceForCustomer')) AS Definition
""".strip()
    with sql_connection(get_settings()) as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        if cursor.description:
            names = [str(item[0]) for item in cursor.description]
            result = [dict(zip(names, row)) for row in cursor.fetchall()]
        else:
            result = []
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
