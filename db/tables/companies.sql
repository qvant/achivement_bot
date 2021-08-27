create table achievements_hunt.companies
(
	id 			        serial primary key,
	platform_id         integer not null,
	name		        varchar(1024) not null
);
create unique index u_companies_name on achievements_hunt.companies(platform_id, name);
alter table  achievements_hunt.companies ADD CONSTRAINT fk_companies_to_platforms foreign key (platform_id) references  achievements_hunt.platforms(id);
alter table achievements_hunt.companies owner to achievements_hunt_bot;