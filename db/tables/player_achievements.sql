create table  achievements_hunt.player_achievements
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	achievement_id  integer not null,
	player_id       integer not null,
	dt_unlock	    timestamp with time zone
);
create unique index u_player_achievements_key on achievements_hunt.player_achievements(player_id, platform_id, game_id, achievement_id);
create index idx_player_achievements_game on achievements_hunt.player_achievements(game_id);
create index idx_player_achievements_achievement on achievements_hunt.player_achievements(achievement_id);
create index idx_player_achievements_player on achievements_hunt.player_achievements(player_id);
alter table achievements_hunt.player_achievements ADD CONSTRAINT fk_player_achievements_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.player_achievements ADD CONSTRAINT fk_player_achievements_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table achievements_hunt.player_achievements ADD CONSTRAINT fk_player_achievements_to_players foreign key (player_id) references  achievements_hunt.players(id) on delete cascade;
alter table achievements_hunt.player_achievements ADD CONSTRAINT fk_player_achievements_to_achievement foreign key (achievement_id) references  achievements_hunt.achievements(id);
alter table achievements_hunt.player_achievements owner to achievements_hunt_bot;