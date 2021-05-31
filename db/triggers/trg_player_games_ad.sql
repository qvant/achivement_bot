create trigger trg_player_games_ad after
delete
    on
    achievements_hunt.player_games for each row execute procedure achievements_hunt.f_on_player_games_del();