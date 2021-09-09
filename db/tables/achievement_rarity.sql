create table  achievements_hunt.achievement_rarity
(
	id 			    serial primary key,
	name            varchar(1024) not null,
	color_code      varchar(255) not null,
	n_bottom_border real,
	n_upper_border  real
);
alter table achievements_hunt.achievement_rarity owner to achievements_hunt_bot;

create unique index u_achievement_rarity_name_key on achievements_hunt.achievement_rarity(name);

insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Common', 'White', 50, 100);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Uncommon', '#0BDA51', 20, 50);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Rare', '#63b5cf', 10, 20);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Epic', '#800080', 5, 10);
insert into achievements_hunt.achievement_rarity (name, color_code, n_bottom_border, n_upper_border)
values ('Legendary', '##FFA500', -1, 5);
