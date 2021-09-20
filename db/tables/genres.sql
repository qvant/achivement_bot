create table achievements_hunt.genres
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null
);
create unique index u_genres_name on achievements_hunt.genres(platform_id, name);
alter table  achievements_hunt.genres ADD CONSTRAINT fk_genres_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.genres owner to achievements_hunt_bot;