create table achievements_hunt.consoles
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null,
	ext_id		        varchar(1024) not null
);
create unique index u_consoles_ext_key on achievements_hunt.consoles(platform_id, ext_id);
alter table achievements_hunt.consoles ADD CONSTRAINT u_consoles_ext_key unique using index u_consoles_ext_key;
alter table achievements_hunt.consoles owner to achievements_hunt_bot;