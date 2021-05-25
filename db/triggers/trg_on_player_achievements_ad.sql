create trigger trg_on_player_achievements_ad after
delete
    on
    achievements_hunt.player_achievements for each row execute procedure achievements_hunt.f_on_player_achievements_del()