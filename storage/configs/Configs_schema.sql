CREATE TABLE "acronyms" (
    member_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    acronyms TEXT NOT NULL DEFAULT '{}',

    PRIMARY KEY (member_id, guild_id),

    FOREIGN KEY (member_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE `application_groups` (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `guild_id` INTEGER REFERENCES `data`(`guild_id`), `name` TEXT, `description` TEXT);

CREATE TABLE `application_question` (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `guild_id` INTEGER REFERENCES `data`(`guild_id`), `question` TEXT, `question_type` TEXT, `metadata` TEXT);

CREATE TABLE "botlogs" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    guild_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,

    timestamp TEXT,
    log TEXT,

    FOREIGN KEY (guild_id)
        REFERENCES data(guild_id),

    FOREIGN KEY (member_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE "data" (`guild_id` INTEGER PRIMARY KEY UNIQUE, prefix TEXT);

CREATE TABLE "globals" (`key` TEXT, `value` TEXT);

CREATE TABLE "guild_channels" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER REFERENCES data(guild_id),
    channel_type TEXT,
    channel_id INTEGER,
    UNIQUE(guild_id, channel_type, channel_id)
);

CREATE TABLE guild_connections (
                primary_guild_id INTEGER REFERENCES data(guild_id) ON DELETE CASCADE,
                secondary_guild_id INTEGER REFERENCES data(guild_id) ON DELETE CASCADE,

                PRIMARY KEY (primary_guild_id, secondary_guild_id),

                CHECK (primary_guild_id != secondary_guild_id)
            );

CREATE TABLE `guild_webhooks` (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `guild_id` INTEGER REFERENCES `data`(`guild_id`), `channel_type` TEXT, `webhook_url` TEXT);

CREATE TABLE "leaves" (
    leave_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id   INTEGER NOT NULL,
    guild_id   INTEGER NOT NULL,
    reason     TEXT,
    days       INTEGER,
    issued_by  INTEGER, `started_on` TEXT, `ended_on` TEXT,

    -- FIX 3a: was FOREIGN KEY (staff_id) REFERENCES staffs(staff_id)
    --         staffs PK is (staff_id, guild_id); single-col FK is unenforced
    FOREIGN KEY (staff_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    -- FIX 3b: was FOREIGN KEY (issued_by) REFERENCES staffs(staff_id)
    --         same root cause; issued_by is also a staff_id in the same guild
    FOREIGN KEY (issued_by, guild_id)
        REFERENCES staffs(staff_id, guild_id)
);

CREATE TABLE "leaves_pending" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER,
    guild_id INTEGER,
    message_id INTEGER,
    reason TEXT,
    days TEXT,

    FOREIGN KEY (staff_id, guild_id)
        REFERENCES staffs(staff_id, guild_id)
);

CREATE TABLE "members" (
    member_id INTEGER,
    guild_id INTEGER, avatar_url TEXT, `name` TEXT, `timezone` TEXT, `prefix` TEXT,
    PRIMARY KEY (member_id, guild_id),
    FOREIGN KEY (guild_id) REFERENCES data(guild_id)
);

CREATE TABLE "messages" (
    "member_id"        INTEGER NOT NULL,
    guild_id        INTEGER NOT NULL,
    daily_messages  INTEGER DEFAULT 0,
    weekly_messages INTEGER DEFAULT 0,
    monthly_messages INTEGER DEFAULT 0,
    total_messages  INTEGER DEFAULT 0,

    PRIMARY KEY ("member_id", guild_id),

    FOREIGN KEY ("member_id", guild_id)
        REFERENCES members(member_id, guild_id),

    FOREIGN KEY (guild_id)
        REFERENCES data(guild_id)
);

CREATE TABLE "mod_logs_queue" (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL
                       REFERENCES data(guild_id),
    moderator_id   INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    mod_type       TEXT,
    reason         TEXT,
    timestamp      TEXT,
    message_source TEXT,

    FOREIGN KEY (moderator_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    FOREIGN KEY (target_user_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE "modlogs" (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL
                       REFERENCES data(guild_id),
    moderator_id   INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    mod_type       TEXT,
    reason         TEXT,
    timestamp      TEXT, `deleted` INTEGER,

    FOREIGN KEY (moderator_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    FOREIGN KEY (target_user_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE "permissions" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER REFERENCES data(guild_id),
    role_id INTEGER,
    command TEXT,
    UNIQUE(guild_id, role_id, command)
);

CREATE TABLE "proofs" (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         INTEGER NOT NULL
                        REFERENCES modlogs(id),
    proof_reference INTEGER,
    author          INTEGER NOT NULL,
    guild_id        INTEGER NOT NULL,

    FOREIGN KEY (author, guild_id)
        REFERENCES staffs(staff_id, guild_id)
);

CREATE TABLE "rank_updates" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    staff_id    INTEGER NOT NULL,
    updated_by  INTEGER NOT NULL,
    old_role_id INTEGER,
    new_role_id INTEGER,
    update_type TEXT CHECK(update_type IN ('promotion', 'demotion')),
    reason      TEXT,
    timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (guild_id)
        REFERENCES data(guild_id),

    FOREIGN KEY (staff_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    -- FIX 4: column order must match referenced PK staffs(staff_id, guild_id)
    --        was FOREIGN KEY (updated_by, guild_id) REFERENCES staffs(staff_id, guild_id)
    --        which is semantically correct but the local column order was ambiguous;
    --        made explicit here for clarity and SQLite compliance.
    FOREIGN KEY (updated_by, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    FOREIGN KEY (guild_id, old_role_id)
        REFERENCES roles(guild_id, role_id),

    FOREIGN KEY (guild_id, new_role_id)
        REFERENCES roles(guild_id, role_id)
);

CREATE TABLE "role_assignments" (
    guild_id INTEGER,
    role_id INTEGER,
    target_role_id INTEGER,

    PRIMARY KEY (guild_id, role_id, target_role_id),

    FOREIGN KEY (guild_id, role_id)
        REFERENCES roles(guild_id, role_id)
        ON DELETE CASCADE
);

CREATE TABLE "roles" (
    guild_id INTEGER REFERENCES data(guild_id),
    role_id INTEGER, `role_name` TEXT,
    ban_limit INTEGER,
    ban_queue INTEGER,
    assignment_scope TEXT CHECK(assignment_scope IN ('all', 'specific', 'except', 'none')),
    role_type TEXT,

    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE roles_customize (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,

                UNIQUE (member_id, guild_id, role_id),

                FOREIGN KEY (member_id, guild_id)
                    REFERENCES members(member_id, guild_id)
            );

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE "staff_quota" (
    quota_id INTEGER PRIMARY KEY AUTOINCREMENT,

    guild_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,

    min_msg INTEGER,
    min_ms INTEGER,

    on_quota_passed TEXT,
    on_quota_failed TEXT,
    check_by TEXT,

    FOREIGN KEY (guild_id)
        REFERENCES data(guild_id),

    FOREIGN KEY (guild_id, role_id)
        REFERENCES roles(guild_id, role_id)
);

CREATE TABLE "staff_ranks" (
    role_id INTEGER,
    guild_id INTEGER,
    priority INTEGER,
    PRIMARY KEY (guild_id, role_id),
    FOREIGN KEY (guild_id) REFERENCES data(guild_id),
    FOREIGN KEY (guild_id, role_id) REFERENCES roles(guild_id, role_id)
);

CREATE TABLE "staff_roles" (
    staff_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    role_id  INTEGER NOT NULL,

    PRIMARY KEY (staff_id, guild_id, role_id),

    FOREIGN KEY (staff_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    -- FIX 2: was FOREIGN KEY (role_id) REFERENCES roles(role_id)
    --        must be composite to match roles UNIQUE(guild_id, role_id)
    FOREIGN KEY (guild_id, role_id)
        REFERENCES roles(guild_id, role_id)
);

CREATE TABLE "staffs" (
    staff_id        INTEGER NOT NULL,
    guild_id        INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    joined_on       TEXT,
    on_loa          INTEGER DEFAULT 0,
    retired         INTEGER DEFAULT 0,
    timezone        TEXT,
    responsibility  TEXT,
    avatar_url      TEXT,

    PRIMARY KEY (staff_id, guild_id),

    FOREIGN KEY (staff_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE "strikes" (
    strike_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    issued_by_id INTEGER NOT NULL,
    issued_to_id INTEGER NOT NULL,
    reason      TEXT,
    date        TEXT, `expiry_date` TEXT, `type` TEXT,

    FOREIGN KEY (issued_by_id, guild_id)
        REFERENCES staffs(staff_id, guild_id),

    FOREIGN KEY (issued_to_id, guild_id)
        REFERENCES staffs(staff_id, guild_id)
);

CREATE TABLE "ticket_logs" (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,

    guild_id             INTEGER NOT NULL
                             REFERENCES data(guild_id),

    opened_user_id       INTEGER NOT NULL,
    staff_handled        INTEGER,

    reason               TEXT,
    ticket_type          TEXT,
    timestamp            TEXT,
    transcripts_reference INTEGER,

    FOREIGN KEY (opened_user_id, guild_id)
        REFERENCES members(member_id, guild_id),

    FOREIGN KEY (staff_handled, guild_id)
        REFERENCES staffs(staff_id, guild_id)
);

CREATE TABLE "ticket_views" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    guild_id INTEGER NOT NULL REFERENCES data(guild_id),
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    config_json TEXT NOT NULL,

    UNIQUE(guild_id, channel_id, message_id)
);

CREATE TABLE "tickets" (
    ticket_id INTEGER PRIMARY KEY,

    guild_id INTEGER NOT NULL
        REFERENCES data(guild_id),

    opened_user_id INTEGER NOT NULL,
    claimer_user_id INTEGER,

    submission_json TEXT,
    ticket_type TEXT,

    log_channel_id INTEGER,
    message_id INTEGER,

    FOREIGN KEY (opened_user_id, guild_id)
        REFERENCES members(member_id, guild_id),

    FOREIGN KEY (claimer_user_id, guild_id)
        REFERENCES members(member_id, guild_id)
);

CREATE TABLE "updates" (`next_day_update` TEXT, `next_week_update` TEXT, `next_month_update` TEXT, next_day_quota_update TEXT, next_week_quota_update TEXT, next_month_quota_update TEXT);

