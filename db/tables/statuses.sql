create table achievements_hunt.statuses
(
    id 			integer primary key,
    name        varchar(32)
);
create unique index u_statuses_name on achievements_hunt.statuses(name);
alter table  achievements_hunt.statuses owner to achievements_hunt_bot;
insert into achievements_hunt.statuses(id, name) values (1, 'New');
insert into achievements_hunt.statuses(id, name) values (2, 'Valid');