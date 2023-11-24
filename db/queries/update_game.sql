update achievements_hunt.games l set dt_update=current_timestamp, name=%s,
                            has_achievements=%s, console_id=%s,
                            icon_url=%s, release_date=%s,
                            developer_id=%s, publisher_id=%s
                            where id = %s and platform_id = %s
                            and (%s != name or %s != has_achievements
                                or coalesce(%s, -1) != coalesce(console_id, -1)
                                or coalesce(%s, icon_url, '') != coalesce(icon_url, '')
                                or coalesce(%s, release_date, '') != coalesce(release_date, '')
                                or coalesce(%s, developer_id, -1) != coalesce(developer_id, -1)
                                or coalesce(%s, publisher_id, -1) != coalesce(publisher_id, -1)
                                )