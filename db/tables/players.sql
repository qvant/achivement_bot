create table achievements_hunt.players
(
    id          serial primary key,
    platform_id integer not null,
	name		varchar(1024) not null,
	ext_id		varchar(255) not null,
	dt_create	timestamp with time zone default current_timestamp not null,
	dt_update	timestamp with time zone,
	telegram_id integer,
	status_id   integer not null,
	is_public   boolean not null default true,
	dt_update_full	timestamp with time zone,
	dt_update_inc	timestamp with time zone
);
create unique index u_players_ext_key on achievements_hunt.players(platform_id, ext_id);
create unique index u_players_telegram on achievements_hunt.players(platform_id, telegram_id);
create index idx_players_name on achievements_hunt.players(name);
alter table achievements_hunt.players ADD CONSTRAINT u_players_ext_key unique using index u_players_ext_key;
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_statuses foreign key (status_id) references  achievements_hunt.statuses(id);
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_users foreign key (telegram_id) references  achievements_hunt.users(telegram_id) on delete cascade;
alter table achievements_hunt.players owner to achievements_hunt_bot;
