import asyncio
import sys

import aiomysql

import ujson


async def migrate():
    _, host, user, password = sys.argv
    conn: aiomysql.Connection = await aiomysql.connect(host, user, password)
    cur: aiomysql.Cursor = await conn.cursor()

    with open('db.json', encoding="utf-8") as bd_file:
        bd = ujson.load(bd_file)

    ignore: list = bd['ignore']
    images = bd['images']
    current_chat = bd['current_chat']
    users: dict[str, dict] = bd['users']
    abstracts: dict[str, dict] = bd['abstracts']
    chat_id_my = bd['chat_id_my']
    chat_id_pen: list = bd['chat_id_pen']
    chat_msg_my = bd['chat_msg_my']
    chat_msg_pen = bd['chat_msg_pen']
    current_users = bd['current_users']

    await cur.execute("""DROP
DATABASE IF EXISTS `kozlo_db`;

CREATE
DATABASE `kozlo_db`;

USE
`kozlo_db`;

CREATE TABLE `users`
(
    `id`          BIGINT   NOT NULL,
    `name`        TINYTEXT NOT NULL,
    `desc`        VARCHAR(255) NULL,
    `photo_id`    TINYTEXT NULL,
    `is_private`  TINYINT  NOT NULL,
    `coord`       POINT NULL,
    `birth_day`   TINYINT NULL,
    `birth_month` TINYINT NULL,
    `balance`     VARBINARY(64) NOT NULL DEFAULT 1000,
    `log_msg`     TINYINT  NOT NULL DEFAULT 1,
    `only_chess`  TINYINT  NOT NULL DEFAULT 0,
    `is_greeted`  TINYINT  NOT NULL DEFAULT 0,
    `state`       TINYINT  NOT NULL DEFAULT -1,
    `state_data`  JSON NULL,
    UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
    PRIMARY KEY (`id`)
);

CREATE TABLE `books`
(
    `grade`      TINYINT      NOT NULL,
    `subject`    TINYTEXT     NOT NULL,
    `name`       TINYTEXT     NOT NULL,
    `author`     TINYTEXT     NOT NULL,
    `time`       INT UNSIGNED NOT NULL,
    `data_doc`   JSON NULL,
    `data_photo` JSON NULL,
    `data_url`   VARCHAR(500) NULL
);

CREATE TABLE `chess`
(
    `id`           INT    NOT NULL AUTO_INCREMENT,
    `player_white` BIGINT NOT NULL,
    `player_black` BIGINT NOT NULL,
    `fen`          VARCHAR(90) NULL,
    `status`       BIGINT NOT NULL DEFAULT 0,
    UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
    PRIMARY KEY (`id`, `player_white`, `player_black`)
);

create table chats
(
    initiator      bigint not null primary key,
    target         bigint not null,
    `current_user` bigint null,
    index (target),

    foreign key (initiator) references users (id) on delete cascade,
    foreign key (target) references users (id) on delete cascade
);

create table chat_msgs
(
    chat_id          bigint not null,
    initiator_msg_id int    not null,
    target_msg_id    int    not null,
    index (chat_id),

    foreign key (chat_id) references chats (initiator) on delete cascade
);

    """)
# create table ai_talk_msgs
# (
#     msg_id    int    not null AUTO_INCREMENT PRIMARY KEY,
#     chat_id   bigint not null,
#     from_user bool   not null,
#     content   text   not null,
#
#     UNIQUE INDEX ai_msg_id_UNIQUE (msg_id ASC) VISIBLE,
#     UNIQUE INDEX ai_talk_msgs_UNIQUE (chat_id ASC) VISIBLE,
#     foreign key (chat_id) references users (id) on delete cascade
# );
# create table images
# (
#     orig_id   CHAR(100) not null PRIMARY KEY,
#     resent_id CHAR(100) not null,
#
#     UNIQUE INDEX orig_id_UNIQUE (orig_id ASC) VISIBLE
# );
    for grade in abstracts:
        for subject in abstracts[grade]:
            for b in abstracts[grade][subject]:
                await cur.execute(
                    "INSERT INTO `books` (`grade`, `subject`, `name`, `author`, `time`, `data_doc`, `data_photo`, `data_url`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                    (grade, subject, b['n'], b['a'], b['t'],
                     ujson.dumps(b['id']['d']), ujson.dumps(b['id']['p']), b['id']['u']))
    for uid in users:
        u = users[uid]

        if 'birthday' in u:
            day, month = map(int, u.get('birthday').split('/'))
        else:
            day = month = None
        if 'talk' in u:
            state = 2
            data = {'reply': False, 'model': 0, 'messages': [{
                "role": "user" if index % 2 == 0 else "assistant",
                "content": msg
            } for index, msg in enumerate(u['talk'])]}
            state_data = ujson.dumps(data, ensure_ascii=False)
        else:
            state = -1
            state_data = None
        if u['desc'] == '':
            u['desc'] = None
        await cur.execute(
            "INSERT INTO `users` (`id`, `name`, `desc`, `photo_id`, `is_private`, `coord`,"
            "`birth_day`, `birth_month`, `balance`, `log_msg`, `state`, `state_data`) "
            "VALUES (%s, %s, %s, %s, %s, Point(%s, %s), %s, %s, %s, %s, %s, %s);",
            (int(uid), u['name'], u['desc'], u['photo_id'], u['private'], u.get('lat'), u.get('lon'),
             day, month, u['balance'], uid not in ignore, state, state_data))
    # for orig in images:
    #     await cur.execute(
    #         "INSERT INTO `images` (orig_id, resent_id) VALUES (%s, %s);", (orig, images[orig]))

    await conn.commit()


asyncio.run(migrate())
