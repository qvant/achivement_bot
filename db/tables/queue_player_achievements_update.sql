create table  achievements_hunt.queue_player_achievements_update
(
	id          	serial primary key,
	achievement_id 	integer not null,
	game_id 	    integer not null,
	platform_id     integer not null,
	dt_insert	    timestamp with time zone default current_timestamp not null,
	player_id       integer not null,
	operation       text
);
alter table  achievements_hunt.queue_player_achievements_update owner to achievements_hunt_bot;