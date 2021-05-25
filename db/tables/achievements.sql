create table  achievements_hunt.achievements
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	name		    text not null,
	ext_id		    text not null,
	description     text,
	dt_create	    timestamp with time zone default current_timestamp not null,
	dt_update	    timestamp with time zone,
	num_owners      integer  default 0 not null,
	percent_owners  real  default 0 not null
);
create unique index u_achievements_ext_key on achievements_hunt.achievements(platform_id, game_id, ext_id);
alter table  achievements_hunt.achievements ADD CONSTRAINT u_achievements_ext_key unique using index u_achievements_ext_key;
alter table  achievements_hunt.achievements ADD CONSTRAINT fk_achievements_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.achievements ADD CONSTRAINT fk_achievements_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table  achievements_hunt.achievements owner to achievements_hunt_bot;