select id,
       name,
       locale_name,
       dt_last_update
from achievements_hunt.platform_languages
where platform_id = %s
order by dt_last_update nulls first, locale_name