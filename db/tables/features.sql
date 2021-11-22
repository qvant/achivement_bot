create table achievements_hunt.features
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null
);
create unique index u_features_name on achievements_hunt.features(platform_id, name);
alter table  achievements_hunt.features ADD CONSTRAINT fk_features_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.features owner to achievements_hunt_bot;