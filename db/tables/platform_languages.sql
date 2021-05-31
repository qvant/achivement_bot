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