create trigger trg_player_games_bu before
update
    on
    achievements_hunt.player_games for each row execute procedure achievements_hunt.f_on_player_games_upd();