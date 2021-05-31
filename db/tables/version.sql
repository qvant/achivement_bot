create table achievements_hunt.version
(
	v_name varchar(255),
	n_version integer,
	dt_update timestamp with time zone
);
alter table  achievements_hunt.version owner to achievements_hunt_bot;
insert into achievements_hunt.version(v_name, n_version, dt_update) values('Achievement hunt bot', 1, current_timestamp);
commit;