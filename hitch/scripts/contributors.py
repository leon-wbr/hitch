import logging
import os

import pandas as pd
from flask import render_template_string

from hitch.helpers import get_db, get_dirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dirs = get_dirs()

logger.info("Creating directories if they don't exist")
os.makedirs(dirs["dist"], exist_ok=True)

logger.info("Loading template and output paths")
template_path = os.path.join(dirs["templates"], "security/contributors_template.html")
outname = os.path.join(dirs["dist"], "contributors.html")

logger.info("Fetching data for spots")
query = """select
        u.username AS hitchhiker,
        COUNT(*) AS total_contributions
    from points p left join user u on p.user_id = u.id
    where p.user_id is not null
    group by p.user_id
    order by total_contributions desc"""
overall_contributions = pd.read_sql(
    query,
    get_db(),
)
overall_contributions.index = overall_contributions.index + 1

query = """select
        u.username AS hitchhiker,
        COUNT(*) AS total_contributions
    from points p left join user u on p.user_id = u.id
    where p.user_id is not null
        and strftime('%Y-%m', p.datetime) = strftime('%Y-%m', 'now')
    group by p.user_id
    order by total_contributions desc;"""
monthly_contributions = pd.read_sql(
    query,
    get_db(),
)
monthly_contributions.index = monthly_contributions.index + 1

### Put together ###
logger.info("Combining all parts into the final HTML")
with open(template_path, encoding="utf-8") as template, open(outname, "w", encoding="utf-8") as out:
    output = render_template_string(
        template.read(),
        overall_contributions=overall_contributions.to_html(),
        monthly_contributions=monthly_contributions.to_html(),
    )
    out.write(output)

logger.info("Contribution page generation complete")
