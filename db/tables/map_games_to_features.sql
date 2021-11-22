create table achievements_hunt.map_games_to_features
(
	platform_id         integer not null,
	game_id 			integer not null,
	feature_id          integer not null
);
create unique index u_map_games_to_features_key on achievements_hunt.map_games_to_features(platform_id, game_id, feature_id);
alter table  achievements_hunt.map_games_to_features ADD CONSTRAINT fk_map_games_to_features_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.map_games_to_features ADD CONSTRAINT fk_map_games_to_features_to_games foreign key (game_id) references  achievements_hunt.games(id) on delete cascade;
alter table  achievements_hunt.map_games_to_features ADD CONSTRAINT fk_map_games_to_features_to_genres foreign key (feature_id) references  achievements_hunt.features(id) on delete cascade;
alter table achievements_hunt.map_games_to_features owner to achievements_hunt_bot;