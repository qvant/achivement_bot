update achievements_hunt.platform_languages
  set dt_last_update = current_timestamp
where platform_id = %s
  and locale_name = %s