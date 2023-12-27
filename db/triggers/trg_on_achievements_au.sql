create trigger trg_on_achievements_au after
update of removed
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_upd();