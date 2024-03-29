create table achievements_hunt.update_history
(
    id 			    serial primary key,
    dt_started      timestamp with time zone default current_timestamp,
    dt_ended        timestamp with time zone,
    dt_next_update  timestamp with time zone,
    id_platform     integer not null,
    id_process      integer default 1 not null
);
create index idx_update_history_dt_next_update on achievements_hunt.update_history(id_platform, dt_next_update, dt_ended);
create index idx_update_history_active on achievements_hunt.update_history(id_platform, id_process, ) where dt_ended is null;
alter table  achievements_hunt.update_history owner to achievements_hunt_bot;