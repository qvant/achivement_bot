create table achievements_hunt.map_games_to_genres
(
	platform_id         integer not null,
	game_id 			integer not null,
	genre_id            integer not null
);
create unique index u_map_games_to_genres_key on achievements_hunt.map_games_to_genres(platform_id, game_id, genre_id);
alter table  achievements_hunt.map_games_to_genres ADD CONSTRAINT fk_map_games_to_genres_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.map_games_to_genres ADD CONSTRAINT fk_map_games_to_genres_to_games foreign key (game_id) references  achievements_hunt.games(id) on delete cascade;
alter table  achievements_hunt.map_games_to_genres ADD CONSTRAINT fk_map_games_to_genres_to_genres foreign key (genre_id) references  achievements_hunt.genres(id) on delete cascade;
alter table achievements_hunt.map_games_to_genres owner to achievements_hunt_bot;