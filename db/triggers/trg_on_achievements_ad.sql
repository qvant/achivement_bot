create trigger trg_on_achievements_ad after
delete
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_del();