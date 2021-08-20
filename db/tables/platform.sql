create table achievements_hunt.platforms
(
	id      serial primary key,
	name    varchar(255) not null
);
alter table  achievements_hunt.platforms owner to achievements_hunt_bot;

insert into achievements_hunt.platforms(id, name) values(1, 'Steam');
insert into achievements_hunt.platforms(id, name) values(2, 'Retroachievements');
insert into achievements_hunt.platforms(id, name) values(3, 'GOG');