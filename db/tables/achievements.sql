create table  achievements_hunt.achievements
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	name		    varchar(4096) not null,
	ext_id		    varchar(1024) not null,
	description     varchar(1024),
	dt_create	    timestamp with time zone default current_timestamp not null,
	dt_update	    timestamp with time zone,
	num_owners      integer  default 0 not null,
	percent_owners  real  default 0 not null,
	icon_url        varchar(1024),
	locked_icon_url varchar(1024).
	is_hidden       boolean default false not null
	is_removed      boolean default false not null
	is_broken       boolean default false not null
);
create unique index u_achievements_ext_key on achievements_hunt.achievements(platform_id, game_id, ext_id);
alter table  achievements_hunt.achievements ADD CONSTRAINT u_achievements_ext_key unique using index u_achievements_ext_key;
alter table  achievements_hunt.achievements ADD CONSTRAINT fk_achievements_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.achievements ADD CONSTRAINT fk_achievements_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table  achievements_hunt.achievements owner to achievements_hunt_bot;
comment on column achievements_hunt.achievements.is_removed is 'Achievement removed by developer';
comment on column achievements_hunt.achievements.is_removed is 'Achievement can''t be obtained in legit way any more';