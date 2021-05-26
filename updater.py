import json

import psycopg2

from lib.config import Config, MODE_BOT
from lib.log import get_logger
from lib.platform import Platform
from lib.queue import set_config as set_queue_config, set_logger as set_queue_log, get_mq_connect, UPDATER_QUEUE_NAME, \
    enqueue_command
from lib.stats import get_stats
from lib.telegram import set_logger
from lib.db import load, set_load_logger


def main_updater(config: Config):
    queue_log = get_logger("Rabbit_updater", config.log_level, True)

    set_load_logger(config)
    set_logger(config)
    set_queue_config(config)
    set_queue_log(queue_log)

    Platform.set_config(config)
    platforms = load(config, load_games=False)
    connect = Platform.get_connect()

    m_queue = get_mq_connect(config)
    m_channel = m_queue.channel()
    m_channel.queue_declare(queue=UPDATER_QUEUE_NAME, durable=True)
    m_channel.exchange_declare(exchange='main',
                               exchange_type='direct')
    m_channel.queue_bind(exchange='main',
                         queue=UPDATER_QUEUE_NAME,
                         routing_key=config.mode)

    is_running = True

    while is_running:

        try:
            cursor = connect.cursor()
            # Process new games queue - recalc owner numbers and percent of achievers
            cursor.execute("""
            select id, game_id, operation 
            from achievements_hunt.queue_games_update 
            order by game_id 
            for update skip locked 
            fetch first 1000 rows only
            """)
            games = {}
            recs = []
            for id_rec, game_id, operation in cursor:
                if game_id not in games:
                    games[game_id] = 0
                if operation == "INSERT":
                    games[game_id] += 1
                else:
                    games[game_id] -= 1
                recs.append((id_rec, ))
            if len(games) > 0:
                cursor.execute("""
                        PREPARE upd_games as 
                        update achievements_hunt.games set num_owners = num_owners + $1 where id = $2 
                        """)
                game_res = []
                game_4_ach = []
                for i in games:
                    game_res.append((games[i], i))
                    game_4_ach.append((i, ))

                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_games (%s, %s)""", game_res)
                cursor.execute("""
                PREPARE del_q as delete from achievements_hunt.queue_games_update where id = $1
                """)
                cursor.execute("""PREPARE upd_achievement as 
                                update achievements_hunt.achievements as a 
                                    set percent_owners = 
                                    case when num_owners > 0 then 
                                        round(a.num_owners * 100 / 
                                        greatest(1, (select g.num_owners 
                                                        from achievements_hunt.games as g 
                                                        where g.id = a.game_id
                                                            and g.platform_id = a.platform_id)), 2)
                                    else 0
                                    end
                                where a.game_id = $1
                                """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement (%s)""", game_4_ach)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
                cursor.execute("""DEALLOCATE  upd_games""")
                cursor.execute("""DEALLOCATE  del_q""")
                cursor.execute("""DEALLOCATE  upd_achievement""")
            connect.commit()

            # Process new achievements queue - reset perfect games and recalc % complete for all players
            cursor.execute("""
                                select id, game_id, platform_id 
                                from achievements_hunt.queue_achievements_update 
                                order by achievement_id 
                                for update skip locked 
                                fetch first 1000 rows only
                                """)
            recs = []
            games = []
            games_ids = []
            for id_rec, game_id, platform_id in cursor:
                if game_id not in games_ids:
                    games_ids.append(game_id)
                    games.append((game_id, platform_id))
                recs.append((id_rec,))
            if len(games) > 0:

                cursor.execute("""
                                                        PREPARE update_player_games as 
                                                        update achievements_hunt.player_games pg set percent_complete =
                                                        round(
                                                        (select count(1) from achievements_hunt.player_achievements a
                                                         where a.platform_id = pg.platform_id
                                                         and a.game_id = pg.game_id
                                                         and a.player_id = pg.player_id) * 100 /
                                                        (select count(1) from  achievements_hunt.achievements ac
                                                        where ac.platform_id = pg.platform_id
                                                        and ac.game_id = pg.game_id)  , 2)
                                                         where pg.game_id = $1
                                                         and pg.platform_id = $2
                                                        """)
                cursor.execute("""
                                                        PREPARE update_player_games_perf as 
                                                        update achievements_hunt.player_games pg 
                                                        set is_perfect = (percent_complete = 100)
                                                        where pg.game_id = $1 and pg.platform_id = $2
                                                        """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games  (%s, %s)""", games)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games_perf  (%s, %s)""", games)

                cursor.execute("""
                                PREPARE del_q as delete from achievements_hunt.queue_achievements_update where id = $1
                                """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)

                cursor.execute("""DEALLOCATE  update_player_games""")
                cursor.execute("""DEALLOCATE  update_player_games_perf""")
                cursor.execute("""DEALLOCATE  del_q""")
            connect.commit()

            # Process player achievements queue, renew percent of achievers and update player perfect games status
            cursor.execute("""
                    select id, achievement_id, player_id, game_id, platform_id, operation 
                    from achievements_hunt.queue_player_achievements_update 
                    order by achievement_id 
                    for update skip locked 
                    fetch first 1000 rows only
                    """)
            achievements = {}
            recs = []
            player_games = []
            for id_rec, achievement_id, player_id, game_id, platform_id, operation in cursor:
                if achievement_id not in achievements:
                    achievements[achievement_id] = 0
                if operation == "INSERT":
                    achievements[achievement_id] += 1
                else:
                    achievements[achievement_id] -= 1
                recs.append((id_rec,))
                player_games.append((player_id, game_id, platform_id))
            if len(player_games) > 0:
                cursor.execute("""
                                PREPARE upd_achievements as update achievements_hunt.achievements 
                                set num_owners = num_owners + $1 where id = $2 
                                """)
                game_res = []
                game_4_ach = []
                for i in achievements:
                    game_res.append((achievements[i], i))
                    game_4_ach.append((i,))

                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievements (%s, %s)""", game_res)

                cursor.execute("""PREPARE upd_achievement_percent as 
                                        update achievements_hunt.achievements as a set percent_owners = 
                                            case when num_owners > 0 then 
                                                round(a.num_owners * 100 / 
                                                greatest((select g.num_owners from achievements_hunt.games as g 
                                                            where g.id = a.game_id
                                                            and g.platform_id = a.platform_id), 1), 2)
                                            else 0
                                            end
                                        where a.id = $1
                                        """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE upd_achievement_percent (%s)""", game_4_ach)
                cursor.execute("""
                                            PREPARE update_player_games as 
                                            update achievements_hunt.player_games pg set percent_complete =
                                            round(
                                            (select count(1) from achievements_hunt.player_achievements a
                                             where a.platform_id = pg.platform_id
                                             and a.game_id = pg.game_id
                                             and a.player_id = pg.player_id) * 100 /
                                            (select count(1) from achievements_hunt.achievements ac
                                            where ac.platform_id = pg.platform_id
                                            and ac.game_id = pg.game_id), 2) 
                                             where pg.player_id = $1 and pg.game_id = $2
                                             and pg.platform_id = $3 
                                            """)
                cursor.execute("""
                                            PREPARE update_player_games_perf as 
                                            update achievements_hunt.player_games pg 
                                            set is_perfect = (percent_complete = 100)
                                            where pg.player_id = $1 and pg.game_id = $2 and pg.platform_id = $3
                                            """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games (%s, %s, %s)""", player_games)
                psycopg2.extras.execute_batch(cursor, """EXECUTE update_player_games_perf (%s, %s, %s)""", player_games)

                cursor.execute("""
                                PREPARE del_q as 
                                delete from achievements_hunt.queue_player_achievements_update 
                                where id = $1
                                """)
                psycopg2.extras.execute_batch(cursor, """EXECUTE del_q (%s)""", recs)
                cursor.execute("""DEALLOCATE  update_player_games""")
                cursor.execute("""DEALLOCATE  update_player_games_perf""")
                cursor.execute("""DEALLOCATE  upd_achievements""")
                cursor.execute("""DEALLOCATE  del_q""")
                cursor.execute("""DEALLOCATE  upd_achievement_percent""")
            connect.commit()

            for method_frame, properties, body in m_channel.consume(UPDATER_QUEUE_NAME, inactivity_timeout=5,
                                                                    auto_ack=False,
                                                                    arguments={"routing_key": config.mode}):
                if body is not None:
                    queue_log.info("Received user message {0} with delivery_tag {1}".format(body,
                                                                                            method_frame.delivery_tag))
                    cmd = json.loads(body)
                    cmd_type = cmd.get("cmd")
                    if cmd_type == 'stop_server':
                        is_running = False
                        cmd = {"cmd": "process_response", "text": "Updater shutdown started"}
                        enqueue_command(cmd, MODE_BOT)
                    elif cmd_type == "get_stats":
                        msg = get_stats()
                        msg["module"] = "Updater"
                        cmd = {"cmd": "process_response", "text": str(msg)}
                        enqueue_command(cmd, MODE_BOT)
                    m_channel.basic_ack(method_frame.delivery_tag)
                    queue_log.info("User message " + str(body) + " with delivery_tag " +
                                   str(method_frame.delivery_tag) + " acknowledged")
                else:
                    queue_log.info("No more messages in {0}".format(UPDATER_QUEUE_NAME))
                    m_channel.cancel()
                    break
        except BaseException as err:
            queue_log.critical(err)
            if config.supress_errors:
                pass
            else:
                raise
