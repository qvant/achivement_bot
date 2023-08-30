create table achievements_hunt.processes
(
    id 			    integer primary key,
    name		    varchar(255) not null
);
alter table achievements_hunt.processes owner to achievements_hunt_bot;
insert into achievements_hunt.processes(id, name) values (1, 'updater');
insert into achievements_hunt.processes(id, name) values (2, 'game_updater');

alter table achievements_hunt.update_history add id_process      integer default 1 not null;

update achievements_hunt.version set n_version=7, dt_update=current_timestamp  where v_name = 'Achievement hunt bot';
commit;