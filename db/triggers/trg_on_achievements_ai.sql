create trigger trg_on_achievements_ai after
insert
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_ins();