create table achievements_hunt.users
(
    id 			    serial primary key,
    telegram_id     integer not null,
    dt_created      timestamp with time zone default current_timestamp,
    dt_last_update  timestamp with time zone,
    locale          varchar(32)
);
create unique index u_users_telegram_id on achievements_hunt.users(telegram_id);
alter table  achievements_hunt.users owner to achievements_hunt_bot;