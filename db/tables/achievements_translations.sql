create table  achievements_hunt.achievement_translations
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	achievement_id  integer not null,
	locale          text not null,
	name            text,
	description     text,
	dt_create	    timestamp with time zone default current_timestamp not null,
	dt_update	    timestamp with time zone
);
create unique index u_achievement_translations_key on achievements_hunt.achievement_translations(platform_id, game_id, achievement_id, locale);
create index idx_achievement_achievement on achievements_hunt.achievement_translations(achievement_id);
alter table achievements_hunt.achievement_translations ADD CONSTRAINT u_achievement_translations_key unique using index u_achievement_translations_key;
alter table achievements_hunt.achievement_translations ADD CONSTRAINT fk_achievements_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.achievement_translations ADD CONSTRAINT fk_achievements_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table achievements_hunt.achievement_translations ADD CONSTRAINT fk_achievements_to_achievements foreign key (achievement_id) references  achievements_hunt.achievements(id);
alter table achievements_hunt.achievement_translations owner to achievements_hunt_bot;