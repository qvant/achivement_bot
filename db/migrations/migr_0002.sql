alter table achievements_hunt.games add icon_url varchar(1024);
alter table achievements_hunt.games add release_date varchar(255);
alter table achievements_hunt.achievements add icon_url varchar(1024);
alter table achievements_hunt.achievements add locked_icon_url varchar(1024);

create table achievements_hunt.companies
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null
);
create unique index u_companies_name on achievements_hunt.companies(platform_id, name);
alter table  achievements_hunt.companies ADD CONSTRAINT fk_companies_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.companies owner to achievements_hunt_bot;

alter table achievements_hunt.games add developer_id        integer;
alter table achievements_hunt.games add publisher_id        integer;
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_developers foreign key (developer_id) references  achievements_hunt.companies(id);
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_publishers foreign key (publisher_id) references  achievements_hunt.companies(id);

create table achievements_hunt.genres
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null
);
create unique index u_genres_name on achievements_hunt.genres(platform_id, name);
alter table  achievements_hunt.genres ADD CONSTRAINT fk_genres_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.genres owner to achievements_hunt_bot;

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

update achievements_hunt.version set n_version=3, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;