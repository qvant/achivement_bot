create trigger trg_on_player_games_zbu before
  update on achievements_hunt.player_games
  for each row execute procedure suppress_redundant_updates_trigger();