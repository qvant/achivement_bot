create index idx_update_history_active on achievements_hunt.update_history(id_platform, id_process) where dt_ended is null;

drop index achievements_hunt.u_players_telegram;
create unique index u_players_telegram on achievements_hunt.players(telegram_id, platform_id);

update achievements_hunt.version set n_version=8, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;