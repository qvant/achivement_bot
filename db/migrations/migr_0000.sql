CREATE SCHEMA achievements_hunt
       AUTHORIZATION achievements_hunt_bot;

create table achievements_hunt.statuses
(
    id 			integer primary key,
    name        varchar(32)
);
create unique index u_statuses_name on achievements_hunt.statuses(name);
alter table  achievements_hunt.statuses owner to achievements_hunt_bot;
insert into achievements_hunt.statuses(id, name) values (1, 'New');
insert into achievements_hunt.statuses(id, name) values (2, 'Valid');


create table achievements_hunt.platforms
(
	id      serial primary key,
	name    varchar(255) not null
);
alter table  achievements_hunt.platforms owner to achievements_hunt_bot;

insert into achievements_hunt.platforms(id, name) values(1, 'Steam');

create table achievements_hunt.platform_languages
(
	id              serial primary key,
	platform_id     integer not null,
	name            varchar(1024) not null,
	locale_name     varchar(32) not null,
	dt_created      timestamp with time zone default current_timestamp,
    dt_last_update  timestamp with time zone
);
alter table  achievements_hunt.platform_languages owner to achievements_hunt_bot;
create unique index u_platform_languages_key on achievements_hunt.platform_languages(platform_id, locale_name);
create unique index u_platform_languages_key2 on achievements_hunt.platform_languages(platform_id, name);
insert into achievements_hunt.platform_languages(platform_id, name, locale_name) values(1, 'English', 'en');
insert into achievements_hunt.platform_languages(platform_id, name, locale_name) values(1, 'Russian', 'ru');

create table  achievements_hunt.games
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null,
	ext_id		        varchar(1024) not null,
	dt_create	        timestamp with time zone default current_timestamp not null,
	dt_update	        timestamp with time zone,
	num_owners          integer default 0 not null,
	has_achievements    boolean default true not null
);
create unique index u_games_ext_key on achievements_hunt.games(platform_id, ext_id);
alter table  achievements_hunt.games ADD CONSTRAINT u_games_ext_key unique using index u_games_ext_key;
alter table  achievements_hunt.games ADD CONSTRAINT fk_games_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table  achievements_hunt.games owner to achievements_hunt_bot;

create table  achievements_hunt.achievements
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	name		    varchar(1024) not null,
	ext_id		    varchar(1024) not null,
	description     varchar(1024),
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

create table  achievements_hunt.achievement_translations
(
	id 			    serial primary key,
	platform_id     integer not null,
	game_id         integer not null,
	achievement_id  integer not null,
	locale          varchar(32) not null,
	name            varchar(1024),
	description     varchar(1024),
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

create table achievements_hunt.users
(
    id 			    serial primary key,
    telegram_id     integer not null,
    dt_created      timestamp with time zone default current_timestamp,
    dt_last_update  timestamp with time zone,
    locale          varchar(32)
);
create unique index u_users_telegram_id on achievements_hunt.users(telegram_id);
alter table  achievements_hunt.users owner to achievements_hunt_bot;

create table achievements_hunt.players
(
    id          serial primary key,
    platform_id integer not null,
	name		varchar(1024) not null,
	ext_id		varchar(255) not null,
	dt_create	timestamp with time zone default current_timestamp not null,
	dt_update	timestamp with time zone,
	telegram_id integer,
	status_id   integer not null
);
create unique index u_players_ext_key on achievements_hunt.players(platform_id, ext_id);
create unique index u_players_telegram on achievements_hunt.players(platform_id, telegram_id);
create index idx_players_name on achievements_hunt.players(name);
alter table achievements_hunt.players ADD CONSTRAINT u_players_ext_key unique using index u_players_ext_key;
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_statuses foreign key (status_id) references  achievements_hunt.statuses(id);
alter table achievements_hunt.players ADD CONSTRAINT fk_players_to_users foreign key (telegram_id) references  achievements_hunt.users(telegram_id) on delete cascade;
alter table achievements_hunt.players owner to achievements_hunt_bot;


create table  achievements_hunt.player_games
(
	id 			        serial primary key,
	platform_id         integer not null,
	game_id             integer not null,
	player_id           integer not null,
	percent_complete    real,
	is_perfect          boolean
);
create unique index u_player_games_key on achievements_hunt.player_games(platform_id, game_id, player_id);
create index idx_player_games_player on achievements_hunt.player_games(player_id);
create index idx_player_games_game on achievements_hunt.player_games(game_id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_games foreign key (game_id) references  achievements_hunt.games(id);
alter table achievements_hunt.player_games ADD CONSTRAINT fk_player_games_to_players foreign key (player_id) references  achievements_hunt.players(id) on delete cascade;
alter table achievements_hunt.player_games owner to achievements_hunt_bot;

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

create table achievements_hunt.update_history
(
    id 			    serial primary key,
    dt_started      timestamp with time zone default current_timestamp,
    dt_ended        timestamp with time zone,
    dt_next_update  timestamp with time zone,
    id_platform     integer not null
);
create index idx_update_history_dt_next_update on achievements_hunt.update_history(id_platform, dt_next_update, dt_ended);
alter table  achievements_hunt.update_history owner to achievements_hunt_bot;

create table  achievements_hunt.queue_achievements_update
(
	id          	serial primary key,
	achievement_id 	integer not null,
	game_id 	    integer not null,
	platform_id     integer not null,
	dt_insert	    timestamp with time zone default current_timestamp not null,
	operation       varchar(32)
);
alter table  achievements_hunt.queue_achievements_update owner to achievements_hunt_bot;

create table  achievements_hunt.queue_games_update
(
	id          serial primary key,
	game_id 	integer not null,
	platform_id integer not null,
	dt_insert	timestamp with time zone default current_timestamp not null,
	player_id   integer not null,
	operation   varchar(32)
);
alter table  achievements_hunt.queue_games_update owner to achievements_hunt_bot;

create table  achievements_hunt.queue_player_achievements_update
(
	id          	serial primary key,
	achievement_id 	integer not null,
	game_id 	    integer not null,
	platform_id     integer not null,
	dt_insert	    timestamp with time zone default current_timestamp not null,
	player_id       integer not null,
	operation       varchar(32)
);
alter table  achievements_hunt.queue_player_achievements_update owner to achievements_hunt_bot;

CREATE OR REPLACE FUNCTION achievements_hunt.f_on_achievements_del()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_achievements_update(achievement_id, game_id, platform_id, operation) values (old.id, old.game_id, old.platform_id, TG_OP);
	    return old;
	END;
$function$
;

CREATE OR REPLACE FUNCTION achievements_hunt.f_on_achievements_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_achievements_update(achievement_id, game_id, platform_id, operation) values (new.id, new.game_id, new.platform_id, TG_OP);
	    return new;
	END;
$function$
;

CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_achievements_del()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_player_achievements_update(achievement_id, game_id, platform_id, player_id, operation) values (old.achievement_id, old.game_id, old.platform_id, old.player_id, TG_OP);
	    return old;
	END;
$function$
;


CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_achievements_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_player_achievements_update(achievement_id, game_id, platform_id, player_id, operation) values (new.achievement_id, new.game_id, new.platform_id, new.player_id, TG_OP);
	    return new;
	END;
$function$
;


CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_games_del()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_games_update(game_id, platform_id, player_id, operation) values (old.game_id, old.platform_id, old.player_id, TG_OP);
	    return old;
	END;
$function$
;


CREATE OR REPLACE FUNCTION achievements_hunt.f_on_player_games_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
	BEGIN
		insert into achievements_hunt.queue_games_update(game_id, platform_id, player_id, operation) values (new.game_id, new.platform_id, new.player_id, TG_OP);
	    return new;
	END;
$function$
;


create trigger trg_on_achievements_ad after
delete
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_del();

create trigger trg_on_achievements_ai after
insert
    on
    achievements_hunt.achievements for each row execute procedure achievements_hunt.f_on_achievements_ins();

create trigger trg_on_player_achievements_ad after
delete
    on
    achievements_hunt.player_achievements for each row execute procedure achievements_hunt.f_on_player_achievements_del();

create trigger trg_on_player_achievements_ai after
insert
    on
    achievements_hunt.player_achievements for each row execute procedure achievements_hunt.f_on_player_achievements_ins();

create trigger trg_player_games_ad after
delete
    on
    achievements_hunt.player_games for each row execute procedure achievements_hunt.f_on_player_games_del();

create trigger trg_player_games_ai after
insert
    on
    achievements_hunt.player_games for each row execute procedure achievements_hunt.f_on_player_games_ins();

create table achievements_hunt.version
(
	v_name varchar(255),
	n_version integer,
	dt_update timestamp with time zone
);
alter table  achievements_hunt.version owner to achievements_hunt_bot;
insert into achievements_hunt.version(v_name, n_version, dt_update) values('Achievement hunt bot', 1, current_timestamp);
commit;